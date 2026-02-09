/**
 * Overview: Dialog for creating/editing semantic categories.
 * Architecture: Feature dialog for semantic layer CRUD (Section 5)
 * Dependencies: @angular/core, @angular/forms, app/shared/services/dialog.service
 * Concepts: Category CRUD, is_system protection (name readonly for system records)
 */
import { Component, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { DIALOG_DATA, DialogService } from '@shared/services/dialog.service';
import { SemanticCategory } from '@shared/models/semantic.model';
import { IconPickerComponent } from '@shared/components/icon-picker/icon-picker.component';

@Component({
  selector: 'nimbus-category-dialog',
  standalone: true,
  imports: [CommonModule, FormsModule, IconPickerComponent],
  template: `
    <div class="dialog">
      <h2>{{ isEdit ? 'Edit Category' : 'New Category' }}</h2>
      <div class="form-group">
        <label>Name</label>
        <input type="text" [(ngModel)]="name" [disabled]="nameDisabled" placeholder="e.g. monitoring" />
      </div>
      <div class="form-group">
        <label>Display Name</label>
        <input type="text" [(ngModel)]="displayName" placeholder="e.g. Monitoring" />
      </div>
      <div class="form-group">
        <label>Description</label>
        <textarea [(ngModel)]="description" rows="3" placeholder="Optional description"></textarea>
      </div>
      <div class="form-row">
        <div class="form-group half">
          <label>Icon</label>
          <nimbus-icon-picker [(value)]="icon" />
        </div>
        <div class="form-group half">
          <label>Sort Order</label>
          <input type="number" [(ngModel)]="sortOrder" />
        </div>
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
    .dialog { padding: 1.5rem; min-width: 420px; }
    h2 { margin: 0 0 1.25rem; font-size: 1.125rem; font-weight: 600; color: #1e293b; }
    .form-group { margin-bottom: 1rem; }
    .form-group label { display: block; font-size: 0.75rem; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.375rem; }
    .form-row { display: flex; gap: 1rem; }
    .half { flex: 1; }
    input, textarea, select {
      width: 100%; box-sizing: border-box; padding: 0.5rem 0.75rem; border: 1px solid #e2e8f0;
      border-radius: 6px; font-size: 0.8125rem; font-family: inherit; color: #374151;
      background: #fff; outline: none;
    }
    input:focus, textarea:focus, select:focus { border-color: #3b82f6; }
    input:disabled { background: #f8fafc; color: #94a3b8; cursor: not-allowed; }
    .actions { display: flex; justify-content: flex-end; gap: 0.75rem; margin-top: 1.5rem; }
    .btn { font-family: inherit; font-size: 0.8125rem; font-weight: 500; border-radius: 6px; cursor: pointer; padding: 0.5rem 1.25rem; transition: background 0.15s; }
    .btn-cancel { background: #fff; color: #374151; border: 1px solid #e2e8f0; }
    .btn-cancel:hover { background: #f8fafc; }
    .btn-primary { background: #3b82f6; color: #fff; border: none; }
    .btn-primary:hover { background: #2563eb; }
    .btn-primary:disabled { background: #94a3b8; cursor: not-allowed; }
  `],
})
export class CategoryDialogComponent implements OnInit {
  data = inject<SemanticCategory | null>(DIALOG_DATA);
  private dialogService = inject(DialogService);

  isEdit = false;
  nameDisabled = false;
  name = '';
  displayName = '';
  description = '';
  icon = '';
  sortOrder = 0;

  ngOnInit(): void {
    if (this.data) {
      this.isEdit = true;
      this.nameDisabled = this.data.isSystem;
      this.name = this.data.name;
      this.displayName = this.data.displayName;
      this.description = this.data.description || '';
      this.icon = this.data.icon || '';
      this.sortOrder = this.data.sortOrder;
    }
  }

  isValid(): boolean {
    return this.name.trim().length > 0 && this.displayName.trim().length > 0;
  }

  onSave(): void {
    if (this.isEdit) {
      this.dialogService.close({
        displayName: this.displayName,
        description: this.description || null,
        icon: this.icon || null,
        sortOrder: this.sortOrder,
      });
    } else {
      this.dialogService.close({
        name: this.name,
        displayName: this.displayName,
        description: this.description || null,
        icon: this.icon || null,
        sortOrder: this.sortOrder,
      });
    }
  }

  onCancel(): void {
    this.dialogService.close(undefined);
  }
}
