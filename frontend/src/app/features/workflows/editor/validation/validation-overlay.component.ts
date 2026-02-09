/**
 * Overview: Validation overlay — red borders on invalid nodes and error list panel.
 * Architecture: Validation feedback component for workflow editor (Section 3.2)
 * Dependencies: @angular/core, @angular/common
 * Concepts: Validation errors, visual feedback, error list
 */
import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ValidationResult } from '@shared/models/workflow.model';

@Component({
  selector: 'nimbus-validation-overlay',
  standalone: true,
  imports: [CommonModule],
  template: `
    @if (validationResult && (!validationResult.valid || validationResult.warnings.length)) {
      <div class="validation-panel" [class.has-errors]="!validationResult.valid">
        <div class="validation-header">
          @if (!validationResult.valid) {
            <span class="error-icon">&#10060;</span>
            <span>{{ validationResult.errors.length }} error(s)</span>
          }
          @if (validationResult.warnings.length) {
            <span class="warning-icon">&#9888;</span>
            <span>{{ validationResult.warnings.length }} warning(s)</span>
          }
        </div>
        <div class="validation-items">
          @for (err of validationResult.errors; track $index) {
            <div class="validation-item error">
              <span class="item-icon">&#10060;</span>
              <span class="item-message">{{ err.message }}</span>
              @if (err.nodeId) {
                <span class="item-node">{{ err.nodeId }}</span>
              }
            </div>
          }
          @for (warn of validationResult.warnings; track $index) {
            <div class="validation-item warning">
              <span class="item-icon">&#9888;</span>
              <span class="item-message">{{ warn.message }}</span>
              @if (warn.nodeId) {
                <span class="item-node">{{ warn.nodeId }}</span>
              }
            </div>
          }
        </div>
      </div>
    }
  `,
  styles: [`
    .validation-panel {
      position: absolute; bottom: 12px; left: 12px; right: 12px;
      max-height: 200px; overflow-y: auto;
      background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.1);
      z-index: 10;
    }
    .validation-panel.has-errors { border-color: #fecaca; }
    .validation-header {
      display: flex; align-items: center; gap: 8px;
      padding: 8px 12px; border-bottom: 1px solid #f1f5f9;
      font-size: 0.8125rem; color: #1e293b;
    }
    .error-icon { color: #dc2626; }
    .warning-icon { color: #ca8a04; }
    .validation-items { padding: 4px 0; }
    .validation-item {
      display: flex; align-items: center; gap: 6px;
      padding: 4px 12px; font-size: 0.75rem;
    }
    .validation-item.error .item-message { color: #dc2626; }
    .validation-item.warning .item-message { color: #ca8a04; }
    .item-icon { font-size: 0.625rem; }
    .item-node {
      margin-left: auto; font-family: 'JetBrains Mono', monospace;
      font-size: 0.625rem; color: #94a3b8;
    }
  `],
})
export class ValidationOverlayComponent {
  @Input() validationResult: ValidationResult | null = null;
}
