/**
 * Overview: Dialog for creating/editing type mappings between provider resource types and
 *     semantic types.
 * Architecture: Feature dialog for semantic layer CRUD (Section 5)
 * Dependencies: @angular/core, @angular/forms, app/shared/services/dialog.service
 * Concepts: Type mapping CRUD, parameter mapping JSON, is_system protection
 */
import { Component, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { DIALOG_DATA, DialogService } from '@shared/services/dialog.service';
import {
  SemanticProviderResourceType,
  SemanticResourceType,
  SemanticTypeMapping,
} from '@shared/models/semantic.model';
import { SearchableSelectComponent, SelectOption } from '@shared/components/searchable-select/searchable-select.component';

export interface TypeMappingDialogData {
  mapping: SemanticTypeMapping | null;
  providerResourceTypes: SemanticProviderResourceType[];
  semanticTypes: SemanticResourceType[];
  preselectedPrtId?: string;
}

@Component({
  selector: 'nimbus-type-mapping-dialog',
  standalone: true,
  imports: [CommonModule, FormsModule, SearchableSelectComponent],
  template: `
    <div class="dialog">
      <h2>{{ isEdit ? 'Edit Type Mapping' : 'New Type Mapping' }}</h2>
      <div class="form-group">
        <label>Provider Resource Type</label>
        <nimbus-searchable-select
          [(ngModel)]="providerResourceTypeId"
          [options]="prtOptions"
          placeholder="Select provider resource type..."
          [disabled]="isEdit"
        />
      </div>
      <div class="form-group">
        <label>Semantic Type</label>
        <nimbus-searchable-select
          [(ngModel)]="semanticTypeId"
          [options]="semanticTypeOptions"
          placeholder="Select semantic type..."
          [disabled]="isEdit"
        />
      </div>
      <div class="form-group">
        <label>Parameter Mapping (JSON)</label>
        <textarea [(ngModel)]="parameterMappingJson" rows="4" class="mono" placeholder='{"vcpus": "cores", "ram_mb": "memory"}'></textarea>
        @if (jsonError) {
          <span class="error">{{ jsonError }}</span>
        }
      </div>
      <div class="form-group">
        <label>Notes</label>
        <textarea [(ngModel)]="notes" rows="2" placeholder="Optional notes"></textarea>
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
export class TypeMappingDialogComponent implements OnInit {
  dialogData = inject<TypeMappingDialogData>(DIALOG_DATA);
  private dialogService = inject(DialogService);

  isEdit = false;
  providerResourceTypeId = '';
  semanticTypeId = '';
  parameterMappingJson = '';
  notes = '';
  jsonError = '';

  prtOptions: SelectOption[] = [];
  semanticTypeOptions: SelectOption[] = [];

  ngOnInit(): void {
    this.prtOptions = this.dialogData.providerResourceTypes.map(prt => ({
      value: prt.id,
      label: `${prt.providerName} / ${prt.displayName} (${prt.apiType})`,
    }));
    this.semanticTypeOptions = this.dialogData.semanticTypes.map(t => ({
      value: t.id,
      label: `${t.category.displayName} / ${t.displayName}`,
    }));

    const m = this.dialogData.mapping;
    if (m) {
      this.isEdit = true;
      this.providerResourceTypeId = m.providerResourceTypeId;
      this.semanticTypeId = m.semanticTypeId;
      this.parameterMappingJson = m.parameterMapping ? JSON.stringify(m.parameterMapping, null, 2) : '';
      this.notes = m.notes || '';
    } else if (this.dialogData.preselectedPrtId) {
      this.providerResourceTypeId = this.dialogData.preselectedPrtId;
    }
  }

  isValid(): boolean {
    if (this.parameterMappingJson.trim()) {
      try {
        JSON.parse(this.parameterMappingJson);
        this.jsonError = '';
      } catch {
        this.jsonError = 'Invalid JSON';
        return false;
      }
    }
    if (this.isEdit) return true;
    return this.providerResourceTypeId.length > 0 && this.semanticTypeId.length > 0;
  }

  onSave(): void {
    const parameterMapping = this.parameterMappingJson.trim()
      ? JSON.parse(this.parameterMappingJson)
      : null;

    if (this.isEdit) {
      this.dialogService.close({
        parameterMapping,
        notes: this.notes || null,
      });
    } else {
      this.dialogService.close({
        providerResourceTypeId: this.providerResourceTypeId,
        semanticTypeId: this.semanticTypeId,
        parameterMapping,
        notes: this.notes || null,
      });
    }
  }

  onCancel(): void {
    this.dialogService.close(undefined);
  }
}
