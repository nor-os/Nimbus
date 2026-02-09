/**
 * Overview: Test variables — JSON editor for workflow test input.
 * Architecture: Test input form component (Section 3.2)
 * Dependencies: @angular/core, @angular/common, @angular/forms
 * Concepts: Test input, JSON editing, variable configuration
 */
import { Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'nimbus-test-variables',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="test-variables">
      <label>Workflow Input (JSON)</label>
      <textarea
        class="json-editor"
        [ngModel]="jsonText"
        (ngModelChange)="onTextChange($event)"
        rows="8"
        placeholder='{ "key": "value" }'
      ></textarea>
      @if (parseError) {
        <div class="parse-error">{{ parseError }}</div>
      }
    </div>
  `,
  styles: [`
    .test-variables { display: flex; flex-direction: column; gap: 4px; }
    label { font-size: 0.75rem; color: #64748b; }
    .json-editor {
      width: 100%; padding: 8px; background: #f8fafc; border: 1px solid #e2e8f0;
      border-radius: 6px; color: #1e293b; font-family: 'JetBrains Mono', monospace;
      font-size: 0.75rem; outline: none; resize: vertical;
    }
    .json-editor:focus { border-color: #3b82f6; }
    .parse-error { font-size: 0.625rem; color: #dc2626; }
  `],
})
export class TestVariablesComponent {
  @Input() set variables(val: Record<string, unknown>) {
    this.jsonText = JSON.stringify(val, null, 2);
  }
  @Output() variablesChange = new EventEmitter<Record<string, unknown>>();

  jsonText = '{}';
  parseError: string | null = null;

  onTextChange(text: string): void {
    this.jsonText = text;
    try {
      const parsed = JSON.parse(text);
      this.parseError = null;
      this.variablesChange.emit(parsed);
    } catch (e: any) {
      this.parseError = e.message;
    }
  }
}
