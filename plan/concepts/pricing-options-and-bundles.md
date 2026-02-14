# Pricing Options & Service Bundles

> **Status: DRAFT — Needs refinement before implementation.**
>
> This concept was designed during planning but paused when we identified that
> **Pricing Options are actually Service Options** — not merely pricing modifiers
> but configurable service variants that have pricing implications. The scope is
> broader than originally drafted, and the model design needs rethinking before
> any code is written.

---

## Open Design Questions

1. **Where should options live?** The draft attaches options to `PriceListItem`
   (pricing-centric). But if options are service-level concepts ("24/7 Coverage",
   "Express SLA"), they may need to be defined on `ServiceOffering` first, then
   priced per `PriceListItem`. This is the key unresolved question.

2. **Consumption-time selection.** Options should be selectable at consumption
   time — the caller passes `selected_option_ids` to `get_effective_price`. This
   means the API and UI must support "pick your options" inline, not just
   "options are always applied."

3. **UI placement.** Options should be managed inline (not a separate page).
   But if options are service-level, the definition UI belongs on the offering
   editor, while the pricing UI belongs on the price list item editor.

4. **Bundles may be independently implementable.** The bundle pattern is more
   self-contained and doesn't have the same identity question. It could ship
   before options are fully refined.

---

## Pattern 1: Base + Option Markups

**Example:** Standard Change = 120 CHF/hr, +30% for 24/7 = 156 CHF/hr.

Currently, `PriceListItem` stores absolute prices per `coverage_model`. If the
base goes from 120 to 130, you'd have to manually update the 24/7 line too.
The goal is derived pricing — define the markup rule once, and the effective
price is always calculated.

| Concept | How it works |
|---------|-------------|
| PricingOption | Reusable option definition (e.g., "24/7 Coverage", "Weekend Support", "Express SLA") |
| PriceListItemOption | Attaches an option to a price list item with a modifier: percentage (+30%) or fixed (+50 CHF) |
| Effective price | `base_price * (1 + sum_percentage_modifiers / 100) + sum_fixed_modifiers` |

So a "Standard Change" `PriceListItem` at 120 CHF would have:
- Option "24/7" -> +30% -> effective = 156 CHF
- Option "24/7" + "Express" (+15%) -> effective = 120 * 1.45 = 174 CHF

The base price changes -> all derived prices follow automatically.

---

## Pattern 2: Flat-Rate Bundles / Packages

**Example:** "Monitoring Package" at 2,000 CHF/month — includes Alerting,
Dashboards, Log Ingestion at zero cost. Optional add-on: "Custom Integrations"
at 200 CHF/month.

| Concept | How it works |
|---------|-------------|
| ServiceBundle | Named package with a flat rate (e.g., "Monitoring Package", 2000 CHF/month) |
| ServiceBundleItem | Links offerings to a bundle as **included** (-> $0) or **addon** (-> specific price) |
| Effective price | Included items: 0. Add-ons: their addon price. The bundle itself: its flat rate. |

When a tenant subscribes to a bundle, the pricing engine would:
1. Charge the bundle's flat rate
2. Zero out included items
3. Charge add-ons at their bundle-specific rates (not the normal catalog price)

---

## Draft Database Schema

> These schemas reflect the original pricing-centric design. The `pricing_options`
> table may need to be restructured as `service_options` on `ServiceOffering`
> once the design is refined.

### Table: `pricing_options`

Reusable option definitions (system or tenant-scoped).

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `UUID` | PK, default uuid4 | Via IDMixin |
| `tenant_id` | `UUID` | FK -> tenants.id, nullable, indexed | Null = system-level option |
| `name` | `String(255)` | NOT NULL | Internal key, e.g., "24x7_coverage" |
| `display_name` | `String(255)` | NOT NULL | UI label, e.g., "24/7 Coverage" |
| `description` | `Text` | nullable | |
| `category` | `String(100)` | nullable | Group options in UI, e.g., "SLA", "Support" |
| `is_system` | `Boolean` | NOT NULL, default false | Protect system options from tenant deletion |
| `is_active` | `Boolean` | NOT NULL, default true | Soft toggle |
| `sort_order` | `Integer` | NOT NULL, default 0 | |
| `created_at` | `DateTime(tz)` | NOT NULL | Via TimestampMixin |
| `updated_at` | `DateTime(tz)` | NOT NULL | Via TimestampMixin |
| `deleted_at` | `DateTime(tz)` | nullable | Via SoftDeleteMixin |

