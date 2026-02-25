/**
 * Overview: Expression editor — Monaco-powered code input with variable hint chips.
 * Architecture: Expression input component for node properties (Section 3.2)
 * Dependencies: @angular/core, @angular/common, MonacoEditorComponent
 * Concepts: Expression editing, variable autocomplete, Monaco integration
 */
import { Component, EventEmitter, Input, Output, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MonacoEditorComponent } from '@shared/components/monaco-editor/monaco-editor.component';

@Component({
  selector: 'nimbus-expression-editor',
  standalone: true,
  imports: [CommonModule, MonacoEditorComponent],
  template: `
    <div class="expression-editor">
      <nimbus-monaco-editor
        [value]="value"
        [language]="language"
        [height]="height"
        (valueChange)="onValueChange($event)"
      ></nimbus-monaco-editor>
      <div class="expression-hints">
        <span class="hint-chip" (click)="insertText('$input.')">$input</span>
        <span class="hint-chip" (click)="insertText('$vars.')">$vars</span>
        <span class="hint-chip" (click)="insertText('$nodes.')">$nodes</span>
        <span class="hint-chip" (click)="insertText('$loop.')">$loop</span>
      </div>
      @if (error()) {
        <div class="expression-error">{{ error() }}</div>
      }
    </div>
  `,
  styles: [`
    .expression-editor { display: flex; flex-direction: column; gap: 4px; }
    .expression-hints { display: flex; gap: 4px; flex-wrap: wrap; }
    .hint-chip {
      padding: 2px 6px; background: #f1f5f9; border: 1px solid #e2e8f0; border-radius: 4px;
      font-size: 0.625rem; color: #64748b; cursor: pointer;
      font-family: 'JetBrains Mono', monospace;
    }
    .hint-chip:hover { background: #e2e8f0; color: #1e293b; }
    .expression-error {
      font-size: 0.625rem; color: #dc2626; padding: 2px 4px;
    }
  `],
})
export class ExpressionEditorComponent {
  @Input() value = '';
  @Input() placeholder = 'Enter expression...';
  @Input() rows = 2;
  @Input() language: 'typescript' | 'python' | 'json' | 'shell' = 'typescript';
  @Input() height = '120px';
  @Output() valueChange = new EventEmitter<string>();

  error = signal<string | null>(null);

  onValueChange(value: string): void {
    this.value = value;
    this.valueChange.emit(value);
    this.error.set(null);
  }

  insertText(text: string): void {
    this.value = (this.value || '') + text;
    this.valueChange.emit(this.value);
  }
}
