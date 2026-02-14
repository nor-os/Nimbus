/**
 * Overview: Dialog for creating/editing OS images.
 * Architecture: Feature dialog for OS image catalog CRUD (Section 5)
 * Dependencies: @angular/core, @angular/forms, app/shared/services/dialog.service
 * Concepts: OS image create/edit, os_family selection, architecture selection
 */
import { Component, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { DIALOG_DATA, DialogService } from '@shared/services/dialog.service';
import { OsImage } from '@shared/models/os-image.model';

@Component({
  selector: 'nimbus-image-dialog',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="dialog">
      <h2>{{ isEdit ? 'Edit OS Image' : 'New OS Image' }}</h2>
      <div class="form-row">
        <div class="form-group half">
          <label>Name</label>
          <input type="text" [(ngModel)]="name" [disabled]="isEdit && isSystem" placeholder="e.g. ubuntu-2204" />
        </div>
        <div class="form-group half">
          <label>Display Name</label>
          <input type="text" [(ngModel)]="displayName" placeholder="e.g. Ubuntu 22.04 LTS" />
        </div>
      </div>
      <div class="form-row">
        <div class="form-group third">
          <label>OS Family</label>
          <select [(ngModel)]="osFamily">
            <option value="linux">Linux</option>
            <option value="windows">Windows</option>
            <option value="macos">macOS</option>
            <option value="bsd">BSD</option>
            <option value="other">Other</option>
          </select>
        </div>
        <div class="form-group third">
          <label>Version</label>
          <input type="text" [(ngModel)]="version" placeholder="e.g. 22.04 LTS" />
        </div>
        <div class="form-group third">
          <label>Architecture</label>
          <select [(ngModel)]="architecture">
            <option value="x86_64">x86_64</option>
            <option value="arm64">arm64</option>
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
          <input type="text" [(ngModel)]="icon" placeholder="e.g. ubuntu" />
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
    .dialog { padding: 1.5rem; min-width: 520px; }
    h2 { margin: 0 0 1.25rem; font-size: 1.125rem; font-weight: 600; color: #1e293b; }
    .form-group { margin-bottom: 1rem; }
    .form-group label { display: block; font-size: 0.75rem; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.375rem; }
    .form-row { display: flex; gap: 1rem; }
    .half { flex: 1; }
    .third { flex: 1; }
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
export class ImageDialogComponent implements OnInit {
  dialogData = inject<OsImage | null>(DIALOG_DATA);
  private dialogService = inject(DialogService);

  isEdit = false;
  isSystem = false;
  name = '';
  displayName = '';
  osFamily = 'linux';
  version = '';
  architecture = 'x86_64';
  description = '';
  icon = '';
  sortOrder = 0;

  ngOnInit(): void {
    const image = this.dialogData;
    if (image) {
      this.isEdit = true;
      this.isSystem = image.isSystem;
      this.name = image.name;
      this.displayName = image.displayName;
      this.osFamily = image.osFamily;
      this.version = image.version;
      this.architecture = image.architecture;
      this.description = image.description || '';
      this.icon = image.icon || '';
      this.sortOrder = image.sortOrder;
    }
  }

  isValid(): boolean {
    if (this.isEdit) return this.displayName.trim().length > 0;
    return this.name.trim().length > 0 && this.displayName.trim().length > 0 && this.version.trim().length > 0;
  }

  onSave(): void {
    if (this.isEdit) {
      this.dialogService.close({
        displayName: this.displayName,
        osFamily: this.osFamily,
        version: this.version,
        architecture: this.architecture,
        description: this.description || null,
        icon: this.icon || null,
        sortOrder: this.sortOrder,
      });
    } else {
      this.dialogService.close({
        name: this.name,
        displayName: this.displayName,
        osFamily: this.osFamily,
        version: this.version,
        architecture: this.architecture,
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
