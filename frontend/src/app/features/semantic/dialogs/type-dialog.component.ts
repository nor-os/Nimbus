/**
 * Overview: Dialog for creating/editing semantic resource types.
 * Architecture: Feature dialog for semantic layer CRUD (Section 5)
 * Dependencies: @angular/core, @angular/forms, app/shared/services/dialog.service
 * Concepts: Type CRUD, category selection, parent type, property schema editor, is_system protection
 */
import { Component, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { DIALOG_DATA, DialogService } from '@shared/services/dialog.service';
import {
  SemanticCategory,
  SemanticRelationshipKind,
  SemanticResourceType,
} from '@shared/models/semantic.model';
import { IconPickerComponent } from '@shared/components/icon-picker/icon-picker.component';
import { PropertySchemaEditorComponent, PropertyDefRow } from '@shared/components/property-schema-editor/property-schema-editor.component';

export interface TypeDialogData {
  type: SemanticResourceType | null;
  categories: SemanticCategory[];
  types: SemanticResourceType[];
  relationshipKinds: SemanticRelationshipKind[];
}

@Component({
  selector: 'nimbus-type-dialog',
  standalone: true,
  imports: [CommonModule, FormsModule, IconPickerComponent, PropertySchemaEditorComponent],
  template: `
    <div class="dialog">
      <h2>{{ isEdit ? 'Edit Type' : 'New Type' }}</h2>
      <div class="form-row">
        <div class="form-group half">
          <label>Name</label>
          <input type="text" [(ngModel)]="name" [disabled]="nameDisabled" placeholder="e.g. LoadBalancer" />
        </div>
        <div class="form-group half">
          <label>Display Name</label>
          <input type="text" [(ngModel)]="displayName" placeholder="e.g. Load Balancer" />
        </div>
      </div>
      <div class="form-row">
        <div class="form-group half">
          <label>Category</label>
          <select [(ngModel)]="categoryId">
            @for (cat of dialogData.categories; track cat.id) {
              <option [value]="cat.id">{{ cat.displayName }}</option>
            }
          </select>
        </div>
        <div class="form-group half">
          <label>Parent Type</label>
          <select [(ngModel)]="parentTypeId">
            <option value="">None</option>
            @for (t of dialogData.types; track t.id) {
              <option [value]="t.id">{{ t.displayName }}</option>
            }
          </select>
        </div>
      </div>
      <div class="form-group">
        <label>Description</label>
        <textarea [(ngModel)]="description" rows="2" placeholder="Optional description"></textarea>
      </div>
      <div class="form-row">
        <div class="form-group half">
          <label>Icon</label>
          <nimbus-icon-picker [(value)]="icon" />
        </div>
        <div class="form-group quarter">
          <label>Sort Order</label>
          <input type="number" [(ngModel)]="sortOrder" />
        </div>
        <div class="form-group quarter">
          <label>Abstract</label>
          <label class="toggle-row">
            <input type="checkbox" [(ngModel)]="isAbstract" />
            <span>{{ isAbstract ? 'Yes' : 'No' }}</span>
          </label>
        </div>
      </div>
      <div class="form-group">
        <label>Allowed Relationships</label>
        <div class="checkbox-grid">
          @for (kind of dialogData.relationshipKinds; track kind.id) {
            <label class="checkbox-item">
              <input type="checkbox" [checked]="isRelChecked(kind.name)" (change)="toggleRel(kind.name)" />
              {{ kind.displayName }}
            </label>
          }
        </div>
      </div>
      <div class="form-group">
        <label>Properties Schema</label>
        <nimbus-property-schema-editor [value]="propertiesSchema" (valueChange)="propertiesSchema = $event" />
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
    .dialog { padding: 1.5rem; min-width: 620px; max-height: 80vh; overflow-y: auto; }
    h2 { margin: 0 0 1.25rem; font-size: 1.125rem; font-weight: 600; color: #1e293b; }
    .form-group { margin-bottom: 1rem; }
    .form-group label { display: block; font-size: 0.75rem; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.375rem; }
    .form-row { display: flex; gap: 1rem; }
    .half { flex: 1; }
    .quarter { flex: 0.5; }
    input, textarea, select {
      width: 100%; box-sizing: border-box; padding: 0.5rem 0.75rem; border: 1px solid #e2e8f0;
      border-radius: 6px; font-size: 0.8125rem; font-family: inherit; color: #374151;
      background: #fff; outline: none;
    }
    input:focus, textarea:focus, select:focus { border-color: #3b82f6; }
    input:disabled { background: #f8fafc; color: #94a3b8; cursor: not-allowed; }
    .toggle-row { display: flex; align-items: center; gap: 0.5rem; font-size: 0.8125rem; color: #374151; cursor: pointer; text-transform: none; font-weight: 400; letter-spacing: 0; }
    .toggle-row input { width: auto; }
    .checkbox-grid { display: flex; flex-wrap: wrap; gap: 0.5rem 1.25rem; }
    .checkbox-item { display: flex; align-items: center; gap: 0.375rem; font-size: 0.8125rem; color: #374151; cursor: pointer; text-transform: none; font-weight: 400; letter-spacing: 0; }
    .checkbox-item input { width: auto; }
    .actions { display: flex; justify-content: flex-end; gap: 0.75rem; margin-top: 1.5rem; }
    .btn { font-family: inherit; font-size: 0.8125rem; font-weight: 500; border-radius: 6px; cursor: pointer; padding: 0.5rem 1.25rem; transition: background 0.15s; }
    .btn-cancel { background: #fff; color: #374151; border: 1px solid #e2e8f0; }
    .btn-cancel:hover { background: #f8fafc; }
    .btn-primary { background: #3b82f6; color: #fff; border: none; }
    .btn-primary:hover { background: #2563eb; }
    .btn-primary:disabled { background: #94a3b8; cursor: not-allowed; }
  `],
})
export class TypeDialogComponent implements OnInit {
  dialogData = inject<TypeDialogData>(DIALOG_DATA);
  private dialogService = inject(DialogService);

