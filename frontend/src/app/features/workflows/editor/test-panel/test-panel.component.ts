/**
 * Overview: Test panel — bottom drawer for test execution with input form, breakpoints, step-through.
 * Architecture: Test execution panel for workflow editor (Section 3.2)
 * Dependencies: @angular/core, @angular/common
 * Concepts: Test execution, breakpoints, step-through, mock configuration
 */
import { Component, EventEmitter, Input, Output, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { TestVariablesComponent } from './test-variables.component';
import { MockConfigComponent } from './mock-config.component';

@Component({
  selector: 'nimbus-test-panel',
  standalone: true,
  imports: [CommonModule, FormsModule, TestVariablesComponent, MockConfigComponent],
  template: `
    <div class="test-panel" [class.expanded]="expanded()">
      <div class="panel-toggle" (click)="expanded.update(v => !v)">
        <span>Test Runner</span>
        <span class="toggle-icon">{{ expanded() ? '&#9660;' : '&#9650;' }}</span>
      </div>
      @if (expanded()) {
        <div class="panel-body">
          <div class="panel-tabs">
            <button class="panel-tab" [class.active]="activeTab() === 'input'" (click)="activeTab.set('input')">Input</button>
            <button class="panel-tab" [class.active]="activeTab() === 'mocks'" (click)="activeTab.set('mocks')">Mocks</button>
          </div>

          <div class="panel-content">
            @if (activeTab() === 'input') {
              <nimbus-test-variables
                [variables]="testInput()"
                (variablesChange)="testInput.set($event)"
              />
            }
            @if (activeTab() === 'mocks') {
              <nimbus-mock-config
                [configs]="mockConfigs()"
                (configsChange)="mockConfigs.set($event)"
              />
            }
          </div>

          <div class="panel-actions">
            <button class="btn btn-primary" (click)="startTest.emit({ input: testInput(), mockConfigs: mockConfigs() })">
              Start Test
            </button>
          </div>
        </div>
      }
    </div>
  `,
  styles: [`
    .test-panel {
      position: absolute; bottom: 0; left: 0; right: 0;
      background: #fff; border-top: 1px solid #e2e8f0;
      box-shadow: 0 -2px 8px rgba(0,0,0,0.06); z-index: 20;
    }
    .panel-toggle {
      display: flex; justify-content: space-between; align-items: center;
      padding: 8px 16px; cursor: pointer; color: #64748b; font-size: 0.8125rem;
    }
    .panel-toggle:hover { color: #1e293b; }
    .panel-body { padding: 0 16px 16px; max-height: 300px; overflow-y: auto; }
    .panel-tabs { display: flex; gap: 4px; margin-bottom: 12px; }
    .panel-tab {
      padding: 4px 12px; border: none; background: none; color: #64748b;
      cursor: pointer; font-size: 0.8125rem; border-radius: 4px;
    }
    .panel-tab:hover { color: #1e293b; }
    .panel-tab.active { background: #eff6ff; color: #3b82f6; font-weight: 500; }
    .panel-content { margin-bottom: 12px; }
    .panel-actions { display: flex; gap: 8px; }
    .btn { padding: 6px 14px; border: none; border-radius: 6px; cursor: pointer; font-size: 0.8125rem; font-weight: 500; }
    .btn-primary { background: #3b82f6; color: #fff; }
    .btn-primary:hover { background: #2563eb; }
  `],
})
export class TestPanelComponent {
  @Output() startTest = new EventEmitter<{ input: Record<string, unknown>; mockConfigs: Record<string, unknown> }>();

  expanded = signal(false);
  activeTab = signal<'input' | 'mocks'>('input');
  testInput = signal<Record<string, unknown>>({});
  mockConfigs = signal<Record<string, unknown>>({});
}
