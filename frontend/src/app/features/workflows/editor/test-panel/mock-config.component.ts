/**
 * Overview: Mock configuration — per-node mock settings for test runs.
 * Architecture: Test mock configuration component (Section 3.2)
 * Dependencies: @angular/core, @angular/common, @angular/forms
 * Concepts: Mock configuration, test overrides, skip/fixed output/delay/failure simulation
 */
import { Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'nimbus-mock-config',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="mock-config">
      <label>Mock Configurations (JSON)</label>
      <p class="hint">
        Per-node overrides: skip, fixed output, delay, or simulate failure.
      </p>
      <textarea
        class="json-editor"
        [ngModel]="jsonText"
        (ngModelChange)="onTextChange($event)"
        rows="10"
        [placeholder]="placeholder"
      ></textarea>
      @if (parseError) {
        <div class="parse-error">{{ parseError }}</div>
      }
    </div>
  `,
  styles: [`
    .mock-config { display: flex; flex-direction: column; gap: 4px; }
    label { font-size: 0.75rem; color: #64748b; }
    .hint { font-size: 0.625rem; color: #94a3b8; margin: 0; }
    .json-editor {
      width: 100%; padding: 8px; background: #f8fafc; border: 1px solid #e2e8f0;
      border-radius: 6px; color: #1e293b; font-family: 'JetBrains Mono', monospace;
      font-size: 0.75rem; outline: none; resize: vertical;
    }
    .json-editor:focus { border-color: #3b82f6; }
    .parse-error { font-size: 0.625rem; color: #dc2626; }
  `],
})
export class MockConfigComponent {
  @Input() set configs(val: Record<string, unknown>) {
    this.jsonText = JSON.stringify(val, null, 2);
  }
  @Output() configsChange = new EventEmitter<Record<string, unknown>>();

  jsonText = '{}';
  parseError: string | null = null;

  placeholder = `{
  "node_id_1": { "skip": true },
  "node_id_2": { "fixedOutput": { "result": "mock" } },
  "node_id_3": { "delay": 2, "simulateFailure": true }
}`;

  onTextChange(text: string): void {
    this.jsonText = text;
    try {
      const parsed = JSON.parse(text);
      this.parseError = null;
      this.configsChange.emit(parsed);
    } catch (e: any) {
      this.parseError = e.message;
    }
  }
}
