/**
 * Overview: Landing zone detail page — wizard for new zones, tabbed layout for configured zones.
 * Architecture: Feature component for landing zone configuration (Section 7.2)
 * Dependencies: @angular/core, @angular/router, landing-zone.service, cloud-backend.service, hierarchy-tree, hierarchy-node-config, zone-overview
 * Concepts: New zones get a step-by-step wizard (Blueprint > Strategy > Foundation > Regions > Review).
 *     Configured zones get a tabbed layout (Overview, Hierarchy, Network, IAM, Security, Regions, Resolvers).
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
import { BackendRegion, CloudBackend } from '@shared/models/cloud-backend.model';
import { ComponentService } from '@core/services/component.service';
import { Resolver, ResolverConfiguration } from '@shared/models/component.model';
import { HierarchyTreeComponent } from './hierarchy-tree/hierarchy-tree.component';
import { HierarchyNodeConfigComponent } from './hierarchy-node-config/hierarchy-node-config.component';
import { ZoneOverviewComponent } from './zone-overview/zone-overview.component';
import { SchemaFormRendererComponent } from '@shared/components/schema-form/schema-form-renderer.component';
import { EnvConfiguratorComponent } from '../environments/env-configurator/env-configurator.component';
import { LzStrategyComponent } from './lz-strategy/lz-strategy.component';
import { NetworkingService } from '@core/services/networking.service';
import {
  ConnectivityConfig,
  ConnectivityConfigInput,
  PeeringConfig,
  PeeringConfigInput,
  PrivateEndpointPolicy,
  PrivateEndpointPolicyInput,
  SharedLoadBalancer,
  SharedLoadBalancerInput,
} from '@shared/models/networking.model';

type WizardStep = 'blueprint' | 'region' | 'strategy' | 'foundation' | 'review';
type TabId = 'overview' | 'hierarchy' | 'network' | 'iam' | 'security' | 'regions' | 'connectivity' | 'peering' | 'endpoints' | 'loadbalancers' | 'resolvers';

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
    EnvConfiguratorComponent,
    LzStrategyComponent,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <nimbus-layout>
      <div class="page-container">
        @if (landingZone()) {
          <!-- Header -->
          <div class="page-header">
            <div class="header-left">
              <a class="back-link" (click)="goBack()">&larr; Landing Zones</a>
              <div class="title-row">
                <input
                  type="text"
                  class="name-input"
                  [(ngModel)]="zoneName"
                  [disabled]="isReadOnly()"
                  placeholder="Landing zone name..."
                  (change)="onNameChange()"
                />
                <span class="status-badge" [class]="'badge-' + landingZone()!.status.toLowerCase()">
                  {{ landingZone()!.status }}
                </span>
                <span class="version-badge">v{{ landingZone()!.version }}</span>
                @if (backend()) {
                  <span class="provider-badge">{{ backend()!.providerDisplayName }}</span>
                }
                @if (landingZone()?.region) {
                  <span class="provider-badge" style="background: #f0fdf4; color: #166534;">{{ landingZone()!.region!.displayName }}</span>
                }
              </div>
            </div>
            <div class="header-right">
              @if (!isReadOnly()) {
                <button class="btn btn-outline btn-sm" (click)="onSave()" [disabled]="saving()">
                  {{ saving() ? 'Saving...' : 'Save' }}
                </button>
                <button class="btn btn-primary btn-sm" (click)="onPublish()" [disabled]="saving()">Publish</button>
              }
              <button class="btn btn-outline btn-sm" (click)="onValidate()">Validate</button>
            </div>
          </div>

          <!-- Wizard mode: new/unconfigured zones -->
          @if (showWizard()) {
            <div class="wizard">
              <!-- Wizard step indicators -->
              <div class="wizard-steps">
                @for (step of wizardSteps; track step.id; let i = $index) {
                  <button
                    class="wizard-step"
                    [class.active]="wizardStep() === step.id"
                    [class.completed]="isWizardStepCompleted(step.id)"
                    (click)="wizardStep.set(step.id)"
                  >
                    <span class="step-num">{{ i + 1 }}</span>
                    <span class="step-label">{{ step.label }}</span>
                  </button>
                  @if (i < wizardSteps.length - 1) {
                    <span class="step-connector" [class.filled]="isWizardStepCompleted(step.id)"></span>
                  }
                }
              </div>

              <!-- Wizard content -->
              <div class="wizard-content">
                @if (wizardStep() === 'blueprint') {
                  <div class="section-card">
                    <h2 class="section-title">Quick Start with a Blueprint</h2>
                    <p class="section-desc">Choose a pre-built configuration or start from scratch. Blueprints provide a complete hierarchy, network, IAM, and security setup for common patterns.</p>
                    <div class="blueprint-grid">
                      @for (bp of blueprints(); track bp.id) {
                        <button
                          class="blueprint-card"
                          [class.selected]="selectedBlueprintId() === bp.id"
                          (click)="onSelectBlueprint(bp)"
                          [disabled]="isReadOnly()"
                        >
                          <div class="bp-header">
                            <span class="bp-name">{{ bp.name }}</span>
                            <span class="bp-complexity" [class]="'complexity-' + bp.complexity">{{ bp.complexity }}</span>
                          </div>
                          <div class="bp-desc">{{ bp.description }}</div>
                          <div class="bp-features">
                            @for (f of bp.features.slice(0, 4); track f) {
                              <span class="bp-feature">{{ f }}</span>
                            }
                            @if (bp.features.length > 4) {
                              <span class="bp-feature bp-more">+{{ bp.features.length - 4 }} more</span>
                            }
                          </div>
                        </button>
                      }
                      <button
                        class="blueprint-card blank-card"
                        [class.selected]="selectedBlueprintId() === 'blank'"
                        (click)="onStartBlank()"
                        [disabled]="isReadOnly()"
                      >
                        <span class="bp-name">Start from Scratch</span>
                        <div class="bp-desc">Build your own hierarchy manually. Recommended for advanced users who need full control.</div>
                      </button>
                    </div>
                  </div>
                }

                @if (wizardStep() === 'strategy') {
                  <div class="section-card">
                    <nimbus-lz-strategy
                      [providerName]="backend()?.providerName || ''"
                      [currentSettings]="landingZone()?.settings || {}"
                      [currentHierarchy]="currentHierarchy()"
                      (settingsChange)="onStrategySettingsChange($event)"
                      (hierarchyChange)="onStrategyHierarchyChange($event)"
                    />
                  </div>
                }

                @if (wizardStep() === 'foundation') {
                  <div class="section-card">
                    <h2 class="section-title">Foundation Configuration</h2>
                    <p class="section-desc">Configure the core infrastructure settings for your landing zone.</p>

                    <div class="foundation-accordion">
                      <button class="accordion-toggle" (click)="foundationSection = foundationSection === 'network' ? null : 'network'">
                        <span>Network</span>
                        <span class="chevron" [class.expanded]="foundationSection === 'network'">&#9206;</span>
                      </button>
                      @if (foundationSection === 'network') {
                        <div class="accordion-body">
                          <nimbus-env-configurator
                            domain="network"
                            [providerName]="backend()?.providerName || ''"
                            [currentValues]="foundationValues['network']"
                            [schema]="networkSchema()"
                            catalogSource="lz"
                            (valuesChange)="onFoundationChange('network', $event)"
                          />
                        </div>
                      }
                    </div>

                    <div class="foundation-accordion">
                      <button class="accordion-toggle" (click)="foundationSection = foundationSection === 'iam' ? null : 'iam'">
                        <span>IAM / Identity</span>
                        <span class="chevron" [class.expanded]="foundationSection === 'iam'">&#9206;</span>
                      </button>
                      @if (foundationSection === 'iam') {
                        <div class="accordion-body">
                          <nimbus-env-configurator
                            domain="iam"
                            [providerName]="backend()?.providerName || ''"
                            [currentValues]="foundationValues['iam']"
                            [schema]="iamConfigSchema()"
                            catalogSource="lz"
                            (valuesChange)="onFoundationChange('iam', $event)"
                          />
                        </div>
                      }
                    </div>

                    <div class="foundation-accordion">
                      <button class="accordion-toggle" (click)="foundationSection = foundationSection === 'security' ? null : 'security'">
                        <span>Security</span>
                        <span class="chevron" [class.expanded]="foundationSection === 'security'">&#9206;</span>
                      </button>
                      @if (foundationSection === 'security') {
                        <div class="accordion-body">
                          <nimbus-env-configurator
                            domain="security"
                            [providerName]="backend()?.providerName || ''"
                            [currentValues]="foundationValues['security']"
                            [schema]="securitySchema()"
                            catalogSource="lz"
                            (valuesChange)="onFoundationChange('security', $event)"
                          />
                        </div>
                      }
                    </div>
                  </div>
                }

                @if (wizardStep() === 'region') {
                  <div class="section-card">
                    <h2 class="section-title">Select Deployment Region</h2>
                    <p class="section-desc">Choose which backend region this landing zone will deploy to. Each landing zone is pinned to exactly one region. For multi-region deployments, create separate landing zones per region.</p>

                    @if (backendRegions().length === 0) {
                      <div class="empty-hint">
                        No regions configured on the backend. Go to the
                        <a class="link" (click)="goToBackendRegions()">Backend detail &rarr; Regions tab</a>
                        to add regions first.
                      </div>
                    }

                    @if (backendRegions().length > 0) {
                      <div class="region-select-grid">
                        @for (r of backendRegions(); track r.id) {
                          <button
                            class="region-select-card"
                            [class.selected]="selectedBackendRegionId() === r.id"
                            [class.disabled-region]="!r.isEnabled"
                            [disabled]="!r.isEnabled || isReadOnly()"
                            (click)="onSelectBackendRegion(r)"
                          >
                            <div class="rsc-header">
                              <span class="rsc-id">{{ r.regionIdentifier }}</span>
                              @if (!r.isEnabled) {
                                <span class="rsc-disabled-badge">Disabled</span>
                              }
                            </div>
                            <div class="rsc-name">{{ r.displayName }}</div>
                            @if (r.availabilityZones?.length) {
                              <div class="rsc-azs">
                                @for (az of r.availabilityZones; track az) {
                                  <span class="rsc-az">{{ az }}</span>
                                }
                              </div>
                            }
                          </button>
                        }
                      </div>
                    }
                  </div>
                }

                @if (wizardStep() === 'review') {
                  <div class="section-card">
                    <h2 class="section-title">Review & Validate</h2>
                    <p class="section-desc">Review your landing zone configuration before saving.</p>
                    <nimbus-zone-overview
                      [hierarchy]="currentHierarchy()"
                      [levelDefs]="levelDefsMap()"
                      [validation]="validation()"
                      [hubRegion]="landingZone()?.region || null"
                      [tagPolicies]="tagPolicies()"
                    />
                    <div class="form-actions">
                      <button class="btn btn-outline btn-sm" (click)="onValidate()">Run Validation</button>
                      <button class="btn btn-primary btn-sm" (click)="finishWizard()">Finish Setup</button>
                    </div>
                  </div>
                }
              </div>

              <!-- Wizard navigation -->
              <div class="wizard-nav">
                @if (wizardStepIndex() > 0) {
                  <button class="btn btn-outline btn-sm" (click)="prevWizardStep()">Back</button>
                }
                <div class="wizard-nav-spacer"></div>
                @if (wizardStepIndex() < wizardSteps.length - 1) {
                  <button class="btn btn-primary btn-sm" (click)="nextWizardStep()">Continue</button>
                }
                <button class="btn btn-outline btn-sm" (click)="skipWizard()">Skip to Tabs</button>
              </div>
            </div>
          } @else {
            <!-- Tabbed mode: configured zones -->
            <div class="tabs">
              @for (tab of tabs; track tab.id) {
                <button
                  class="tab"
                  [class.active]="activeTab() === tab.id"
                  (click)="switchTab(tab.id)"
                >{{ tab.label }}
                  @if (tab.id === 'resolvers') {
                    <span class="tab-count">{{ resolverConfigs().length }}</span>
                  }
                </button>
              }
            </div>

            <!-- Tab: Overview -->
            @if (activeTab() === 'overview') {
              <div class="tab-content">
                <div class="section-card">
                  <nimbus-zone-overview
                    [hierarchy]="currentHierarchy()"
                    [levelDefs]="levelDefsMap()"
                    [validation]="validation()"
                    [hubRegion]="landingZone()?.region || null"
                    [tagPolicies]="tagPolicies()"
                  />
                </div>

                @if (selectedBlueprintId() && selectedBlueprintId() !== 'blank') {
                  <div class="section-card">
                    <h2 class="section-title">Blueprint</h2>
                    <p class="config-value">{{ getSelectedBlueprintName() }}</p>
                  </div>
                }
              </div>
            }

            <!-- Tab: Hierarchy -->
            @if (activeTab() === 'hierarchy') {
              <div class="tab-content">
                <!-- Org Strategy section -->
                <div class="section-card">
                  <nimbus-lz-strategy
                    [providerName]="backend()?.providerName || ''"
                    [currentSettings]="landingZone()?.settings || {}"
                    [currentHierarchy]="currentHierarchy()"
                    (settingsChange)="onStrategySettingsChange($event)"
                    (hierarchyChange)="onStrategyHierarchyChange($event)"
                  />
                </div>

                <!-- Hierarchy tree + node config split -->
                <div class="hierarchy-layout">
                  <div class="hierarchy-left">
                    <!-- Levels palette -->
                    @if (hierarchyLevels().length > 0) {
                      <div class="palette-bar">
                        <span class="palette-label">Add level:</span>
                        @for (level of hierarchyLevels(); track level.typeId) {
                          <button
                            class="palette-chip"
                            [class.disabled]="!canAddLevel(level)"
                            [disabled]="isReadOnly() || !canAddLevel(level)"
                            (click)="addLevelToHierarchy(level)"
                            [title]="levelTooltip(level)"
                          >
                            <span class="chip-icon">{{ level.icon }}</span>
                            {{ level.label }}
                          </button>
                        }
                      </div>
                    }
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
                  <div class="hierarchy-right">
                    @if (selectedNode()) {
                      <nimbus-hierarchy-node-config
                        [node]="selectedNode()!"
                        [allNodes]="currentHierarchy()?.nodes || []"
                        [levelDef]="selectedLevelDef()"
                        [providerName]="backend()?.providerName || ''"
                        [readOnly]="isReadOnly()"
                        (nodeChange)="onNodeChange($event)"
                      />
                    } @else {
                      <div class="node-hint">
                        <p>Select a node in the tree to configure it, or add a new level using the palette above.</p>
                      </div>
                    }
                  </div>
                </div>
              </div>
            }

            <!-- Tab: Network -->
            @if (activeTab() === 'network') {
              <div class="tab-content">
                <div class="section-card">
                  <div class="section-header">
                    <h2 class="section-title">Network Configuration</h2>
                  </div>
                  <nimbus-env-configurator
                    domain="network"
                    [providerName]="backend()?.providerName || ''"
                    [currentValues]="foundationValues['network']"
                    [schema]="networkSchema()"
                    catalogSource="lz"
                    (valuesChange)="onFoundationChange('network', $event)"
                  />
                  @if (!isReadOnly()) {
                    <div class="form-actions">
                      <button class="btn btn-primary btn-sm" (click)="saveFoundation()" [disabled]="saving()">Save Network Config</button>
                    </div>
                  }
                </div>
              </div>
            }

            <!-- Tab: IAM -->
            @if (activeTab() === 'iam') {
              <div class="tab-content">
                <div class="section-card">
                  <div class="section-header">
                    <h2 class="section-title">IAM / Identity Configuration</h2>
                  </div>
                  <nimbus-env-configurator
                    domain="iam"
                    [providerName]="backend()?.providerName || ''"
                    [currentValues]="foundationValues['iam']"
                    [schema]="iamConfigSchema()"
                    catalogSource="lz"
                    (valuesChange)="onFoundationChange('iam', $event)"
                  />
                  @if (!isReadOnly()) {
                    <div class="form-actions">
                      <button class="btn btn-primary btn-sm" (click)="saveFoundation()" [disabled]="saving()">Save IAM Config</button>
                    </div>
                  }
                </div>
              </div>
            }

            <!-- Tab: Security -->
            @if (activeTab() === 'security') {
              <div class="tab-content">
                <div class="section-card">
                  <div class="section-header">
                    <h2 class="section-title">Security Configuration</h2>
                  </div>
                  <nimbus-env-configurator
                    domain="security"
                    [providerName]="backend()?.providerName || ''"
                    [currentValues]="foundationValues['security']"
                    [schema]="securitySchema()"
                    catalogSource="lz"
                    (valuesChange)="onFoundationChange('security', $event)"
                  />
                  @if (!isReadOnly()) {
                    <div class="form-actions">
                      <button class="btn btn-primary btn-sm" (click)="saveFoundation()" [disabled]="saving()">Save Security Config</button>
                    </div>
                  }
                </div>
              </div>
            }

            <!-- Tab: Regions -->
            @if (activeTab() === 'regions') {
              <div class="tab-content">
                <!-- Hub Region (pinned) -->
                <div class="section-card">
                  <h2 class="section-title">Hub Region</h2>
                  <p class="section-desc">This landing zone is pinned to one backend region for hub infrastructure.</p>
                  @if (landingZone()?.region; as reg) {
                    <div class="region-item">
                      <div class="region-info">
                        <span class="region-name">{{ reg.displayName }}</span>
                        <span class="region-id">{{ reg.regionIdentifier }}</span>
                        <span class="region-badge primary">Hub</span>
                      </div>
                    </div>
                  } @else {
                    <p class="empty-hint">No hub region assigned.
                      @if (!isReadOnly()) {
                        <button class="btn btn-primary btn-sm" style="margin-left: 8px" (click)="showRegionPicker = true">Select Region</button>
                      }
                    </p>
                  }
                  @if (showRegionPicker) {
                    <div class="region-select-grid" style="margin-top: 12px">
                      @for (r of backendRegions(); track r.id) {
                        <button
                          class="region-select-card"
                          [class.selected]="selectedBackendRegionId() === r.id"
                          [class.disabled-region]="!r.isEnabled"
                          [disabled]="!r.isEnabled || isReadOnly()"
                          (click)="onSelectBackendRegion(r); showRegionPicker = false"
                        >
                          <div class="rsc-header">
                            <span class="rsc-id">{{ r.regionIdentifier }}</span>
                          </div>
                          <div class="rsc-name">{{ r.displayName }}</div>
                        </button>
                      }
                    </div>
                  }
                </div>

                <!-- Available Backend Regions (read-only reference) -->
                <div class="section-card">
                  <h2 class="section-title">Available Backend Regions</h2>
                  <p class="section-desc">All regions configured on this backend. Environments can be pinned to any enabled region.</p>
                  @if (backendRegions().length === 0) {
                    <p class="empty-hint">No regions configured on the backend.</p>
                  }
                  @for (r of backendRegions(); track r.id) {
                    <div class="region-item">
                      <div class="region-info">
                        <span class="region-name">{{ r.displayName }}</span>
                        <span class="region-id">{{ r.regionIdentifier }}</span>
                        @if (!r.isEnabled) { <span class="region-badge dr">Disabled</span> }
                        @if (r.id === landingZone()?.regionId) { <span class="region-badge primary">Hub</span> }
                      </div>
                    </div>
                  }
                </div>
              </div>
            }

            <!-- Tab: Connectivity -->
            @if (activeTab() === 'connectivity') {
              <div class="tab-content">
                <div class="section-card">
                  <div class="section-header">
                    <h2 class="section-title">Connectivity</h2>
                    @if (!isReadOnly()) {
                      <button class="btn btn-primary btn-sm" (click)="showConnForm = true">Add Connection</button>
                    }
                  </div>
                  <p class="section-desc">VPN, ExpressRoute, Direct Connect, and other connectivity configurations for this landing zone.</p>

                  @if (showConnForm) {
                    <div class="inline-form">
                      <div class="form-grid">
                        <div class="form-group">
                          <label class="form-label">Name</label>
                          <input class="form-input" [(ngModel)]="connName" placeholder="e.g. Primary VPN" />
                        </div>
                        <div class="form-group">
                          <label class="form-label">Type</label>
                          <select class="form-input" [(ngModel)]="connType">
                            <option value="">Select...</option>
                            <option value="VPN">VPN</option>
                            <option value="EXPRESS_ROUTE">ExpressRoute</option>
                            <option value="DIRECT_CONNECT">Direct Connect</option>
                            <option value="FAST_CONNECT">Fast Connect</option>
                            <option value="HA_VPN">HA VPN</option>
                            <option value="CLOUD_INTERCONNECT">Cloud Interconnect</option>
                            <option value="SDN_OVERLAY">SDN Overlay</option>
                          </select>
                        </div>
                      </div>
                      <div class="form-grid">
                        <div class="form-group">
                          <label class="form-label">Provider</label>
                          <input class="form-input" [(ngModel)]="connProvider" placeholder="e.g. aws, azure" />
                        </div>
                        <div class="form-group">
                          <label class="form-label">Description</label>
                          <input class="form-input" [(ngModel)]="connDescription" />
                        </div>
                      </div>
                      <div class="form-actions">
                        <button class="btn btn-outline btn-sm" (click)="showConnForm = false">Cancel</button>
                        <button class="btn btn-primary btn-sm" (click)="createConnectivity()"
                          [disabled]="!connName.trim() || !connType">Create</button>
                      </div>
                    </div>
                  }

                  @if (connectivityConfigs().length === 0 && !showConnForm) {
                    <p class="empty-hint">No connectivity configurations. Add VPN, ExpressRoute, or other connections.</p>
                  }
                  @for (c of connectivityConfigs(); track c.id) {
                    <div class="net-item">
                      <div class="net-item-info">
                        <span class="net-item-name">{{ c.name }}</span>
                        <span class="status-badge badge-active">{{ c.connectivityType }}</span>
                        <span class="net-item-meta">{{ c.providerType }}</span>
                        <span class="status-badge" [class]="'badge-' + c.status.toLowerCase()">{{ c.status }}</span>
                      </div>
                      @if (!isReadOnly()) {
                        <button class="action-btn danger" (click)="deleteConnectivity(c.id)">&times;</button>
                      }
                    </div>
                  }
                </div>
              </div>
            }

            <!-- Tab: Peering -->
            @if (activeTab() === 'peering') {
              <div class="tab-content">
                <div class="section-card">
                  <div class="section-header">
                    <h2 class="section-title">Peering</h2>
                    @if (!isReadOnly()) {
                      <button class="btn btn-primary btn-sm" (click)="showPeerForm = true">Add Peering</button>
                    }
                  </div>
                  <p class="section-desc">Hub-to-spoke peering, transit gateway attachments, and VPC/VNet peering configurations.</p>

                  @if (showPeerForm) {
                    <div class="inline-form">
                      <div class="form-grid">
                        <div class="form-group">
                          <label class="form-label">Name</label>
                          <input class="form-input" [(ngModel)]="peerName" placeholder="e.g. Hub-Spoke Peering" />
                        </div>
                        <div class="form-group">
                          <label class="form-label">Peering Type</label>
                          <select class="form-input" [(ngModel)]="peerType">
                            <option value="">Select...</option>
                            <option value="VPC_PEERING">VPC Peering</option>
                            <option value="VNET_PEERING">VNet Peering</option>
                            <option value="TGW_ATTACHMENT">TGW Attachment</option>
                            <option value="DRG_ATTACHMENT">DRG Attachment</option>
                            <option value="SHARED_VPC">Shared VPC</option>
                          </select>
                        </div>
                      </div>
                      <div class="form-actions">
                        <button class="btn btn-outline btn-sm" (click)="showPeerForm = false">Cancel</button>
                        <button class="btn btn-primary btn-sm" (click)="createPeering()"
                          [disabled]="!peerName.trim() || !peerType">Create</button>
                      </div>
                    </div>
                  }

                  @if (peeringConfigs().length === 0 && !showPeerForm) {
                    <p class="empty-hint">No peering configurations.</p>
                  }
                  @for (p of peeringConfigs(); track p.id) {
                    <div class="net-item">
                      <div class="net-item-info">
                        <span class="net-item-name">{{ p.name }}</span>
                        <span class="status-badge badge-active">{{ p.peeringType }}</span>
                        <span class="status-badge" [class]="'badge-' + p.status.toLowerCase()">{{ p.status }}</span>
                      </div>
                      @if (!isReadOnly()) {
                        <button class="action-btn danger" (click)="deletePeering(p.id)">&times;</button>
                      }
                    </div>
                  }
                </div>
              </div>
            }

            <!-- Tab: Private Endpoints -->
            @if (activeTab() === 'endpoints') {
              <div class="tab-content">
                <div class="section-card">
                  <div class="section-header">
                    <h2 class="section-title">Private Endpoint Policies</h2>
                    @if (!isReadOnly()) {
                      <button class="btn btn-primary btn-sm" (click)="showEndpointForm = true">Add Policy</button>
                    }
                  </div>
                  <p class="section-desc">Landing zone-level private endpoint policies. Per-environment endpoints inherit from these.</p>

                  @if (showEndpointForm) {
                    <div class="inline-form">
                      <div class="form-grid">
                        <div class="form-group">
                          <label class="form-label">Policy Name</label>
                          <input class="form-input" [(ngModel)]="epName" placeholder="e.g. S3 Private Endpoint" />
                        </div>
                        <div class="form-group">
                          <label class="form-label">Service Name</label>
                          <input class="form-input" [(ngModel)]="epServiceName" placeholder="e.g. com.amazonaws.us-east-1.s3" />
                        </div>
                      </div>
                      <div class="form-grid">
                        <div class="form-group">
                          <label class="form-label">Endpoint Type</label>
                          <select class="form-input" [(ngModel)]="epEndpointType">
                            <option value="">Select...</option>
                            <option value="PRIVATE_LINK">Private Link</option>
                            <option value="PRIVATE_ENDPOINT">Private Endpoint</option>
                            <option value="PRIVATE_SERVICE_CONNECT">Private Service Connect</option>
                            <option value="SERVICE_GATEWAY">Service Gateway</option>
                          </select>
                        </div>
                        <div class="form-group">
                          <label class="form-label">Provider</label>
                          <input class="form-input" [(ngModel)]="epProvider" placeholder="e.g. aws" />
                        </div>
                      </div>
                      <div class="form-actions">
                        <button class="btn btn-outline btn-sm" (click)="showEndpointForm = false">Cancel</button>
                        <button class="btn btn-primary btn-sm" (click)="createEndpointPolicy()"
                          [disabled]="!epName.trim() || !epServiceName.trim() || !epEndpointType || !epProvider.trim()">Create</button>
                      </div>
                    </div>
                  }

                  @if (endpointPolicies().length === 0 && !showEndpointForm) {
                    <p class="empty-hint">No private endpoint policies.</p>
                  }
                  @for (ep of endpointPolicies(); track ep.id) {
                    <div class="net-item">
                      <div class="net-item-info">
                        <span class="net-item-name">{{ ep.name }}</span>
                        <span class="status-badge badge-active">{{ ep.endpointType }}</span>
                        <span class="net-item-meta">{{ ep.serviceName }}</span>
                        <span class="status-badge" [class]="'badge-' + ep.status.toLowerCase()">{{ ep.status }}</span>
                      </div>
                      @if (!isReadOnly()) {
                        <button class="action-btn danger" (click)="deleteEndpointPolicy(ep.id)">&times;</button>
                      }
                    </div>
                  }
                </div>
              </div>
            }

            <!-- Tab: Load Balancers -->
            @if (activeTab() === 'loadbalancers') {
              <div class="tab-content">
                <div class="section-card">
                  <div class="section-header">
                    <h2 class="section-title">Shared Load Balancers</h2>
                    @if (!isReadOnly()) {
                      <button class="btn btn-primary btn-sm" (click)="showLbForm = true">Add Load Balancer</button>
                    }
                  </div>
                  <p class="section-desc">Hub-level shared load balancers. Environments can link to these or create their own.</p>

                  @if (showLbForm) {
                    <div class="inline-form">
                      <div class="form-grid">
                        <div class="form-group">
                          <label class="form-label">Name</label>
                          <input class="form-input" [(ngModel)]="lbName" placeholder="e.g. Shared ALB" />
                        </div>
                        <div class="form-group">
                          <label class="form-label">LB Type</label>
                          <select class="form-input" [(ngModel)]="lbType">
                            <option value="">Select...</option>
                            <option value="ALB">ALB</option>
                            <option value="NLB">NLB</option>
                            <option value="APP_GATEWAY">App Gateway</option>
                            <option value="AZURE_LB">Azure LB</option>
                            <option value="GCP_LB">GCP LB</option>
                            <option value="OCI_LB">OCI LB</option>
                          </select>
                        </div>
                      </div>
                      <div class="form-group">
                        <label class="form-label">Provider</label>
                        <input class="form-input" [(ngModel)]="lbProvider" placeholder="e.g. aws" />
                      </div>
                      <div class="form-actions">
                        <button class="btn btn-outline btn-sm" (click)="showLbForm = false">Cancel</button>
                        <button class="btn btn-primary btn-sm" (click)="createSharedLb()"
                          [disabled]="!lbName.trim() || !lbType || !lbProvider.trim()">Create</button>
                      </div>
                    </div>
                  }

                  @if (sharedLoadBalancers().length === 0 && !showLbForm) {
                    <p class="empty-hint">No shared load balancers.</p>
                  }
                  @for (lb of sharedLoadBalancers(); track lb.id) {
                    <div class="net-item">
                      <div class="net-item-info">
                        <span class="net-item-name">{{ lb.name }}</span>
                        <span class="status-badge badge-active">{{ lb.lbType }}</span>
                        <span class="net-item-meta">{{ lb.providerType }}</span>
                        <span class="status-badge" [class]="'badge-' + lb.status.toLowerCase()">{{ lb.status }}</span>
                      </div>
                      @if (!isReadOnly()) {
                        <button class="action-btn danger" (click)="deleteSharedLb(lb.id)">&times;</button>
                      }
                    </div>
                  }
                </div>
              </div>
            }

            <!-- Tab: Resolvers -->
            @if (activeTab() === 'resolvers') {
              <div class="tab-content">
                <div class="section-card">
                  <div class="section-header">
                    <h2 class="section-title">Resolver Configurations</h2>
                    @if (!isReadOnly()) {
                      <button class="btn btn-primary btn-sm" (click)="showResolverForm = true">Add Config</button>
                    }
                  </div>

                  @if (showResolverForm) {
                    <div class="inline-form">
                      <div class="form-group">
                        <label class="form-label">Resolver Type</label>
                        <select class="form-input" [(ngModel)]="resolverFormType" (ngModelChange)="onResolverTypeChange()">
                          <option value="">Select resolver...</option>
                          @for (r of availableResolvers(); track r.id) {
                            <option [value]="r.id">{{ r.displayName }}</option>
                          }
                        </select>
                      </div>
                      @if (selectedResolverDef(); as rDef) {
                        <p class="empty-hint">{{ rDef.description }}</p>
                        @for (f of resolverConfigFields(); track f.key) {
                          <div class="form-group">
                            <label class="form-label">{{ f.label }}</label>
                            <input class="form-input" [(ngModel)]="resolverConfigValues[f.key]" [placeholder]="f.placeholder" />
                          </div>
                        }
                      }
                      <div class="form-actions">
                        <button class="btn btn-outline btn-sm" (click)="cancelResolverForm()">Cancel</button>
                        <button class="btn btn-primary btn-sm" (click)="saveResolverConfig()" [disabled]="!resolverFormType">Save</button>
                      </div>
                    </div>
                  }

                  @if (resolverConfigs().length === 0 && !showResolverForm) {
                    <p class="empty-hint">No resolver configurations.</p>
                  }
                  @for (rc of resolverConfigs(); track rc.id) {
                    <div class="resolver-item">
                      <div class="resolver-item-header">
                        <span class="status-badge badge-active">{{ rc.resolverType }}</span>
                        <div class="resolver-config-kv">
                          @for (entry of getConfigEntries(rc.config); track entry.key) {
                            <span class="config-kv-pair">{{ entry.key }}: {{ entry.value }}</span>
                          }
                        </div>
                      </div>
                      @if (!isReadOnly()) {
                        <button class="action-btn danger" (click)="deleteResolverConfig(rc.id)">Delete</button>
                      }
                    </div>
                  }
                </div>
              </div>
            }
          }

          <!-- Validation bar -->
          @if (validationErrors().length > 0) {
            <div class="validation-bar">
              @for (err of validationErrors(); track err.message) {
                <span class="validation-error">{{ err.message }}</span>
              }
            </div>
          }
        } @else if (loading()) {
          <div class="loading-text">Loading landing zone...</div>
        } @else {
          <div class="loading-text">Landing zone not found</div>
        }
      </div>
    </nimbus-layout>
  `,
  styles: [`
    .page-container { padding: 0; max-width: 1200px; }

    /* ── Header ──────────────────────────────── */
    .page-header {
      display: flex; justify-content: space-between; align-items: flex-start;
      margin-bottom: 1rem;
    }
    .header-left { display: flex; flex-direction: column; gap: 4px; }
    .header-right { display: flex; gap: 8px; align-items: center; }
    .back-link {
      font-size: 0.8125rem; color: #3b82f6; cursor: pointer;
      text-decoration: none; margin-bottom: 4px;
    }
    .back-link:hover { text-decoration: underline; }
    .title-row { display: flex; align-items: center; gap: 12px; }
    .name-input {
      padding: 6px 10px; border: 1px solid #e2e8f0; border-radius: 6px;
      font-size: 1.25rem; font-weight: 700; color: #1e293b; background: #fff;
      min-width: 280px; outline: none; font-family: inherit;
    }
    .name-input:focus { border-color: #3b82f6; }
    .name-input:disabled { background: #f8fafc; }

    .status-badge {
      display: inline-block; padding: 2px 8px; border-radius: 12px;
      font-size: 0.6875rem; font-weight: 600; text-transform: uppercase;
    }
    .badge-draft { background: #fef3c7; color: #92400e; }
    .badge-published { background: #d1fae5; color: #065f46; }
    .badge-archived { background: #f1f5f9; color: #64748b; }
    .badge-active { background: #d1fae5; color: #065f46; }
    .version-badge { font-size: 0.6875rem; color: #94a3b8; font-weight: 500; }
    .provider-badge {
      padding: 2px 8px; border-radius: 12px; font-size: 0.6875rem;
      font-weight: 600; background: #dbeafe; color: #1d4ed8;
    }

    /* ── Buttons ──────────────────────────────── */
    .btn {
      padding: 8px 16px; border-radius: 6px; font-size: 0.875rem; font-weight: 500;
      cursor: pointer; border: none; font-family: inherit; display: inline-flex;
      align-items: center; transition: background 0.15s;
    }
    .btn-sm { padding: 6px 12px; font-size: 0.8125rem; }
    .btn-primary { background: #3b82f6; color: #fff; }
    .btn-primary:hover { background: #2563eb; }
    .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
    .btn-outline { background: #fff; color: #374151; border: 1px solid #e2e8f0; }
    .btn-outline:hover { background: #f8fafc; }

    /* ── Wizard ───────────────────────────────── */
    .wizard { }
    .wizard-steps {
      display: flex; align-items: center; gap: 0;
      padding: 16px 0; margin-bottom: 16px;
    }
    .wizard-step {
      display: flex; align-items: center; gap: 8px;
      padding: 8px 16px; background: #fff; border: 1px solid #e2e8f0;
      border-radius: 8px; cursor: pointer; font-family: inherit;
      transition: all 0.15s;
    }
    .wizard-step:hover { border-color: #3b82f6; }
    .wizard-step.active { border-color: #3b82f6; background: #eff6ff; }
    .wizard-step.completed { border-color: #22c55e; }
    .step-num {
      display: inline-flex; align-items: center; justify-content: center;
      width: 22px; height: 22px; border-radius: 50%; font-size: 0.6875rem;
      font-weight: 700; background: #f1f5f9; color: #64748b;
    }
    .wizard-step.active .step-num { background: #3b82f6; color: #fff; }
    .wizard-step.completed .step-num { background: #22c55e; color: #fff; }
    .step-label { font-size: 0.8125rem; font-weight: 500; color: #374151; }
    .step-connector {
      flex: 0 0 24px; height: 2px; background: #e2e8f0;
    }
    .step-connector.filled { background: #22c55e; }

    .wizard-content { margin-bottom: 16px; }
    .wizard-nav {
      display: flex; align-items: center; gap: 8px;
      padding: 12px 0; border-top: 1px solid #e2e8f0;
    }
    .wizard-nav-spacer { flex: 1; }

    /* ── Tab bar ──────────────────────────────── */
    .tabs { display: flex; gap: 0; border-bottom: 2px solid #e2e8f0; margin-bottom: 1.5rem; }
    .tab {
      padding: 0.625rem 0.875rem; font-size: 0.8125rem; font-weight: 500; color: #64748b;
      background: none; border: none; cursor: pointer; border-bottom: 2px solid transparent;
      margin-bottom: -2px; font-family: inherit; display: inline-flex; align-items: center; gap: 6px;
    }
    .tab:hover { color: #1e293b; }
    .tab.active { color: #3b82f6; border-bottom-color: #3b82f6; }
    .tab-count {
      background: #f1f5f9; color: #64748b; padding: 1px 6px;
      border-radius: 8px; font-size: 0.625rem; font-weight: 600;
    }

    .tab-content { }

    /* ── Section card ─────────────────────────── */
    .section-card {
      background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
      padding: 20px; margin-bottom: 16px;
    }
    .section-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
    .section-title { font-size: 1rem; font-weight: 600; color: #1e293b; margin: 0; }
    .section-desc { font-size: 0.8125rem; color: #64748b; margin: 0 0 16px; line-height: 1.5; }
    .config-value { font-size: 0.8125rem; color: #374151; }

    /* ── Blueprint grid ──────────────────────── */
    .blueprint-grid {
      display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
      gap: 12px;
    }
    .blueprint-card {
      display: flex; flex-direction: column; text-align: left; padding: 16px;
      background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
      cursor: pointer; font-family: inherit; transition: border-color 0.15s;
    }
    .blueprint-card:hover:not(:disabled) { border-color: #3b82f6; }
    .blueprint-card.selected { border-color: #3b82f6; background: #eff6ff; }
    .blueprint-card:disabled { opacity: 0.5; cursor: not-allowed; }
    .blank-card { border-style: dashed; }
    .bp-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px; }
    .bp-name { font-size: 0.875rem; font-weight: 600; color: #1e293b; }
    .bp-complexity {
      padding: 2px 8px; border-radius: 10px; font-size: 0.5625rem;
      font-weight: 700; text-transform: uppercase;
    }
    .complexity-basic { background: #dcfce7; color: #166534; }
    .complexity-standard { background: #dbeafe; color: #1d4ed8; }
    .complexity-advanced { background: #ede9fe; color: #6d28d9; }
    .bp-desc { font-size: 0.75rem; color: #64748b; margin-bottom: 8px; line-height: 1.4; }
    .bp-features { display: flex; flex-wrap: wrap; gap: 4px; }
    .bp-feature {
      padding: 2px 6px; background: #f1f5f9; border-radius: 4px;
      font-size: 0.625rem; color: #475569;
    }
    .bp-more { font-style: italic; color: #94a3b8; }

    /* ── Foundation accordion ─────────────────── */
    .foundation-accordion { border-bottom: 1px solid #f1f5f9; }
    .accordion-toggle {
      display: flex; align-items: center; justify-content: space-between;
      width: 100%; padding: 12px 0; background: none; border: none;
      font-size: 0.875rem; font-weight: 600; color: #374151;
      cursor: pointer; font-family: inherit;
    }
    .accordion-toggle:hover { color: #1e293b; }
    .accordion-body { padding-bottom: 12px; }
    .chevron { font-size: 0.625rem; transition: transform 0.2s; transform: rotate(180deg); }
    .chevron.expanded { transform: rotate(0deg); }

    /* ── Hierarchy tab layout ────────────────── */
    .hierarchy-layout {
      display: grid; grid-template-columns: 1fr 360px; gap: 16px;
      min-height: 400px;
    }
    .hierarchy-left { display: flex; flex-direction: column; gap: 8px; min-height: 0; }
    .hierarchy-right {
      background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
      overflow-y: auto; padding: 12px;
    }
    .node-hint {
      display: flex; align-items: center; justify-content: center;
      height: 100%; color: #94a3b8; font-size: 0.8125rem; text-align: center;
      padding: 24px;
    }
    .node-hint p { margin: 0; line-height: 1.5; }

    /* ── Palette bar ─────────────────────────── */
    .palette-bar {
      display: flex; align-items: center; gap: 6px; flex-wrap: wrap;
      padding: 8px 12px; background: #fff; border: 1px solid #e2e8f0;
      border-radius: 8px;
    }
    .palette-label { font-size: 0.6875rem; font-weight: 600; color: #64748b; }
    .palette-chip {
      display: inline-flex; align-items: center; gap: 4px;
      padding: 4px 10px; background: #f8fafc; border: 1px solid #e2e8f0;
      border-radius: 6px; cursor: pointer; font-family: inherit;
      font-size: 0.75rem; color: #374151; transition: all 0.15s;
    }
    .palette-chip:hover:not(:disabled) { border-color: #3b82f6; background: #eff6ff; }
    .palette-chip.disabled, .palette-chip:disabled {
      opacity: 0.35; cursor: not-allowed;
    }
    .chip-icon { font-size: 0.875rem; }

    /* ── Forms ────────────────────────────────── */
    .inline-form {
      background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px;
      padding: 16px; margin-bottom: 16px;
    }
    .form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
    .form-group { display: flex; flex-direction: column; gap: 4px; margin-bottom: 8px; }
    .form-label {
      font-size: 0.75rem; font-weight: 600; color: #64748b;
      text-transform: uppercase; letter-spacing: 0.04em;
    }
    .form-input {
      padding: 8px 12px; border: 1px solid #e2e8f0; border-radius: 6px;
      font-size: 0.8125rem; color: #1e293b; background: #fff;
      outline: none; font-family: inherit;
    }
    .form-input:focus { border-color: #3b82f6; }
    .form-row-checks { display: flex; gap: 16px; margin-bottom: 8px; }
    .check-label {
      font-size: 0.75rem; color: #374151; display: flex; align-items: center; gap: 4px; cursor: pointer;
    }
    .form-actions { display: flex; gap: 8px; margin-top: 16px; }

    /* ── Region items ─────────────────────────── */
    .region-item {
      display: flex; justify-content: space-between; align-items: center;
      padding: 10px 12px; border-bottom: 1px solid #f1f5f9;
    }
    .region-item:last-child { border-bottom: none; }
    .region-info { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
    .region-name { font-size: 0.8125rem; font-weight: 500; color: #1e293b; }
    .region-id { font-size: 0.75rem; color: #94a3b8; font-family: monospace; }
    .region-badge {
      padding: 2px 6px; border-radius: 8px; font-size: 0.625rem;
      font-weight: 600; text-transform: uppercase;
    }
    .region-badge.primary { background: #dbeafe; color: #1d4ed8; }
    .region-badge.dr { background: #fef3c7; color: #92400e; }

    /* ── Networking items ─────────────────────────── */
    .net-item {
      display: flex; justify-content: space-between; align-items: center;
      padding: 10px 12px; border: 1px solid #e2e8f0; border-radius: 6px;
      margin-bottom: 8px; background: #f8fafc;
    }
    .net-item-info { display: flex; align-items: center; gap: 8px; flex: 1; flex-wrap: wrap; }
    .net-item-name { font-size: 0.8125rem; font-weight: 500; color: #1e293b; }
    .net-item-meta { font-size: 0.75rem; color: #64748b; font-family: monospace; }
    .badge-planned { background: #fef3c7; color: #92400e; }
    .badge-provisioning { background: #dbeafe; color: #1d4ed8; }
    .badge-failed { background: #fef2f2; color: #dc2626; }
    .badge-decommissioned { background: #f1f5f9; color: #64748b; }

    /* ── Region select grid ─────────────────────── */
    .region-select-grid {
      display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
      gap: 10px;
    }
    .region-select-card {
      display: flex; flex-direction: column; text-align: left; padding: 12px 16px;
      background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
      cursor: pointer; font-family: inherit; transition: border-color 0.15s;
    }
    .region-select-card:hover:not(:disabled) { border-color: #3b82f6; }
    .region-select-card.selected { border-color: #3b82f6; background: #eff6ff; }
    .region-select-card:disabled { opacity: 0.45; cursor: not-allowed; }
    .disabled-region { border-style: dashed; }
    .rsc-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px; }
    .rsc-id {
      font-family: 'Cascadia Code', 'Fira Code', monospace; font-size: 0.75rem;
      font-weight: 600; color: #1d4ed8;
    }
    .rsc-disabled-badge {
      font-size: 0.5625rem; font-weight: 600; color: #94a3b8;
      background: #f1f5f9; padding: 1px 6px; border-radius: 8px; text-transform: uppercase;
    }
    .rsc-name { font-size: 0.8125rem; font-weight: 500; color: #1e293b; }
    .rsc-azs { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 6px; }
    .rsc-az {
      padding: 1px 6px; background: #f0fdf4; color: #166534; border-radius: 4px;
      font-size: 0.5625rem; font-family: 'Cascadia Code', 'Fira Code', monospace;
    }
    .link { color: #3b82f6; cursor: pointer; text-decoration: none; }
    .link:hover { text-decoration: underline; }

    /* ── Resolver items ───────────────────────── */
    .resolver-item {
      display: flex; justify-content: space-between; align-items: center;
      padding: 10px 16px; border: 1px solid #e2e8f0; border-radius: 6px;
      margin-bottom: 8px; background: #f8fafc;
    }
    .resolver-item-header { display: flex; align-items: center; gap: 12px; flex: 1; flex-wrap: wrap; }
    .resolver-config-kv { display: flex; gap: 12px; flex-wrap: wrap; }
    .config-kv-pair {
      font-size: 0.75rem; color: #374151; background: #fff;
      padding: 2px 8px; border-radius: 4px; border: 1px solid #e2e8f0;
    }

    .action-btn {
      padding: 4px 8px; border: none; background: none; color: #3b82f6;
      font-size: 0.75rem; font-weight: 500; cursor: pointer; font-family: inherit;
    }
    .action-btn:hover { text-decoration: underline; }
    .action-btn.danger { color: #ef4444; }

    /* ── Validation bar ───────────────────────── */
    .validation-bar {
      display: flex; flex-wrap: wrap; gap: 8px; padding: 10px 16px;
      background: #fef2f2; border: 1px solid #fecaca; border-radius: 8px;
      margin-top: 16px;
    }
    .validation-error { font-size: 0.75rem; color: #dc2626; }

    .empty-hint { color: #94a3b8; font-size: 0.8125rem; padding: 16px 0; }
    .loading-text { color: #94a3b8; font-size: 0.875rem; padding: 32px 0; text-align: center; }
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
  private networkingService = inject(NetworkingService);
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

  // Backend regions (for region selection step)
  backendRegions = signal<BackendRegion[]>([]);
  selectedBackendRegionId = signal<string | null>(null);

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

  // Wizard
  wizardSteps: { id: WizardStep; label: string }[] = [
    { id: 'blueprint', label: 'Quick Start' },
    { id: 'region', label: 'Region' },
    { id: 'strategy', label: 'Strategy' },
    { id: 'foundation', label: 'Foundation' },
    { id: 'review', label: 'Review' },
  ];
  wizardStep = signal<WizardStep>('blueprint');
  wizardSkipped = signal(false);

  wizardStepIndex = computed(() =>
    this.wizardSteps.findIndex(s => s.id === this.wizardStep())
  );

  /** Show wizard when zone has no hierarchy and user hasn't skipped */
  showWizard = computed(() => {
    if (this.wizardSkipped()) return false;
    if (this.loading()) return false;
    const h = this.currentHierarchy();
    return !h || (h.nodes?.length ?? 0) === 0;
  });

  // Tabbed mode
  tabs: { id: TabId; label: string }[] = [
    { id: 'overview', label: 'Overview' },
    { id: 'hierarchy', label: 'Hierarchy' },
    { id: 'network', label: 'Network' },
    { id: 'iam', label: 'IAM' },
    { id: 'security', label: 'Security' },
    { id: 'regions', label: 'Regions' },
    { id: 'connectivity', label: 'Connectivity' },
    { id: 'peering', label: 'Peering' },
    { id: 'endpoints', label: 'Endpoints' },
    { id: 'loadbalancers', label: 'Load Balancers' },
    { id: 'resolvers', label: 'Resolvers' },
  ];
  activeTab = signal<TabId>('overview');

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
  showRegionPicker = false;

  // Networking state
  connectivityConfigs = signal<ConnectivityConfig[]>([]);
  peeringConfigs = signal<PeeringConfig[]>([]);
  endpointPolicies = signal<PrivateEndpointPolicy[]>([]);
  sharedLoadBalancers = signal<SharedLoadBalancer[]>([]);
  showConnForm = false;
  showPeerForm = false;
  showEndpointForm = false;
  showLbForm = false;
  connName = ''; connType = ''; connProvider = ''; connDescription = '';
  peerName = ''; peerType = '';
  epName = ''; epServiceName = ''; epEndpointType = ''; epProvider = '';
  lbName = ''; lbType = ''; lbProvider = '';

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

        if (zone.hierarchy) {
          this.currentHierarchy.set(zone.hierarchy);
        }
        this.loading.set(false);

        // Initialize selected region from zone data
        if (zone.regionId) {
          this.selectedBackendRegionId.set(zone.regionId);
        }

        this.backendService.getBackend(zone.backendId).subscribe({
          next: b => {
            this.backend.set(b);
            if (b) {
              this.loadBlueprints(b.providerName);
              this.loadFoundationSchemas(b.providerName);
              this.loadHierarchyLevels(b.providerName);
              this.backendRegions.set(b.regions || []);
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

  // ── Wizard navigation ────────────────────────────────────────────

  nextWizardStep(): void {
    const idx = this.wizardStepIndex();
    if (idx < this.wizardSteps.length - 1) {
      this.wizardStep.set(this.wizardSteps[idx + 1].id);
    }
  }

  prevWizardStep(): void {
    const idx = this.wizardStepIndex();
    if (idx > 0) {
      this.wizardStep.set(this.wizardSteps[idx - 1].id);
    }
  }

  isWizardStepCompleted(stepId: WizardStep): boolean {
    switch (stepId) {
      case 'blueprint':
        return !!this.selectedBlueprintId();
      case 'strategy': {
        const settings = this.landingZone()?.settings as Record<string, unknown> | undefined;
        const strat = settings?.['strategySelections'] as Record<string, unknown> | undefined;
        return !!strat && Object.keys(strat).length > 0;
      }
      case 'foundation':
        return Object.values(this.foundationValues).some(v => Object.keys(v).length > 0);
      case 'region':
        return !!this.selectedBackendRegionId();
      case 'review':
        return !!this.validation()?.ready;
      default:
        return false;
    }
  }

  skipWizard(): void {
    this.wizardSkipped.set(true);
  }

  finishWizard(): void {
    this.saveFoundation();
    this.doAutoSave();
    this.wizardSkipped.set(true);
    this.toast.success('Landing zone setup complete');
  }

  // ── Tab switching ────────────────────────────────────────────────

  switchTab(tab: TabId): void {
    this.activeTab.set(tab);
    if (tab === 'resolvers') {
      this.loadResolverData();
    } else if (tab === 'connectivity') {
      this.loadConnectivity();
    } else if (tab === 'peering') {
      this.loadPeering();
    } else if (tab === 'endpoints') {
      this.loadEndpointPolicies();
    } else if (tab === 'loadbalancers') {
      this.loadSharedLbs();
    }
  }

  // ── Blueprint selection ──────────────────────────────────────────

  async onSelectBlueprint(bp: LandingZoneBlueprint): Promise<void> {
    const zone = this.landingZone();
    if (!zone || this.isReadOnly()) return;

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

    this.foundationValues = {
      network: { ...bp.networkConfig },
      iam: { ...bp.iamConfig },
      security: { ...bp.securityConfig },
    };

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
            }).subscribe({ error: () => {} });
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

  getSelectedBlueprintName(): string {
    const id = this.selectedBlueprintId();
    if (!id || id === 'blank') return 'Custom';
    const bp = this.blueprints().find(b => b.id === id);
    return bp?.name ?? id;
  }

  // ── Hierarchy tree events ────────────────────────────────────────

  onHierarchyChange(hierarchy: LandingZoneHierarchy): void {
    this.currentHierarchy.set(hierarchy);
    this.autoSave$.next();
  }

  onNodeSelected(nodeId: string | null): void {
    this.selectedNodeId.set(nodeId);
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

  // ── Hierarchy levels palette ─────────────────────────────────────

  canAddLevel(level: HierarchyLevelDef): boolean {
    const hierarchy = this.currentHierarchy();
    const selectedId = this.selectedNodeId();
    const ph = this.providerHierarchy();
    if (!ph) return false;

    if (!selectedId) {
      return level.typeId === ph.rootType;
    }

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
    this.autoSave$.next();
  }

  // ── Strategy ─────────────────────────────────────────────────────

  onStrategySettingsChange(settings: Record<string, unknown>): void {
    const zone = this.landingZone();
    if (!zone || this.isReadOnly()) return;

    this.lzService.updateLandingZone(zone.id, { settings }).subscribe({
      next: updated => {
        if (updated) this.landingZone.set(updated);
      },
    });
  }

  onStrategyHierarchyChange(hierarchy: LandingZoneHierarchy): void {
    this.currentHierarchy.set(hierarchy);
    this.autoSave$.next();
  }

  // ── Save / Publish ───────────────────────────────────────────────

  onNameChange(): void {
    const zone = this.landingZone();
    if (!zone || this.isReadOnly()) return;
    this.lzService.updateLandingZone(zone.id, { name: this.zoneName.trim() }).subscribe();
  }

  onSave(): void {
    this.saveFoundation();
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

  // ── Foundation config ────────────────────────────────────────────

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

  // ── Backend Region selection ─────────────────────────────────────

  onSelectBackendRegion(r: BackendRegion): void {
    this.selectedBackendRegionId.set(r.id);
    const zone = this.landingZone();
    if (!zone || this.isReadOnly()) return;

    this.lzService.updateLandingZone(zone.id, { regionId: r.id }).subscribe({
      next: updated => {
        if (updated) this.landingZone.set(updated);
        this.toast.success(`Region set to ${r.displayName}`);
      },
      error: err => this.toast.error(err.message || 'Failed to set region'),
    });
  }

  goToBackendRegions(): void {
    const b = this.backend();
    if (b) {
      this.router.navigate(['/backends', b.id]);
    }
  }

  // ── LZ Regions (legacy) ────────────────────────────────────────

  // ── Networking ───────────────────────────────────────────────────

  private loadConnectivity(): void {
    const zone = this.landingZone();
    if (!zone) return;
    this.networkingService.listConnectivityConfigs(zone.id).subscribe({
      next: configs => this.connectivityConfigs.set(configs),
      error: () => this.toast.error('Failed to load connectivity configs'),
    });
  }

  createConnectivity(): void {
    const zone = this.landingZone();
    if (!zone) return;
    const input: ConnectivityConfigInput = {
      name: this.connName.trim(),
      connectivityType: this.connType,
      providerType: this.connProvider.trim(),
      description: this.connDescription.trim() || null,
    };
    this.networkingService.createConnectivityConfig(zone.id, input).subscribe({
      next: () => {
        this.showConnForm = false;
        this.connName = ''; this.connType = ''; this.connProvider = ''; this.connDescription = '';
        this.loadConnectivity();
        this.toast.success('Connectivity config created');
      },
      error: err => this.toast.error(err.message || 'Failed to create connectivity config'),
    });
  }

  deleteConnectivity(id: string): void {
    this.networkingService.deleteConnectivityConfig(id).subscribe({
      next: () => { this.loadConnectivity(); this.toast.success('Deleted'); },
      error: err => this.toast.error(err.message || 'Failed to delete'),
    });
  }

  private loadPeering(): void {
    const zone = this.landingZone();
    if (!zone) return;
    this.networkingService.listPeeringConfigs(zone.id).subscribe({
      next: configs => this.peeringConfigs.set(configs),
      error: () => this.toast.error('Failed to load peering configs'),
    });
  }

  createPeering(): void {
    const zone = this.landingZone();
    if (!zone) return;
    const input: PeeringConfigInput = {
      name: this.peerName.trim(),
      peeringType: this.peerType,
    };
    this.networkingService.createPeeringConfig(zone.id, input).subscribe({
      next: () => {
        this.showPeerForm = false;
        this.peerName = ''; this.peerType = '';
        this.loadPeering();
        this.toast.success('Peering config created');
      },
      error: err => this.toast.error(err.message || 'Failed to create peering config'),
    });
  }

  deletePeering(id: string): void {
    this.networkingService.deletePeeringConfig(id).subscribe({
      next: () => { this.loadPeering(); this.toast.success('Deleted'); },
      error: err => this.toast.error(err.message || 'Failed to delete'),
    });
  }

  private loadEndpointPolicies(): void {
    const zone = this.landingZone();
    if (!zone) return;
    this.networkingService.listPrivateEndpointPolicies(zone.id).subscribe({
      next: policies => this.endpointPolicies.set(policies),
      error: () => this.toast.error('Failed to load endpoint policies'),
    });
  }

  createEndpointPolicy(): void {
    const zone = this.landingZone();
    if (!zone) return;
    const input: PrivateEndpointPolicyInput = {
      name: this.epName.trim(),
      serviceName: this.epServiceName.trim(),
      endpointType: this.epEndpointType,
      providerType: this.epProvider.trim(),
    };
    this.networkingService.createPrivateEndpointPolicy(zone.id, input).subscribe({
      next: () => {
        this.showEndpointForm = false;
        this.epName = ''; this.epServiceName = ''; this.epEndpointType = ''; this.epProvider = '';
        this.loadEndpointPolicies();
        this.toast.success('Endpoint policy created');
      },
      error: err => this.toast.error(err.message || 'Failed to create endpoint policy'),
    });
  }

  deleteEndpointPolicy(id: string): void {
    this.networkingService.deletePrivateEndpointPolicy(id).subscribe({
      next: () => { this.loadEndpointPolicies(); this.toast.success('Deleted'); },
      error: err => this.toast.error(err.message || 'Failed to delete'),
    });
  }

  private loadSharedLbs(): void {
    const zone = this.landingZone();
    if (!zone) return;
    this.networkingService.listSharedLoadBalancers(zone.id).subscribe({
      next: lbs => this.sharedLoadBalancers.set(lbs),
      error: () => this.toast.error('Failed to load load balancers'),
    });
  }

  createSharedLb(): void {
    const zone = this.landingZone();
    if (!zone) return;
    const input: SharedLoadBalancerInput = {
      name: this.lbName.trim(),
      lbType: this.lbType,
      providerType: this.lbProvider.trim(),
    };
    this.networkingService.createSharedLoadBalancer(zone.id, input).subscribe({
      next: () => {
        this.showLbForm = false;
        this.lbName = ''; this.lbType = ''; this.lbProvider = '';
        this.loadSharedLbs();
        this.toast.success('Load balancer created');
      },
      error: err => this.toast.error(err.message || 'Failed to create load balancer'),
    });
  }

  deleteSharedLb(id: string): void {
    this.networkingService.deleteSharedLoadBalancer(id).subscribe({
      next: () => { this.loadSharedLbs(); this.toast.success('Deleted'); },
      error: err => this.toast.error(err.message || 'Failed to delete'),
    });
  }

  // ── Resolvers ────────────────────────────────────────────────────

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

  // ── Helpers ──────────────────────────────────────────────────────

  private parseNodeValidationErrors(v: LandingZoneValidation): void {
    const errors = new Map<string, string[]>();
    const hierarchy = this.currentHierarchy();
    if (!hierarchy || !v.checks) {
      this.nodeValidationErrors.set(errors);
      return;
    }

    for (const check of v.checks) {
      if (check.status === 'error' || check.status === 'warning') {
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
