/**
 * Overview: Impersonation configuration form for tenant settings.
 * Architecture: Feature component for impersonation config management (Section 3.2)
 * Dependencies: @angular/core, @angular/forms, @angular/common, app/core/services/impersonation.service
 * Concepts: Impersonation configuration, approval toggles, duration settings
 */
import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ImpersonationService } from '@core/services/impersonation.service';
import { ImpersonationConfig } from '@core/models/impersonation.model';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { ToastService } from '@shared/services/toast.service';

@Component({
  selector: 'nimbus-impersonation-config',
  standalone: true,
  imports: [CommonModule, FormsModule, LayoutComponent],
  template: `
    <nimbus-layout>
      <div class="page">
        <div class="page-header">
          <h1>Impersonation Configuration</h1>
        </div>

        @if (loading()) {
          <div class="loading">Loading configuration...</div>
        } @else if (config()) {
          <div class="config-card">
            <h2>Standard Impersonation</h2>
            <div class="field-row">
              <label>Default Duration (minutes)</label>
              <input
                type="number"
                class="form-input form-input-sm"
                [(ngModel)]="config()!.standard_duration_minutes"
                (ngModelChange)="markDirty()"
                min="5"
                max="480"
              />
            </div>
            <div class="field-row">
              <label>Requires Approval</label>
              <label class="toggle-wrapper">
                <input
                  type="checkbox"
                  class="toggle-input"
                  [(ngModel)]="config()!.standard_requires_approval"
                  (ngModelChange)="markDirty()"
                />
                <span class="toggle-track"><span class="toggle-thumb"></span></span>
              </label>
            </div>

            <h2>Override Impersonation</h2>
            <div class="field-row">
              <label>Default Duration (minutes)</label>
              <input
                type="number"
                class="form-input form-input-sm"
                [(ngModel)]="config()!.override_duration_minutes"
                (ngModelChange)="markDirty()"
                min="5"
                max="480"
              />
            </div>
            <div class="field-row">
              <label>Requires Approval</label>
              <label class="toggle-wrapper">
                <input
                  type="checkbox"
                  class="toggle-input"
                  [(ngModel)]="config()!.override_requires_approval"
                  (ngModelChange)="markDirty()"
                />
                <span class="toggle-track"><span class="toggle-thumb"></span></span>
              </label>
            </div>

            <h2>Limits</h2>
            <div class="field-row">
              <label>Maximum Duration (minutes)</label>
              <input
                type="number"
                class="form-input form-input-sm"
                [(ngModel)]="config()!.max_duration_minutes"
                (ngModelChange)="markDirty()"
                min="5"
                max="1440"
              />
            </div>

            @if (dirty()) {
              <div class="save-row">
                <button class="btn btn-primary" [disabled]="saving()" (click)="save()">
                  {{ saving() ? 'Saving...' : 'Save Changes' }}
                </button>
              </div>
            }
          </div>
        }
      </div>
    </nimbus-layout>
  `,
  styles: [`
    .page { padding: 0; }
    .page-header {
      display: flex; justify-content: space-between; align-items: center;
      margin-bottom: 1.5rem;
    }
    .page-header h1 { margin: 0; font-size: 1.5rem; font-weight: 700; color: #1e293b; }
    .config-card {
      background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
      padding: 1.5rem; max-width: 600px;
    }
    .config-card h2 {
      font-size: 1rem; font-weight: 600; color: #1e293b;
      margin: 1.5rem 0 1rem; padding-top: 1rem; border-top: 1px solid #e2e8f0;
    }
    .config-card h2:first-child { margin-top: 0; padding-top: 0; border-top: none; }
    .field-row {
      display: flex; align-items: center; justify-content: space-between;
      margin-bottom: 0.75rem;
    }
    .field-row label:first-child {
      font-size: 0.8125rem; font-weight: 500; color: #374151;
    }
    .form-input {
      padding: 0.5rem 0.75rem; border: 1px solid #e2e8f0; border-radius: 6px;
      font-size: 0.8125rem; font-family: inherit;
    }
    .form-input:focus { border-color: #3b82f6; outline: none; }
    .form-input-sm { width: 100px; text-align: center; }
    .toggle-wrapper { display: flex; align-items: center; cursor: pointer; }
    .toggle-input { position: absolute; opacity: 0; width: 0; height: 0; }
    .toggle-track {
      position: relative; width: 36px; height: 20px; background: #cbd5e1;
      border-radius: 10px; transition: background 0.2s; flex-shrink: 0;
    }
    .toggle-input:checked + .toggle-track { background: #3b82f6; }
    .toggle-thumb {
      position: absolute; top: 2px; left: 2px; width: 16px; height: 16px;
      background: #fff; border-radius: 50%; transition: transform 0.2s;
    }
    .toggle-input:checked + .toggle-track .toggle-thumb { transform: translateX(16px); }
    .save-row { margin-top: 1.25rem; }
    .btn {
      padding: 0.5rem 1rem; border-radius: 6px; font-size: 0.8125rem;
      font-weight: 500; cursor: pointer; font-family: inherit; border: none;
    }
    .btn-primary { background: #3b82f6; color: #fff; }
    .btn-primary:hover { background: #2563eb; }
    .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
    .loading { color: #64748b; font-size: 0.8125rem; padding: 2rem; text-align: center; }
  `],
})
export class ImpersonationConfigComponent implements OnInit {
  private impersonationService = inject(ImpersonationService);
  private toastService = inject(ToastService);

  config = signal<ImpersonationConfig | null>(null);
  loading = signal(true);
  dirty = signal(false);
  saving = signal(false);

  ngOnInit(): void {
    this.loadConfig();
  }

  markDirty(): void {
    this.dirty.set(true);
  }

  loadConfig(): void {
    this.loading.set(true);
    this.impersonationService.getConfig().subscribe({
      next: (config) => {
        this.config.set({ ...config });
        this.loading.set(false);
        this.dirty.set(false);
      },
      error: () => {
        this.loading.set(false);
        this.toastService.error('Failed to load config');
      },
    });
  }

  save(): void {
    const cfg = this.config();
    if (!cfg) return;

    this.saving.set(true);
    this.impersonationService.updateConfig(cfg).subscribe({
      next: (updated) => {
        this.config.set({ ...updated });
        this.saving.set(false);
        this.dirty.set(false);
        this.toastService.success('Configuration saved');
      },
      error: (err) => {
        this.saving.set(false);
        this.toastService.error(err.error?.detail?.error?.message || 'Failed to save config');
      },
    });
  }
}