### Table: `price_list_item_options`

Attaches a pricing option (with modifier) to a price list item.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `UUID` | PK | |
| `price_list_item_id` | `UUID` | FK -> price_list_items.id, NOT NULL | |
| `pricing_option_id` | `UUID` | FK -> pricing_options.id, NOT NULL | |
| `modifier_type` | `String(20)` | NOT NULL, default "percentage" | "percentage" or "fixed" |
| `modifier_value` | `Numeric(12,4)` | NOT NULL | 30.0 = +30% or +30 currency units |
| `sort_order` | `Integer` | NOT NULL, default 0 | |
| `created_at` | `DateTime(tz)` | NOT NULL | |
| `updated_at` | `DateTime(tz)` | NOT NULL | |
| `deleted_at` | `DateTime(tz)` | nullable | |

Unique constraint: `(price_list_item_id, pricing_option_id)` WHERE `deleted_at IS NULL`.

### Table: `service_bundles`

Named flat-rate package.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `UUID` | PK | |
| `tenant_id` | `UUID` | FK -> tenants.id, nullable, indexed | Null = system-level bundle |
| `name` | `String(255)` | NOT NULL | |
| `display_name` | `String(255)` | nullable | |
| `description` | `Text` | nullable | |
| `flat_rate` | `Numeric(12,4)` | NOT NULL | Monthly/annual flat price |
| `currency` | `String(3)` | NOT NULL, default "EUR" | |
| `measuring_unit` | `String(20)` | NOT NULL, default "month" | Period for flat_rate |
| `status` | `String(20)` | NOT NULL, default "draft" | draft / published / archived |
| `effective_from` | `Date` | nullable | |
| `effective_to` | `Date` | nullable | |
| `created_at` | `DateTime(tz)` | NOT NULL | |
| `updated_at` | `DateTime(tz)` | NOT NULL | |
| `deleted_at` | `DateTime(tz)` | nullable | |

### Table: `service_bundle_items`

Links offerings to a bundle with inclusion type.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `UUID` | PK | |
| `bundle_id` | `UUID` | FK -> service_bundles.id, NOT NULL | |
| `service_offering_id` | `UUID` | FK -> service_offerings.id, NOT NULL | |
| `inclusion_type` | `String(20)` | NOT NULL, default "included" | "included" or "addon" |
| `addon_price` | `Numeric(12,4)` | nullable | Only for "addon" items |
| `addon_currency` | `String(3)` | nullable | Only for "addon" items |
| `sort_order` | `Integer` | NOT NULL, default 0 | |
| `created_at` | `DateTime(tz)` | NOT NULL | |
| `updated_at` | `DateTime(tz)` | NOT NULL | |
| `deleted_at` | `DateTime(tz)` | nullable | |

Unique constraint: `(bundle_id, service_offering_id)` WHERE `deleted_at IS NULL`.

### Table: `tenant_bundle_pins`

Subscribes a tenant to a bundle.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `UUID` | PK | |
| `tenant_id` | `UUID` | FK -> tenants.id, NOT NULL | |
| `bundle_id` | `UUID` | FK -> service_bundles.id, NOT NULL | |
| `created_at` | `DateTime(tz)` | NOT NULL | |
| `updated_at` | `DateTime(tz)` | NOT NULL | |
| `deleted_at` | `DateTime(tz)` | nullable | |

Unique constraint: `(tenant_id, bundle_id)` WHERE `deleted_at IS NULL`.

---

## Draft Service Layer

### PricingOptionService (`pricing_option_service.py`)

