/**
 * Overview: Create/edit form for identity providers with dynamic config sections per IdP type.
 * Architecture: Feature component for IdP creation and editing (Section 3.2)
 * Dependencies: @angular/core, @angular/forms, @angular/router, app/core/services/identity-provider.service
 * Concepts: Identity providers, OIDC, SAML, reactive forms, dynamic configuration
 */
import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { IdentityProviderService } from '@core/services/identity-provider.service';
import { IdentityProvider } from '@core/models/identity-provider.model';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { ToastService } from '@shared/services/toast.service';

@Component({
  selector: 'nimbus-idp-form',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, LayoutComponent],
  template: `
    <nimbus-layout>
      <div class="idp-form-page">
        <h1>{{ isEditMode() ? 'Edit Identity Provider' : 'Create Identity Provider' }}</h1>

        <form [formGroup]="form" (ngSubmit)="onSubmit()" class="form">
          <div class="form-section">
            <h2>General</h2>

            <div class="form-group">
              <label for="name">Name *</label>
              <input id="name" formControlName="name" class="form-input" placeholder="e.g. Corporate SSO" />
              @if (form.get('name')?.hasError('required') && form.get('name')?.touched) {
                <span class="error">Name is required</span>
              }
            </div>

            <div class="form-group">
              <label for="idp_type">Type *</label>
              <select id="idp_type" formControlName="idp_type" class="form-input">
                <option value="local" [disabled]="hasLocalProvider()">Local{{ hasLocalProvider() ? ' (already configured)' : '' }}</option>
                <option value="oidc">OIDC</option>
                <option value="saml">SAML</option>
              </select>
            </div>

            <div class="form-row">
              <div class="form-group form-group-toggle">
                <label class="toggle-label">
                  <input type="checkbox" formControlName="is_enabled" />
                  <span>Enabled</span>
                </label>
              </div>

              <div class="form-group form-group-toggle">
                <label class="toggle-label">
                  <input type="checkbox" formControlName="is_default" />
                  <span>Default Provider</span>
                </label>
              </div>
            </div>
          </div>

          @if (selectedType() === 'oidc') {
            <div class="form-section">
              <h2>OIDC Configuration</h2>

              <div class="form-group">
                <label for="client_id">Client ID *</label>
                <input id="client_id" formControlName="oidc_client_id" class="form-input" placeholder="OAuth 2.0 Client ID" />
              </div>

              <div class="form-group">
                <label for="client_secret">Client Secret *</label>
                <input id="client_secret" formControlName="oidc_client_secret" type="password" class="form-input" placeholder="OAuth 2.0 Client Secret" />
              </div>

              <div class="form-group">
                <label for="issuer_url">Issuer URL *</label>
                <input id="issuer_url" formControlName="oidc_issuer_url" class="form-input" placeholder="https://accounts.example.com" />
                <span class="hint">Used for auto-discovery of endpoints via .well-known/openid-configuration</span>
              </div>

              <div class="form-group">
                <label for="scopes">Scopes</label>
                <input id="scopes" formControlName="oidc_scopes" class="form-input" placeholder="openid profile email" />
              </div>

              <div class="form-section-sub">
                <h3>Endpoint Overrides <span class="optional-tag">optional</span></h3>
                <span class="hint">Leave blank to auto-discover from the issuer URL.</span>

                <div class="form-group">
                  <label for="auth_endpoint">Authorization Endpoint</label>
                  <input id="auth_endpoint" formControlName="oidc_authorization_endpoint" class="form-input" placeholder="https://accounts.example.com/authorize" />
                </div>

                <div class="form-group">
                  <label for="token_endpoint">Token Endpoint</label>
                  <input id="token_endpoint" formControlName="oidc_token_endpoint" class="form-input" placeholder="https://accounts.example.com/token" />
                </div>

                <div class="form-group">
                  <label for="userinfo_endpoint">UserInfo Endpoint</label>
                  <input id="userinfo_endpoint" formControlName="oidc_userinfo_endpoint" class="form-input" placeholder="https://accounts.example.com/userinfo" />
                </div>
              </div>
            </div>
          }

          @if (selectedType() === 'saml') {
            <div class="form-section">
              <h2>SAML Configuration</h2>

              <div class="form-group">
                <label for="entity_id">IdP Entity ID *</label>
                <input id="entity_id" formControlName="saml_entity_id" class="form-input" placeholder="https://idp.example.com/metadata" />
              </div>

              <div class="form-group">
                <label for="sso_url">SSO URL *</label>
                <input id="sso_url" formControlName="saml_sso_url" class="form-input" placeholder="https://idp.example.com/sso" />
                <span class="hint">HTTP-Redirect or HTTP-POST binding URL for single sign-on</span>
              </div>

              <div class="form-group">
                <label for="slo_url">SLO URL</label>
                <input id="slo_url" formControlName="saml_slo_url" class="form-input" placeholder="https://idp.example.com/slo" />
                <span class="hint">Single logout URL (optional)</span>
              </div>

              <div class="form-group">
                <label for="certificate">Certificate *</label>
                <textarea id="certificate" formControlName="saml_certificate" class="form-input form-textarea" rows="6" placeholder="-----BEGIN CERTIFICATE-----&#10;...&#10;-----END CERTIFICATE-----"></textarea>
                <span class="hint">X.509 certificate for signature verification (PEM format)</span>
              </div>

              <div class="form-group">
                <label for="name_id_format">Name ID Format</label>
                <select id="name_id_format" formControlName="saml_name_id_format" class="form-input">
                  <option value="urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress">Email Address</option>
                  <option value="urn:oasis:names:tc:SAML:1.1:nameid-format:unspecified">Unspecified</option>
                  <option value="urn:oasis:names:tc:SAML:2.0:nameid-format:persistent">Persistent</option>
                  <option value="urn:oasis:names:tc:SAML:2.0:nameid-format:transient">Transient</option>
                </select>
              </div>

              <div class="form-group form-group-toggle">
                <label class="toggle-label">
                  <input type="checkbox" formControlName="saml_sign_requests" />
                  <span>Sign Authentication Requests</span>
                </label>
                <span class="hint">Enable if the IdP requires signed AuthnRequest messages</span>
              </div>
            </div>
          }

          @if (errorMessage()) {
            <div class="form-error">{{ errorMessage() }}</div>
          }

          <div class="form-actions">
            <button type="submit" class="btn btn-primary" [disabled]="form.invalid || submitting()">
              {{ submitting() ? 'Saving...' : (isEditMode() ? 'Update' : 'Create') }}
            </button>
            <button type="button" class="btn btn-secondary" (click)="cancel()">Cancel</button>
          </div>
        </form>
      </div>
    </nimbus-layout>
  `,
  styles: [`
    .idp-form-page { padding: 0; max-width: 640px; }
    h1 { font-size: 1.5rem; font-weight: 700; color: #1e293b; margin-bottom: 1.5rem; }
    .form {
      background: #fff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 1.5rem;
    }
    .form-section { margin-bottom: 1.5rem; }
    .form-section h2 {
      font-size: 1.0625rem; font-weight: 600; color: #1e293b;
      margin-bottom: 1rem; padding-bottom: 0.5rem; border-bottom: 1px solid #f1f5f9;
    }
    .form-section-sub {
      margin-top: 1.25rem; padding-top: 1rem; border-top: 1px dashed #e2e8f0;
    }
    .form-section-sub h3 {
      font-size: 0.875rem; font-weight: 600; color: #475569; margin-bottom: 0.75rem;
    }
    .optional-tag {
      font-size: 0.6875rem; font-weight: 400; color: #94a3b8; margin-left: 0.25rem;
    }
    .form-group { margin-bottom: 1.25rem; }
    .form-group label {
      display: block; margin-bottom: 0.375rem; font-size: 0.8125rem;
      font-weight: 600; color: #374151;
    }
    .hint {
      display: block; font-size: 0.75rem; color: #94a3b8; margin-top: 0.25rem;
    }
    .form-input {
      width: 100%; padding: 0.5rem 0.75rem; border: 1px solid #e2e8f0;
      border-radius: 6px; font-size: 0.8125rem; box-sizing: border-box;
      font-family: inherit; transition: border-color 0.15s;
    }
    .form-input:focus { border-color: #3b82f6; outline: none; box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.1); }
    .form-input:disabled { background: #f8fafc; color: #94a3b8; cursor: not-allowed; }
    .form-textarea { resize: vertical; min-height: 100px; }
    .form-row { display: flex; gap: 1.5rem; margin-bottom: 1.25rem; }
    .form-group-toggle { margin-bottom: 0; }
    .toggle-label {
      display: flex; align-items: center; gap: 0.5rem; font-size: 0.8125rem;
      font-weight: 500; color: #374151; cursor: pointer;
    }
    .toggle-label input[type="checkbox"] {
      width: 1rem; height: 1rem; accent-color: #3b82f6; cursor: pointer;
    }
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
export class IdpFormComponent implements OnInit {
  private fb = inject(FormBuilder);
  private idpService = inject(IdentityProviderService);
  private router = inject(Router);
  private route = inject(ActivatedRoute);
  private toastService = inject(ToastService);

  isEditMode = signal(false);
  submitting = signal(false);
  errorMessage = signal('');
  existingProvider = signal<IdentityProvider | null>(null);
  hasLocalProvider = signal(false);

  form = this.fb.group({
    name: ['', Validators.required],
    idp_type: ['local' as 'local' | 'oidc' | 'saml', Validators.required],
    is_enabled: [true],
    is_default: [false],
    // OIDC config fields
    oidc_client_id: [''],
    oidc_client_secret: [''],
    oidc_issuer_url: [''],
    oidc_scopes: ['openid profile email'],
    oidc_authorization_endpoint: [''],
    oidc_token_endpoint: [''],
    oidc_userinfo_endpoint: [''],
    // SAML config fields
    saml_entity_id: [''],
    saml_sso_url: [''],
    saml_slo_url: [''],
    saml_certificate: [''],
    saml_name_id_format: ['urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress'],
    saml_sign_requests: [false],
  });

  selectedType = signal<string>('local');

  ngOnInit(): void {
    const id = this.route.snapshot.params['id'];

    if (id) {
      this.isEditMode.set(true);
      this.form.get('idp_type')?.disable();
      this.loadProvider(id);
    } else {
      // In create mode, check if a LOCAL provider already exists
      this.idpService.listProviders().subscribe({
        next: (providers) => {
          if (providers.some((p) => p.idp_type === 'local')) {
            this.hasLocalProvider.set(true);
            this.form.patchValue({ idp_type: 'oidc' });
            this.selectedType.set('oidc');
          }
        },
      });
    }

    // Sync form control changes to signal
    this.form.get('idp_type')?.valueChanges.subscribe((value) => {
      this.selectedType.set(value ?? 'local');
    });
  }

  onSubmit(): void {
    if (this.form.invalid) return;

    this.submitting.set(true);
    this.errorMessage.set('');

    const values = this.form.getRawValue();
    const idpType = values.idp_type as 'local' | 'oidc' | 'saml';
    const config = this.buildConfig(idpType, values);

    if (this.isEditMode()) {
      const id = this.route.snapshot.params['id'];
      this.idpService.updateProvider(id, {
        name: values.name!,
        is_enabled: values.is_enabled ?? true,
        is_default: values.is_default ?? false,
        config,
      }).subscribe({
        next: () => {
          this.toastService.success('Identity provider updated');
          this.router.navigate(['/settings/auth']);
        },
        error: (err) => {
          this.submitting.set(false);
          const msg = err.error?.detail?.error?.message || 'Failed to update provider';
          this.errorMessage.set(msg);
          this.toastService.error(msg);
        },
      });
    } else {
      this.idpService.createProvider({
        name: values.name!,
        idp_type: idpType,
        is_enabled: values.is_enabled ?? true,
        is_default: values.is_default ?? false,
        config,
      }).subscribe({
        next: () => {
          this.toastService.success('Identity provider created');
          this.router.navigate(['/settings/auth']);
        },
        error: (err) => {
          this.submitting.set(false);
          const msg = err.error?.detail?.error?.message || 'Failed to create provider';
          this.errorMessage.set(msg);
          this.toastService.error(msg);
        },
      });
    }
  }

  cancel(): void {
    this.router.navigate(['/settings/auth']);
  }

  private loadProvider(id: string): void {
    this.idpService.getProvider(id).subscribe({
      next: (provider) => {
        this.existingProvider.set(provider);
        this.form.patchValue({
          name: provider.name,
          idp_type: provider.idp_type,
          is_enabled: provider.is_enabled,
          is_default: provider.is_default,
        });
        this.selectedType.set(provider.idp_type);
        this.patchConfigFields(provider.idp_type, provider.config);
      },
      error: (err) => {
        this.errorMessage.set(err.error?.detail?.error?.message || 'Failed to load provider');
      },
    });
  }

  private patchConfigFields(type: string, config: Record<string, unknown> | null): void {
    if (!config) return;

    if (type === 'oidc') {
      this.form.patchValue({
        oidc_client_id: (config['client_id'] as string) ?? '',
        oidc_client_secret: (config['client_secret'] as string) ?? '',
        oidc_issuer_url: (config['issuer_url'] as string) ?? '',
        oidc_scopes: (config['scopes'] as string) ?? 'openid profile email',
        oidc_authorization_endpoint: (config['authorization_endpoint'] as string) ?? '',
        oidc_token_endpoint: (config['token_endpoint'] as string) ?? '',
        oidc_userinfo_endpoint: (config['userinfo_endpoint'] as string) ?? '',
      });
    } else if (type === 'saml') {
      this.form.patchValue({
        saml_entity_id: (config['entity_id'] as string) ?? '',
        saml_sso_url: (config['sso_url'] as string) ?? '',
        saml_slo_url: (config['slo_url'] as string) ?? '',
        saml_certificate: (config['certificate'] as string) ?? '',
        saml_name_id_format: (config['name_id_format'] as string) ?? 'urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress',
        saml_sign_requests: (config['sign_requests'] as boolean) ?? false,
      });
    }
  }

  private buildConfig(type: string, values: Record<string, unknown>): Record<string, unknown> | null {
    if (type === 'oidc') {
      const config: Record<string, unknown> = {
        client_id: values['oidc_client_id'],
        client_secret: values['oidc_client_secret'],
        issuer_url: values['oidc_issuer_url'],
        scopes: values['oidc_scopes'],
      };
      // Only include optional endpoint overrides if populated
      if (values['oidc_authorization_endpoint']) config['authorization_endpoint'] = values['oidc_authorization_endpoint'];
      if (values['oidc_token_endpoint']) config['token_endpoint'] = values['oidc_token_endpoint'];
      if (values['oidc_userinfo_endpoint']) config['userinfo_endpoint'] = values['oidc_userinfo_endpoint'];
      return config;
    } else if (type === 'saml') {
      const config: Record<string, unknown> = {
        entity_id: values['saml_entity_id'],
        sso_url: values['saml_sso_url'],
        certificate: values['saml_certificate'],
        name_id_format: values['saml_name_id_format'],
        sign_requests: values['saml_sign_requests'],
      };
      if (values['saml_slo_url']) config['slo_url'] = values['saml_slo_url'];
      return config;
    }
    return null;
  }
}
