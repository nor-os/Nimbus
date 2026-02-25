/**
 * Overview: Subnet editor — expandable subnet cards with IPAM-driven addressing and inline security rules.
 * Architecture: Shared component for unified subnet + security editing (Section 7.2)
 * Dependencies: @angular/core, @angular/common, @angular/forms, landing-zone.service, SecurityRuleTableComponent
 * Concepts: SubnetViewModel joins network_config.subnets with security_config entities by name.
 *   On save, splits back into separate network and security updates. IPAM is the primary addressing mode.
 */
import {
  Component,
  ChangeDetectionStrategy,
  Input,
  Output,
  EventEmitter,
  OnChanges,
  SimpleChanges,
  inject,
  signal,
  computed,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { LandingZoneService } from '@core/services/landing-zone.service';
import { ToastService } from '@shared/services/toast.service';
import { SecurityRuleTableComponent } from './security-rule-table.component';

interface SubnetViewModel {
  name: string;
  cidr: string;
  gateway: string;
  type: string;
  az: string;
  region: string;
  serviceEndpoints: string[];
  privateGoogleAccess: boolean;
  securityAssociation: string;
  ipamAllocationId: string;
  ipamMode: boolean;
  inboundRules: Record<string, unknown>[];
  outboundRules: Record<string, unknown>[];
  expanded: boolean;
}

// Provider-specific key for the security association field on subnets
const SECURITY_FIELD_MAP: Record<string, string> = {
  aws: 'security_groups',
  azure: 'nsg',
  gcp: 'firewall_tags',
  oci: 'security_list',
  proxmox: 'firewall_group',
};

// Provider-specific key for the security entity array in security_config
const SECURITY_ENTITY_MAP: Record<string, string> = {
  aws: 'security_groups',
  azure: 'nsgs',
  gcp: 'firewall_rules',
  oci: 'security_lists',
  proxmox: 'firewall_groups',
};

// Provider-specific inbound/outbound key names
const RULE_KEY_MAP: Record<string, { inbound: string; outbound: string }> = {
  aws: { inbound: 'inbound_rules', outbound: 'outbound_rules' },
  azure: { inbound: 'inbound_rules', outbound: 'outbound_rules' },
  gcp: { inbound: 'allowed', outbound: 'denied' },
  oci: { inbound: 'ingress_rules', outbound: 'egress_rules' },
  proxmox: { inbound: 'rules', outbound: 'rules' },
};

@Component({
  selector: 'nimbus-subnet-editor',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [CommonModule, FormsModule, SecurityRuleTableComponent],
  template: `
    <div class="subnet-editor">
      <div class="editor-header">
        <h3 class="editor-title">Subnets & Security Rules</h3>
        <button class="add-subnet-btn" (click)="addSubnet()">+ Add Subnet</button>
      </div>

      @if (subnets().length === 0) {
        <p class="empty-hint">No subnets defined. Click "Add Subnet" to create one.</p>
      }

      @for (subnet of subnets(); let i = $index; track i) {
        <div class="subnet-card" [class.expanded]="subnet.expanded">
          <!-- Collapsed header -->
          <div class="subnet-header" (click)="toggleExpand(i)">
            <div class="subnet-info">
              <span class="subnet-name">{{ subnet.name || '(unnamed)' }}</span>
              <span class="subnet-cidr">{{ subnet.cidr || '—' }}</span>
              @if (subnet.type) {
                <span class="subnet-type" [class]="'type-' + subnet.type">{{ subnet.type }}</span>
              }
              @if (subnet.securityAssociation) {
                <span class="subnet-security">{{ securityLabel() }}: {{ subnet.securityAssociation }}</span>
              }
            </div>
            <div class="subnet-actions">
              <button class="remove-btn" (click)="removeSubnet(i, $event)" title="Remove subnet">&times;</button>
              <span class="expand-icon">{{ subnet.expanded ? '\u25B2' : '\u25BC' }}</span>
            </div>
          </div>

          <!-- Expanded body -->
          @if (subnet.expanded) {
            <div class="subnet-body">
              <div class="field-grid">
                <div class="field">
                  <label class="field-label">Name</label>
                  <input class="field-input" [ngModel]="subnet.name" (ngModelChange)="onFieldChange(i, 'name', $event)" placeholder="e.g. web-tier" />
                </div>
                <div class="field">
                  <label class="field-label">CIDR</label>
                  <div class="cidr-row">
                    @if (subnet.ipamMode && addressSpaces.length > 0) {
                      <select class="field-input cidr-select" [ngModel]="ipamSpaceId()" (ngModelChange)="ipamSpaceId.set($event)">
                        <option value="">Select address space...</option>
                        @for (sp of addressSpaces; track sp.id) {
                          <option [value]="sp.id">{{ sp.name }} ({{ sp.cidr }})</option>
                        }
                      </select>
                      <select class="field-input prefix-select" [ngModel]="ipamPrefixLength()" (ngModelChange)="ipamPrefixLength.set(+$event)">
                        @for (pl of prefixOptions; track pl) {
                          <option [value]="pl">/{{ pl }}</option>
                        }
                      </select>
                      <button class="alloc-btn" (click)="allocateIpam(i)" [disabled]="!ipamSpaceId() || allocating()">
                        {{ allocating() ? '...' : 'Allocate' }}
                      </button>
                      <button class="switch-mode-link" (click)="onFieldChange(i, 'ipamMode', false)">Manual</button>
                    } @else {
                      <input class="field-input" [ngModel]="subnet.cidr" (ngModelChange)="onFieldChange(i, 'cidr', $event)" placeholder="10.0.0.0/24" />
                      @if (addressSpaces.length > 0) {
                        <button class="switch-mode-link" (click)="onFieldChange(i, 'ipamMode', true)">IPAM</button>
                      }
                    }
                  </div>
                  @if (subnet.ipamAllocationId) {
                    <span class="ipam-badge">IPAM allocated</span>
                  }
                </div>
                <div class="field">
                  <label class="field-label">Gateway</label>
                  <input class="field-input" [ngModel]="subnet.gateway" (ngModelChange)="onFieldChange(i, 'gateway', $event)" placeholder="10.0.0.1" />
                </div>
                @if (providerName === 'aws') {
                  <div class="field">
                    <label class="field-label">Type</label>
                    <select class="field-input" [ngModel]="subnet.type" (ngModelChange)="onFieldChange(i, 'type', $event)">
                      <option value="">—</option>
                      <option value="public">Public</option>
                      <option value="private">Private</option>
                      <option value="isolated">Isolated</option>
                    </select>
                  </div>
                  <div class="field">
                    <label class="field-label">Availability Zone</label>
                    <input class="field-input" [ngModel]="subnet.az" (ngModelChange)="onFieldChange(i, 'az', $event)" placeholder="us-east-1a" />
                  </div>
                }
                @if (providerName === 'azure') {
                  <div class="field full-width">
                    <label class="field-label">Service Endpoints</label>
                    <input class="field-input" [ngModel]="subnet.serviceEndpoints.join(', ')" (ngModelChange)="onServiceEndpointsChange(i, $event)" placeholder="Microsoft.Sql, Microsoft.Storage" />
                  </div>
                }
                @if (providerName === 'gcp') {
                  <div class="field">
                    <label class="field-label">Region</label>
                    <input class="field-input" [ngModel]="subnet.region" (ngModelChange)="onFieldChange(i, 'region', $event)" placeholder="us-central1" />
                  </div>
                }
                @if (providerName === 'oci') {
                  <div class="field">
                    <label class="field-label">Type</label>
                    <select class="field-input" [ngModel]="subnet.type" (ngModelChange)="onFieldChange(i, 'type', $event)">
                      <option value="">—</option>
                      <option value="public">Public</option>
                      <option value="private">Private</option>
                    </select>
                  </div>
                }
                <div class="field">
                  <label class="field-label">{{ securityLabel() }}</label>
                  <input class="field-input" [ngModel]="subnet.securityAssociation" (ngModelChange)="onFieldChange(i, 'securityAssociation', $event)" [placeholder]="securityPlaceholder()" />
                </div>
              </div>

              <!-- Security rules inline -->
              <div class="security-rules-section">
                @if (providerName !== 'gcp') {
                  <nimbus-security-rule-table
                    [rules]="subnet.inboundRules"
                    [providerName]="providerName"
                    direction="inbound"
                    (rulesChange)="onRulesChange(i, 'inboundRules', $event)"
                  />
                  <nimbus-security-rule-table
                    [rules]="subnet.outboundRules"
                    [providerName]="providerName"
                    direction="outbound"
                    (rulesChange)="onRulesChange(i, 'outboundRules', $event)"
                  />
                } @else {
                  <!-- GCP uses allowed/denied pattern -->
                  <nimbus-security-rule-table
                    [rules]="subnet.inboundRules"
                    [providerName]="providerName"
                    direction="inbound"
                    (rulesChange)="onRulesChange(i, 'inboundRules', $event)"
                  />
                }
              </div>
            </div>
          }
        </div>
      }
    </div>
  `,
  styles: [`
    .subnet-editor { }
    .editor-header {
      display: flex; justify-content: space-between; align-items: center;
      margin-bottom: 12px;
    }
    .editor-title {
      font-size: 0.75rem; font-weight: 600; color: #64748b;
      text-transform: uppercase; letter-spacing: 0.04em; margin: 0;
    }
    .add-subnet-btn {
      padding: 6px 14px; font-size: 0.8125rem; font-weight: 500;
      color: #3b82f6; background: #fff; border: 1px solid #3b82f6;
      border-radius: 6px; cursor: pointer; font-family: inherit;
    }
    .add-subnet-btn:hover { background: #eff6ff; }
    .empty-hint { color: #94a3b8; font-size: 0.8125rem; padding: 12px 0; }

    .subnet-card {
      border: 1px solid #e2e8f0; border-radius: 8px; margin-bottom: 10px;
      background: #fff; overflow: hidden;
    }
    .subnet-card.expanded { border-color: #93c5fd; }
    .subnet-header {
      display: flex; justify-content: space-between; align-items: center;
      padding: 10px 16px; cursor: pointer;
    }
    .subnet-header:hover { background: #fafbfc; }
    .subnet-info { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
    .subnet-name { font-size: 0.8125rem; font-weight: 600; color: #1e293b; }
    .subnet-cidr { font-size: 0.75rem; color: #64748b; font-family: monospace; }
    .subnet-type {
      font-size: 0.625rem; padding: 1px 6px; border-radius: 3px;
      text-transform: uppercase; font-weight: 600;
    }
    .type-public { background: #d1fae5; color: #065f46; }
    .type-private { background: #dbeafe; color: #1e40af; }
    .type-isolated { background: #fef3c7; color: #92400e; }
    .subnet-security { font-size: 0.6875rem; color: #64748b; }
    .subnet-actions { display: flex; align-items: center; gap: 8px; }
    .remove-btn {
      background: none; border: none; color: #ef4444; font-size: 1.125rem;
      cursor: pointer; padding: 0 4px; line-height: 1; font-family: inherit;
    }
    .remove-btn:hover { color: #dc2626; }
    .expand-icon { font-size: 0.625rem; color: #94a3b8; }

    .subnet-body {
      padding: 12px 16px; border-top: 1px solid #e2e8f0; background: #fafbfc;
    }
    .field-grid {
      display: grid; grid-template-columns: 1fr 1fr; gap: 10px;
      margin-bottom: 14px;
    }
    .field { display: flex; flex-direction: column; gap: 3px; }
    .field.full-width { grid-column: 1 / -1; }
    .field-label {
      font-size: 0.625rem; font-weight: 600; color: #64748b;
      text-transform: uppercase; letter-spacing: 0.04em;
    }
    .field-input {
      padding: 6px 10px; border: 1px solid #e2e8f0; border-radius: 4px;
      font-size: 0.8125rem; color: #1e293b; background: #fff; outline: none;
      font-family: inherit;
    }
    .field-input:focus { border-color: #3b82f6; }

    .cidr-row { display: flex; gap: 6px; align-items: center; }
    .cidr-select { flex: 1; }
    .prefix-select { width: 70px; }
    .alloc-btn {
      padding: 5px 12px; font-size: 0.75rem; font-weight: 500;
      color: #fff; background: #3b82f6; border: none; border-radius: 4px;
      cursor: pointer; font-family: inherit; white-space: nowrap;
    }
    .alloc-btn:hover { background: #2563eb; }
    .alloc-btn:disabled { opacity: 0.5; cursor: not-allowed; }
    .switch-mode-link {
      background: none; border: none; color: #3b82f6; font-size: 0.6875rem;
      cursor: pointer; text-decoration: underline; font-family: inherit;
      white-space: nowrap;
    }
    .ipam-badge {
      font-size: 0.625rem; color: #065f46; background: #d1fae5;
      padding: 1px 6px; border-radius: 3px; font-weight: 600;
      display: inline-block; margin-top: 2px;
    }

    .security-rules-section {
      border-top: 1px solid #e2e8f0; padding-top: 10px; margin-top: 6px;
    }
  `],
})
export class SubnetEditorComponent implements OnChanges {
  @Input() providerName = '';
  @Input() networkConfig: Record<string, unknown> = {};
  @Input() securityConfig: Record<string, unknown> = {};
  @Input() addressSpaces: { id: string; name: string; cidr: string }[] = [];
  @Input() environmentId = '';
  @Input() existingAllocations: { id: string; name: string; cidr: string }[] = [];

  @Output() networkConfigChange = new EventEmitter<Record<string, unknown>>();
  @Output() securityConfigChange = new EventEmitter<Record<string, unknown>>();

  private lzService = inject(LandingZoneService);
  private toast = inject(ToastService);

  subnets = signal<SubnetViewModel[]>([]);
  ipamSpaceId = signal('');
  ipamPrefixLength = signal(24);
  allocating = signal(false);

  prefixOptions = [16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28];

  securityLabel = computed(() => {
    switch (this.providerName) {
      case 'aws': return 'Security Group';
      case 'azure': return 'NSG';
      case 'gcp': return 'Firewall Tags';
      case 'oci': return 'Security List';
      case 'proxmox': return 'Firewall Group';
      default: return 'Security';
    }
  });

  securityPlaceholder = computed(() => {
    switch (this.providerName) {
      case 'aws': return 'web-sg';
      case 'azure': return 'web-nsg';
      case 'gcp': return 'https,ssh';
      case 'oci': return 'env-seclist';
      case 'proxmox': return 'web-fw';
      default: return '';
    }
  });

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['networkConfig'] || changes['securityConfig'] || changes['providerName']) {
      this.parseConfigs();
    }
  }

  private parseConfigs(): void {
    const rawSubnets = (this.networkConfig?.['subnets'] as Record<string, unknown>[]) || [];
    const secField = SECURITY_FIELD_MAP[this.providerName] || '';
    const entityKey = SECURITY_ENTITY_MAP[this.providerName] || '';
    const entities = (this.securityConfig?.[entityKey] as Record<string, unknown>[]) || [];
    const ruleKeys = RULE_KEY_MAP[this.providerName] || { inbound: 'inbound_rules', outbound: 'outbound_rules' };

    const vms: SubnetViewModel[] = rawSubnets.map(s => {
      // Get security association value
      let secAssoc = '';
      if (secField === 'security_groups' || secField === 'firewall_tags') {
        const arr = (s[secField] as string[]) || [];
        secAssoc = arr.join(', ');
      } else {
        secAssoc = (s[secField] as string) || '';
      }

      // Find matching security entity
      let inbound: Record<string, unknown>[] = [];
      let outbound: Record<string, unknown>[] = [];
      const assocName = secAssoc.split(',')[0]?.trim() || '';

      if (assocName && entities.length > 0) {
        const matchKey = this.providerName === 'gcp' ? 'name' : 'name';
        let entity: Record<string, unknown> | undefined;
        if (this.providerName === 'gcp') {
          // GCP: match by target_tags
          entity = entities.find(e => {
            const tags = (e['target_tags'] as string[]) || [];
            return tags.includes(assocName);
          });
          if (entity) {
            inbound = (entity[ruleKeys.inbound] as Record<string, unknown>[]) || [];
          }
        } else {
          entity = entities.find(e => e[matchKey] === assocName);
          if (entity) {
            inbound = (entity[ruleKeys.inbound] as Record<string, unknown>[]) || [];
            if (ruleKeys.inbound !== ruleKeys.outbound) {
              outbound = (entity[ruleKeys.outbound] as Record<string, unknown>[]) || [];
            }
          }
        }
      }

      return {
        name: (s['name'] as string) || '',
        cidr: (s['cidr'] as string) || '',
        gateway: (s['gateway'] as string) || '',
        type: (s['type'] as string) || '',
        az: (s['az'] as string) || '',
        region: (s['region'] as string) || '',
        serviceEndpoints: (s['service_endpoints'] as string[]) || [],
        privateGoogleAccess: (s['private_google_access'] as boolean) ?? true,
        securityAssociation: secAssoc,
        ipamAllocationId: (s['ipam_allocation_id'] as string) || '',
        ipamMode: this.addressSpaces.length > 0 && !(s['cidr']),
        inboundRules: inbound,
        outboundRules: outbound,
        expanded: false,
      };
    });

    this.subnets.set(vms);
  }

  toggleExpand(index: number): void {
    const updated = this.subnets().map((s, i) =>
      i === index ? { ...s, expanded: !s.expanded } : s
    );
    this.subnets.set(updated);
  }

  addSubnet(): void {
    const newSubnet: SubnetViewModel = {
      name: '', cidr: '', gateway: '', type: '', az: '', region: '',
      serviceEndpoints: [], privateGoogleAccess: true,
      securityAssociation: '', ipamAllocationId: '',
      ipamMode: this.addressSpaces.length > 0,
      inboundRules: [], outboundRules: [], expanded: true,
    };
    this.subnets.set([...this.subnets(), newSubnet]);
    this.emitChanges();
  }

  removeSubnet(index: number, event: Event): void {
    event.stopPropagation();
    const subnet = this.subnets()[index];
    if (subnet.ipamAllocationId) {
      this.lzService.releaseSubnetIpamAllocation(subnet.ipamAllocationId).subscribe({
        next: () => this.toast.info('IPAM allocation released'),
        error: () => this.toast.error('Failed to release IPAM allocation'),
      });
    }
    const updated = this.subnets().filter((_, i) => i !== index);
    this.subnets.set(updated);
    this.emitChanges();
  }

  onFieldChange(index: number, field: string, value: unknown): void {
    const updated = this.subnets().map((s, i) =>
      i === index ? { ...s, [field]: value } : s
    );
    this.subnets.set(updated);
    this.emitChanges();
  }

  onServiceEndpointsChange(index: number, value: string): void {
    const endpoints = value.split(',').map(s => s.trim()).filter(Boolean);
    this.onFieldChange(index, 'serviceEndpoints', endpoints);
  }

  onRulesChange(index: number, field: 'inboundRules' | 'outboundRules', rules: Record<string, unknown>[]): void {
    const updated = this.subnets().map((s, i) =>
      i === index ? { ...s, [field]: rules } : s
    );
    this.subnets.set(updated);
    this.emitChanges();
  }

  allocateIpam(index: number): void {
    const spaceId = this.ipamSpaceId();
    const prefix = this.ipamPrefixLength();
    const subnet = this.subnets()[index];
    if (!spaceId || !this.environmentId) return;

    this.allocating.set(true);
    this.lzService.allocateSubnetFromIpam(
      this.environmentId, spaceId, prefix, subnet.name || 'subnet',
    ).subscribe({
      next: (result) => {
        const updated = this.subnets().map((s, i) =>
          i === index ? {
            ...s,
            cidr: result.cidr,
            gateway: result.gateway,
            ipamAllocationId: result.allocationId,
            ipamMode: false,
          } : s
        );
        this.subnets.set(updated);
        this.allocating.set(false);
        this.emitChanges();
        this.toast.success(`Allocated ${result.cidr}`);
      },
      error: (err: Error) => {
        this.allocating.set(false);
        this.toast.error(err.message || 'IPAM allocation failed');
      },
    });
  }

  private emitChanges(): void {
    const subs = this.subnets();
    const secField = SECURITY_FIELD_MAP[this.providerName] || '';
    const entityKey = SECURITY_ENTITY_MAP[this.providerName] || '';
    const ruleKeys = RULE_KEY_MAP[this.providerName] || { inbound: 'inbound_rules', outbound: 'outbound_rules' };

    // Build network subnets (strip security rules, keep association refs)
    const networkSubnets = subs.map(s => {
      const sub: Record<string, unknown> = {
        name: s.name,
        cidr: s.cidr,
        gateway: s.gateway,
      };
      if (s.ipamAllocationId) sub['ipam_allocation_id'] = s.ipamAllocationId;

      // Provider-specific fields
      if (this.providerName === 'aws') {
        if (s.type) sub['type'] = s.type;
        if (s.az) sub['az'] = s.az;
        const groups = s.securityAssociation ? s.securityAssociation.split(',').map(x => x.trim()).filter(Boolean) : [];
        if (groups.length) sub['security_groups'] = groups;
      } else if (this.providerName === 'azure') {
        if (s.serviceEndpoints.length) sub['service_endpoints'] = s.serviceEndpoints;
        if (s.securityAssociation) sub['nsg'] = s.securityAssociation;
      } else if (this.providerName === 'gcp') {
        if (s.region) sub['region'] = s.region;
        sub['private_google_access'] = s.privateGoogleAccess;
        const tags = s.securityAssociation ? s.securityAssociation.split(',').map(x => x.trim()).filter(Boolean) : [];
        if (tags.length) sub['firewall_tags'] = tags;
      } else if (this.providerName === 'oci') {
        if (s.type) sub['type'] = s.type;
        if (s.securityAssociation) sub['security_list'] = s.securityAssociation;
      } else if (this.providerName === 'proxmox') {
        if (s.securityAssociation) sub['firewall_group'] = s.securityAssociation;
      }

      return sub;
    });

    // Build security entities from subnets' rule arrays
    const entityMap = new Map<string, Record<string, unknown>>();
    for (const s of subs) {
      const assocName = s.securityAssociation?.split(',')[0]?.trim();
      if (!assocName) continue;
      if (entityMap.has(assocName)) continue;

      const entity: Record<string, unknown> = { name: assocName };
      if (this.providerName === 'gcp') {
        // GCP firewall rules are different — each rule is an entity
        entity['target_tags'] = s.securityAssociation.split(',').map(x => x.trim()).filter(Boolean);
        entity[ruleKeys.inbound] = s.inboundRules;
      } else if (this.providerName === 'proxmox') {
        // Merge inbound + outbound into single rules array
        entity[ruleKeys.inbound] = [...s.inboundRules, ...s.outboundRules];
      } else {
        entity[ruleKeys.inbound] = s.inboundRules;
        entity[ruleKeys.outbound] = s.outboundRules;
      }
      entityMap.set(assocName, entity);
    }

    // Emit network config with subnets
    this.networkConfigChange.emit({ subnets: networkSubnets });

    // Emit security config with entities
    const securityEntities: Record<string, unknown> = {};
    if (entityMap.size > 0) {
      securityEntities[entityKey] = Array.from(entityMap.values());
    }
    this.securityConfigChange.emit(securityEntities);
  }
}
