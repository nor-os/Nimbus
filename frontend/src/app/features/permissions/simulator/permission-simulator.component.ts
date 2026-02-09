/**
 * Overview: Permission simulator page for testing user permissions with autocomplete and structured context inputs.
 * Architecture: Feature component for permission simulation (Section 3.2)
 * Dependencies: @angular/core, @angular/forms, @angular/router, app/core/services/permission.service, app/core/services/user.service
 * Concepts: Permission simulation, RBAC/ABAC testing, evaluation steps, what-if analysis
 */
import { Component, inject, signal, computed, OnInit, ElementRef, ViewChild, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, ReactiveFormsModule, Validators, FormsModule } from '@angular/forms';
import { PermissionService } from '@core/services/permission.service';
import { UserService } from '@core/services/user.service';
import { SimulationResult, Permission } from '@core/models/permission.model';
import { User } from '@core/models/user.model';
import { LayoutComponent } from '@shared/components/layout/layout.component';

interface KvPair { key: string; value: string; }

@Component({
  selector: 'nimbus-permission-simulator',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, FormsModule, LayoutComponent],
  template: `
    <nimbus-layout>
      <div class="simulator-page">
        <div class="page-header">
          <h1>Permission Simulator</h1>
        </div>

        <p class="subtitle">Test permission checks by simulating a user, permission key, and optional resource/context.</p>

        <div class="simulator-layout">
          <div class="simulator-form-panel">
            <form [formGroup]="form" (ngSubmit)="onSimulate()" class="form">
              <!-- User selector -->
              <div class="form-group">
                <label for="userId">User *</label>
                <select id="userId" formControlName="userId" class="form-input">
                  <option value="">Select a user...</option>
                  @for (user of users(); track user.id) {
                    <option [value]="user.id">{{ user.email }}{{ user.display_name ? ' (' + user.display_name + ')' : '' }}</option>
                  }
                </select>
                @if (form.get('userId')?.hasError('required') && form.get('userId')?.touched) {
                  <span class="error">User is required</span>
                }
              </div>

              <!-- Permission key with autocomplete -->
              <div class="form-group autocomplete-wrapper">
                <label for="permissionKey">Permission Key *</label>
                <input
                  #permissionInput
                  id="permissionKey"
                  formControlName="permissionKey"
                  class="form-input mono-input"
                  placeholder="Start typing to search permissions..."
                  autocomplete="off"
                  (focus)="onPermissionFocus()"
                  (input)="onPermissionInput()"
                  (keydown)="onPermissionKeydown($event)"
                />
                @if (form.get('permissionKey')?.hasError('required') && form.get('permissionKey')?.touched) {
                  <span class="error">Permission key is required</span>
                }
                @if (showDropdown() && filteredPermissions().length > 0) {
                  <div class="autocomplete-dropdown" #dropdown>
                    @for (perm of filteredPermissions(); track perm.id) {
                      <div
                        class="autocomplete-item"
                        [class.active]="activeIndex() === $index"
                        (mousedown)="selectPermission(perm)"
                        (mouseenter)="activeIndex.set($index)">
                        <span class="ac-key">{{ perm.key }}</span>
                        @if (perm.description) {
                          <span class="ac-desc">{{ perm.description }}</span>
                        }
                      </div>
                    }
                  </div>
                }
                @if (showDropdown() && filteredPermissions().length === 0 && permissionSearch().length > 0) {
                  <div class="autocomplete-dropdown">
                    <div class="autocomplete-empty">No matching permissions</div>
                  </div>
                }
              </div>

              <!-- Resource Context -->
              <div class="form-group">
                <div class="section-header">
                  <label>Resource Context <span class="optional">(optional)</span></label>
                  <button type="button" class="toggle-link" (click)="resourceRawMode.set(!resourceRawMode())">
                    {{ resourceRawMode() ? 'Builder' : 'Raw JSON' }}
                  </button>
                </div>

                @if (resourceRawMode()) {
                  <textarea
                    formControlName="resource"
                    class="form-input mono-input"
                    rows="4"
                    placeholder='{ "type": "virtualmachine", "owner": "user-123" }'
                  ></textarea>
                  @if (resourceParseError()) {
                    <span class="error">{{ resourceParseError() }}</span>
                  }
                } @else {
                  <div class="kv-builder">
                    @for (pair of resourcePairs(); track $index) {
                      <div class="kv-row">
                        <input
                          class="form-input kv-key"
                          placeholder="Key"
                          [value]="pair.key"
                          (input)="updateResourcePair($index, 'key', $event)"
                        />
                        <input
                          class="form-input kv-value"
                          placeholder="Value"
                          [value]="pair.value"
                          (input)="updateResourcePair($index, 'value', $event)"
                        />
                        <button type="button" class="kv-remove" (click)="removeResourcePair($index)" title="Remove">&#x2715;</button>
                      </div>
                    }
                    <button type="button" class="kv-add" (click)="addResourcePair()">+ Add property</button>
                  </div>
                }
              </div>

              <!-- Additional Context -->
              <div class="form-group">
                <div class="section-header">
                  <label>Additional Context <span class="optional">(optional)</span></label>
                  <button type="button" class="toggle-link" (click)="contextRawMode.set(!contextRawMode())">
                    {{ contextRawMode() ? 'Builder' : 'Raw JSON' }}
                  </button>
                </div>

                @if (contextRawMode()) {
                  <textarea
                    formControlName="context"
                    class="form-input mono-input"
                    rows="4"
                    placeholder='{ "mfa_verified": true, "ip": "10.0.0.1" }'
                  ></textarea>
                  @if (contextParseError()) {
                    <span class="error">{{ contextParseError() }}</span>
                  }
                } @else {
                  <div class="kv-builder">
                    <!-- Preset: mfa_verified -->
                    <div class="kv-row preset-row">
                      <span class="kv-preset-label">mfa_verified</span>
                      <select class="form-input kv-value" [value]="contextMfa()" (change)="contextMfa.set(asInputValue($event))">
                        <option value="">-- not set --</option>
                        <option value="true">true</option>
                        <option value="false">false</option>
                      </select>
                      <span class="kv-spacer"></span>
                    </div>
                    <!-- Preset: ip -->
                    <div class="kv-row preset-row">
                      <span class="kv-preset-label">ip</span>
                      <input
                        class="form-input kv-value"
                        placeholder="e.g. 10.0.0.1"
                        [value]="contextIp()"
                        (input)="contextIp.set(asInputValue($event))"
                      />
                      <span class="kv-spacer"></span>
                    </div>
                    <!-- Preset: time_of_day -->
                    <div class="kv-row preset-row">
                      <span class="kv-preset-label">time_of_day</span>
                      <input
                        class="form-input kv-value"
                        placeholder="e.g. 14:30"
                        [value]="contextTime()"
                        (input)="contextTime.set(asInputValue($event))"
                      />
                      <span class="kv-spacer"></span>
                    </div>
                    <!-- Custom pairs -->
                    @for (pair of contextPairs(); track $index) {
                      <div class="kv-row">
                        <input
                          class="form-input kv-key"
                          placeholder="Key"
                          [value]="pair.key"
                          (input)="updateContextPair($index, 'key', $event)"
                        />
                        <input
                          class="form-input kv-value"
                          placeholder="Value"
                          [value]="pair.value"
                          (input)="updateContextPair($index, 'value', $event)"
                        />
                        <button type="button" class="kv-remove" (click)="removeContextPair($index)" title="Remove">&#x2715;</button>
                      </div>
                    }
                    <button type="button" class="kv-add" (click)="addContextPair()">+ Add property</button>
                  </div>
                }
              </div>

              @if (errorMessage()) {
                <div class="form-error">{{ errorMessage() }}</div>
              }

              <button type="submit" class="btn btn-primary" [disabled]="form.invalid || simulating()">
                {{ simulating() ? 'Simulating...' : 'Simulate' }}
              </button>
            </form>
          </div>

          <div class="simulator-result-panel">
            <h2>Result</h2>

            @if (result()) {
              <div class="result-card" [class.result-allowed]="result()!.allowed" [class.result-denied]="!result()!.allowed">
                <div class="result-header">
                  <span class="result-badge" [class.badge-allowed]="result()!.allowed" [class.badge-denied]="!result()!.allowed">
                    {{ result()!.allowed ? 'ALLOWED' : 'DENIED' }}
                  </span>
                  <span class="result-key">{{ result()!.permission_key }}</span>
                </div>

                @if (result()!.source) {
                  <div class="result-source">
                    <span class="label">Source:</span>
                    <span class="value">{{ result()!.source }}</span>
                  </div>
                }

                @if (result()!.evaluation_steps.length > 0) {
                  <div class="evaluation-steps">
                    <h3>Evaluation Steps</h3>
                    <ol class="steps-list">
                      @for (step of result()!.evaluation_steps; track $index) {
                        <li>{{ step }}</li>
                      }
                    </ol>
                  </div>
                }
              </div>
            } @else {
              <div class="result-placeholder">
                <p>Run a simulation to see the result here.</p>
              </div>
            }
          </div>
        </div>
      </div>
    </nimbus-layout>
  `,
  styles: [`
    .simulator-page { padding: 0; }
    .page-header {
      display: flex; justify-content: space-between; align-items: center;
      margin-bottom: 0.5rem;
    }
    .page-header h1 { margin: 0; font-size: 1.5rem; font-weight: 700; color: #1e293b; }
    .subtitle { color: #64748b; font-size: 0.8125rem; margin-bottom: 1.5rem; }
    .simulator-layout { display: flex; gap: 1.5rem; align-items: flex-start; }
    .simulator-form-panel { flex: 1; min-width: 0; }
    .simulator-result-panel { width: 380px; flex-shrink: 0; }
    .simulator-result-panel h2 { font-size: 1.0625rem; font-weight: 600; color: #1e293b; margin: 0 0 1rem 0; }
    .form {
      background: #fff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 1.5rem;
    }
    .form-group { margin-bottom: 1.25rem; }
    .form-group label, .section-header label {
      display: block; margin-bottom: 0.375rem; font-size: 0.8125rem;
      font-weight: 600; color: #374151;
    }
    .form-input {
      width: 100%; padding: 0.5rem 0.75rem; border: 1px solid #e2e8f0;
      border-radius: 6px; font-size: 0.8125rem; box-sizing: border-box;
      font-family: inherit; transition: border-color 0.15s;
      background: #fff; color: #1e293b;
    }
    .form-input:focus { border-color: #3b82f6; outline: none; box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.1); }
    .mono-input {
      font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
      font-size: 0.8125rem;
    }
    .optional { font-weight: 400; color: #94a3b8; }
    .error { color: #ef4444; font-size: 0.75rem; margin-top: 0.25rem; display: block; }
    .form-error {
      background: #fef2f2; color: #dc2626; padding: 0.75rem 1rem;
      border-radius: 6px; margin-bottom: 1rem; font-size: 0.8125rem;
      border: 1px solid #fecaca;
    }
    .btn-primary {
      background: #3b82f6; color: #fff; padding: 0.5rem 1.5rem;
      border: none; border-radius: 6px; cursor: pointer; font-size: 0.8125rem;
      font-weight: 500; font-family: inherit; transition: background 0.15s;
    }
    .btn-primary:hover:not(:disabled) { background: #2563eb; }
    .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }

    /* Autocomplete */
    .autocomplete-wrapper { position: relative; }
    .autocomplete-dropdown {
      position: absolute; left: 0; right: 0; top: 100%; margin-top: 2px;
      background: #fff; border: 1px solid #e2e8f0; border-radius: 6px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.08); z-index: 50;
      max-height: 240px; overflow-y: auto;
    }
    .autocomplete-item {
      padding: 0.5rem 0.75rem; cursor: pointer; display: flex;
      flex-direction: column; gap: 0.125rem;
      border-bottom: 1px solid #f8fafc;
    }
    .autocomplete-item:last-child { border-bottom: none; }
    .autocomplete-item:hover, .autocomplete-item.active { background: #f0f7ff; }
    .ac-key {
      font-family: 'SFMono-Regular', Consolas, monospace;
      font-size: 0.8125rem; color: #1e293b; font-weight: 500;
    }
    .ac-desc { font-size: 0.6875rem; color: #64748b; }
    .autocomplete-empty {
      padding: 0.75rem; text-align: center; color: #94a3b8; font-size: 0.8125rem;
    }

    /* Section header with toggle */
    .section-header {
      display: flex; justify-content: space-between; align-items: baseline;
      margin-bottom: 0.375rem;
    }
    .section-header label { margin-bottom: 0; }
    .toggle-link {
      background: none; border: none; cursor: pointer; font-size: 0.75rem;
      color: #3b82f6; font-weight: 500; padding: 0; font-family: inherit;
    }
    .toggle-link:hover { color: #2563eb; text-decoration: underline; }

    /* Key-Value Builder */
    .kv-builder {
      background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px;
      padding: 0.75rem;
    }
    .kv-row {
      display: flex; gap: 0.5rem; align-items: center; margin-bottom: 0.5rem;
    }
    .kv-row:last-of-type { margin-bottom: 0.5rem; }
    .kv-key { flex: 0 0 35%; }
    .kv-value { flex: 1; }
    .kv-remove {
      background: none; border: none; cursor: pointer; color: #94a3b8;
      font-size: 0.875rem; padding: 0.25rem; line-height: 1; flex-shrink: 0;
      width: 24px; height: 24px; display: flex; align-items: center; justify-content: center;
      border-radius: 4px;
    }
    .kv-remove:hover { color: #ef4444; background: #fef2f2; }
    .kv-spacer { width: 24px; flex-shrink: 0; }
    .kv-add {
      background: none; border: 1px dashed #cbd5e1; border-radius: 4px;
      cursor: pointer; font-size: 0.75rem; color: #64748b; padding: 0.375rem 0.75rem;
      font-family: inherit; width: 100%; transition: all 0.15s;
    }
    .kv-add:hover { border-color: #3b82f6; color: #3b82f6; background: #f0f7ff; }

    /* Preset rows */
    .preset-row { }
    .kv-preset-label {
      flex: 0 0 35%; font-family: 'SFMono-Regular', Consolas, monospace;
      font-size: 0.8125rem; color: #374151; font-weight: 500;
      padding: 0.5rem 0.75rem; box-sizing: border-box;
    }

    /* Result panel */
    .result-placeholder {
      background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
      padding: 2rem; text-align: center;
    }
    .result-placeholder p { color: #94a3b8; font-size: 0.8125rem; margin: 0; }
    .result-card {
      background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
      padding: 1.25rem; border-left: 4px solid;
    }
    .result-allowed { border-left-color: #16a34a; }
    .result-denied { border-left-color: #dc2626; }
    .result-header { display: flex; align-items: center; gap: 0.75rem; margin-bottom: 1rem; }
    .result-badge {
      padding: 0.25rem 0.75rem; border-radius: 12px; font-size: 0.75rem;
      font-weight: 700; letter-spacing: 0.05em;
    }
    .badge-allowed { background: #dcfce7; color: #16a34a; }
    .badge-denied { background: #fef2f2; color: #dc2626; }
    .result-key {
      font-family: 'SFMono-Regular', Consolas, monospace; font-size: 0.75rem;
      color: #1e293b; font-weight: 500;
    }
    .result-source { margin-bottom: 1rem; font-size: 0.8125rem; }
    .result-source .label { color: #64748b; font-weight: 600; margin-right: 0.375rem; }
    .result-source .value { color: #1e293b; }
    .evaluation-steps { margin-top: 1rem; }
    .evaluation-steps h3 {
      font-size: 0.8125rem; font-weight: 600; color: #374151;
      margin: 0 0 0.625rem 0; padding-bottom: 0.375rem;
      border-bottom: 1px solid #f1f5f9;
    }
    .steps-list {
      margin: 0; padding: 0 0 0 1.25rem; font-size: 0.8125rem; color: #374151;
    }
    .steps-list li { margin-bottom: 0.375rem; line-height: 1.5; }
  `],
})
export class PermissionSimulatorComponent implements OnInit {
  private fb = inject(FormBuilder);
  private permissionService = inject(PermissionService);
  private userService = inject(UserService);

