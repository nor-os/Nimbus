/**
 * Overview: Landing zone detail page — hierarchy tree designer with blueprint picker, config panels, and validation.
 * Architecture: Feature component for landing zone hierarchy design (Section 7.2)
 * Dependencies: @angular/core, @angular/router, landing-zone.service, cloud-backend.service, hierarchy-tree, hierarchy-node-config, zone-overview
 * Concepts: The LZ page IS the visual designer. Left panel has blueprint picker + hierarchy levels palette.
 *     Center is the hierarchy tree showing provider-specific organizational structure.
 *     Right panel is context-sensitive: selected node shows node config; no selection shows zone overview.
 *     Blueprints are pre-built hierarchies that load into the tree view.
 */
import {
  Component,
  OnInit,
  OnDestroy,
  inject,
  signal,
  computed,
  ChangeDetectionStrategy,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { Subject, debounceTime, firstValueFrom, takeUntil } from 'rxjs';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { LandingZoneService } from '@core/services/landing-zone.service';
import { CloudBackendService } from '@core/services/cloud-backend.service';
import { ToastService } from '@shared/services/toast.service';
import { ConfirmService } from '@shared/services/confirm.service';
import {
  LandingZone,
  LandingZoneBlueprint,
  LandingZoneValidation,
  LandingZoneHierarchy,
  HierarchyNode,
  HierarchyLevelDef,
  ProviderHierarchy,
  AddressSpace,
} from '@shared/models/landing-zone.model';
import { CloudBackend } from '@shared/models/cloud-backend.model';
import { ComponentService } from '@core/services/component.service';
import { Resolver, ResolverConfiguration } from '@shared/models/component.model';
import { HierarchyTreeComponent } from './hierarchy-tree/hierarchy-tree.component';
import { HierarchyNodeConfigComponent } from './hierarchy-node-config/hierarchy-node-config.component';
import { ZoneOverviewComponent } from './zone-overview/zone-overview.component';
import { SchemaFormRendererComponent } from '@shared/components/schema-form/schema-form-renderer.component';

@Component({
  selector: 'nimbus-landing-zone-detail',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    LayoutComponent,
    HierarchyTreeComponent,
    HierarchyNodeConfigComponent,
    ZoneOverviewComponent,
    SchemaFormRendererComponent,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <nimbus-layout>
      <div class="designer-page">
        <!-- Top toolbar -->
        <div class="designer-toolbar">
          <div class="toolbar-left">
            <button class="btn-back" (click)="goBack()">&larr;</button>
            <input
              type="text"
              class="name-input"
              [(ngModel)]="zoneName"
              [disabled]="isReadOnly()"
              placeholder="Landing zone name..."
              (change)="onNameChange()"
            />
            @if (landingZone()) {
              <span class="status-badge" [class]="'badge-' + landingZone()!.status.toLowerCase()">
                {{ landingZone()!.status }}
              </span>
              <span class="version-badge">v{{ landingZone()!.version }}</span>
            }
            @if (backend()) {
              <span class="provider-badge">{{ backend()!.providerDisplayName }}</span>
            }
          </div>
          <div class="toolbar-right">
            @if (!isReadOnly()) {
              <button class="btn btn-secondary" (click)="onSave()" [disabled]="saving()">
                {{ saving() ? 'Saving...' : 'Save' }}
              </button>
              <button class="btn btn-primary" (click)="onPublish()" [disabled]="saving()">Publish</button>
            }
            <button class="btn btn-secondary" (click)="onValidate()">Validate</button>
          </div>
        </div>

        <!-- Three-panel layout -->
        <div class="designer-body">
          <!-- Left panel: Blueprints + Hierarchy Levels palette -->
          <div class="left-panel">
            <!-- Blueprint section (collapsible) -->
            <div class="panel-section">
              <button class="section-header" (click)="blueprintSectionOpen = !blueprintSectionOpen">
                <span>Blueprints</span>
                <span class="chevron" [class.expanded]="blueprintSectionOpen">&#9206;</span>
              </button>
              @if (blueprintSectionOpen) {
                <div class="blueprint-list">
                  @for (bp of blueprints(); track bp.id) {
                    <button
                      class="blueprint-card"
                      [class.selected]="selectedBlueprintId() === bp.id"
                      (click)="onSelectBlueprint(bp)"
                      [disabled]="isReadOnly()"
                    >
                      <div class="bp-name">{{ bp.name }}</div>
                      <span class="bp-complexity" [class]="'complexity-' + bp.complexity">{{ bp.complexity }}</span>
                      <div class="bp-desc">{{ bp.description }}</div>
                      <div class="bp-features">
                        @for (f of bp.features.slice(0, 3); track f) {
                          <span class="bp-feature">{{ f }}</span>
                        }
                        @if (bp.features.length > 3) {
                          <span class="bp-feature bp-more">+{{ bp.features.length - 3 }} more</span>
                        }
                      </div>
                    </button>
                  }
                  @if (blueprints().length === 0) {
                    <div class="panel-hint">No blueprints for this provider.</div>
                  }
                  <button
                    class="blueprint-card blank-card"
                    [class.selected]="selectedBlueprintId() === 'blank'"
                    (click)="onStartBlank()"
                    [disabled]="isReadOnly()"
                  >
                    <div class="bp-name">Start from Scratch</div>
                    <div class="bp-desc">Build your own hierarchy from an empty canvas.</div>
                  </button>
                </div>
              }
            </div>

            <!-- Hierarchy Levels palette -->
            @if (hierarchyLevels().length > 0) {
              <div class="panel-section">
                <button class="section-header" (click)="levelsPaletteOpen = !levelsPaletteOpen">
                  <span>Hierarchy Levels</span>
                  <span class="chevron" [class.expanded]="levelsPaletteOpen">&#9206;</span>
                </button>
                @if (levelsPaletteOpen) {
                  <div class="levels-palette">
                    @for (level of hierarchyLevels(); track level.typeId) {
                      <button
                        class="level-card"
                        [class.disabled]="!canAddLevel(level)"
                        [disabled]="isReadOnly() || !canAddLevel(level)"
                        (click)="addLevelToHierarchy(level)"
                        [title]="levelTooltip(level)"
                      >
                        <span class="level-icon">{{ level.icon }}</span>
                        <div class="level-info">
                          <span class="level-label">{{ level.label }}</span>
                          <span class="level-type-id">{{ level.typeId }}</span>
                        </div>
                        <span class="level-badges">
                          @if (level.supportsIpam) { <span class="level-badge badge-ipam">IPAM</span> }
                          @if (level.supportsTags) { <span class="level-badge badge-tags">Tags</span> }
                          @if (level.supportsEnvironment) { <span class="level-badge badge-env">Env</span> }
                        </span>
                      </button>
                    }
                  </div>
                }
              </div>
            }

            <!-- Actions section -->
            <div class="panel-section">
              <button class="section-header" (click)="actionsSectionOpen = !actionsSectionOpen">
                <span>Actions</span>
                <span class="chevron" [class.expanded]="actionsSectionOpen">&#9206;</span>
              </button>
              @if (actionsSectionOpen) {
                <div class="actions-list">
                  <button class="action-item" (click)="showRegionsPanel()">
                    <span class="action-icon">&#127760;</span>
                    <span>Manage Regions</span>
                    <span class="action-count">{{ regions().length }}</span>
                  </button>
                  <button class="action-item" (click)="showResolversPanel()">
                    <span class="action-icon">&#9881;</span>
                    <span>Resolvers</span>
                    <span class="action-count">{{ resolverConfigs().length }}</span>
                  </button>
                  <button class="action-item" (click)="showFoundationPanel()">
                    <span class="action-icon">&#9881;</span>
                    <span>Global Config</span>
                  </button>
                  <button class="action-item" (click)="onValidate()">
                    <span class="action-icon">&#10003;</span>
                    <span>Validate</span>
                    @if (validation()) {
                      <span class="check-dot" [class.check-pass]="validation()!.ready" [class.check-fail]="!validation()!.ready"></span>
                    }
                  </button>
                </div>
              }
            </div>
          </div>

          <!-- Center: Hierarchy Tree -->
          <div class="center-panel">
            <nimbus-hierarchy-tree
              [hierarchy]="currentHierarchy()"
              [providerName]="backend()?.providerName || ''"
              [readOnly]="isReadOnly()"
              [levelDefs]="levelDefsMap()"
              [validationErrors]="nodeValidationErrors()"
              (nodeSelected)="onNodeSelected($event)"
              (hierarchyChange)="onHierarchyChange($event)"
            />
          </div>

          <!-- Right panel: Context-sensitive -->
          <div class="right-panel">
            @if (rightPanelMode() === 'node-config' && selectedNode()) {
              <nimbus-hierarchy-node-config
                [node]="selectedNode()!"
                [allNodes]="currentHierarchy()?.nodes || []"
                [levelDef]="selectedLevelDef()"
                [providerName]="backend()?.providerName || ''"
                [readOnly]="isReadOnly()"
                (nodeChange)="onNodeChange($event)"
              />
            } @else if (rightPanelMode() === 'regions') {
              <div class="config-panel">
                <div class="cpanel-header">
                  <h3>Regions</h3>
                  <div class="cpanel-actions">
                    @if (!isReadOnly()) {
                      <button class="btn-sm btn-primary-sm" (click)="showRegionForm = true">Add</button>
                    }
                    <button class="btn-sm" (click)="clearRightPanel()">Back</button>
                  </div>
                </div>

                @if (showRegionForm) {
                  <div class="inline-form">
                    <input class="form-input-sm" [(ngModel)]="regionIdentifier" placeholder="Region ID (e.g. us-east-1)" />
                    <input class="form-input-sm" [(ngModel)]="regionDisplayName" placeholder="Display name" />
                    <div class="form-row-sm">
                      <label class="check-label"><input type="checkbox" [(ngModel)]="regionIsPrimary" /> Primary</label>
                      <label class="check-label"><input type="checkbox" [(ngModel)]="regionIsDr" /> DR</label>
                    </div>
                    <div class="form-actions-sm">
                      <button class="btn-sm" (click)="showRegionForm = false">Cancel</button>
                      <button class="btn-sm btn-primary-sm" (click)="addRegion()" [disabled]="!regionIdentifier.trim()">Add</button>
                    </div>
                  </div>
                }

                @if (regions().length === 0) {
                  <div class="panel-hint">No regions configured. Add deployment regions.</div>
                }
                @for (r of regions(); track r.id) {
                  <div class="region-item">
                    <div class="region-info">
                      <span class="region-name">{{ r.displayName }}</span>
                      <span class="region-id">{{ r.regionIdentifier }}</span>
                      @if (r.isPrimary) { <span class="region-badge primary">Primary</span> }
                      @if (r.isDr) { <span class="region-badge dr">DR</span> }
                    </div>
                    @if (!isReadOnly()) {
                      <button class="btn-icon-sm btn-danger-sm" (click)="removeRegion(r.id)">&times;</button>
                    }
                  </div>
                }
              </div>
            } @else if (rightPanelMode() === 'resolvers') {
              <div class="config-panel">
                <div class="cpanel-header">
                  <h3>Resolver Configs</h3>
                  <div class="cpanel-actions">
                    @if (!isReadOnly()) {
                      <button class="btn-sm btn-primary-sm" (click)="showResolverForm = true">Add</button>
                    }
                    <button class="btn-sm" (click)="clearRightPanel()">Back</button>
                  </div>
                </div>

                @if (showResolverForm) {
                  <div class="inline-form">
                    <label class="cr-label">Resolver Type</label>
                    <select class="form-input-sm" [(ngModel)]="resolverFormType" (ngModelChange)="onResolverTypeChange()">
                      <option value="">Select resolver...</option>
                      @for (r of availableResolvers(); track r.id) {
                        <option [value]="r.id">{{ r.displayName }}</option>
                      }
                    </select>
                    @if (selectedResolverDef(); as rDef) {
                      <div class="resolver-desc">{{ rDef.description }}</div>
                      @if (resolverConfigFields().length > 0) {
                        @for (f of resolverConfigFields(); track f.key) {
                          <div class="rcf-field">
                            <label class="cr-label">{{ f.label }}</label>
                            <input class="form-input-sm" [(ngModel)]="resolverConfigValues[f.key]" [placeholder]="f.placeholder" />
                          </div>
                        }
                      }
                    }
                    <div class="form-actions-sm">
                      <button class="btn-sm" (click)="cancelResolverForm()">Cancel</button>
                      <button class="btn-sm btn-primary-sm" (click)="saveResolverConfig()" [disabled]="!resolverFormType">Save</button>
                    </div>
                  </div>
                }

                @if (resolverConfigs().length === 0 && !showResolverForm) {
                  <div class="panel-hint">No resolver configurations.</div>
                }
                @for (rc of resolverConfigs(); track rc.id) {
                  <div class="resolver-item">
                    <div class="resolver-info">
                      <span class="resolver-type-badge">{{ rc.resolverType }}</span>
                      <div class="resolver-config-preview">
                        @for (entry of getConfigEntries(rc.config); track entry.key) {
                          <span class="config-kv">{{ entry.key }}: {{ entry.value }}</span>
                        }
                      </div>
                    </div>
                    @if (!isReadOnly()) {
                      <button class="btn-icon-sm btn-danger-sm" (click)="deleteResolverConfig(rc.id)">&times;</button>
                    }
                  </div>
                }
              </div>
            } @else if (rightPanelMode() === 'foundation') {
              <div class="config-panel">
                <div class="cpanel-header">
                  <h3>Foundation Config</h3>
                  <button class="btn-sm" (click)="clearRightPanel()">Back</button>
                </div>

                <div class="foundation-section">
                  <button class="fsection-toggle" (click)="foundationSection = foundationSection === 'network' ? null : 'network'">
                    <span>Network</span>
                    <span class="chevron" [class.expanded]="foundationSection === 'network'">&#9206;</span>
                  </button>
                  @if (foundationSection === 'network' && networkSchema()) {
                    <nimbus-schema-form-renderer
                      [schema]="networkSchema()!"
                      [values]="foundationValues['network']"
                      (valuesChange)="onFoundationChange('network', $event)"
                    />
                  }
                </div>

                <div class="foundation-section">
                  <button class="fsection-toggle" (click)="foundationSection = foundationSection === 'iam' ? null : 'iam'">
                    <span>IAM / Identity</span>
                    <span class="chevron" [class.expanded]="foundationSection === 'iam'">&#9206;</span>
                  </button>
                  @if (foundationSection === 'iam' && iamConfigSchema()) {
                    <nimbus-schema-form-renderer
                      [schema]="iamConfigSchema()!"
                      [values]="foundationValues['iam']"
                      (valuesChange)="onFoundationChange('iam', $event)"
                    />
                  }
                </div>

                <div class="foundation-section">
                  <button class="fsection-toggle" (click)="foundationSection = foundationSection === 'security' ? null : 'security'">
                    <span>Security</span>
                    <span class="chevron" [class.expanded]="foundationSection === 'security'">&#9206;</span>
                  </button>
                  @if (foundationSection === 'security' && securitySchema()) {
                    <nimbus-schema-form-renderer
                      [schema]="securitySchema()!"
                      [values]="foundationValues['security']"
                      (valuesChange)="onFoundationChange('security', $event)"
                    />
                  }
                </div>

                @if (!isReadOnly()) {
                  <div class="form-actions-sm" style="margin-top: 0.5rem;">
                    <button class="btn-sm btn-primary-sm" (click)="saveFoundation()" [disabled]="saving()">Save Config</button>
                  </div>
                }
              </div>
            } @else {
              <!-- Zone overview (default when nothing selected) -->
              <nimbus-zone-overview
                [hierarchy]="currentHierarchy()"
                [levelDefs]="levelDefsMap()"
                [validation]="validation()"
                [regions]="regions()"
                [tagPolicies]="tagPolicies()"
              />
            }
          </div>
        </div>

        <!-- Bottom validation bar -->
        @if (validationErrors().length > 0) {
          <div class="validation-bar">
            @for (err of validationErrors(); track err.message) {
              <span class="validation-error">{{ err.message }}</span>
            }
          </div>
        }
      </div>
    </nimbus-layout>
  `,
  styles: [`
    .designer-page {
      display: flex; flex-direction: column;
      height: calc(100vh - 56px); background: #f5f6f8;
    }

    /* ── Toolbar ─────────────────────────────────── */
    .designer-toolbar {
      display: flex; align-items: center; justify-content: space-between;
      padding: 8px 16px; background: #fff; border-bottom: 1px solid #e2e8f0; min-height: 48px;
    }
    .toolbar-left { display: flex; align-items: center; gap: 12px; }
    .toolbar-right { display: flex; align-items: center; gap: 8px; }
    .btn-back {
      background: none; border: 1px solid #e2e8f0; border-radius: 6px;
      padding: 4px 10px; cursor: pointer; font-size: 1rem; color: #64748b;
    }
    .btn-back:hover { background: #f8fafc; }
    .name-input {
      padding: 6px 10px; border: 1px solid #e2e8f0; border-radius: 6px;
      font-size: 0.875rem; font-weight: 600; color: #1e293b; background: #fff;
      min-width: 240px; outline: none; font-family: inherit;
    }
    .name-input:focus { border-color: #3b82f6; }
    .name-input:disabled { background: #f8fafc; }
    .status-badge {
      padding: 2px 8px; border-radius: 12px; font-size: 0.6875rem;
      font-weight: 600; text-transform: uppercase;
    }
    .badge-draft { background: #fef3c7; color: #92400e; }
    .badge-published { background: #d1fae5; color: #065f46; }
    .badge-archived { background: #f1f5f9; color: #64748b; }
    .version-badge { font-size: 0.6875rem; color: #94a3b8; font-weight: 500; }
    .provider-badge {
      padding: 2px 8px; border-radius: 12px; font-size: 0.6875rem;
      font-weight: 600; background: #dbeafe; color: #1d4ed8;
    }

    .btn {
      padding: 6px 14px; border-radius: 6px; font-size: 0.8125rem; font-weight: 500;
      cursor: pointer; border: none; font-family: inherit;
    }
    .btn-primary { background: #3b82f6; color: #fff; }
    .btn-primary:hover { background: #2563eb; }
    .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
    .btn-secondary { background: #fff; color: #374151; border: 1px solid #e2e8f0; }
    .btn-secondary:hover { background: #f8fafc; }

    /* ── Three-panel body ────────────────────────── */
    .designer-body { display: flex; flex: 1; overflow: hidden; }

    .left-panel {
      width: 240px; background: #fff; border-right: 1px solid #e2e8f0;
      display: flex; flex-direction: column; overflow-y: auto;
    }

    .center-panel {
      flex: 1; display: flex; flex-direction: column; padding: 12px;
      min-width: 0; overflow: hidden;
    }

    .right-panel {
      width: 340px; background: #fff; border-left: 1px solid #e2e8f0;
      display: flex; flex-direction: column; overflow: hidden;
    }

    /* ── Left panel: Blueprints ──────────────────── */
    .panel-section { border-bottom: 1px solid #e2e8f0; }
    .section-header {
      display: flex; align-items: center; justify-content: space-between;
      width: 100%; padding: 10px 12px; background: none; border: none;
      font-size: 0.75rem; font-weight: 700; text-transform: uppercase;
      letter-spacing: 0.05em; color: #64748b; cursor: pointer; font-family: inherit;
    }
    .section-header:hover { background: #f8fafc; }
    .chevron { font-size: 0.625rem; transition: transform 0.2s; transform: rotate(180deg); }
    .chevron.expanded { transform: rotate(0deg); }

    .blueprint-list { padding: 0 8px 8px; }
    .blueprint-card {
      display: block; width: 100%; text-align: left; padding: 10px;
      margin-bottom: 6px; background: #f8fafc; border: 1px solid #e2e8f0;
      border-radius: 6px; cursor: pointer; font-family: inherit;
      transition: border-color 0.15s;
    }
    .blueprint-card:hover:not(:disabled) { border-color: #3b82f6; }
    .blueprint-card.selected { border-color: #3b82f6; background: #eff6ff; }
    .blueprint-card:disabled { opacity: 0.5; cursor: not-allowed; }
    .blank-card { border-style: dashed; background: #fff; }
    .bp-name { font-size: 0.8125rem; font-weight: 600; color: #1e293b; margin-bottom: 2px; }
    .bp-complexity {
      display: inline-block; padding: 1px 6px; border-radius: 8px;
      font-size: 0.5625rem; font-weight: 700; text-transform: uppercase; margin-bottom: 4px;
    }
    .complexity-basic { background: #dcfce7; color: #166534; }
    .complexity-standard { background: #dbeafe; color: #1d4ed8; }
    .complexity-advanced { background: #ede9fe; color: #6d28d9; }
    .bp-desc { font-size: 0.6875rem; color: #64748b; margin-bottom: 6px; line-height: 1.3; }
    .bp-features { display: flex; flex-wrap: wrap; gap: 3px; }
    .bp-feature {
      padding: 1px 5px; background: #f1f5f9; border-radius: 4px;
      font-size: 0.5625rem; color: #475569;
    }
    .bp-more { font-style: italic; color: #94a3b8; }

    /* ── Hierarchy Levels Palette ─────────────────── */
    .levels-palette { padding: 0 8px 8px; }
    .level-card {
      display: flex; align-items: center; gap: 8px; width: 100%;
      padding: 8px 10px; margin-bottom: 4px; background: #fff;
      border: 1px solid #e2e8f0; border-radius: 6px; cursor: pointer;
      font-family: inherit; transition: border-color 0.15s, background 0.15s;
    }
    .level-card:hover:not(:disabled) { border-color: #3b82f6; background: #eff6ff; }
    .level-card.disabled, .level-card:disabled {
      opacity: 0.4; cursor: not-allowed; background: #f8fafc;
    }
    .level-icon { font-size: 1rem; flex-shrink: 0; }
    .level-info { display: flex; flex-direction: column; flex: 1; min-width: 0; }
    .level-label { font-size: 0.75rem; font-weight: 600; color: #1e293b; }
    .level-type-id { font-size: 0.625rem; color: #94a3b8; font-family: monospace; }
    .level-badges { display: flex; gap: 2px; flex-shrink: 0; }
    .level-badge {
      padding: 1px 4px; border-radius: 3px; font-size: 0.5rem;
      font-weight: 600; text-transform: uppercase;
    }
    .badge-ipam { background: #dcfce7; color: #166534; }
    .badge-tags { background: #fef3c7; color: #92400e; }
    .badge-env { background: #dbeafe; color: #1d4ed8; }

    /* ── Actions section ─────────────────────────── */
    .actions-list { padding: 0 8px 8px; }
    .action-item {
      display: flex; align-items: center; gap: 8px; width: 100%;
      padding: 7px 10px; margin-bottom: 2px; background: none;
      border: none; border-radius: 6px; cursor: pointer;
      font-family: inherit; font-size: 0.75rem; color: #374151;
    }
    .action-item:hover { background: #f8fafc; }
    .action-icon { font-size: 0.875rem; flex-shrink: 0; }
    .action-count {
      margin-left: auto; background: #f1f5f9; color: #64748b;
      padding: 1px 6px; border-radius: 8px; font-size: 0.625rem; font-weight: 600;
    }
    .check-dot {
      width: 6px; height: 6px; border-radius: 50%; display: inline-block; margin-left: auto;
    }
    .check-pass { background: #22c55e; }
    .check-fail { background: #ef4444; }

    /* ── Config panels (right panel when showing regions/resolvers/foundation) ── */
    .config-panel { padding: 12px; overflow-y: auto; flex: 1; }
    .cpanel-header {
      display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;
    }
    .cpanel-header h3 { margin: 0; font-size: 0.8125rem; font-weight: 600; color: #1e293b; }
    .cpanel-actions { display: flex; gap: 4px; }
    .panel-hint { font-size: 0.75rem; color: #94a3b8; padding: 12px 0; text-align: center; }

    /* ── Inline forms ────────────────────────────── */
    .inline-form {
      background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px;
      padding: 8px; margin-bottom: 8px;
    }
    .form-input-sm {
      width: 100%; padding: 5px 8px; border: 1px solid #e2e8f0; border-radius: 4px;
      font-size: 0.75rem; color: #1e293b; background: #fff; box-sizing: border-box;
      font-family: inherit; margin-bottom: 4px;
    }
    .form-input-sm:focus { border-color: #3b82f6; outline: none; }
    .form-row-sm { display: flex; gap: 8px; margin-bottom: 4px; }
    .check-label {
      font-size: 0.6875rem; color: #374151; display: flex; align-items: center; gap: 4px; cursor: pointer;
    }
    .form-actions-sm { display: flex; gap: 4px; justify-content: flex-end; }
    .btn-sm {
      padding: 4px 10px; border-radius: 4px; font-size: 0.6875rem;
      font-weight: 500; cursor: pointer; border: 1px solid #e2e8f0;
      background: #fff; color: #374151; font-family: inherit;
    }
    .btn-sm:hover { background: #f8fafc; }
    .btn-primary-sm { background: #3b82f6; color: #fff; border-color: #3b82f6; }
    .btn-primary-sm:hover { background: #2563eb; }
    .btn-primary-sm:disabled { opacity: 0.5; cursor: not-allowed; }
    .btn-icon-sm {
      background: none; border: none; cursor: pointer; padding: 2px 4px;
      font-size: 0.75rem; border-radius: 3px; color: #64748b;
    }
    .btn-icon-sm:hover { background: #f1f5f9; }
    .btn-danger-sm { color: #dc2626; }
    .btn-danger-sm:hover { background: #fef2f2; color: #dc2626; }
    .cr-label { display: block; font-size: 0.6875rem; font-weight: 600; color: #64748b; margin-bottom: 2px; }

    /* ── Region items ────────────────────────────── */
    .region-item {
      display: flex; justify-content: space-between; align-items: center;
      padding: 6px 8px; border-bottom: 1px solid #f1f5f9;
    }
    .region-item:last-child { border-bottom: none; }
    .region-info { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
    .region-name { font-size: 0.75rem; font-weight: 500; color: #1e293b; }
    .region-id { font-size: 0.6875rem; color: #94a3b8; font-family: monospace; }
    .region-badge {
      padding: 1px 5px; border-radius: 8px; font-size: 0.5625rem;
      font-weight: 600; text-transform: uppercase;
    }
    .region-badge.primary { background: #dbeafe; color: #1d4ed8; }
    .region-badge.dr { background: #fef3c7; color: #92400e; }

    /* ── Foundation sections ──────────────────────── */
    .foundation-section { border-bottom: 1px solid #f1f5f9; }
    .fsection-toggle {
      display: flex; align-items: center; justify-content: space-between;
      width: 100%; padding: 8px 0; background: none; border: none;
      font-size: 0.75rem; font-weight: 600; color: #374151;
      cursor: pointer; font-family: inherit;
    }
    .fsection-toggle:hover { color: #1e293b; }

    /* ── Resolver items ──────────────────────────── */
    .resolver-desc { font-size: 0.6875rem; color: #64748b; margin: 4px 0 8px; }
    .rcf-field { margin-bottom: 4px; }
    .resolver-item {
      display: flex; justify-content: space-between; align-items: flex-start;
      padding: 8px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px;
      margin-bottom: 6px;
    }
    .resolver-info { flex: 1; min-width: 0; }
    .resolver-type-badge {
      display: inline-block; padding: 1px 6px; border-radius: 4px;
      font-size: 0.6875rem; font-weight: 600; background: #ede9fe; color: #6d28d9;
      margin-bottom: 4px;
    }
    .resolver-config-preview { display: flex; flex-wrap: wrap; gap: 4px; }
    .config-kv {
      font-size: 0.625rem; color: #64748b; font-family: monospace;
      background: #fff; padding: 1px 4px; border-radius: 3px; border: 1px solid #e2e8f0;
    }

    /* ── Validation bar ──────────────────────────── */
    .validation-bar {
      display: flex; flex-wrap: wrap; gap: 8px; padding: 8px 16px;
      background: #fef2f2; border-top: 1px solid #fecaca;
    }
    .validation-error { font-size: 0.75rem; color: #dc2626; }
  `],
})
export class LandingZoneDetailComponent implements OnInit, OnDestroy {
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private lzService = inject(LandingZoneService);
  private backendService = inject(CloudBackendService);
  private toast = inject(ToastService);
  private confirmService = inject(ConfirmService);
  private componentService = inject(ComponentService);
  private destroy$ = new Subject<void>();
  private autoSave$ = new Subject<void>();

  // Core data
  landingZone = signal<LandingZone | null>(null);
  backend = signal<CloudBackend | null>(null);
  loading = signal(true);
  saving = signal(false);

  // Blueprints
  blueprints = signal<LandingZoneBlueprint[]>([]);
  selectedBlueprintId = signal<string | null>(null);
  blueprintSectionOpen = true;

  // Hierarchy data
  currentHierarchy = signal<LandingZoneHierarchy | null>(null);
  validationErrors = signal<{ message: string }[]>([]);

  // Provider hierarchy levels
  providerHierarchy = signal<ProviderHierarchy | null>(null);
  hierarchyLevels = computed(() => this.providerHierarchy()?.levels || []);
  levelDefsMap = computed(() => {
    const map = new Map<string, HierarchyLevelDef>();
    for (const level of this.hierarchyLevels()) {
      map.set(level.typeId, level);
    }
    return map;
  });

  // Selection state
  selectedNodeId = signal<string | null>(null);

  // Left panel state
  levelsPaletteOpen = true;
  actionsSectionOpen = true;

  // Right panel mode
  rightPanelOverride = signal<'regions' | 'resolvers' | 'foundation' | null>(null);
  rightPanelMode = computed((): 'node-config' | 'regions' | 'resolvers' | 'foundation' | 'overview' => {
    const override = this.rightPanelOverride();
    if (override) return override;
    if (this.selectedNodeId()) return 'node-config';
    return 'overview';
  });

  validation = signal<LandingZoneValidation | null>(null);
  nodeValidationErrors = signal<Map<string, string[]>>(new Map());
  addressSpaces = signal<AddressSpace[]>([]);

  // Foundation schemas
  networkSchema = signal<Record<string, unknown> | null>(null);
  iamConfigSchema = signal<Record<string, unknown> | null>(null);
  securitySchema = signal<Record<string, unknown> | null>(null);
  foundationSection: string | null = null;
  foundationValues: Record<string, Record<string, unknown>> = {
    network: {}, iam: {}, security: {},
  };

  // Form state
  zoneName = '';

  // Region form
  showRegionForm = false;
  regionIdentifier = '';
  regionDisplayName = '';
  regionIsPrimary = false;
  regionIsDr = false;

  // Resolver state
  availableResolvers = signal<Resolver[]>([]);
  resolverConfigs = signal<ResolverConfiguration[]>([]);
  showResolverForm = false;
  resolverFormType = '';
  resolverConfigValues: Record<string, string> = {};

  selectedResolverDef = computed((): Resolver | null => {
    const id = this.resolverFormType;
    return this.availableResolvers().find(r => r.id === id) || null;
  });

  resolverConfigFields = computed((): { key: string; label: string; placeholder: string }[] => {
    const def = this.selectedResolverDef();
    if (!def?.inputSchema) return [];
    const schema = def.inputSchema as Record<string, unknown>;
    const props = (schema['properties'] || {}) as Record<string, Record<string, unknown>>;
    return Object.entries(props).map(([key, prop]) => ({
      key,
      label: (prop['title'] as string) || key,
      placeholder: (prop['description'] as string) || '',
    }));
  });

  // Computed
  isReadOnly = computed(() => {
    const z = this.landingZone();
    return !!z && z.status !== 'DRAFT';
  });

  regions = computed(() => this.landingZone()?.regions || []);
  tagPolicies = computed(() => this.landingZone()?.tagPolicies || []);

  selectedNode = computed((): HierarchyNode | null => {
    const nodeId = this.selectedNodeId();
    if (!nodeId) return null;
    const hierarchy = this.currentHierarchy();
    return hierarchy?.nodes?.find(n => n.id === nodeId) || null;
  });

  selectedLevelDef = computed((): HierarchyLevelDef | null => {
    const node = this.selectedNode();
    if (!node) return null;
    return this.levelDefsMap().get(node.typeId) || null;
  });

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      this.loadLandingZone(id);
    }

    // Auto-save debounced
    this.autoSave$.pipe(
      debounceTime(2000),
      takeUntil(this.destroy$),
    ).subscribe(() => this.doAutoSave());
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  private loadLandingZone(id: string): void {
    this.loading.set(true);
    this.lzService.getLandingZone(id).subscribe({
      next: zone => {
        if (!zone) {
          this.toast.error('Landing zone not found');
          this.router.navigate(['/landing-zones']);
          return;
        }
        this.landingZone.set(zone);
        this.zoneName = zone.name;
        this.foundationValues = {
          network: { ...(zone.networkConfig || {}) },
          iam: { ...(zone.iamConfig || {}) },
          security: { ...(zone.securityConfig || {}) },
        };

        // Load hierarchy from zone
        if (zone.hierarchy) {
          this.currentHierarchy.set(zone.hierarchy);
        }
        this.loading.set(false);

        // Load backend for provider info
        this.backendService.getBackend(zone.backendId).subscribe({
          next: b => {
            this.backend.set(b);
            if (b) {
              this.loadBlueprints(b.providerName);
              this.loadFoundationSchemas(b.providerName);
              this.loadHierarchyLevels(b.providerName);
              // Check if blueprint was previously selected
              if (zone.settings?.['blueprintId']) {
                this.selectedBlueprintId.set(zone.settings['blueprintId'] as string);
              }
            }
          },
        });
      },
      error: () => {
        this.toast.error('Failed to load landing zone');
        this.loading.set(false);
      },
    });
  }

  private loadBlueprints(providerName: string): void {
    this.lzService.getBlueprints(providerName).subscribe({
      next: bps => this.blueprints.set(bps),
    });
  }

  private loadHierarchyLevels(providerName: string): void {
    this.lzService.getProviderHierarchyLevels(providerName).subscribe({
      next: h => this.providerHierarchy.set(h),
    });
  }

  private loadFoundationSchemas(providerName: string): void {
    this.lzService.getNetworkConfigSchema(providerName).subscribe({
      next: s => this.networkSchema.set(s),
    });
    this.lzService.getIamConfigSchema(providerName).subscribe({
      next: s => this.iamConfigSchema.set(s),
    });
    this.lzService.getSecurityConfigSchema(providerName).subscribe({
      next: s => this.securitySchema.set(s),
    });
  }

  // ── Blueprint selection ─────────────────────────────────────────

  async onSelectBlueprint(bp: LandingZoneBlueprint): Promise<void> {
    const zone = this.landingZone();
    if (!zone || this.isReadOnly()) return;

    // Confirm if there's existing hierarchy data
    const hierarchy = this.currentHierarchy();
    const hasExisting = hierarchy && (hierarchy.nodes?.length ?? 0) > 0;
    if (hasExisting && this.selectedBlueprintId() !== bp.id) {
      const ok = await this.confirmService.confirm({
        title: 'Load Blueprint',
        message: `Loading "${bp.name}" will replace the current hierarchy. Continue?`,
        confirmLabel: 'Load Blueprint',
      });
      if (!ok) return;
    }

    this.selectedBlueprintId.set(bp.id);
    this.currentHierarchy.set(bp.hierarchy);

    // Apply blueprint defaults to LZ config
    this.foundationValues = {
      network: { ...bp.networkConfig },
      iam: { ...bp.iamConfig },
      security: { ...bp.securityConfig },
    };

    // Save blueprint selection + configs + hierarchy, then handle tags
    this.lzService.updateLandingZone(zone.id, {
      settings: { ...(zone.settings || {}), blueprintId: bp.id },
      networkConfig: bp.networkConfig,
      iamConfig: bp.iamConfig,
      securityConfig: bp.securityConfig,
      namingConfig: bp.namingConfig,
      hierarchy: bp.hierarchy as unknown as Record<string, unknown>,
    }).subscribe({
      next: updated => {
        if (updated) this.landingZone.set(updated);

        // Delete existing tag policies first, then create from blueprint
        const existingTags = this.tagPolicies();
        const deleteOps = existingTags.map(tp =>
          firstValueFrom(this.lzService.deleteTagPolicy(zone.id, tp.id))
        );
        Promise.all(deleteOps).then(() => {
          for (const tag of bp.defaultTags) {
            this.lzService.createTagPolicy(zone.id, {
              tagKey: tag.tagKey,
              displayName: tag.displayName,
              isRequired: tag.isRequired,
              allowedValues: tag.allowedValues || null,
            }).subscribe({
              error: () => {},
            });
          }
          this.reloadZone();
        });
      },
    });

    this.toast.success(`Blueprint "${bp.name}" loaded`);
  }

  onStartBlank(): void {
    this.selectedBlueprintId.set('blank');
    this.currentHierarchy.set({ nodes: [] });
  }

  // ── Hierarchy tree events ───────────────────────────────────────

  onHierarchyChange(hierarchy: LandingZoneHierarchy): void {
    this.currentHierarchy.set(hierarchy);
    this.autoSave$.next();
  }

  onNodeSelected(nodeId: string | null): void {
    this.selectedNodeId.set(nodeId);
    // Clear any right panel override when selecting a node
    if (nodeId) {
      this.rightPanelOverride.set(null);
    }
  }

  onNodeChange(updatedNode: HierarchyNode): void {
    const hierarchy = this.currentHierarchy();
    if (!hierarchy) return;

    const updatedNodes = hierarchy.nodes.map(n =>
      n.id === updatedNode.id ? updatedNode : n
    );
    this.currentHierarchy.set({ nodes: updatedNodes });
    this.autoSave$.next();
  }

  // ── Hierarchy levels palette ────────────────────────────────────

  canAddLevel(level: HierarchyLevelDef): boolean {
    const hierarchy = this.currentHierarchy();
    const selectedId = this.selectedNodeId();
    const ph = this.providerHierarchy();
    if (!ph) return false;

    // If nothing selected: only the root type can be added
    if (!selectedId) {
      return level.typeId === ph.rootType;
    }

    // If a node is selected: check if this level is an allowed child
    const selectedNode = hierarchy?.nodes?.find(n => n.id === selectedId);
    if (!selectedNode) return false;
    const parentDef = this.levelDefsMap().get(selectedNode.typeId);
    return !!parentDef && parentDef.allowedChildren.includes(level.typeId);
  }

  levelTooltip(level: HierarchyLevelDef): string {
    if (this.canAddLevel(level)) {
      const selectedId = this.selectedNodeId();
      return selectedId
        ? `Add ${level.label} as child of selected node`
        : `Add ${level.label} as root node`;
    }
    const selectedId = this.selectedNodeId();
    if (!selectedId) return `Select a node first, or this must be the root type`;
    return `Cannot add ${level.label} as child of selected node type`;
  }

  addLevelToHierarchy(level: HierarchyLevelDef): void {
    if (!this.canAddLevel(level)) return;

    const hierarchy = this.currentHierarchy() || { nodes: [] };
    const parentId = this.selectedNodeId();

    const newNode: HierarchyNode = {
      id: crypto.randomUUID(),
      parentId: parentId,
      typeId: level.typeId,
      label: `New ${level.label}`,
      properties: {},
    };

    const updatedHierarchy: LandingZoneHierarchy = {
      nodes: [...hierarchy.nodes, newNode],
    };

    this.currentHierarchy.set(updatedHierarchy);
    this.selectedNodeId.set(newNode.id);
    this.rightPanelOverride.set(null);
    this.autoSave$.next();
  }

  // ── Right panel mode switches ──────────────────────────────────

  showRegionsPanel(): void {
    this.selectedNodeId.set(null);
    this.rightPanelOverride.set('regions');
  }

  showResolversPanel(): void {
    this.selectedNodeId.set(null);
    this.rightPanelOverride.set('resolvers');
    this.loadResolverData();
  }

  showFoundationPanel(): void {
    this.selectedNodeId.set(null);
    this.rightPanelOverride.set('foundation');
  }

  clearRightPanel(): void {
    this.rightPanelOverride.set(null);
  }

  // ── Save / Publish ──────────────────────────────────────────────

  onNameChange(): void {
    const zone = this.landingZone();
    if (!zone || this.isReadOnly()) return;
    this.lzService.updateLandingZone(zone.id, { name: this.zoneName.trim() }).subscribe();
  }

  onSave(): void {
    this.doAutoSave();
  }

  private doAutoSave(): void {
    const zone = this.landingZone();
    if (!zone || this.isReadOnly()) return;

    const hierarchy = this.currentHierarchy();
    if (hierarchy) {
      this.saving.set(true);
      this.lzService.updateLandingZone(zone.id, {
        hierarchy: hierarchy as unknown as Record<string, unknown>,
      }).subscribe({
        next: updated => {
          this.saving.set(false);
          if (updated) this.landingZone.set(updated);
        },
        error: () => this.saving.set(false),
      });
    }
  }

  onPublish(): void {
    const zone = this.landingZone();
    if (!zone) return;

    this.lzService.publishLandingZone(zone.id).subscribe({
      next: published => {
        this.landingZone.set(published);
        this.toast.success('Landing zone published');
      },
      error: err => this.toast.error(err.message || 'Failed to publish'),
    });
  }

  onValidate(): void {
    const zone = this.landingZone();
    if (!zone) return;

    this.lzService.validateLandingZone(zone.id).subscribe({
      next: v => {
        this.validation.set(v);
        this.parseNodeValidationErrors(v);
      },
      error: () => this.toast.error('Failed to validate'),
    });
  }

  // ── Foundation config ───────────────────────────────────────────

  onFoundationChange(section: string, values: Record<string, unknown>): void {
    this.foundationValues = { ...this.foundationValues, [section]: values };
  }

  saveFoundation(): void {
    const zone = this.landingZone();
    if (!zone) return;

    this.saving.set(true);
    this.lzService.updateLandingZone(zone.id, {
      networkConfig: this.foundationValues['network'] || null,
      iamConfig: this.foundationValues['iam'] || null,
      securityConfig: this.foundationValues['security'] || null,
    }).subscribe({
      next: updated => {
        this.saving.set(false);
        if (updated) {
          this.landingZone.set(updated);
          this.toast.success('Config saved');
        }
      },
      error: err => {
        this.saving.set(false);
        this.toast.error(err.message || 'Failed to save config');
      },
    });
  }

  // ── Regions ─────────────────────────────────────────────────────

  addRegion(): void {
    const zone = this.landingZone();
    if (!zone || !this.regionIdentifier.trim()) return;

    this.lzService.addRegion(zone.id, {
      regionIdentifier: this.regionIdentifier.trim(),
      displayName: this.regionDisplayName.trim() || this.regionIdentifier.trim(),
      isPrimary: this.regionIsPrimary,
      isDr: this.regionIsDr,
    }).subscribe({
      next: () => {
        this.showRegionForm = false;
        this.regionIdentifier = '';
        this.regionDisplayName = '';
        this.regionIsPrimary = false;
        this.regionIsDr = false;
        this.reloadZone();
        this.toast.success('Region added');
      },
      error: err => this.toast.error(err.message || 'Failed to add region'),
    });
  }

  removeRegion(regionId: string): void {
    const zone = this.landingZone();
    if (!zone) return;

    this.lzService.removeRegion(zone.id, regionId).subscribe({
      next: () => {
        this.reloadZone();
        this.toast.success('Region removed');
      },
      error: err => this.toast.error(err.message || 'Failed to remove region'),
    });
  }

  // ── Resolvers ──────────────────────────────────────────────────

  private loadResolverData(): void {
    const zone = this.landingZone();
    if (!zone) return;

    this.componentService.listResolvers().subscribe({
      next: resolvers => this.availableResolvers.set(resolvers),
    });
    this.componentService.listResolverConfigurations(zone.id).subscribe({
      next: configs => this.resolverConfigs.set(configs),
    });
  }

  onResolverTypeChange(): void {
    this.resolverConfigValues = {};
  }

  cancelResolverForm(): void {
    this.showResolverForm = false;
    this.resolverFormType = '';
    this.resolverConfigValues = {};
  }

  saveResolverConfig(): void {
    const zone = this.landingZone();
    if (!zone || !this.resolverFormType) return;

    this.componentService.setResolverConfiguration({
      resolverId: this.resolverFormType,
      config: { ...this.resolverConfigValues },
      landingZoneId: zone.id,
    }).subscribe({
      next: () => {
        this.cancelResolverForm();
        this.loadResolverData();
        this.toast.success('Resolver configuration saved');
      },
      error: err => this.toast.error(err.message || 'Failed to save resolver config'),
    });
  }

  deleteResolverConfig(configId: string): void {
    this.componentService.deleteResolverConfiguration(configId).subscribe({
      next: () => {
        this.loadResolverData();
        this.toast.success('Resolver configuration deleted');
      },
      error: err => this.toast.error(err.message || 'Failed to delete resolver config'),
    });
  }

  getConfigEntries(config: Record<string, unknown>): { key: string; value: string }[] {
    return Object.entries(config).map(([key, val]) => ({
      key,
      value: String(val),
    }));
  }

  // ── Helpers ─────────────────────────────────────────────────────

  private parseNodeValidationErrors(v: LandingZoneValidation): void {
    const errors = new Map<string, string[]>();
    const hierarchy = this.currentHierarchy();
    if (!hierarchy || !v.checks) {
      this.nodeValidationErrors.set(errors);
      return;
    }

    // Hierarchy checks contain node references in their key/message
    // Pattern: "node:<nodeId>:<check>" or message containing node labels
    for (const check of v.checks) {
      if (check.status === 'error' || check.status === 'warning') {
        // Try to match node IDs referenced in the check key
        const nodeIdMatch = check.key.match(/node:([a-f0-9-]+)/);
        if (nodeIdMatch) {
          const nodeId = nodeIdMatch[1];
          const existing = errors.get(nodeId) || [];
          existing.push(check.message);
          errors.set(nodeId, existing);
        }
      }
    }

    this.nodeValidationErrors.set(errors);
  }

  private reloadZone(): void {
    const zone = this.landingZone();
    if (!zone) return;
    this.lzService.getLandingZone(zone.id).subscribe({
      next: z => {
        if (z) {
          this.landingZone.set(z);
          if (z.hierarchy) {
            this.currentHierarchy.set(z.hierarchy);
          }
        }
      },
    });
  }

  goBack(): void {
    this.router.navigate(['/landing-zones']);
  }
}