| Method | Purpose |
|--------|---------|
| `list_options(tenant_id, category?, active_only?)` | List options visible to tenant (own + system) |
| `get_option(option_id)` | Get single option |
| `create_option(tenant_id, data)` | Create a pricing option |
| `update_option(option_id, data)` | Update (check not system if tenant-scoped) |
| `delete_option(option_id)` | Soft-delete (protect system options) |
| `list_item_options(price_list_item_id)` | Options attached to a price list item |
| `add_item_option(price_list_item_id, pricing_option_id, modifier_type, modifier_value, sort_order)` | Attach option to item |
| `update_item_option(item_option_id, data)` | Update modifier |
| `remove_item_option(item_option_id)` | Soft-delete link |
| `calculate_option_adjusted_price(base_price, item_options)` | Pure calc: `base * (1 + sum_%/100) + sum_fixed` |

### BundleService (`bundle_service.py`)

| Method | Purpose |
|--------|---------|
| `list_bundles(tenant_id, status?, offset?, limit?)` | List bundles visible to tenant |
| `get_bundle(bundle_id, tenant_id?)` | Get bundle with items |
| `create_bundle(tenant_id, data)` | Create bundle |
| `update_bundle(bundle_id, data)` | Update (draft only) |
| `delete_bundle(bundle_id)` | Soft-delete |
| `publish_bundle(bundle_id)` | Draft -> published |
| `archive_bundle(bundle_id)` | Published -> archived |
| `add_bundle_item(bundle_id, offering_id, inclusion_type, addon_price?, addon_currency?, sort_order?)` | Add offering |
| `update_bundle_item(item_id, data)` | Update item |
| `remove_bundle_item(item_id)` | Soft-delete item |
| `pin_tenant_to_bundle(tenant_id, bundle_id)` | Subscribe tenant |
| `unpin_tenant_from_bundle(tenant_id, bundle_id)` | Unsubscribe tenant |
| `get_tenant_bundle_pins(tenant_id)` | List tenant's active bundles |
| `get_active_bundle_for_offering(tenant_id, offering_id, as_of?)` | Check if tenant has active bundle containing this offering |

### Pricing Engine Integration (`catalog_service.py`)

**Options:** After resolving the base price through the cascade, check if the
matched `PriceListItem` has attached `PriceListItemOption` records. Compute
adjusted price and return `options_applied` list.

**Bundles:** Insert a new **Tier 1.5** check between overrides (Tier 1) and
pinned client lists (Tier 2):

```
TIER 1:   Tenant Overrides (1a-1d specificity) — UNCHANGED
TIER 1.5: Active Bundle Check — NEW
           -> tenant_bundle_pins WHERE tenant_id AND deleted_at IS NULL
           -> service_bundles WHERE status='published' AND effective dates valid
           -> service_bundle_items WHERE service_offering_id = target
           -> inclusion_type='included': price=0, source_type='bundle'
           -> inclusion_type='addon': price=addon_price, source_type='bundle_addon'
           -> Not found: fall through
TIER 2-4: Price List Items (2a-4d) — UNCHANGED
           -> After resolving, apply option modifiers if present
```

**Backward compatibility:** Options are additive. Existing `coverage_model`
semantics are preserved. Existing calculations produce identical results when
no options/bundles exist.

**Price list copy:** `copy_price_list` and `create_price_list_version` must
also clone `PriceListItemOption` records.

---

## Draft GraphQL API

### Pricing Option Types

```python
@strawberry.type
class PricingOptionType:
    id: uuid.UUID
    tenant_id: uuid.UUID | None
    name: str
    display_name: str
    description: str | None
    category: str | None
    is_system: bool
    is_active: bool
    sort_order: int

@strawberry.type
class PriceListItemOptionType:
    id: uuid.UUID
    price_list_item_id: uuid.UUID
    pricing_option_id: uuid.UUID
    pricing_option: PricingOptionType | None
    modifier_type: str           # "percentage" or "fixed"
    modifier_value: Decimal
    sort_order: int

@strawberry.input
class PriceListItemOptionInput:
    pricing_option_id: uuid.UUID
    modifier_type: str = "percentage"
    modifier_value: Decimal
    sort_order: int = 0
```

### Bundle Types