  @ViewChild('permissionInput') permissionInput!: ElementRef<HTMLInputElement>;
  @ViewChild('dropdown') dropdownEl?: ElementRef<HTMLDivElement>;

  users = signal<User[]>([]);
  permissions = signal<Permission[]>([]);
  result = signal<SimulationResult | null>(null);
  simulating = signal(false);
  errorMessage = signal('');
  resourceParseError = signal('');
  contextParseError = signal('');

  // Autocomplete state
  showDropdown = signal(false);
  permissionSearch = signal('');
  activeIndex = signal(0);

  filteredPermissions = computed(() => {
    const search = this.permissionSearch().toLowerCase();
    const all = this.permissions();
    if (!search) return all.slice(0, 50);
    return all.filter(p =>
      p.key.toLowerCase().includes(search) ||
      (p.description?.toLowerCase().includes(search) ?? false)
    ).slice(0, 50);
  });

  // Context builder state
  resourceRawMode = signal(false);
  contextRawMode = signal(false);
  resourcePairs = signal<KvPair[]>([{ key: '', value: '' }]);
  contextPairs = signal<KvPair[]>([]);

  // Preset context fields
  contextMfa = signal('');
  contextIp = signal('');
  contextTime = signal('');

  form = this.fb.group({
    userId: ['', Validators.required],
    permissionKey: ['', Validators.required],
    resource: [''],
    context: [''],
  });

