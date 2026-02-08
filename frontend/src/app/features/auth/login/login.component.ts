/**
 * Overview: Login page with email-first discovery flow and SSO provider support.
 * Architecture: Feature component for authentication (Section 3.2)
 * Dependencies: @angular/core, @angular/forms, @angular/router
 * Concepts: Authentication, email discovery, SSO, tenant slug routing
 */
import { Component, inject, signal, OnInit } from '@angular/core';
import { FormControl, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { AuthService } from '@core/auth/auth.service';
import { DiscoverResponse, SSOProviderInfo } from '@core/auth/auth.models';

@Component({
  selector: 'nimbus-login',
  standalone: true,
  imports: [ReactiveFormsModule],
  templateUrl: './login.component.html',
  styleUrl: './login.component.scss',
})
export class LoginComponent implements OnInit {
  private authService = inject(AuthService);
  private router = inject(Router);
  private route = inject(ActivatedRoute);

  error = signal<string | null>(null);
  loading = signal(false);
  phase = signal<'email' | 'auth'>('email');
  discoveryResult = signal<DiscoverResponse | null>(null);

  emailForm = new FormGroup({
    email: new FormControl('', [Validators.required, Validators.email]),
  });

  passwordForm = new FormGroup({
    password: new FormControl('', [Validators.required]),
  });

  ngOnInit(): void {
    this.authService.checkSetupStatus().subscribe({
      next: (status) => {
        if (!status.is_complete) {
          this.router.navigate(['/setup']);
        }
      },
    });

    if (this.authService.accessToken) {
      this.router.navigate(['/dashboard']);
      return;
    }

    // Check for slug route param
    const slug = this.route.snapshot.paramMap.get('slug');
    if (slug) {
      this.loading.set(true);
      this.authService.getLoginInfo(slug).subscribe({
        next: (info) => {
          this.loading.set(false);
          this.discoveryResult.set({
            found: true,
            tenant_id: info.tenant_id,
            tenant_name: info.tenant_name,
            tenant_slug: info.slug,
            has_local_auth: info.has_local_auth,
            sso_providers: info.sso_providers,
          });
          this.phase.set('auth');
        },
        error: () => {
          this.loading.set(false);
          this.error.set('Organization not found. Please check the URL or enter your email.');
        },
      });
    }
  }

  onDiscover(): void {
    if (this.emailForm.invalid) return;

    this.loading.set(true);
    this.error.set(null);

    this.authService.discover(this.emailForm.value.email!).subscribe({
      next: (result) => {
        this.loading.set(false);
        if (!result.found) {
          // Fallback: no domain mapping — show plain password login
          this.discoveryResult.set({ found: false, has_local_auth: true, sso_providers: [] });
        } else {
          this.discoveryResult.set(result);
        }
        this.phase.set('auth');
      },
      error: () => {
        this.loading.set(false);
        // Network/server error — still allow password login as fallback
        this.discoveryResult.set({ found: false, has_local_auth: true, sso_providers: [] });
        this.phase.set('auth');
      },
    });
  }

  onLogin(): void {
    if (this.passwordForm.invalid) return;

    this.loading.set(true);
    this.error.set(null);

    this.authService
      .login({
        email: this.emailForm.value.email!,
        password: this.passwordForm.value.password!,
      })
      .subscribe({
        next: () => {
          this.loading.set(false);
          this.router.navigate(['/dashboard']);
        },
        error: (err) => {
          this.loading.set(false);
          this.error.set(err.error?.error?.message ?? 'Login failed. Please try again.');
        },
      });
  }

  onSSOLogin(provider: SSOProviderInfo): void {
    const result = this.discoveryResult();
    if (!result?.tenant_id) return;
    this.authService.loginWithProvider(result.tenant_id, provider.id, provider.idp_type);
  }

  backToEmail(): void {
    this.phase.set('email');
    this.discoveryResult.set(null);
    this.error.set(null);
    this.passwordForm.reset();
  }
}