```python
@strawberry.type
class ServiceBundleType:
    id: uuid.UUID
    tenant_id: uuid.UUID | None
    name: str
    display_name: str | None
    description: str | None
    flat_rate: Decimal
    currency: str
    measuring_unit: str
    status: str                  # draft / published / archived
    effective_from: date | None
    effective_to: date | None
    items: list[ServiceBundleItemType]

@strawberry.type
class ServiceBundleItemType:
    id: uuid.UUID
    service_offering_id: uuid.UUID
    inclusion_type: str          # "included" or "addon"
    addon_price: Decimal | None
    addon_currency: str | None

@strawberry.type
class TenantBundlePinType:
    id: uuid.UUID
    tenant_id: uuid.UUID
    bundle_id: uuid.UUID
    bundle: ServiceBundleType | None
```

### EffectivePrice Updates

```python
# Add to EffectivePriceType:
options_applied: list[EffectivePriceOptionType]  # [{option_name, modifier_type, modifier_value}]
bundle_id: str | None
bundle_name: str | None
```

### Queries

- `pricingOptions(tenantId, category?, activeOnly?) -> PricingOptionListType`
- `pricingOption(tenantId, id) -> PricingOptionType`
- `priceListItemOptions(tenantId, priceListItemId) -> [PriceListItemOptionType]`
- `serviceBundles(tenantId, status?) -> ServiceBundleListType`
- `serviceBundle(tenantId, id) -> ServiceBundleType`
- `tenantBundlePins(tenantId) -> [TenantBundlePinType]`

### Mutations

**Options:**
- `createPricingOption`, `updatePricingOption`, `deletePricingOption`
- `addItemOption`, `updateItemOption`, `removeItemOption`

**Bundles:**
- `createServiceBundle`, `updateServiceBundle`, `deleteServiceBundle`
- `publishServiceBundle`, `archiveServiceBundle`
- `addBundleItem`, `updateBundleItem`, `removeBundleItem`
- `pinTenantToBundle`, `unpinTenantFromBundle`

---

## Draft Frontend Design

### Components

**Pricing Options** — integrated into `pricing-config.component.ts`:
- Collapsible "Pricing Options" section at top (above price lists)
- Table listing all `PricingOption` records (tenant + system)
- Create/Edit inline (name, display_name, category, description)
- When expanding a price list item, an "Options" sub-section with:
  - Dropdown to select from available pricing options
  - Modifier type (percentage/fixed) and modifier value fields
  - Inline calculated effective price preview

**Service Bundles** — new route with own components:
- `bundle-list.component.ts` — List with name, flat_rate, status, item count,
  effective dates. Actions: create, publish, archive, delete.
- `bundle-detail.component.ts` — Editor with:
  - Header: name, display_name, description, flat_rate, currency, measuring_unit, dates
  - Items: table of linked offerings with inclusion_type toggle, addon_price field
  - Add offering picker (searchable select)
  - Tenant Pins: list of subscribed tenants with pin/unpin controls

**Routes:**
- `/catalog/bundles` -> `BundleListComponent` (guard: `catalog:bundle:read`)
- `/catalog/bundles/:id` -> `BundleDetailComponent` (guard: `catalog:bundle:read`)

**Sidebar:** Add "Bundles" under Catalog nav group after "Price Lists".

---

## Permissions

```
catalog:option:read    — View pricing options
catalog:option:manage  — Create/update/delete pricing options
catalog:bundle:read    — View service bundles
catalog:bundle:manage  — Create/update/delete service bundles
```

Assigned to `Tenant Admin` and `Provider Admin` roles.

---

## Design Decisions (from draft)

1. **Separate services** — Options and Bundles each get their own service file.
   CatalogService (1221 lines) stays focused on the pricing engine.

2. **Bundle cascade position (Tier 1.5)** — Bundles sit between overrides and
   price lists because they represent explicit commercial package agreements.

3. **Options attached to PriceListItems** — The same offering can have different
   option modifiers in different price lists. **However, this may change** — see
   Open Design Questions above.

4. **No circular dependency** — Options and Bundles are fully independent.

5. **Backward compatibility** — Existing `coverage_model` semantics are
   preserved. Options are additive.

---

## Implementation Outline (8 steps, not yet refined)

1. Migration + Models (backend)
2. Service Layer — Options (backend)
3. Service Layer — Bundles (backend)
4. Pricing Engine Integration (backend)
5. GraphQL Types + Queries + Mutations (backend)
6. Frontend Models + Service
7. Frontend — Options UI (inline in pricing-config)
8. Frontend — Bundles UI (new route + components)
