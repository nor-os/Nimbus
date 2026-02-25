/**
 * Overview: Full-page resolver editor — create/edit resolver definitions with Monaco code editor and schema builders.
 * Architecture: Feature component for resolver authoring (Section 11)
 * Dependencies: @angular/core, @angular/router, ComponentService, SemanticService, MonacoEditorComponent
 * Concepts: Full resolver editor with code, structured input/output/instance-config schema builders,
 *     provider compatibility. Follows same layout patterns as component-editor.
 */
import { Component, OnInit, inject, signal, computed, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { MonacoEditorComponent } from '@shared/components/monaco-editor/monaco-editor.component';
import { ComponentService } from '@core/services/component.service';
import { SemanticService } from '@core/services/semantic.service';
import { Resolver, ResolverDefinitionCreateInput, ResolverDefinitionUpdateInput } from '@shared/models/component.model';
import { ToastService } from '@shared/services/toast.service';

type ConfigTab = 'inputSchema' | 'outputSchema' | 'instanceConfig';

interface SchemaProperty {
  name: string;
  type: 'string' | 'integer' | 'number' | 'boolean' | 'object' | 'array';
  description: string;
  required: boolean;
  defaultValue: string;
  enumValues: string;
}

const EXAMPLE_RESOLVER_CODE = `"""
Example resolver handler implementation.
Resolvers pre-resolve parameters before deployment (e.g. IPAM, naming, DNS).
"""

from typing import Any


class ExampleResolver:
    """Base resolver interface.

    Implement resolve() to return computed values for component inputs.
    """

    async def resolve(self, context: dict[str, Any]) -> dict[str, Any]:
        """Resolve parameters for a deployment.

        Args:
            context: Contains environment, landing_zone, config, and request params.

        Returns:
            Dictionary of resolved values to inject into the component.
        """
        # Access instance config (per-environment settings)
        config = context.get("config", {})

        # Access request parameters
        params = context.get("params", {})

        # TODO: Implement resolution logic
        return {
            "resolved_value": "placeholder",
        }

    async def release(self, context: dict[str, Any]) -> None:
        """Release previously allocated resources (e.g. return IP to pool)."""
        pass

    async def validate(self, context: dict[str, Any]) -> list[str]:
        """Validate that resolution is possible. Return list of error messages."""
        return []
`;

@Component({
  selector: 'nimbus-resolver-editor',
  standalone: true,
  imports: [CommonModule, FormsModule, LayoutComponent, MonacoEditorComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <nimbus-layout>
      <div class="page-container">
        <!-- Header -->
        <div class="page-header">
          <button class="back-btn" (click)="router.navigate(['/provider/resolvers'])">&larr; Resolvers</button>
          <div class="header-main">
            <h1>{{ isNew() ? 'New Resolver' : resolver()?.displayName || 'Resolver' }}</h1>
            @if (resolver(); as r) {
              <div class="header-badges">
                @if (r.category) {
                  <span class="badge badge-category">{{ r.category }}</span>
                }
              </div>
            }
          </div>
          <div class="header-actions">
            <button class="btn btn-secondary" (click)="save()" [disabled]="saving()">
              {{ saving() ? 'Saving...' : 'Save Draft' }}
            </button>
            @if (!isNew() && resolver()) {
              <button class="btn btn-danger" (click)="confirmDelete()">Delete</button>
            }
          </div>
        </div>

        <!-- Form Fields -->
        <div class="form-section">
          <div class="form-row">
            <div class="form-group">
              <label>Resolver Type (slug)</label>
              <input type="text" [(ngModel)]="form.resolverType" placeholder="e.g. custom_dns"
                     [disabled]="!isNew()" />
            </div>
            <div class="form-group">
              <label>Display Name</label>
              <input type="text" [(ngModel)]="form.displayName" placeholder="e.g. DNS Resolver" />
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>Category</label>
              <select [(ngModel)]="form.category">
                <option value="">— Select —</option>
                @for (cat of categories; track cat.value) {
                  <option [value]="cat.value">{{ cat.label }}</option>
                }
              </select>
            </div>
            <div class="form-group">
              <label>Handler Class</label>
              <input type="text" [(ngModel)]="form.handlerClass"
                     placeholder="e.g. app.services.resolver.dns_resolver.DNSResolver"
                     [disabled]="!isNew()" />
            </div>
          </div>
          <div class="form-group" style="margin-bottom: 0.75rem;">
            <label>Description</label>
            <textarea [(ngModel)]="form.description" rows="2" placeholder="What this resolver does..."></textarea>
          </div>
          <div class="form-group" style="margin-bottom: 0;">
            <label>Compatible Providers</label>
            <div class="provider-chips">
              @for (p of providers(); track p.id) {
                <label class="chip-label">
                  <input type="checkbox"
                    [checked]="selectedProviderIds.has(p.id)"
                    (change)="toggleProvider(p.id)" />
                  {{ p.displayName || p.name }}
                </label>
              }
              @if (providers().length === 0) {
                <span class="muted">No providers available</span>
              }
            </div>
          </div>
        </div>

        <!-- Split Pane: Code + Config -->
        <div class="split-container">
          <div class="split-pane">
            <!-- Left: Monaco Editor -->
            <div class="editor-pane">
              <div class="pane-header">
                <span class="pane-title">Handler Code (Python)</span>
              </div>
              @if (editorVisible()) {
                <nimbus-monaco-editor
                  [value]="form.code"
                  [language]="'python'"
                  [height]="'calc(100vh - 440px)'"
                  (valueChange)="form.code = $event"
                />
              }
            </div>

            <!-- Right: Config Panel -->
            <div class="config-pane">
              <div class="config-tabs">
                <button class="config-tab" [class.active]="configTab() === 'inputSchema'" (click)="configTab.set('inputSchema')">Input Schema</button>
                <button class="config-tab" [class.active]="configTab() === 'outputSchema'" (click)="configTab.set('outputSchema')">Output Schema</button>
                <button class="config-tab" [class.active]="configTab() === 'instanceConfig'" (click)="configTab.set('instanceConfig')">Instance Config</button>
              </div>
              <div class="config-body">
                <!-- Input Schema -->
                @if (configTab() === 'inputSchema') {
                  <ng-container *ngTemplateOutlet="schemaBuilderTpl; context: { props: inputProperties, label: 'Input Parameters', addFn: addInputProperty, removeFn: removeInputProperty }"></ng-container>
                }

                <!-- Output Schema -->
                @if (configTab() === 'outputSchema') {
                  <ng-container *ngTemplateOutlet="schemaBuilderTpl; context: { props: outputProperties, label: 'Output Values', addFn: addOutputProperty, removeFn: removeOutputProperty }"></ng-container>
                }

                <!-- Instance Config -->
                @if (configTab() === 'instanceConfig') {
                  <ng-container *ngTemplateOutlet="schemaBuilderTpl; context: { props: instanceConfigProperties, label: 'Instance Config', addFn: addInstanceConfigProperty, removeFn: removeInstanceConfigProperty }"></ng-container>
                }

                <!-- Shared schema builder template -->
                <ng-template #schemaBuilderTpl let-props="props" let-label="label" let-addFn="addFn" let-removeFn="removeFn">
                  <div class="schema-builder">
                    <div class="schema-header">
                      <h3>{{ label }}</h3>
                      <button class="btn btn-sm" (click)="addFn()">+ Add</button>
                    </div>
                    @if (props().length === 0) {
                      <div class="empty-schema">No properties defined.</div>
                    }
                    @for (prop of props(); track prop.name; let i = $index) {
                      <div class="schema-row stacked">
                        <div class="schema-row-top">
                          <div class="schema-field">
                            <label>Name</label>
                            <input type="text" [(ngModel)]="prop.name" placeholder="param_name" />
                          </div>
                          <div class="schema-field type-field">
                            <label>Type</label>
                            <select [(ngModel)]="prop.type">
                              <option value="string">String</option>
                              <option value="integer">Integer</option>
                              <option value="number">Number</option>
                              <option value="boolean">Boolean</option>
                              <option value="object">Object</option>
                              <option value="array">Array</option>
                            </select>
                          </div>
                          <div class="schema-field check-field">
                            <label>
                              <input type="checkbox" [(ngModel)]="prop.required" /> Req
                            </label>
                          </div>
                          <button class="btn-icon btn-remove" (click)="removeFn(i)" title="Remove">&times;</button>
                        </div>
                        <div class="schema-field">
                          <label>Description</label>
                          <input type="text" [(ngModel)]="prop.description" placeholder="Description" />
                        </div>
                        <div class="schema-row-top">
                          <div class="schema-field">
                            <label>Default</label>
                            <input type="text" [(ngModel)]="prop.defaultValue" placeholder="Default value" />
                          </div>
                          <div class="schema-field">
                            <label>Enum (comma-sep)</label>
                            <input type="text" [(ngModel)]="prop.enumValues" placeholder="a, b, c" />
                          </div>
                        </div>
                      </div>
                    }
                  </div>
                </ng-template>
              </div>
            </div>
          </div>
        </div>
      </div>
    </nimbus-layout>
  `,
  styles: [`
    .page-container { padding: 1.5rem; }
    .page-header { display: flex; flex-direction: column; gap: 0.5rem; margin-bottom: 1.5rem; }
    .back-btn {
      background: none; border: none; color: #3b82f6; cursor: pointer;
      font-size: 0.875rem; padding: 0; text-align: left; font-family: inherit;
    }
    .back-btn:hover { text-decoration: underline; }
    .header-main { display: flex; align-items: center; gap: 0.75rem; }
    .header-main h1 { font-size: 1.5rem; font-weight: 700; color: #1e293b; margin: 0; }
    .header-badges { display: flex; gap: 0.5rem; }
    .badge {
      font-size: 0.6875rem; font-weight: 600; padding: 0.125rem 0.5rem; border-radius: 4px;
      text-transform: uppercase;
    }
    .badge-category { background: #f1f5f9; color: #475569; }
    .badge-feature { background: #dcfce7; color: #166534; }
    .header-actions { display: flex; gap: 0.5rem; }

    .btn { padding: 0.5rem 1rem; border-radius: 6px; font-size: 0.875rem; cursor: pointer; border: none; font-weight: 500; font-family: inherit; }
    .btn-sm { padding: 0.375rem 0.75rem; font-size: 0.8125rem; }
    .btn-primary { background: #3b82f6; color: #fff; }
    .btn-primary:hover { background: #2563eb; }
    .btn-secondary { background: #f1f5f9; color: #374151; border: 1px solid #e2e8f0; }
    .btn-secondary:hover { background: #e2e8f0; }
    .btn-danger { background: #fee2e2; color: #991b1b; }
    .btn-danger:hover { background: #fecaca; }
    .btn:disabled { opacity: 0.5; cursor: not-allowed; }

    .form-section { background: #fff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 1.25rem; margin-bottom: 1rem; }
    .form-row { display: flex; gap: 1rem; margin-bottom: 0.75rem; }
    .form-group { flex: 1; display: flex; flex-direction: column; gap: 0.25rem; }
    .form-group label { font-size: 0.75rem; font-weight: 600; color: #64748b; text-transform: uppercase; }
    .form-group input[type="text"], .form-group textarea, .form-group select {
      padding: 0.5rem 0.75rem; border: 1px solid #e2e8f0; border-radius: 6px;
      font-size: 0.875rem; color: #1e293b; background: #fff; font-family: inherit;
    }
    .form-group input:focus, .form-group textarea:focus, .form-group select:focus {
      outline: none; border-color: #3b82f6; box-shadow: 0 0 0 3px rgba(59,130,246,0.1);
    }
    .form-group input:disabled, .form-group textarea:disabled {
      background: #f8fafc; color: #94a3b8; cursor: not-allowed;
    }
    .provider-chips { display: flex; flex-wrap: wrap; gap: 0.5rem; }
    .chip-label {
      display: flex; align-items: center; gap: 0.25rem;
      padding: 0.25rem 0.625rem; border: 1px solid #e2e8f0; border-radius: 16px;
      font-size: 0.75rem; color: #374151; background: #f8fafc; cursor: pointer;
    }
    .chip-label input { margin: 0; width: auto; }
    .muted { color: #94a3b8; font-size: 0.75rem; }

    /* ── Split pane ────────────────────── */
    .split-container {
      background: #fff; border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden;
    }
    .split-pane { display: flex; gap: 0; min-height: calc(100vh - 440px); }
    .editor-pane { flex: 3; min-width: 0; display: flex; flex-direction: column; }
    .pane-header {
      padding: 0.5rem 0.75rem; background: #f8fafc; border-bottom: 1px solid #e2e8f0;
    }
    .pane-title { font-size: 0.75rem; font-weight: 600; color: #64748b; text-transform: uppercase; }
    .config-pane {
      flex: 2; min-width: 300px; display: flex; flex-direction: column;
      border-left: 1px solid #e2e8f0;
    }
    .config-tabs {
      display: flex; gap: 0; border-bottom: 1px solid #e2e8f0; background: #f8fafc;
    }
    .config-tab {
      padding: 0.5rem 0.875rem; border: none; border-bottom: 2px solid transparent;
      background: none; cursor: pointer; font-size: 0.8125rem; font-weight: 500;
      color: #64748b; font-family: inherit;
    }
    .config-tab:hover { color: #1e293b; }
    .config-tab.active { color: #3b82f6; border-bottom-color: #3b82f6; }
    .config-body { flex: 1; overflow-y: auto; max-height: calc(100vh - 500px); padding: 0.75rem; }

    /* ── Schema builder ──────────────────── */
    .schema-builder { display: flex; flex-direction: column; gap: 0.75rem; }
    .schema-header { display: flex; justify-content: space-between; align-items: center; }
    .schema-header h3 { font-size: 0.9375rem; font-weight: 600; color: #1e293b; margin: 0; }
    .empty-schema { color: #94a3b8; font-size: 0.875rem; padding: 1.5rem; text-align: center; }

    .schema-row.stacked {
      display: flex; flex-direction: column; gap: 0.5rem;
      padding: 0.75rem; background: #f8fafc; border-radius: 6px; border: 1px solid #e2e8f0;
    }
    .schema-row-top { display: flex; gap: 0.5rem; align-items: flex-end; }
    .schema-field { display: flex; flex-direction: column; gap: 0.125rem; flex: 1; }
    .schema-field.type-field { flex: 0.8; }
    .schema-field.check-field { flex: 0 0 auto; align-self: center; }
    .schema-field label { font-size: 0.6875rem; font-weight: 600; color: #94a3b8; text-transform: uppercase; }
    .schema-field input, .schema-field select {
      padding: 0.375rem 0.5rem; border: 1px solid #e2e8f0; border-radius: 4px;
      font-size: 0.8125rem; color: #1e293b; background: #fff; font-family: inherit;
    }
    .schema-field input:focus, .schema-field select:focus { outline: none; border-color: #3b82f6; }
    .schema-field input[type="checkbox"] { width: auto; margin-right: 0.25rem; }

    .btn-icon { background: none; border: none; cursor: pointer; font-size: 1.25rem; padding: 0.25rem; line-height: 1; color: #94a3b8; }
    .btn-remove:hover { color: #dc2626; }
  `],
})
export class ResolverEditorComponent implements OnInit {
  router = inject(Router);
  private route = inject(ActivatedRoute);
  private componentService = inject(ComponentService);
  private semanticService = inject(SemanticService);
  private toast = inject(ToastService);
  private cdr = inject(ChangeDetectorRef);

  resolver = signal<Resolver | null>(null);
  saving = signal(false);
  editorVisible = signal(false);
  configTab = signal<ConfigTab>('inputSchema');
  providers = signal<Array<{ id: string; name: string; displayName: string }>>([]);

  selectedProviderIds = new Set<string>();

  isNew = computed(() => !this.route.snapshot.params['id']);

  categories = [
    { value: 'networking', label: 'Networking' },
    { value: 'naming', label: 'Naming' },
    { value: 'compute', label: 'Compute' },
    { value: 'storage', label: 'Storage' },
    { value: 'security', label: 'Security' },
    { value: 'identity', label: 'Identity' },
    { value: 'dns', label: 'DNS' },
    { value: 'other', label: 'Other' },
  ];

  form = {
    resolverType: '',
    displayName: '',
    handlerClass: '',
    description: '',
    category: '',
    code: EXAMPLE_RESOLVER_CODE,
  };

  // Structured schema editing
  inputProperties = signal<SchemaProperty[]>([]);
  outputProperties = signal<SchemaProperty[]>([]);
  instanceConfigProperties = signal<SchemaProperty[]>([]);

  ngOnInit(): void {
    const id = this.route.snapshot.params['id'];
    this.loadProviders();

    if (id) {
      this.loadResolver(id);
    } else {
      setTimeout(() => {
        this.editorVisible.set(true);
        this.cdr.markForCheck();
      }, 50);
    }
  }

  private loadProviders(): void {
    this.semanticService.listProviders().subscribe({
      next: (p: Array<{ id: string; name: string; displayName: string }>) => {
        this.providers.set(p);
        this.cdr.markForCheck();
      },
    });
  }

  private loadResolver(id: string): void {
    this.componentService.getResolverDefinition(id).subscribe({
      next: (r) => {
        if (!r) {
          this.toast.error('Resolver not found');
          this.router.navigate(['/provider/resolvers']);
          return;
        }
        this.resolver.set(r);
        this.form.resolverType = r.resolverType;
        this.form.displayName = r.displayName;
        this.form.handlerClass = r.handlerClass;
        this.form.description = r.description || '';
        this.form.category = r.category || '';
        this.form.code = r.code || EXAMPLE_RESOLVER_CODE;
        this.selectedProviderIds = new Set(r.compatibleProviderIds || []);

        this.inputProperties.set(this.schemaToProperties(r.inputSchema));
        this.outputProperties.set(this.schemaToProperties(r.outputSchema));
        this.instanceConfigProperties.set(this.schemaToProperties(r.instanceConfigSchema));

        setTimeout(() => {
          this.editorVisible.set(true);
          this.cdr.markForCheck();
        }, 50);
        this.cdr.markForCheck();
      },
      error: () => {
        this.toast.error('Failed to load resolver');
        this.router.navigate(['/provider/resolvers']);
      },
    });
  }

  toggleProvider(id: string): void {
    if (this.selectedProviderIds.has(id)) {
      this.selectedProviderIds.delete(id);
    } else {
      this.selectedProviderIds.add(id);
    }
  }

  // ── Schema <-> Properties conversion ──────────────────────────────

  private schemaToProperties(schema: Record<string, unknown> | null): SchemaProperty[] {
    if (!schema) return [];
    const props = (schema['properties'] || {}) as Record<string, Record<string, unknown>>;
    const required = ((schema['required'] || []) as string[]);
    return Object.entries(props).map(([name, def]) => ({
      name,
      type: (def['type'] as SchemaProperty['type']) || 'string',
      description: (def['description'] as string) || '',
      required: required.includes(name),
      defaultValue: def['default'] !== undefined ? String(def['default']) : '',
      enumValues: Array.isArray(def['enum']) ? (def['enum'] as string[]).join(', ') : '',
    }));
  }

  private propertiesToSchema(properties: SchemaProperty[]): Record<string, unknown> | undefined {
    if (properties.length === 0) return undefined;
    const props: Record<string, Record<string, unknown>> = {};
    const required: string[] = [];

    for (const p of properties) {
      if (!p.name.trim()) continue;
      const def: Record<string, unknown> = { type: p.type };
      if (p.description) def['description'] = p.description;
      if (p.defaultValue) {
        if (p.type === 'integer' || p.type === 'number') {
          def['default'] = Number(p.defaultValue);
        } else if (p.type === 'boolean') {
          def['default'] = p.defaultValue === 'true';
        } else {
          def['default'] = p.defaultValue;
        }
      }
      if (p.enumValues.trim()) {
        def['enum'] = p.enumValues.split(',').map(v => v.trim()).filter(Boolean);
      }
      props[p.name] = def;
      if (p.required) required.push(p.name);
    }

    const schema: Record<string, unknown> = { type: 'object', properties: props };
    if (required.length > 0) schema['required'] = required;
    return schema;
  }

  // ── Schema builders ───────────────────────────────────────────────

  addInputProperty = (): void => {
    this.inputProperties.update(props => [
      ...props,
      { name: '', type: 'string', description: '', required: false, defaultValue: '', enumValues: '' },
    ]);
  };

  removeInputProperty = (index: number): void => {
    this.inputProperties.update(props => props.filter((_, i) => i !== index));
  };

  addOutputProperty = (): void => {
    this.outputProperties.update(props => [
      ...props,
      { name: '', type: 'string', description: '', required: false, defaultValue: '', enumValues: '' },
    ]);
  };

  removeOutputProperty = (index: number): void => {
    this.outputProperties.update(props => props.filter((_, i) => i !== index));
  };

  addInstanceConfigProperty = (): void => {
    this.instanceConfigProperties.update(props => [
      ...props,
      { name: '', type: 'string', description: '', required: false, defaultValue: '', enumValues: '' },
    ]);
  };

  removeInstanceConfigProperty = (index: number): void => {
    this.instanceConfigProperties.update(props => props.filter((_, i) => i !== index));
  };

  // ── Save / Delete ─────────────────────────────────────────────────

  save(): void {
    this.saving.set(true);
    const providerIds = Array.from(this.selectedProviderIds);
    const inputSchema = this.propertiesToSchema(this.inputProperties());
    const outputSchema = this.propertiesToSchema(this.outputProperties());
    const instanceConfigSchema = this.propertiesToSchema(this.instanceConfigProperties());

    if (this.resolver()) {
      const input: ResolverDefinitionUpdateInput = {
        displayName: this.form.displayName || undefined,
        description: this.form.description || undefined,
        category: this.form.category || undefined,
        code: this.form.code || undefined,
        inputSchema,
        outputSchema,
        instanceConfigSchema,
        compatibleProviderIds: providerIds,
      };

      this.componentService.updateResolverDefinition(this.resolver()!.id, input).subscribe({
        next: (updated) => {
          this.resolver.set(updated);
          this.saving.set(false);
          this.toast.success('Resolver saved');
          this.cdr.markForCheck();
        },
        error: (e: Error) => {
          this.saving.set(false);
          this.toast.error('Failed to save: ' + e.message);
          this.cdr.markForCheck();
        },
      });
    } else {
      if (!this.form.resolverType || !this.form.displayName || !this.form.handlerClass) {
        this.saving.set(false);
        this.toast.error('Resolver type, display name, and handler class are required');
        return;
      }

      const input: ResolverDefinitionCreateInput = {
        resolverType: this.form.resolverType,
        displayName: this.form.displayName,
        handlerClass: this.form.handlerClass,
        description: this.form.description || undefined,
        category: this.form.category || undefined,
        code: this.form.code || undefined,
        inputSchema,
        outputSchema,
        instanceConfigSchema,
        compatibleProviderIds: providerIds.length ? providerIds : undefined,
      };

      this.componentService.createResolverDefinition(input).subscribe({
        next: (created) => {
          this.resolver.set(created);
          this.saving.set(false);
          this.toast.success('Resolver created');
          this.router.navigate(['/provider/resolvers', created.id, 'edit']);
          this.cdr.markForCheck();
        },
        error: (e: Error) => {
          this.saving.set(false);
          this.toast.error('Failed to create: ' + e.message);
          this.cdr.markForCheck();
        },
      });
    }
  }

  confirmDelete(): void {
    const r = this.resolver();
    if (!r) return;
    if (!confirm(`Delete resolver definition "${r.displayName}"?`)) return;

    this.componentService.deleteResolverDefinition(r.id).subscribe({
      next: () => {
        this.toast.success('Resolver deleted');
        this.router.navigate(['/provider/resolvers']);
      },
      error: (e: Error) => this.toast.error('Failed to delete: ' + e.message),
    });
  }
}
