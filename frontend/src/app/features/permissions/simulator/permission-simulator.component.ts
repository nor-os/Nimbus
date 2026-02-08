/**
 * Overview: Permission simulator page for testing user permissions with resource and context inputs.
 * Architecture: Feature component for permission simulation (Section 3.2)
 * Dependencies: @angular/core, @angular/forms, @angular/router, app/core/services/permission.service, app/core/services/user.service
 * Concepts: Permission simulation, RBAC/ABAC testing, evaluation steps, what-if analysis
 */
import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { PermissionService } from '@core/services/permission.service';
import { UserService } from '@core/services/user.service';
import { SimulationResult } from '@core/models/permission.model';
import { User } from '@core/models/user.model';
import { LayoutComponent } from '@shared/components/layout/layout.component';

@Component({
  selector: 'nimbus-permission-simulator',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, LayoutComponent],
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

              <div class="form-group">
                <label for="permissionKey">Permission Key *</label>
                <input
                  id="permissionKey"
                  formControlName="permissionKey"
                  class="form-input mono-input"
                  placeholder="e.g. cmdb:ci:create:virtualmachine"
                />
                @if (form.get('permissionKey')?.hasError('required') && form.get('permissionKey')?.touched) {
                  <span class="error">Permission key is required</span>
                }
              </div>

              <div class="form-group">
                <label for="resource">Resource Context (JSON, optional)</label>
                <textarea
                  id="resource"
                  formControlName="resource"
                  class="form-input mono-input"
                  rows="4"
                  placeholder='{ "type": "virtualmachine", "owner": "user-123" }'
                ></textarea>
                @if (resourceParseError()) {
                  <span class="error">{{ resourceParseError() }}</span>
                }
              </div>

              <div class="form-group">
                <label for="context">Additional Context (JSON, optional)</label>
                <textarea
                  id="context"
                  formControlName="context"
                  class="form-input mono-input"
                  rows="4"
                  placeholder='{ "mfa_verified": true, "ip": "10.0.0.1" }'
                ></textarea>
                @if (contextParseError()) {
                  <span class="error">{{ contextParseError() }}</span>
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
    .form-group label {
      display: block; margin-bottom: 0.375rem; font-size: 0.8125rem;
      font-weight: 600; color: #374151;
    }
    .form-input {
      width: 100%; padding: 0.5rem 0.75rem; border: 1px solid #e2e8f0;
      border-radius: 6px; font-size: 0.8125rem; box-sizing: border-box;
      font-family: inherit; transition: border-color 0.15s;
    }
    .form-input:focus { border-color: #3b82f6; outline: none; box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.1); }
    .mono-input {
      font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
      font-size: 0.8125rem;
    }
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

  users = signal<User[]>([]);
  result = signal<SimulationResult | null>(null);
  simulating = signal(false);
  errorMessage = signal('');
  resourceParseError = signal('');
  contextParseError = signal('');

  form = this.fb.group({
    userId: ['', Validators.required],
    permissionKey: ['', Validators.required],
    resource: [''],
    context: [''],
  });

  ngOnInit(): void {
    this.loadUsers();
  }

  onSimulate(): void {
    if (this.form.invalid) return;

    this.resourceParseError.set('');
    this.contextParseError.set('');
    this.errorMessage.set('');

    const values = this.form.value;

    let resource: Record<string, unknown> | undefined;
    let context: Record<string, unknown> | undefined;

    if (values.resource?.trim()) {
      try {
        resource = JSON.parse(values.resource!);
      } catch {
        this.resourceParseError.set('Invalid JSON format');
        return;
      }
    }

    if (values.context?.trim()) {
      try {
        context = JSON.parse(values.context!);
      } catch {
        this.contextParseError.set('Invalid JSON format');
        return;
      }
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
}