  ngOnInit(): void {
    this.loadUsers();
    this.loadPermissions();
  }

  @HostListener('document:click', ['$event'])
  onDocumentClick(event: MouseEvent): void {
    const target = event.target as HTMLElement;
    if (!target.closest('.autocomplete-wrapper')) {
      this.showDropdown.set(false);
    }
  }

  onPermissionFocus(): void {
    this.permissionSearch.set(this.form.get('permissionKey')?.value || '');
    this.showDropdown.set(true);
    this.activeIndex.set(0);
  }

  onPermissionInput(): void {
    const val = this.form.get('permissionKey')?.value || '';
    this.permissionSearch.set(val);
    this.showDropdown.set(true);
    this.activeIndex.set(0);
  }

  onPermissionKeydown(event: KeyboardEvent): void {
    const filtered = this.filteredPermissions();
    if (!this.showDropdown() || filtered.length === 0) return;

    if (event.key === 'ArrowDown') {
      event.preventDefault();
      this.activeIndex.set(Math.min(this.activeIndex() + 1, filtered.length - 1));
      this.scrollActiveIntoView();
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      this.activeIndex.set(Math.max(this.activeIndex() - 1, 0));
      this.scrollActiveIntoView();
    } else if (event.key === 'Enter' && this.showDropdown()) {
      event.preventDefault();
      event.stopPropagation();
      const selected = filtered[this.activeIndex()];
      if (selected) this.selectPermission(selected);
    } else if (event.key === 'Escape') {
      this.showDropdown.set(false);
    }
  }

