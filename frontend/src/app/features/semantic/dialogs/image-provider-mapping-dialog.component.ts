/**
 * Overview: Dialog for creating/editing OS image provider mappings.
 * Architecture: Feature dialog for OS image provider mapping CRUD (Section 5)
 * Dependencies: @angular/core, @angular/forms, app/shared/services/dialog.service
 * Concepts: Provider-specific image references (AMI IDs, Azure URNs, template names)
 */
import { Component, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { DIALOG_DATA, DialogService } from '@shared/services/dialog.service';
import { SemanticProvider } from '@shared/models/semantic.model';
import { OsImageProviderMapping } from '@shared/models/os-image.model';

export interface ImageProviderMappingDialogData {
  mapping: OsImageProviderMapping | null;
  osImageId: string;
  providers: SemanticProvider[];
}

@Component({
  selector: 'nimbus-image-provider-mapping-dialog',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="dialog">
      <h2>{{ isEdit ? 'Edit Provider Mapping' : 'New Provider Mapping' }}</h2>
      <div class="form-group">
        <label>Provider</label>
        <select [(ngModel)]="providerId" [disabled]="isEdit">
          <option value="">Select provider...</option>
          @for (p of dialogData.providers; track p.id) {
            <option [value]="p.id">{{ p.displayName }}</option>
          }
        </select>
      </div>
      <div class="form-group">
        <label>Image Reference</label>
        <input type="text" [(ngModel)]="imageReference" [placeholder]="referencePlaceholder()" />
        <span class="hint">{{ referenceHint() }}</span>
      </div>
      <div class="form-group">
        <label>Notes</label>
        <textarea [(ngModel)]="notes" rows="2" placeholder="Optional notes about this mapping"></textarea>
      </div>
      <div class="actions">
        <button class="btn btn-cancel" (click)="onCancel()">Cancel</button>
        <button class="btn btn-primary" (click)="onSave()" [disabled]="!isValid()">
          {{ isEdit ? 'Update' : 'Create' }}
        </button>
      </div>
    </div>
  `,
  styles: [`
    .dialog { padding: 1.5rem; min-width: 480px; }
    h2 { margin: 0 0 1.25rem; font-size: 1.125rem; font-weight: 600; color: #1e293b; }
    .form-group { margin-bottom: 1rem; }
    .form-group label { display: block; font-size: 0.75rem; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.375rem; }
    .hint { display: block; font-size: 0.6875rem; color: #94a3b8; margin-top: 0.25rem; }
    input, textarea, select {
      width: 100%; box-sizing: border-box; padding: 0.5rem 0.75rem; border: 1px solid #e2e8f0;
      border-radius: 6px; font-size: 0.8125rem; font-family: inherit; color: #374151;
      background: #fff; outline: none;
    }
    input:focus, textarea:focus, select:focus { border-color: #3b82f6; }
    input:disabled, select:disabled { background: #f8fafc; color: #94a3b8; cursor: not-allowed; }
    .actions { display: flex; justify-content: flex-end; gap: 0.75rem; margin-top: 1.5rem; }
    .btn { font-family: inherit; font-size: 0.8125rem; font-weight: 500; border-radius: 6px; cursor: pointer; padding: 0.5rem 1.25rem; transition: background 0.15s; }
    .btn-cancel { background: #fff; color: #374141; border: 1px solid #e2e8f0; }
    .btn-cancel:hover { background: #f8fafc; }
    .btn-primary { background: #3b82f6; color: #fff; border: none; }
    .btn-primary:hover { background: #2563eb; }
    .btn-primary:disabled { background: #94a3b8; cursor: not-allowed; }
  `],
})
export class ImageProviderMappingDialogComponent implements OnInit {
  dialogData = inject<ImageProviderMappingDialogData>(DIALOG_DATA);
  private dialogService = inject(DialogService);

  isEdit = false;
  providerId = '';
  imageReference = '';
  notes = '';

  ngOnInit(): void {
    const mapping = this.dialogData.mapping;
    if (mapping) {
      this.isEdit = true;
      this.providerId = mapping.providerId;
      this.imageReference = mapping.imageReference;
      this.notes = mapping.notes || '';
    }
  }

  isValid(): boolean {
    if (this.isEdit) return this.imageReference.trim().length > 0;
    return this.providerId.length > 0 && this.imageReference.trim().length > 0;
  }

  referencePlaceholder(): string {
    const provider = this.dialogData.providers.find(p => p.id === this.providerId);
    if (!provider) return 'e.g. ami-0123456789abcdef0';
    const hints: Record<string, string> = {
      aws: 'ami-0123456789abcdef0',
      azure: 'Canonical:0001-com-ubuntu-server-jammy:22_04-lts:latest',
      gcp: 'projects/ubuntu-os-cloud/global/images/ubuntu-2204-jammy-v20240101',
      oci: 'ocid1.image.oc1...',
      proxmox: 'local:iso/ubuntu-22.04-server.iso',
    };
    return hints[provider.name] || 'Provider-specific image identifier';
  }

  referenceHint(): string {
    const provider = this.dialogData.providers.find(p => p.id === this.providerId);
    if (!provider) return 'Select a provider to see format hints';
    const hints: Record<string, string> = {
      aws: 'AWS AMI ID (e.g. ami-xxx)',
      azure: 'Azure image URN (Publisher:Offer:Sku:Version)',
      gcp: 'GCP image self-link or family',
      oci: 'OCI image OCID',
      proxmox: 'Proxmox template/ISO path',
    };
    return hints[provider.name] || 'Enter the provider-specific image reference';
  }

  onSave(): void {
    if (this.isEdit) {
      this.dialogService.close({
        imageReference: this.imageReference,
        notes: this.notes || null,
      });
    } else {
      this.dialogService.close({
        osImageId: this.dialogData.osImageId,
        providerId: this.providerId,
        imageReference: this.imageReference,
        notes: this.notes || null,
      });
    }
  }

  onCancel(): void {
    this.dialogService.close(undefined);
  }
}
