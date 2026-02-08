/**
 * Overview: Multi-step setup wizard container with step navigation.
 * Architecture: Feature component for first-run setup (Section 3.2)
 * Dependencies: @angular/core, @angular/forms, @angular/router
 * Concepts: First-run setup, wizard workflow
 */
import { Component, inject, signal } from '@angular/core';
import { FormControl, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from '@core/auth/auth.service';

@Component({
  selector: 'nimbus-setup',
  standalone: true,
  imports: [ReactiveFormsModule],
  templateUrl: './setup.component.html',
  styleUrl: './setup.component.scss',
})
export class SetupComponent {
  private authService = inject(AuthService);
  private router = inject(Router);

  currentStep = signal(0);
  error = signal<string | null>(null);
  loading = signal(false);

  adminForm = new FormGroup({
    email: new FormControl('', [Validators.required, Validators.email]),
    password: new FormControl('', [Validators.required, Validators.minLength(8)]),
    confirmPassword: new FormControl('', [Validators.required]),
  });

  orgForm = new FormGroup({
    organizationName: new FormControl('', [Validators.required, Validators.minLength(2)]),
  });

  readonly steps = ['Welcome', 'Admin Account', 'Organization', 'Complete'];

  next(): void {
    this.error.set(null);
    const step = this.currentStep();

    if (step === 1 && !this.validateAdminStep()) return;
    if (step === 2 && !this.validateOrgStep()) return;

    if (step === 2) {
      this.submitSetup();
      return;
    }

    this.currentStep.set(step + 1);
  }

  back(): void {
    const step = this.currentStep();
    if (step > 0) {
      this.currentStep.set(step - 1);
    }
  }

  goToDashboard(): void {
    this.router.navigate(['/dashboard']);
  }

  private validateAdminStep(): boolean {
    const { email, password, confirmPassword } = this.adminForm.controls;
    if (email.invalid) {
      this.error.set(email.hasError('required') ? 'Email is required.' : 'Please enter a valid email address.');
      return false;
    }
    if (password.invalid) {
      this.error.set(password.hasError('required') ? 'Password is required.' : 'Password must be at least 8 characters.');
      return false;
    }
    if (confirmPassword.invalid) {
      this.error.set('Please confirm your password.');
      return false;
    }
    if (password.value !== confirmPassword.value) {
      this.error.set('Passwords do not match.');
      return false;
    }
    return true;
  }

  private validateOrgStep(): boolean {
    if (this.orgForm.invalid) {
      this.error.set('Please enter an organization name.');
      return false;
    }
    return true;
  }

  private submitSetup(): void {
    this.loading.set(true);
    this.error.set(null);

    this.authService
      .initializeSetup({
        admin_email: this.adminForm.value.email!,
        admin_password: this.adminForm.value.password!,
        organization_name: this.orgForm.value.organizationName!,
      })
      .subscribe({
        next: () => {
          this.loading.set(false);
          this.currentStep.set(3);
        },
        error: (err) => {
          this.loading.set(false);
          this.error.set(err.error?.error?.message ?? 'Setup failed. Please try again.');
        },
      });
  }
}