  selectPermission(perm: Permission): void {
    this.form.get('permissionKey')?.setValue(perm.key);
    this.permissionSearch.set(perm.key);
    this.showDropdown.set(false);
  }

  // Key-value builder helpers
  asInputValue(event: Event): string {
    return (event.target as HTMLInputElement | HTMLSelectElement).value;
  }

  addResourcePair(): void {
    this.resourcePairs.update(pairs => [...pairs, { key: '', value: '' }]);
  }

  removeResourcePair(index: number): void {
    this.resourcePairs.update(pairs => pairs.filter((_, i) => i !== index));
  }

  updateResourcePair(index: number, field: 'key' | 'value', event: Event): void {
    const val = (event.target as HTMLInputElement).value;
    this.resourcePairs.update(pairs => pairs.map((p, i) => i === index ? { ...p, [field]: val } : p));
  }

  addContextPair(): void {
    this.contextPairs.update(pairs => [...pairs, { key: '', value: '' }]);
  }

  removeContextPair(index: number): void {
    this.contextPairs.update(pairs => pairs.filter((_, i) => i !== index));
  }

  updateContextPair(index: number, field: 'key' | 'value', event: Event): void {
    const val = (event.target as HTMLInputElement).value;
    this.contextPairs.update(pairs => pairs.map((p, i) => i === index ? { ...p, [field]: val } : p));
  }

