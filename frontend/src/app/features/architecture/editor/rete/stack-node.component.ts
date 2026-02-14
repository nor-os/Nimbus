/**
 * Overview: Stack node — visual representation of a stack blueprint instance on the canvas.
 * Architecture: Stack instance rendering for architecture editor (Section 3.2)
 * Dependencies: @angular/core, @angular/common
 * Concepts: Stack instances reference blueprints, show slot count, parameter binding status, light theme
 */
import {
  Component,
  EventEmitter,
  Input,
  Output,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { TopologyStackInstance } from '@shared/models/architecture.model';

@Component({
  selector: 'nimbus-stack-node',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div
      class="stack-node"
      [class.selected]="selected"
      [style.left.px]="stack.position.x"
      [style.top.px]="stack.position.y"
      (mousedown)="onSelect($event)"
    >
      <div class="stack-header">
        <span class="stack-icon">&#9881;</span>
        <span class="stack-label">{{ stack.label }}</span>
      </div>
      <div class="stack-body">
        <div class="stack-info">
          <span class="info-badge blueprint">Blueprint</span>
          <span class="info-text">{{ blueprintName || 'Unlinked' }}</span>
        </div>
        <div class="stack-info">
          <span class="info-badge bindings">Bindings</span>
          <span class="info-text">{{ bindingCount }}</span>
        </div>
        @if (stack.dependsOn.length > 0) {
          <div class="stack-info">
            <span class="info-badge deps">Deps</span>
            <span class="info-text">{{ stack.dependsOn.length }}</span>
          </div>
        }
      </div>
      @if (!readOnly) {
        <button class="stack-remove" (click)="remove.emit(stack.id); $event.stopPropagation()">
          &times;
        </button>
      }
    </div>
  `,
  styles: [`
    .stack-node {
      position: absolute;
      min-width: 180px;
      background: #fff;
      border: 2px solid #a78bfa;
      border-radius: 10px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.06);
      pointer-events: auto;
      z-index: 2;
      cursor: grab;
      transition: border-color 0.15s, box-shadow 0.15s;
    }
    .stack-node.selected {
      border-color: #7c3aed;
      box-shadow: 0 0 0 2px rgba(124, 58, 237, 0.2), 0 2px 8px rgba(0,0,0,0.06);
    }
    .stack-header {
      display: flex;
      align-items: center;
      gap: 6px;
      padding: 8px 10px;
      background: rgba(237, 233, 254, 0.5);
      border-radius: 8px 8px 0 0;
      border-bottom: 1px solid #ede9fe;
    }
    .stack-icon { font-size: 0.875rem; }
    .stack-label {
      font-size: 0.8125rem;
      font-weight: 600;
      color: #5b21b6;
      user-select: none;
    }
    .stack-body { padding: 8px 10px; }
    .stack-info {
      display: flex;
      align-items: center;
      gap: 6px;
      margin-bottom: 4px;
    }
    .stack-info:last-child { margin-bottom: 0; }
    .info-badge {
      font-size: 0.625rem;
      font-weight: 600;
      padding: 1px 6px;
      border-radius: 4px;
      text-transform: uppercase;
      letter-spacing: 0.03em;
    }
    .info-badge.blueprint { background: #ede9fe; color: #7c3aed; }
    .info-badge.bindings { background: #dbeafe; color: #2563eb; }
    .info-badge.deps { background: #fef3c7; color: #92400e; }
    .info-text {
      font-size: 0.75rem;
      color: #64748b;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .stack-remove {
      position: absolute;
      top: 6px;
      right: 6px;
      width: 18px;
      height: 18px;
      border: none;
      background: none;
      color: #c4b5fd;
      font-size: 0.875rem;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      border-radius: 4px;
      padding: 0;
      line-height: 1;
    }
    .stack-remove:hover { color: #dc2626; background: rgba(220, 38, 38, 0.1); }
  `],
})
export class StackNodeComponent {
  @Input() stack!: TopologyStackInstance;
  @Input() blueprintName: string | null = null;
  @Input() selected = false;
  @Input() readOnly = false;

  @Output() select = new EventEmitter<string>();
  @Output() remove = new EventEmitter<string>();
  @Output() move = new EventEmitter<{ id: string; x: number; y: number }>();

  get bindingCount(): number {
    return Object.keys(this.stack.parameterOverrides || {}).length;
  }

  onSelect(event: MouseEvent): void {
    this.select.emit(this.stack.id);
    event.stopPropagation();

    if (this.readOnly) return;

    const startX = event.clientX;
    const startY = event.clientY;
    const origX = this.stack.position.x;
    const origY = this.stack.position.y;
    let moved = false;

    const onMouseMove = (e: MouseEvent) => {
      const dx = e.clientX - startX;
      const dy = e.clientY - startY;
      if (!moved && Math.abs(dx) < 3 && Math.abs(dy) < 3) return;
      moved = true;
      this.move.emit({ id: this.stack.id, x: origX + dx, y: origY + dy });
    };

    const onMouseUp = () => {
      document.removeEventListener('mousemove', onMouseMove);
      document.removeEventListener('mouseup', onMouseUp);
    };

    document.addEventListener('mousemove', onMouseMove);
    document.addEventListener('mouseup', onMouseUp);
  }
}
