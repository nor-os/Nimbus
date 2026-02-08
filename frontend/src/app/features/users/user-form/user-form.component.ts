/**
 * Overview: Reactive form for creating new users. Editing is handled by user-detail inline fields.
 * Architecture: Feature component for user creation (Section 3.2)
 * Dependencies: @angular/core, @angular/forms, @angular/router, app/core/services/user.service
 * Concepts: User management, reactive forms, create mode only
 */
import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { UserService } from '@core/services/user.service';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { ToastService } from '@shared/services/toast.service';

@Component({
  selector: 'nimbus-user-form',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, LayoutComponent],
  template: `
    <nimbus-layout>
      <div class="user-form-page">
        <div class="page-header">
          <h1>Create User</h1>
        </div>

        <form [formGroup]="form" (ngSubmit)="onSubmit()" class="form">
          <div class="form-group">
            <label for="email">Email *</label>
            <input
              id="email"
              formControlName="email"
              type="email"
              class="form-input"
              placeholder="user@example.com"
            />
            @if (form.get('email')?.hasError('required') && form.get('email')?.touched) {
              <span class="error">Email is required</span>
            }
            @if (form.get('email')?.hasError('email') && form.get('email')?.touched) {
              <span class="error">Invalid email format</span>
            }
          </div>

          <div class="form-group">
            <label for="displayName">Display Name</label>
            <input
              id="displayName"
              formControlName="displayName"
              class="form-input"
              placeholder="Full name"
            />
          </div>

          <div class="form-group">
            <label for="password">Password</label>
            <input
              id="password"
              formControlName="password"
              type="password"
              class="form-input"
              placeholder="Leave blank for external auth"
            />
            @if (form.get('password')?.hasError('minlength') && form.get('password')?.touched) {
              <span class="error">Password must be at least 8 characters</span>
            }
          </div>

          @if (errorMessage()) {
            <div class="form-error">{{ errorMessage() }}</div>
          }

          <div class="form-actions">
            <button type="submit" class="btn btn-primary" [disabled]="form.invalid || submitting()">
              {{ submitting() ? 'Creating...' : 'Create' }}
            </button>
            <button type="button" class="btn btn-secondary" (click)="cancel()">Cancel</button>
          </div>
        </form>
      </div>
    </nimbus-layout>
  `,
  styles: [`
    .user-form-page { padding: 0; max-width: 720px; }
    .page-header {
      display: flex; justify-content: space-between; align-items: center;
      margin-bottom: 1.5rem;
    }
    .page-header h1 { margin: 0; font-size: 1.5rem; font-weight: 700; color: #1e293b; }
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
    .error { color: #ef4444; font-size: 0.75rem; margin-top: 0.25rem; display: block; }
    .form-error {
      background: #fef2f2; color: #dc2626; padding: 0.75rem 1rem;
      border-radius: 6px; margin-bottom: 1rem; font-size: 0.8125rem;
      border: 1px solid #fecaca;
    }
    .form-actions { display: flex; gap: 0.75rem; margin-top: 1.5rem; }
    .btn-primary {
      background: #3b82f6; color: #fff; padding: 0.5rem 1.5rem;
      border: none; border-radius: 6px; cursor: pointer; font-size: 0.8125rem;
      font-weight: 500; font-family: inherit; transition: background 0.15s;
    }
    .btn-primary:hover { background: #2563eb; }
    .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
    .btn-secondary {
      background: #fff; color: #374151; padding: 0.5rem 1.5rem;
      border: 1px solid #e2e8f0; border-radius: 6px; cursor: pointer;
      font-size: 0.8125rem; font-family: inherit; transition: background 0.15s;
    }
    .btn-secondary:hover { background: #f8fafc; }
  `],
})
export class UserFormComponent {
  private fb = inject(FormBuilder);
  private userService = inject(UserService);
  private router = inject(Router);
  private toastService = inject(ToastService);

  submitting = signal(false);
  errorMessage = signal('');

  form = this.fb.group({
    email: ['', [Validators.required, Validators.email]],
    displayName: [''],
    password: ['', [Validators.minLength(8), Validators.maxLength(128)]],
  });

  onSubmit(): void {
    if (this.form.invalid) return;

    this.submitting.set(true);
    this.errorMessage.set('');

    const values = this.form.value;

    this.userService
      .createUser({
        email: values.email!,
        password: values.password || null,
        display_name: values.displayName || null,
      })
      .subscribe({
        next: (user) => {
          this.toastService.success('User created');
          this.router.navigate(['/users', user.id]);
        },
        error: (err) => {
          this.submitting.set(false);
          const msg = err.error?.detail?.error?.message || 'Failed to create user';
          this.errorMessage.set(msg);
          this.toastService.error(msg);
        },
      });
  }

  cancel(): void {
    this.router.navigate(['/users']);
  }
}
