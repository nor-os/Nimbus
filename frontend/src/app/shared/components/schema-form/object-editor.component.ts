/**
 * Overview: Renders nested JSON Schema objects as collapsible cards, delegating all child field rendering to SchemaFormRendererComponent.
 * Architecture: Shared reusable form component (Section 3)
 * Dependencies: @angular/core, @angular/common, @angular/forms, SchemaFormRendererComponent
 * Concepts: JSON Schema object rendering, collapsible sections, recursive property editing via forwardRef
 */
import { Component, ChangeDetectionStrategy, Input, Output, EventEmitter, OnInit, signal, forwardRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { SchemaFormRendererComponent } from './schema-form-renderer.component';

@Component({
  selector: 'nimbus-object-editor',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    forwardRef(() => SchemaFormRendererComponent),
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="object-editor" [class.has-values]="hasValues()">
      <div class="object-header" (click)="toggleExpanded()">
        <span class="toggle-icon">{{ expanded() ? '\u25BC' : '\u25B6' }}</span>
        <span class="object-title">{{ getTitle() }}</span>
        @if (getDescription()) {
          <span class="object-desc">{{ getDescription() }}</span>
        }
        @if (hasEnabledProp()) {
          <span class="enabled-badge" [class.is-enabled]="isEnabled()">
            {{ isEnabled() ? 'ON' : 'OFF' }}
          </span>
        }
      </div>
      @if (expanded()) {
        <div class="object-body">
          <nimbus-schema-form-renderer
            [schema]="schema"
            [values]="value"
            (valuesChange)="onValueChange($event)"
          ></nimbus-schema-form-renderer>
        </div>
      }
    </div>
  `,
  styles: [`
    .object-editor {
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      background: #fff;
      overflow: hidden;
    }

    .object-editor.has-values {
      border-color: #93c5fd;
    }

    .object-header {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 10px 14px;
      background: #f8fafc;
      border-bottom: 1px solid #e2e8f0;
      cursor: pointer;
      user-select: none;
      transition: background 0.15s;
    }

    .object-header:hover {
      background: #f1f5f9;
    }

    .toggle-icon {
      font-size: 10px;
      color: #64748b;
      width: 14px;
      text-align: center;
      flex-shrink: 0;
    }

    .object-title {
      font-size: 13px;
      font-weight: 600;
      color: #1e293b;
    }

    .object-desc {
      font-size: 11px;
      color: #94a3b8;
      margin-left: auto;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      max-width: 300px;
    }

    .enabled-badge {
      margin-left: auto;
      font-size: 10px;
      font-weight: 700;
      padding: 2px 8px;
      border-radius: 10px;
      background: #f1f5f9;
      color: #94a3b8;
      flex-shrink: 0;
    }

    .enabled-badge.is-enabled {
      background: #d1fae5;
      color: #065f46;
    }

    .object-body {
      padding: 12px 14px;
    }
  `]
})
export class ObjectEditorComponent implements OnInit {
  @Input() schema: Record<string, unknown> = {};
  @Input() value: Record<string, unknown> = {};
  @Input() startExpanded = false;
  @Output() valueChange = new EventEmitter<Record<string, unknown>>();

  expanded = signal(false);

  ngOnInit(): void {
    this.expanded.set(this.startExpanded);
  }

  toggleExpanded(): void {
    this.expanded.update(v => !v);
  }

  getTitle(): string {
    return (this.schema?.['title'] as string) || 'Object';
  }

  getDescription(): string {
    return (this.schema?.['description'] as string) || '';
  }

  hasValues(): boolean {
    return this.value !== null && this.value !== undefined && Object.keys(this.value).length > 0;
  }

  hasEnabledProp(): boolean {
    const props = this.schema?.['properties'] as Record<string, unknown> | undefined;
    if (!props) return false;
    const enabledProp = props['enabled'] as Record<string, unknown> | undefined;
    return enabledProp?.['type'] === 'boolean';
  }

  isEnabled(): boolean {
    return this.value?.['enabled'] === true;
  }

  onValueChange(updated: Record<string, unknown>): void {
    this.value = updated;
    this.valueChange.emit(updated);
  }
}