  onSimulate(): void {
    if (this.form.invalid) return;

    this.resourceParseError.set('');
    this.contextParseError.set('');
    this.errorMessage.set('');

    const values = this.form.value;

    let resource: Record<string, unknown> | undefined;
    let context: Record<string, unknown> | undefined;

    // Build resource from builder or raw JSON
    if (this.resourceRawMode()) {
      if (values.resource?.trim()) {
        try {
          resource = JSON.parse(values.resource!);
        } catch {
          this.resourceParseError.set('Invalid JSON format');
          return;
        }
      }
    } else {
      resource = this.buildKvObject(this.resourcePairs());
    }

    // Build context from builder or raw JSON
    if (this.contextRawMode()) {
      if (values.context?.trim()) {
        try {
          context = JSON.parse(values.context!);
        } catch {
          this.contextParseError.set('Invalid JSON format');
          return;
        }
      }
    } else {
      context = this.buildContextObject();
    }

    this.simulating.set(true);
    this.result.set(null);

    this.permissionService
      .simulatePermission(values.userId!, values.permissionKey!, resource, context)
      .subscribe({
        next: (result) => {
          this.result.set(result);
          this.simulating.set(false);
        },
        error: (err) => {
          this.simulating.set(false);
          this.errorMessage.set(err.error?.detail?.error?.message || 'Simulation failed');
        },
      });
  }