  isEdit = false;
  nameDisabled = false;
  name = '';
  displayName = '';
  categoryId = '';
  parentTypeId = '';
  description = '';
  icon = '';
  sortOrder = 0;
  isAbstract = false;
  allowedRels: string[] = [];
  propertiesSchema: PropertyDefRow[] = [];

  ngOnInit(): void {
    const t = this.dialogData.type;
    if (t) {
      this.isEdit = true;
      this.nameDisabled = t.isSystem;
      this.name = t.name;
      this.displayName = t.displayName;
      this.categoryId = t.category.id;
      this.parentTypeId = t.parentTypeName ? this.findTypeIdByName(t.parentTypeName) : '';
      this.description = t.description || '';
      this.icon = t.icon || '';
      this.sortOrder = t.sortOrder;
      this.isAbstract = t.isAbstract;
      this.allowedRels = [...(t.allowedRelationshipKinds || [])];
      this.propertiesSchema = t.propertiesSchema ? [...t.propertiesSchema] as any : [];
    } else if (this.dialogData.categories.length > 0) {
      this.categoryId = this.dialogData.categories[0].id;
    }
  }

  isRelChecked(name: string): boolean {
    return this.allowedRels.includes(name);
  }

  toggleRel(name: string): void {
    const idx = this.allowedRels.indexOf(name);
    if (idx >= 0) {
      this.allowedRels.splice(idx, 1);
    } else {
      this.allowedRels.push(name);
    }
  }

  isValid(): boolean {
    return !!(this.name.trim() && this.displayName.trim() && this.categoryId);
  }

  onSave(): void {
    const schema = this.propertiesSchema;
    if (this.isEdit) {
      this.dialogService.close({
        displayName: this.displayName,
        categoryId: this.categoryId,
        description: this.description || null,
        icon: this.icon || null,
        isAbstract: this.isAbstract,
        parentTypeId: this.parentTypeId || null,
        propertiesSchema: schema,
        allowedRelationshipKinds: this.allowedRels,
        sortOrder: this.sortOrder,
      });
    } else {
      this.dialogService.close({
        name: this.name,
        displayName: this.displayName,
        categoryId: this.categoryId,
        description: this.description || null,
        icon: this.icon || null,
        isAbstract: this.isAbstract,
        parentTypeId: this.parentTypeId || null,
        propertiesSchema: schema,
        allowedRelationshipKinds: this.allowedRels,
        sortOrder: this.sortOrder,
      });
    }
  }

  onCancel(): void {
    this.dialogService.close(undefined);
  }

  private findTypeIdByName(name: string): string {
    return this.dialogData.types.find((t) => t.name === name)?.id || '';
  }
}
