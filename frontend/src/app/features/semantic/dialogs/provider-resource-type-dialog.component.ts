/**
 * Overview: Dialog for creating/editing provider resource types.
 * Architecture: Feature dialog for semantic layer CRUD (Section 5)
 * Dependencies: @angular/core, @angular/forms, app/shared/services/dialog.service
 * Concepts: Provider resource type CRUD, parameter schemas, status, is_system protection
 */
import { Component, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { DIALOG_DATA, DialogService } from '@shared/services/dialog.service';
import { SemanticProvider, SemanticProviderResourceType } from '@shared/models/semantic.model';

export interface PRTDialogData {
  prt: SemanticProviderResourceType | null;
  providers: SemanticProvider[];
  preselectedProviderId?: string;
}

@Component({
  selector: 'nimbus-provider-resource-type-dialog',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="dialog">
      <h2>{{ isEdit ? 'Edit Resource Type' : 'New Resource Type' }}</h2>
      <div class="form-group">
        <label>Provider</label>
        <select [(ngModel)]="providerId" [disabled]="isEdit">
          <option value="">Select provider...</option>
          @for (p of dialogData.providers; track p.id) {
            <option [value]="p.id">{{ p.displayName }}</option>
          }
        </select>
      </div>
      <div class="form-row">
        <div class="form-group half">
          <label>API Type</label>
          <input type="text" [(ngModel)]="apiType" [disabled]="isEdit && isSystem" placeholder="e.g. ec2:instance" />
        </div>
        <div class="form-group half">
          <label>Display Name</label>
          <input type="text" [(ngModel)]="displayName" placeholder="e.g. EC2 Instance" />
        </div>
      </div>
      <div class="form-group">
        <label>Description</label>
        <textarea [(ngModel)]="description" rows="2" placeholder="Optional description"></textarea>
      </div>
      <div class="form-row">
        <div class="form-group half">
          <label>Status</label>
          <select [(ngModel)]="status">
            <option value="available">Available</option>
            <option value="preview">Preview</option>
            <option value="deprecated">Deprecated</option>
          </select>
        </div>
        <div class="form-group half">
          <label>Documentation URL</label>
          <input type="text" [(ngModel)]="documentationUrl" placeholder="https://docs..." />
        </div>
      </div>
      <div class="form-group">
        <label>Parameter Schema (JSON)</label>
        <textarea [(ngModel)]="parameterSchemaJson" rows="4" class="mono" placeholder='{"cores": {"type": "integer", "default": 2}}'></textarea>
        @if (jsonError) {
          <span class="error">{{ jsonError }}</span>
        }
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
    .dialog { padding: 1.5rem; min-width: 520px; }
    h2 { margin: 0 0 1.25rem; font-size: 1.125rem; font-weight: 600; color: #1e293b; }
    .form-group { margin-bottom: 1rem; }
    .form-group label { display: block; font-size: 0.75rem; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.375rem; }
    .form-row { display: flex; gap: 1rem; }
    .half { flex: 1; }
    .mono { font-family: 'JetBrains Mono', 'Fira Code', monospace; font-size: 0.75rem; }
    .error { display: block; font-size: 0.6875rem; color: #dc2626; margin-top: 0.25rem; }
    input, textarea, select {
      width: 100%; box-sizing: border-box; padding: 0.5rem 0.75rem; border: 1px solid #e2e8f0;
      border-radius: 6px; font-size: 0.8125rem; font-family: inherit; color: #374151;
      background: #fff; outline: none;
    }
    input:focus, textarea:focus, select:focus { border-color: #3b82f6; }
    input:disabled, select:disabled { background: #f8fafc; color: #94a3b8; cursor: not-allowed; }
    .actions { display: flex; justify-content: flex-end; gap: 0.75rem; margin-top: 1.5rem; }
    .btn { font-family: inherit; font-size: 0.8125rem; font-weight: 500; border-radius: 6px; cursor: pointer; padding: 0.5rem 1.25rem; transition: background 0.15s; }
    .btn-cancel { background: #fff; color: #374151; border: 1px solid #e2e8f0; }
    .btn-cancel:hover { background: #f8fafc; }
    .btn-primary { background: #3b82f6; color: #fff; border: none; }
    .btn-primary:hover { background: #2563eb; }
    .btn-primary:disabled { background: #94a3b8; cursor: not-allowed; }
  `],
})
export class ProviderResourceTypeDialogComponent implements OnInit {
  dialogData = inject<PRTDialogData>(DIALOG_DATA);
  private dialogService = inject(DialogService);

  isEdit = false;
  isSystem = false;
  providerId = '';
  apiType = '';
  displayName = '';
  description = '';
  documentationUrl = '';
  status = 'available';
  parameterSchemaJson = '';
  jsonError = '';

  ngOnInit(): void {
    const prt = this.dialogData.prt;
    if (prt) {
      this.isEdit = true;
      this.isSystem = prt.isSystem;
      this.providerId = prt.providerId;
      this.apiType = prt.apiType;
      this.displayName = prt.displayName;
      this.description = prt.description || '';
      this.documentationUrl = prt.documentationUrl || '';
      this.status = prt.status;
      this.parameterSchemaJson = prt.parameterSchema ? JSON.stringify(prt.parameterSchema, null, 2) : '';
    } else if (this.dialogData.preselectedProviderId) {
      this.providerId = this.dialogData.preselectedProviderId;
    }
  }

  isValid(): boolean {
    if (this.parameterSchemaJson.trim()) {
      try {
        JSON.parse(this.parameterSchemaJson);
        this.jsonError = '';
      } catch {
        this.jsonError = 'Invalid JSON';
        return false;
      }
    }
    if (this.isEdit) return this.displayName.trim().length > 0;
    return this.providerId.length > 0 && this.apiType.trim().length > 0 && this.displayName.trim().length > 0;
  }

  onSave(): void {
    const parameterSchema = this.parameterSchemaJson.trim()
      ? JSON.parse(this.parameterSchemaJson)
      : null;

    if (this.isEdit) {
      this.dialogService.close({
        displayName: this.displayName,
        description: this.description || null,
        documentationUrl: this.documentationUrl || null,
        status: this.status,
        parameterSchema,
      });
    } else {
      this.dialogService.close({
        providerId: this.providerId,
        apiType: this.apiType,
        displayName: this.displayName,
        description: this.description || null,
        documentationUrl: this.documentationUrl || null,
        status: this.status,
        parameterSchema,
      });
    }
  }

  onCancel(): void {
    this.dialogService.close(undefined);
  }
}