  private loadUsers(): void {
    this.userService.listUsers(0, 200).subscribe({
      next: (response) => this.users.set(response.items),
    });
  }

  private loadPermissions(): void {
    this.permissionService.listPermissions().subscribe({
      next: (perms) => this.permissions.set(perms),
    });
  }

  private buildKvObject(pairs: KvPair[]): Record<string, unknown> | undefined {
    const filled = pairs.filter(p => p.key.trim());
    if (filled.length === 0) return undefined;
    const obj: Record<string, unknown> = {};
    for (const pair of filled) {
      obj[pair.key.trim()] = this.parseValue(pair.value);
    }
    return obj;
  }

  private buildContextObject(): Record<string, unknown> | undefined {
    const obj: Record<string, unknown> = {};

    if (this.contextMfa()) {
      obj['mfa_verified'] = this.contextMfa() === 'true';
    }
    if (this.contextIp()) {
      obj['ip'] = this.contextIp();
    }
    if (this.contextTime()) {
      obj['time_of_day'] = this.contextTime();
    }

    const customPairs = this.contextPairs().filter(p => p.key.trim());
    for (const pair of customPairs) {
      obj[pair.key.trim()] = this.parseValue(pair.value);
    }

    return Object.keys(obj).length > 0 ? obj : undefined;
  }

  private parseValue(val: string): unknown {
    const trimmed = val.trim();
    if (trimmed === 'true') return true;
    if (trimmed === 'false') return false;
    if (trimmed === 'null') return null;
    if (trimmed !== '' && !isNaN(Number(trimmed))) return Number(trimmed);
    return trimmed;
  }

  private scrollActiveIntoView(): void {
    setTimeout(() => {
      const el = this.dropdownEl?.nativeElement;
      if (!el) return;
      const active = el.querySelector('.autocomplete-item.active') as HTMLElement;
      if (active) active.scrollIntoView({ block: 'nearest' });
    });
  }
}
