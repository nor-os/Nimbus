/**
 * Overview: Connection dialog — intercepts connection creation to pick a relationship kind.
 * Architecture: Dialog component for architecture editor connections (Section 3.2)
 * Dependencies: @angular/core, @angular/common
 * Concepts: Relationship kind selection, filtered by allowed kinds on source+target types, auto-select
 */
import { Component, EventEmitter, Input, Output, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { SemanticRelationshipKind } from '@shared/models/semantic.model';

@Component({
  selector: 'nimbus-connection-dialog',
  standalone: true,
  imports: [CommonModule],
  template: `
    @if (visible()) {
      <div class="dialog-overlay" (click)="cancel()">
        <div class="dialog-card" (click)="$event.stopPropagation()">
          <div class="dialog-header">
            <h3>Select Relationship</h3>
            <div class="dialog-subtitle">{{ sourceLabel }} &rarr; {{ targetLabel }}</div>
          </div>
          <div class="dialog-body">
            @if (availableKinds.length === 0) {
              <div class="no-kinds">No compatible relationship kinds available.</div>
            }
            @for (kind of availableKinds; track kind.id) {
              <button class="kind-option" (click)="selectKind(kind)">
                <span class="kind-name">{{ kind.displayName }}</span>
                <span class="kind-desc">{{ kind.description || kind.inverseName }}</span>
              </button>
            }
          </div>
          <div class="dialog-footer">
            <button class="btn-cancel" (click)="cancel()">Cancel</button>
          </div>
        </div>
      </div>
    }
  `,
  styles: [`
    .dialog-overlay {
      position: fixed;
      inset: 0;
      background: rgba(0,0,0,0.3);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 1000;
    }
    .dialog-card {
      background: #fff;
      border-radius: 12px;
      box-shadow: 0 8px 32px rgba(0,0,0,0.12);
      min-width: 340px;
      max-width: 420px;
      overflow: hidden;
    }
    .dialog-header {
      padding: 16px 20px 12px;
      border-bottom: 1px solid #e2e8f0;
    }
    .dialog-header h3 {
      margin: 0;
      font-size: 0.9375rem;
      font-weight: 600;
      color: #1e293b;
    }
    .dialog-subtitle {
      margin-top: 4px;
      font-size: 0.75rem;
      color: #64748b;
    }
    .dialog-body {
      padding: 8px;
      max-height: 300px;
      overflow-y: auto;
    }
    .kind-option {
      display: flex;
      flex-direction: column;
      width: 100%;
      padding: 10px 12px;
      border: none;
      background: none;
      border-radius: 8px;
      cursor: pointer;
      text-align: left;
      transition: background 0.15s;
      font-family: inherit;
    }
    .kind-option:hover { background: #f0f4ff; }
    .kind-name { font-size: 0.8125rem; font-weight: 600; color: #1e293b; }
    .kind-desc { font-size: 0.6875rem; color: #64748b; margin-top: 2px; }
    .no-kinds {
      padding: 24px;
      text-align: center;
      font-size: 0.8125rem;
      color: #94a3b8;
    }
    .dialog-footer {
      padding: 12px 20px;
      border-top: 1px solid #e2e8f0;
      display: flex;
      justify-content: flex-end;
    }
    .btn-cancel {
      padding: 6px 14px;
      border: 1px solid #e2e8f0;
      background: #fff;
      border-radius: 6px;
      font-size: 0.8125rem;
      color: #64748b;
      cursor: pointer;
      font-family: inherit;
    }
    .btn-cancel:hover { background: #f8fafc; }
  `],
})
export class ConnectionDialogComponent {
  @Input() availableKinds: SemanticRelationshipKind[] = [];
  @Input() sourceLabel = '';
  @Input() targetLabel = '';

  @Output() kindSelected = new EventEmitter<SemanticRelationshipKind>();
  @Output() cancelled = new EventEmitter<void>();

  visible = signal(false);

  open(): void {
    this.visible.set(true);
  }

  close(): void {
    this.visible.set(false);
  }

  selectKind(kind: SemanticRelationshipKind): void {
    this.kindSelected.emit(kind);
    this.close();
  }

  cancel(): void {
    this.cancelled.emit();
    this.close();
  }
}
