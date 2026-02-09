/**
 * Overview: Dialog for creating/editing semantic relationship kinds.
 * Architecture: Feature dialog for semantic layer CRUD (Section 5)
 * Dependencies: @angular/core, @angular/forms, app/shared/services/dialog.service
 * Concepts: Relationship kind CRUD, is_system protection (name readonly for system records)
 */
import { Component, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { DIALOG_DATA, DialogService } from '@shared/services/dialog.service';
import { SemanticRelationshipKind } from '@shared/models/semantic.model';

@Component({
  selector: 'nimbus-relationship-kind-dialog',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="dialog">
      <h2>{{ isEdit ? 'Edit Relationship Kind' : 'New Relationship Kind' }}</h2>
      <div class="form-row">
        <div class="form-group half">
          <label>Name</label>
          <input type="text" [(ngModel)]="name" [disabled]="nameDisabled" placeholder="e.g. depends_on" />
        </div>
        <div class="form-group half">
          <label>Display Name</label>
          <input type="text" [(ngModel)]="displayName" placeholder="e.g. Depends On" />
        </div>
      </div>
      <div class="form-group">
        <label>Inverse Name</label>
        <input type="text" [(ngModel)]="inverseName" placeholder="e.g. depended_by" />
      </div>
      <div class="form-group">
        <label>Description</label>
        <textarea [(ngModel)]="description" rows="2" placeholder="Optional description"></textarea>
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
    input, textarea {
      width: 100%; box-sizing: border-box; padding: 0.5rem 0.75rem; border: 1px solid #e2e8f0;
      border-radius: 6px; font-size: 0.8125rem; font-family: inherit; color: #374151;
      background: #fff; outline: none;
    }
    input:focus, textarea:focus { border-color: #3b82f6; }
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
export class RelationshipKindDialogComponent implements OnInit {
  data = inject<SemanticRelationshipKind | null>(DIALOG_DATA);
  private dialogService = inject(DialogService);

  isEdit = false;
  nameDisabled = false;
  name = '';
  displayName = '';
  inverseName = '';
  description = '';

  ngOnInit(): void {
    if (this.data) {
      this.isEdit = true;
      this.nameDisabled = this.data.isSystem;
      this.name = this.data.name;
      this.displayName = this.data.displayName;
      this.inverseName = this.data.inverseName;
      this.description = this.data.description || '';
    }
  }

  isValid(): boolean {
    return this.name.trim().length > 0 &&
      this.displayName.trim().length > 0 &&
      this.inverseName.trim().length > 0;
  }

  onSave(): void {
    if (this.isEdit) {
      this.dialogService.close({
        displayName: this.displayName,
        description: this.description || null,
        inverseName: this.inverseName,
      });
    } else {
      this.dialogService.close({
        name: this.name,
        displayName: this.displayName,
        description: this.description || null,
        inverseName: this.inverseName,
      });
    }
  }

  onCancel(): void {
    this.dialogService.close(undefined);
  }
}
