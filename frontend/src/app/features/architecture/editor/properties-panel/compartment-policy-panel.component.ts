/**
 * Overview: Compartment policy panel — attach, manage, and preview policies on topology compartments.
 * Architecture: Properties sub-panel for compartment policy management (Section 3.2)
 * Dependencies: @angular/core, @angular/common, @angular/forms, app/core/services/policy.service
 * Concepts: Attach library or inline policies to compartments, variable overrides, suppression,
 *     resolved policy preview with inheritance chain source indicators
 */
import { Component, EventEmitter, Input, Output, inject, signal, OnChanges, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { PolicyService } from '@core/services/policy.service';
import {
  PolicyLibraryEntry,
  CompartmentPolicyRef,
  ResolvedPolicy,
  PolicyStatement,
} from '@shared/models/policy.model';
import { TopologyCompartment } from '@shared/models/architecture.model';

@Component({
  selector: 'nimbus-compartment-policy-panel',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="policy-panel">
      <div class="section-header">
        <span class="section-title">Policies</span>
        @if (policies.length > 0 || inheritedCount > 0) {
          <span class="summary-badge">{{ policies.length }} direct{{ inheritedCount > 0 ? ', ' + inheritedCount + ' inherited' : '' }}</span>
        }
      </div>

      <!-- Attached policies list -->
      @for (pol of policies; track $index) {
        <div class="policy-row">
          <div class="policy-info">
            <div class="policy-info-top">
              <span class="badge" [class]="pol.policyId ? 'badge-library' : 'badge-inline'">
                {{ pol.policyId ? 'Library' : 'Inline' }}
              </span>
              <span class="policy-label">{{ getPolicyName(pol) }}</span>
            </div>
            @if (!readOnly) {
              <div class="policy-controls">
                <label class="inherit-toggle">
                  <input type="checkbox" [ngModel]="pol.inherit" (ngModelChange)="onInheritChange($index, $event)" />
                  <span class="toggle-label">Inherit</span>
                </label>
                <button class="btn-remove" (click)="removePolicy($index)" title="Remove">&times;</button>
              </div>
            }
          </div>

          <!-- Variable overrides for library policies -->
          @if (pol.policyId && getLibraryPolicy(pol.policyId)?.variables) {
            <div class="variable-overrides">
              @for (varEntry of getVariableEntries(pol.policyId); track varEntry.key) {
                <div class="override-row">
                  <span class="override-key" [title]="varEntry.description">{{ varEntry.key }}</span>
                  <input
                    type="text"
                    class="override-input"
                    [ngModel]="getOverrideValue(pol, varEntry.key)"
                    (ngModelChange)="onOverrideChange($index, varEntry.key, $event)"
                    [disabled]="readOnly"
                    [placeholder]="varEntry.default"
                  />
                </div>
              }
            </div>
          }
        </div>
      }

      @if (policies.length === 0) {
        <div class="empty-hint">No policies attached</div>
      }

      @if (!readOnly) {
        <div class="add-buttons">
          <button class="btn-add" (click)="showPicker.set(true)">+ Library Policy</button>
          <button class="btn-add" (click)="addInlinePolicy()">+ Inline Policy</button>
        </div>
      }

      <!-- Suppressed policies -->
      @if (suppressed.length > 0 || !readOnly) {
        <div class="suppression-section">
          <div class="section-title">Suppressed Policies</div>
          @if (!readOnly) {
            <input
              type="text"
              class="form-input-sm"
              [ngModel]="suppressedStr"
              (ngModelChange)="onSuppressedChange($event)"
              placeholder="Policy names (comma-separated)"
            />
          } @else {
            @for (name of suppressed; track name) {
              <span class="tag">{{ name }}</span>
            }
          }
        </div>
      }

      <!-- Preview Resolved -->
      <div class="preview-section">
        <button class="btn-preview" (click)="togglePreview()">
          {{ previewOpen() ? '&#9660;' : '&#9654;' }} Preview Resolved
        </button>
        @if (previewOpen()) {
          <div class="preview-list">
            @if (previewLoading()) {
              <div class="empty-hint">Loading...</div>
            } @else if (resolvedPolicies().length === 0) {
              <div class="empty-hint">No resolved policies</div>
            } @else {
              @for (rp of resolvedPolicies(); track rp.policyId) {
                <div class="resolved-row">
                  <div class="resolved-info">
                    <span class="badge" [class]="'badge-' + rp.source.replace('inherited_', 'inh-')">{{ rp.source }}</span>
                    <span class="resolved-name">{{ rp.name }}</span>
                  </div>
                  <div class="resolved-meta">
                    <span class="badge" [class]="'sev-' + rp.severity.toLowerCase()">{{ rp.severity }}</span>
                    <span class="stmt-count">{{ rp.statements.length || 0 }} stmts</span>
                  </div>
                </div>
              }
            }
          </div>
        }
      </div>

      <!-- Library Picker Modal -->
      @if (showPicker()) {
        <div class="picker-overlay" (click)="showPicker.set(false)">
          <div class="picker-panel" (click)="$event.stopPropagation()">
            <div class="picker-header">
              <span>Select Library Policy</span>
              <button class="btn-close-sm" (click)="showPicker.set(false)">&times;</button>
            </div>
            <input
              type="text"
              class="picker-search"
              [(ngModel)]="pickerSearch"
              (ngModelChange)="loadLibrary()"
              placeholder="Search policies..."
            />
            <div class="picker-list">
              @for (lib of libraryPolicies(); track lib.id) {
                <button class="picker-item" (click)="selectLibraryPolicy(lib)">
                  <span class="picker-name">{{ lib.displayName }}</span>
                  <span class="picker-meta">{{ lib.category }} / {{ lib.severity }}</span>
                </button>
              }
              @if (libraryPolicies().length === 0) {
                <div class="empty-hint">No policies found</div>
              }
            </div>
          </div>
        </div>
      }
    </div>
  `,
  styles: [`
    .policy-panel { margin-top: 8px; }
    .section-header {
      display: flex; align-items: center; justify-content: space-between;
      margin-bottom: 6px;
    }
    .section-title {
      font-size: 0.6875rem; font-weight: 600; text-transform: uppercase;
      letter-spacing: 0.04em; color: #64748b;
    }
    .summary-badge {
      font-size: 0.625rem; color: #3b82f6; font-weight: 500;
    }
    .policy-row {
      background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px;
      padding: 8px; margin-bottom: 6px;
    }
    .policy-info {
      display: flex; align-items: center; justify-content: space-between;
    }
    .policy-info-top { display: flex; align-items: center; gap: 6px; }
    .badge {
      display: inline-block; padding: 1px 6px; border-radius: 4px;
      font-size: 0.625rem; font-weight: 600;
    }
    .badge-library { background: #dbeafe; color: #3b82f6; }
    .badge-inline { background: #fef3c7; color: #d97706; }
    .badge-inherited_library, .badge-inh-library { background: #e0e7ff; color: #6366f1; }
    .badge-inherited_inline, .badge-inh-inline { background: #fef9c3; color: #ca8a04; }
    .policy-label { font-size: 0.75rem; font-weight: 500; color: #1e293b; }
    .policy-controls { display: flex; align-items: center; gap: 6px; }
    .inherit-toggle {
      display: flex; align-items: center; gap: 3px; font-size: 0.625rem;
      color: #64748b; cursor: pointer;
    }
    .inherit-toggle input { width: 12px; height: 12px; }
    .toggle-label { font-size: 0.625rem; }
    .btn-remove {
      width: 18px; height: 18px; border: none; background: none;
      color: #94a3b8; cursor: pointer; font-size: 0.875rem;
      display: flex; align-items: center; justify-content: center;
    }
    .btn-remove:hover { color: #dc2626; }
    .variable-overrides {
      margin-top: 6px; padding-top: 6px; border-top: 1px solid #e2e8f0;
    }
    .override-row {
      display: flex; align-items: center; gap: 6px; margin-bottom: 4px;
    }
    .override-key {
      font-size: 0.625rem; font-weight: 600; color: #64748b; min-width: 60px;
    }
    .override-input {
      flex: 1; padding: 3px 6px; border: 1px solid #e2e8f0; border-radius: 4px;
      font-size: 0.6875rem; color: #1e293b; background: #fff;
      font-family: inherit; outline: none;
    }
    .override-input:focus { border-color: #3b82f6; }
    .override-input:disabled { background: #f8fafc; }
    .empty-hint {
      font-size: 0.6875rem; color: #94a3b8; padding: 6px 0;
    }
    .add-buttons {
      display: flex; gap: 8px; margin: 6px 0;
    }
    .btn-add {
      font-size: 0.6875rem; color: #3b82f6; background: none;
      border: none; cursor: pointer; font-weight: 500; font-family: inherit;
    }
    .btn-add:hover { text-decoration: underline; }
    .suppression-section { margin-top: 8px; }
    .form-input-sm {
      width: 100%; padding: 4px 6px; border: 1px solid #e2e8f0;
      border-radius: 4px; font-size: 0.6875rem; color: #1e293b;
      background: #fff; font-family: inherit; outline: none;
      margin-top: 4px;
    }
    .form-input-sm:focus { border-color: #3b82f6; }
    .tag {
      display: inline-block; padding: 1px 6px; border-radius: 4px;
      font-size: 0.625rem; background: #f1f5f9; color: #64748b;
      margin: 2px 2px 0 0;
    }
    .preview-section { margin-top: 8px; }
    .btn-preview {
      font-size: 0.6875rem; color: #3b82f6; background: none;
      border: none; cursor: pointer; font-weight: 500; font-family: inherit;
      padding: 0;
    }
    .btn-preview:hover { text-decoration: underline; }
    .preview-list {
      margin-top: 6px; background: #fafbfc; border: 1px solid #e2e8f0;
      border-radius: 6px; padding: 6px; max-height: 200px; overflow-y: auto;
    }
    .resolved-row {
      display: flex; align-items: center; justify-content: space-between;
      padding: 4px 0; border-bottom: 1px solid #f1f5f9;
    }
    .resolved-row:last-child { border-bottom: none; }
    .resolved-info { display: flex; align-items: center; gap: 6px; }
    .resolved-name { font-size: 0.6875rem; font-weight: 500; color: #1e293b; }
    .resolved-meta { display: flex; align-items: center; gap: 6px; }
    .sev-critical { background: #fef2f2; color: #dc2626; }
    .sev-high { background: #fff7ed; color: #ea580c; }
    .sev-medium { background: #fefce8; color: #ca8a04; }
    .sev-low { background: #f0fdf4; color: #16a34a; }
    .sev-info { background: #eff6ff; color: #3b82f6; }
    .stmt-count { font-size: 0.625rem; color: #94a3b8; }

    /* Picker modal */
    .picker-overlay {
      position: fixed; inset: 0; background: rgba(0,0,0,0.3);
      display: flex; align-items: center; justify-content: center; z-index: 1000;
    }
    .picker-panel {
      background: #fff; border-radius: 10px; width: 360px; max-height: 400px;
      display: flex; flex-direction: column;
      box-shadow: 0 10px 30px rgba(0,0,0,0.15);
    }
    .picker-header {
      display: flex; align-items: center; justify-content: space-between;
      padding: 12px 16px; font-size: 0.8125rem; font-weight: 600; color: #1e293b;
    }
    .btn-close-sm {
      border: none; background: none; color: #94a3b8; cursor: pointer; font-size: 1rem;
    }
    .picker-search {
      margin: 0 16px 8px; padding: 6px 8px; border: 1px solid #e2e8f0;
      border-radius: 6px; font-size: 0.75rem; color: #1e293b;
      background: #fff; font-family: inherit; outline: none;
    }
    .picker-search:focus { border-color: #3b82f6; }
    .picker-list {
      flex: 1; overflow-y: auto; padding: 0 8px 8px;
    }
    .picker-item {
      display: flex; align-items: center; justify-content: space-between;
      width: 100%; padding: 8px; border: none; background: none;
      cursor: pointer; border-radius: 6px; font-family: inherit;
      text-align: left;
    }
    .picker-item:hover { background: #f1f5f9; }
    .picker-name { font-size: 0.75rem; font-weight: 500; color: #1e293b; }
    .picker-meta { font-size: 0.625rem; color: #94a3b8; }
  `],
})
export class CompartmentPolicyPanelComponent implements OnChanges {
  @Input() compartment!: TopologyCompartment;
  @Input() topologyId: string = '';
  @Input() readOnly = false;

  @Output() update = new EventEmitter<Partial<TopologyCompartment>>();

  private policySvc = inject(PolicyService);

  showPicker = signal(false);
  previewOpen = signal(false);
  previewLoading = signal(false);
  resolvedPolicies = signal<ResolvedPolicy[]>([]);
  libraryPolicies = signal<PolicyLibraryEntry[]>([]);

  pickerSearch = '';
  inheritedCount = 0;

  private libraryCache = new Map<string, PolicyLibraryEntry>();

  get policies(): CompartmentPolicyRef[] {
    return this.compartment.policies || [];
  }

  get suppressed(): string[] {
    return this.compartment.suppressedPolicies || [];
  }

  get suppressedStr(): string {
    return this.suppressed.join(', ');
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['compartment']) {
      this.previewOpen.set(false);
      this.resolvedPolicies.set([]);
    }
  }

  getPolicyName(ref: CompartmentPolicyRef): string {
    if (ref.policyId) {
      const lib = this.libraryCache.get(ref.policyId);
      return lib?.displayName || ref.policyId;
    }
    return ref.inline?.name || 'Inline Policy';
  }

  getLibraryPolicy(id: string): PolicyLibraryEntry | undefined {
    return this.libraryCache.get(id);
  }

  getVariableEntries(policyId: string): { key: string; default: string; description: string }[] {
    const lib = this.libraryCache.get(policyId);
    if (!lib?.variables) return [];
    return Object.entries(lib.variables).map(([key, v]) => ({
      key,
      default: v.default != null ? String(v.default) : '',
      description: v.description || '',
    }));
  }

  getOverrideValue(ref: CompartmentPolicyRef, key: string): string {
    const val = ref.variableOverrides?.[key];
    return val != null ? String(val) : '';
  }

  onInheritChange(index: number, value: boolean): void {
    const updated = [...this.policies];
    updated[index] = { ...updated[index], inherit: value };
    this.update.emit({ policies: updated });
  }

  onOverrideChange(index: number, key: string, value: string): void {
    const updated = [...this.policies];
    const overrides = { ...(updated[index].variableOverrides || {}) };
    overrides[key] = value || undefined;
    updated[index] = { ...updated[index], variableOverrides: overrides };
    this.update.emit({ policies: updated });
  }

  removePolicy(index: number): void {
    const updated = this.policies.filter((_, i) => i !== index);
    this.update.emit({ policies: updated });
  }

  onSuppressedChange(value: string): void {
    const names = value.split(',').map(s => s.trim()).filter(Boolean);
    this.update.emit({ suppressedPolicies: names });
  }

  loadLibrary(): void {
    this.policySvc.list({ search: this.pickerSearch || undefined }).subscribe({
      next: (entries) => {
        this.libraryPolicies.set(entries);
        for (const e of entries) {
          this.libraryCache.set(e.id, e);
        }
      },
    });
  }

  selectLibraryPolicy(lib: PolicyLibraryEntry): void {
    this.libraryCache.set(lib.id, lib);
    const updated = [...this.policies, {
      policyId: lib.id,
      inherit: true,
      variableOverrides: null,
    }];
    this.update.emit({ policies: updated });
    this.showPicker.set(false);
  }

  addInlinePolicy(): void {
    const updated: CompartmentPolicyRef[] = [...this.policies, {
      inline: {
        name: `inline-${Date.now().toString(36)}`,
        statements: [{
          sid: 'stmt-1',
          effect: 'deny' as const,
          actions: [],
          resources: ['*'],
          principals: ['*'],
          condition: null,
        }],
      },
      inherit: true,
    }];
    this.update.emit({ policies: updated });
  }

  togglePreview(): void {
    if (this.previewOpen()) {
      this.previewOpen.set(false);
      return;
    }
    this.previewOpen.set(true);
    if (!this.topologyId) return;

    this.previewLoading.set(true);
    this.policySvc.resolveCompartmentPolicies(this.topologyId, this.compartment.id).subscribe({
      next: (resolved) => {
        this.resolvedPolicies.set(resolved);
        this.inheritedCount = resolved.filter(r =>
          r.source === 'inherited_library' || r.source === 'inherited_inline'
        ).length;
        this.previewLoading.set(false);
      },
      error: () => {
        this.previewLoading.set(false);
      },
    });
  }
}
