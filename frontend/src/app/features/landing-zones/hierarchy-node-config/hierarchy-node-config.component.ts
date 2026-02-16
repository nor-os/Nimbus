/**
 * Overview: Right-panel config editor for a selected hierarchy tree node in the landing zone designer.
 * Architecture: Feature component for landing zone hierarchy node editing (Section 7.2)
 * Dependencies: @angular/core, @angular/common, @angular/forms, landing-zone.model
 * Concepts: Accordion sections for node details, tag policies (with inheritance), IPAM, network, security, naming, environment.
 */
import {
  Component,
  Input,
  Output,
  EventEmitter,
  ChangeDetectionStrategy,
  signal,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import {
  HierarchyNode,
  HierarchyLevelDef,
} from '@shared/models/landing-zone.model';

interface TagPolicyEntry {
  tagKey: string;
  displayName: string;
  isRequired: boolean;
  allowedValues?: string[];
  defaultValue?: string;
  inherited?: boolean;
  inheritedFrom?: string;
}

interface CidrInfo {
  valid: boolean;
  totalAddresses: number;
  usableAddresses: number;
  network: string;
  prefix: number;
}

@Component({
  selector: 'nimbus-hierarchy-node-config',
  standalone: true,
  imports: [CommonModule, FormsModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="node-config">
      <div class="config-header">
        <span class="type-icon">{{ levelDef?.icon || '&#9632;' }}</span>
        <h3 class="config-title">{{ node?.label || 'Node' }}</h3>
        <span class="type-badge">{{ levelDef?.label || node?.typeId }}</span>
      </div>

      <!-- Details Section -->
      <div class="accordion-section">
        <button class="accordion-toggle" (click)="toggleSection('details')">
          <span class="toggle-icon">{{ openSections().has('details') ? '&#9660;' : '&#9654;' }}</span>
          Details
        </button>
        @if (openSections().has('details')) {
          <div class="accordion-body">
            <div class="form-group">
              <label class="form-label">Name</label>
              <input
                type="text"
                class="form-input"
                [value]="node?.label || ''"
                [disabled]="readOnly"
                (input)="onLabelChange($event)"
                placeholder="Node name..."
              />
            </div>
            <div class="form-group">
              <label class="form-label">Type</label>
              <span class="type-readonly-badge">{{ levelDef?.label || node?.typeId }}</span>
            </div>
            <div class="form-group">
              <label class="form-label">Description</label>
              <textarea
                class="form-textarea"
                [value]="node?.properties?.description || ''"
                [disabled]="readOnly"
                (input)="onDescriptionChange($event)"
                placeholder="Describe this node..."
                rows="3"
              ></textarea>
            </div>
          </div>
        }
      </div>

      <!-- Tag Policies Section -->
      @if (!levelDef || levelDef.supportsTags) {
        <div class="accordion-section">
          <button class="accordion-toggle" (click)="toggleSection('tags')">
            <span class="toggle-icon">{{ openSections().has('tags') ? '&#9660;' : '&#9654;' }}</span>
            Tag Policies
            <span class="section-count">{{ allTagPolicies.length }}</span>
          </button>
          @if (openSections().has('tags')) {
            <div class="accordion-body">
              <!-- Inherited tags -->
              @for (tag of inheritedTagPolicies; track tag.tagKey) {
                <div class="tag-row tag-inherited">
                  <div class="tag-info">
                    <span class="tag-key">{{ tag.tagKey }}</span>
                    <span class="tag-display-name">{{ tag.displayName }}</span>
                    @if (tag.isRequired) {
                      <span class="tag-required-badge">required</span>
                    }
                  </div>
                  <span class="tag-inherited-badge">from {{ tag.inheritedFrom }}</span>
                </div>
              }

              <!-- Local tags -->
              @for (tag of localTagPolicies; track tag.tagKey; let i = $index) {
                <div class="tag-row">
                  <div class="tag-fields">
                    <input
                      type="text"
                      class="form-input tag-input"
                      [value]="tag.tagKey"
                      [disabled]="readOnly"
                      (input)="onLocalTagChange(i, 'tagKey', $event)"
                      placeholder="Tag key"
                    />
                    <input
                      type="text"
                      class="form-input tag-input"
                      [value]="tag.displayName"
                      [disabled]="readOnly"
                      (input)="onLocalTagChange(i, 'displayName', $event)"
                      placeholder="Display name"
                    />
                    <label class="tag-required-toggle">
                      <input
                        type="checkbox"
                        [checked]="tag.isRequired"
                        [disabled]="readOnly"
                        (change)="onLocalTagRequiredChange(i, $event)"
                      />
                      Required
                    </label>
                  </div>
                  @if (!readOnly) {
                    <button class="btn-remove" (click)="removeLocalTag(i)" title="Remove tag">&times;</button>
                  }
                </div>
              }

              @if (!readOnly) {
                <button class="btn-add" (click)="addLocalTag()">+ Add Tag Policy</button>
              }

              @if (allTagPolicies.length === 0) {
                <p class="empty-hint">No tag policies defined.</p>
              }
            </div>
          }
        </div>
      }

      <!-- IPAM Section -->
      @if (!levelDef || levelDef.supportsIpam) {
        <div class="accordion-section">
          <button class="accordion-toggle" (click)="toggleSection('ipam')">
            <span class="toggle-icon">{{ openSections().has('ipam') ? '&#9660;' : '&#9654;' }}</span>
            IPAM
          </button>
          @if (openSections().has('ipam')) {
            <div class="accordion-body">
              @if (parentCidr) {
                <div class="parent-cidr-info">
                  <span class="info-label">Parent CIDR:</span>
                  <code class="cidr-code">{{ parentCidr }}</code>
                </div>
              }
              <div class="form-group">
                <label class="form-label">CIDR Block</label>
                <input
                  type="text"
                  class="form-input"
                  [class.input-error]="cidrValue && !cidrInfo.valid"
                  [value]="cidrValue"
                  [disabled]="readOnly"
                  (input)="onCidrChange($event)"
                  placeholder="e.g. 10.0.0.0/16"
                />
                @if (cidrValue && !cidrInfo.valid) {
                  <span class="validation-error">Invalid CIDR format</span>
                }
              </div>
              @if (cidrInfo.valid) {
                <div class="cidr-summary">
                  <div class="cidr-stat">
                    <span class="stat-label">Network</span>
                    <span class="stat-value">{{ cidrInfo.network }}/{{ cidrInfo.prefix }}</span>
                  </div>
                  <div class="cidr-stat">
                    <span class="stat-label">Total Addresses</span>
                    <span class="stat-value">{{ cidrInfo.totalAddresses | number }}</span>
                  </div>
                  <div class="cidr-stat">
                    <span class="stat-label">Usable Addresses</span>
                    <span class="stat-value">{{ cidrInfo.usableAddresses | number }}</span>
                  </div>
                </div>
              }
            </div>
          }
        </div>
      }

      <!-- Network Config Section -->
      <div class="accordion-section">
        <button class="accordion-toggle" (click)="toggleSection('network')">
          <span class="toggle-icon">{{ openSections().has('network') ? '&#9660;' : '&#9654;' }}</span>
          Network Config
        </button>
        @if (openSections().has('network')) {
          <div class="accordion-body">
            <p class="placeholder-text">Network configuration will be available via schema-driven forms in a future update.</p>
          </div>
        }
      </div>

      <!-- Security Config Section -->
      <div class="accordion-section">
        <button class="accordion-toggle" (click)="toggleSection('security')">
          <span class="toggle-icon">{{ openSections().has('security') ? '&#9660;' : '&#9654;' }}</span>
          Security Config
        </button>
        @if (openSections().has('security')) {
          <div class="accordion-body">
            <p class="placeholder-text">Security configuration will be available via schema-driven forms in a future update.</p>
          </div>
        }
      </div>

      <!-- Naming Section -->
      <div class="accordion-section">
        <button class="accordion-toggle" (click)="toggleSection('naming')">
          <span class="toggle-icon">{{ openSections().has('naming') ? '&#9660;' : '&#9654;' }}</span>
          Naming
        </button>
        @if (openSections().has('naming')) {
          <div class="accordion-body">
            <div class="form-group">
              <label class="form-label">Naming Template</label>
              <input
                type="text"
                class="form-input"
                [value]="namingTemplate"
                [disabled]="readOnly"
                (input)="onNamingTemplateChange($event)"
                [placeholder]="'e.g. {provider}-{env}-{type}-{seq}'"
              />
            </div>
            @if (namingTemplate) {
              <div class="naming-preview">
                <span class="info-label">Preview:</span>
                <code class="naming-code">{{ namingPreview }}</code>
              </div>
            }
          </div>
        }
      </div>

      <!-- Environment Designation Section -->
      @if (levelDef?.supportsEnvironment) {
        <div class="accordion-section">
          <button class="accordion-toggle" (click)="toggleSection('environment')">
            <span class="toggle-icon">{{ openSections().has('environment') ? '&#9660;' : '&#9654;' }}</span>
            Environment Designation
          </button>
          @if (openSections().has('environment')) {
            <div class="accordion-body">
              <div class="form-group">
                <label class="form-label">Designation</label>
                <select
                  class="form-select"
                  [value]="node?.properties?.environmentDesignation || 'none'"
                  [disabled]="readOnly"
                  (change)="onEnvironmentChange($event)"
                >
                  <option value="none">None</option>
                  <option value="shared">Shared</option>
                  <option value="production">Production</option>
                  <option value="development">Development</option>
                  <option value="staging">Staging</option>
                  <option value="sandbox">Sandbox</option>
                </select>
              </div>
            </div>
          }
        </div>
      }
    </div>
  `,
  styles: [`
    .node-config {
      padding: 0;
      background: #fff;
      height: 100%;
      overflow-y: auto;
    }

    .config-header {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 16px;
      border-bottom: 1px solid #e2e8f0;
      background: #f8fafc;
    }

    .type-icon {
      font-size: 18px;
      color: #3b82f6;
    }

    .config-title {
      margin: 0;
      font-size: 16px;
      font-weight: 600;
      color: #1e293b;
      flex: 1;
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .type-badge, .type-readonly-badge {
      font-size: 11px;
      font-weight: 500;
      padding: 2px 8px;
      border-radius: 4px;
      background: #e0e7ff;
      color: #3730a3;
      white-space: nowrap;
    }

    /* ── Accordion ── */
    .accordion-section {
      border-bottom: 1px solid #e2e8f0;
    }

    .accordion-toggle {
      display: flex;
      align-items: center;
      gap: 8px;
      width: 100%;
      padding: 12px 16px;
      border: none;
      background: #fff;
      font-size: 13px;
      font-weight: 600;
      color: #1e293b;
      cursor: pointer;
      text-align: left;
    }

    .accordion-toggle:hover {
      background: #f8fafc;
    }

    .toggle-icon {
      font-size: 10px;
      color: #64748b;
      width: 12px;
    }

    .section-count {
      margin-left: auto;
      font-size: 11px;
      font-weight: 500;
      padding: 1px 6px;
      border-radius: 8px;
      background: #e2e8f0;
      color: #64748b;
    }

    .accordion-body {
      padding: 0 16px 16px 16px;
    }

    /* ── Form Controls ── */
    .form-group {
      margin-bottom: 12px;
    }

    .form-label {
      display: block;
      font-size: 12px;
      font-weight: 500;
      color: #64748b;
      margin-bottom: 4px;
    }

    .form-input, .form-textarea, .form-select {
      width: 100%;
      padding: 8px 10px;
      border: 1px solid #e2e8f0;
      border-radius: 6px;
      font-size: 13px;
      color: #1e293b;
      background: #fff;
      outline: none;
      box-sizing: border-box;
    }

    .form-input:focus, .form-textarea:focus, .form-select:focus {
      border-color: #3b82f6;
      box-shadow: 0 0 0 2px rgba(59,130,246,0.12);
    }

    .form-input:disabled, .form-textarea:disabled, .form-select:disabled {
      background: #f1f5f9;
      color: #94a3b8;
      cursor: not-allowed;
    }

    .form-textarea {
      resize: vertical;
      min-height: 60px;
    }

    .input-error {
      border-color: #ef4444;
    }

    .validation-error {
      display: block;
      font-size: 11px;
      color: #ef4444;
      margin-top: 4px;
    }

    /* ── Tags ── */
    .tag-row {
      display: flex;
      align-items: flex-start;
      gap: 8px;
      padding: 8px;
      border: 1px solid #e2e8f0;
      border-radius: 6px;
      margin-bottom: 8px;
      background: #fff;
    }

    .tag-inherited {
      background: #f8fafc;
      border-style: dashed;
    }

    .tag-info {
      display: flex;
      align-items: center;
      gap: 6px;
      flex: 1;
      flex-wrap: wrap;
    }

    .tag-key {
      font-size: 13px;
      font-weight: 600;
      color: #1e293b;
    }

    .tag-display-name {
      font-size: 12px;
      color: #64748b;
    }

    .tag-required-badge {
      font-size: 10px;
      font-weight: 500;
      padding: 1px 5px;
      border-radius: 3px;
      background: #fef3c7;
      color: #92400e;
    }

    .tag-inherited-badge {
      font-size: 11px;
      color: #94a3b8;
      white-space: nowrap;
      font-style: italic;
    }

    .tag-fields {
      display: flex;
      flex-direction: column;
      gap: 6px;
      flex: 1;
    }

    .tag-input {
      width: 100%;
      padding: 6px 8px;
      font-size: 12px;
    }

    .tag-required-toggle {
      display: flex;
      align-items: center;
      gap: 4px;
      font-size: 12px;
      color: #64748b;
      cursor: pointer;
    }

    .tag-required-toggle input {
      cursor: pointer;
    }

    .btn-remove {
      border: none;
      background: none;
      color: #ef4444;
      font-size: 18px;
      cursor: pointer;
      padding: 2px 6px;
      line-height: 1;
      border-radius: 4px;
    }

    .btn-remove:hover {
      background: #fef2f2;
    }

    .btn-add {
      display: inline-flex;
      align-items: center;
      padding: 6px 12px;
      border: 1px dashed #cbd5e1;
      border-radius: 6px;
      background: #fff;
      font-size: 12px;
      color: #3b82f6;
      cursor: pointer;
    }

    .btn-add:hover {
      background: #f0f5ff;
      border-color: #3b82f6;
    }

    .empty-hint {
      font-size: 12px;
      color: #94a3b8;
      margin: 8px 0 0 0;
    }

    /* ── IPAM ── */
    .parent-cidr-info, .naming-preview {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 8px 10px;
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 6px;
      margin-bottom: 12px;
    }

    .info-label {
      font-size: 12px;
      font-weight: 500;
      color: #64748b;
    }

    .cidr-code, .naming-code {
      font-size: 13px;
      font-family: 'JetBrains Mono', 'Fira Code', monospace;
      color: #1e293b;
    }

    .cidr-summary {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
      margin-top: 12px;
    }

    .cidr-stat {
      padding: 8px 10px;
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 6px;
    }

    .stat-label {
      display: block;
      font-size: 11px;
      color: #94a3b8;
      margin-bottom: 2px;
    }

    .stat-value {
      font-size: 14px;
      font-weight: 600;
      color: #1e293b;
    }

    /* ── Placeholder ── */
    .placeholder-text {
      font-size: 12px;
      color: #94a3b8;
      font-style: italic;
      margin: 0;
    }
  `],
})
export class HierarchyNodeConfigComponent {
  @Input() node: HierarchyNode | null = null;
  @Input() allNodes: HierarchyNode[] = [];
  @Input() levelDef: HierarchyLevelDef | null = null;
  @Input() providerName: string = '';
  @Input() readOnly: boolean = false;

  @Output() nodeChange = new EventEmitter<HierarchyNode>();

  /** Tracks which accordion sections are open. */
  openSections = signal<Set<string>>(new Set(['details']));

  /** CIDR value from node properties. */
  get cidrValue(): string {
    return this.node?.properties?.ipam?.cidr || '';
  }

  /** Parsed CIDR info for display. */
  get cidrInfo(): CidrInfo {
    return this.parseCidr(this.cidrValue);
  }

  /** Parent node's CIDR if available. */
  get parentCidr(): string | null {
    if (!this.node?.parentId || !this.allNodes.length) return null;
    const parent = this.allNodes.find(n => n.id === this.node!.parentId);
    return parent?.properties?.ipam?.cidr || null;
  }

  /** Naming template from node properties. */
  get namingTemplate(): string {
    return this.node?.properties?.namingConfig?.template || '';
  }

  /** Preview of the naming template with sample values. */
  get namingPreview(): string {
    const tpl = this.namingTemplate;
    if (!tpl) return '';
    return tpl
      .replace(/\{\{provider\}\}/g, this.providerName || 'oci')
      .replace(/\{\{env\}\}/g, this.node?.properties?.environmentDesignation || 'dev')
      .replace(/\{\{type\}\}/g, this.node?.typeId || 'node')
      .replace(/\{\{name\}\}/g, (this.node?.label || 'example').toLowerCase().replace(/\s+/g, '-'))
      .replace(/\{\{seq\}\}/g, '001')
      .replace(/\{\{region\}\}/g, 'us-east-1');
  }

  /** Tag policies inherited from ancestor nodes. */
  get inheritedTagPolicies(): TagPolicyEntry[] {
    if (!this.node || !this.allNodes.length) return [];
    const inherited: TagPolicyEntry[] = [];
    let currentId = this.node.parentId;
    while (currentId) {
      const ancestor = this.allNodes.find(n => n.id === currentId);
      if (!ancestor) break;
      const tags = ancestor.properties?.tagPolicies || [];
      for (const tag of tags) {
        if (!tag.inherited && !inherited.some(t => t.tagKey === tag.tagKey)) {
          inherited.push({
            tagKey: tag.tagKey,
            displayName: tag.displayName,
            isRequired: tag.isRequired,
            allowedValues: tag.allowedValues,
            defaultValue: tag.defaultValue,
            inherited: true,
            inheritedFrom: ancestor.label,
          });
        }
      }
      currentId = ancestor.parentId;
    }
    return inherited;
  }

  /** Local (non-inherited) tag policies on this node. */
  get localTagPolicies(): TagPolicyEntry[] {
    return (this.node?.properties?.tagPolicies || []).filter(t => !t.inherited);
  }

  /** All tag policies (inherited + local). */
  get allTagPolicies(): TagPolicyEntry[] {
    return [...this.inheritedTagPolicies, ...this.localTagPolicies];
  }

  toggleSection(section: string): void {
    const current = new Set(this.openSections());
    if (current.has(section)) {
      current.delete(section);
    } else {
      current.add(section);
    }
    this.openSections.set(current);
  }

  onLabelChange(event: Event): void {
    const value = (event.target as HTMLInputElement).value;
    this.emitChange({ label: value });
  }

  onDescriptionChange(event: Event): void {
    const value = (event.target as HTMLTextAreaElement).value;
    this.emitPropertyChange({ description: value });
  }

  onCidrChange(event: Event): void {
    const value = (event.target as HTMLInputElement).value;
    this.emitPropertyChange({ ipam: { cidr: value } });
  }

  onNamingTemplateChange(event: Event): void {
    const value = (event.target as HTMLInputElement).value;
    this.emitPropertyChange({ namingConfig: { template: value } });
  }

  onEnvironmentChange(event: Event): void {
    const value = (event.target as HTMLSelectElement).value;
    this.emitPropertyChange({ environmentDesignation: value === 'none' ? undefined : value });
  }

  onLocalTagChange(index: number, field: 'tagKey' | 'displayName', event: Event): void {
    const value = (event.target as HTMLInputElement).value;
    const tags = [...(this.node?.properties?.tagPolicies || [])];
    const localTags = tags.filter(t => !t.inherited);
    if (localTags[index]) {
      localTags[index] = { ...localTags[index], [field]: value };
    }
    const inheritedTags = tags.filter(t => t.inherited);
    this.emitPropertyChange({ tagPolicies: [...inheritedTags, ...localTags] });
  }

  onLocalTagRequiredChange(index: number, event: Event): void {
    const checked = (event.target as HTMLInputElement).checked;
    const tags = [...(this.node?.properties?.tagPolicies || [])];
    const localTags = tags.filter(t => !t.inherited);
    if (localTags[index]) {
      localTags[index] = { ...localTags[index], isRequired: checked };
    }
    const inheritedTags = tags.filter(t => t.inherited);
    this.emitPropertyChange({ tagPolicies: [...inheritedTags, ...localTags] });
  }

  addLocalTag(): void {
    const tags = [...(this.node?.properties?.tagPolicies || [])];
    tags.push({
      tagKey: '',
      displayName: '',
      isRequired: false,
      inherited: false,
    });
    this.emitPropertyChange({ tagPolicies: tags });
  }

  removeLocalTag(index: number): void {
    const tags = [...(this.node?.properties?.tagPolicies || [])];
    const localTags = tags.filter(t => !t.inherited);
    localTags.splice(index, 1);
    const inheritedTags = tags.filter(t => t.inherited);
    this.emitPropertyChange({ tagPolicies: [...inheritedTags, ...localTags] });
  }

  /** Emit updated node with top-level field changes. */
  private emitChange(partial: Partial<HierarchyNode>): void {
    if (!this.node) return;
    this.nodeChange.emit({ ...this.node, ...partial });
  }

  /** Emit updated node with property-level changes. */
  private emitPropertyChange(propPartial: Record<string, unknown>): void {
    if (!this.node) return;
    this.nodeChange.emit({
      ...this.node,
      properties: { ...this.node.properties, ...propPartial },
    });
  }

  /** Parse a CIDR string into address counts. */
  private parseCidr(cidr: string): CidrInfo {
    if (!cidr) return { valid: false, totalAddresses: 0, usableAddresses: 0, network: '', prefix: 0 };
    const match = cidr.match(/^(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\/(\d{1,2})$/);
    if (!match) return { valid: false, totalAddresses: 0, usableAddresses: 0, network: '', prefix: 0 };

    const octets = match[1].split('.').map(Number);
    const prefix = parseInt(match[2], 10);
    if (prefix < 0 || prefix > 32) return { valid: false, totalAddresses: 0, usableAddresses: 0, network: '', prefix: 0 };
    if (octets.some(o => o < 0 || o > 255)) return { valid: false, totalAddresses: 0, usableAddresses: 0, network: '', prefix: 0 };

    const totalAddresses = Math.pow(2, 32 - prefix);
    const usableAddresses = prefix <= 30 ? totalAddresses - 2 : (prefix === 31 ? 2 : 1);

    // Compute network address by masking
    const ipNum = ((octets[0] << 24) | (octets[1] << 16) | (octets[2] << 8) | octets[3]) >>> 0;
    const mask = prefix === 0 ? 0 : (0xFFFFFFFF << (32 - prefix)) >>> 0;
    const netNum = (ipNum & mask) >>> 0;
    const network = `${(netNum >>> 24) & 0xFF}.${(netNum >>> 16) & 0xFF}.${(netNum >>> 8) & 0xFF}.${netNum & 0xFF}`;

    return { valid: true, totalAddresses, usableAddresses, network, prefix };
  }
}
