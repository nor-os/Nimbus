/**
 * Overview: Compartment overlay — resizable colored container rendered as HTML overlay on the canvas.
 * Architecture: Visual grouping layer for architecture editor (Section 3.2)
 * Dependencies: @angular/core, @angular/common
 * Concepts: Compartments as visual containers, drag-to-resize, nested compartments, light theme
 */
import {
  Component,
  EventEmitter,
  Input,
  Output,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { TopologyCompartment } from '@shared/models/architecture.model';

@Component({
  selector: 'nimbus-compartment-overlay',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div
      class="compartment-overlay"
      [class.selected]="selected"
      [style.left.px]="compartment.position.x"
      [style.top.px]="compartment.position.y"
      [style.width.px]="compartment.size.width"
      [style.height.px]="compartment.size.height"
      (mousedown)="onSelect($event)"
    >
      <div class="compartment-header">
        <span class="compartment-label">{{ compartment.label }}</span>
        @if (!readOnly) {
          <button class="compartment-remove" (click)="remove.emit(compartment.id); $event.stopPropagation()">
            &times;
          </button>
        }
      </div>
      @if (!readOnly) {
        <div
          class="resize-handle"
          (mousedown)="onResizeStart($event)"
        ></div>
      }
    </div>
  `,
  styles: [`
    .compartment-overlay {
      position: absolute;
      border: 2px dashed #93c5fd;
      border-radius: 12px;
      background: rgba(219, 234, 254, 0.15);
      pointer-events: none;
      z-index: 1;
      transition: border-color 0.15s, box-shadow 0.15s;
    }
    .compartment-overlay.selected {
      border-color: #3b82f6;
      box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2);
    }
    .compartment-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 6px 10px;
      background: rgba(219, 234, 254, 0.6);
      border-radius: 10px 10px 0 0;
      cursor: move;
      pointer-events: auto;
    }
    .compartment-label {
      font-size: 0.75rem;
      font-weight: 600;
      color: #1e40af;
      user-select: none;
    }
    .compartment-remove {
      width: 18px;
      height: 18px;
      border: none;
      background: none;
      color: #93c5fd;
      font-size: 0.875rem;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      border-radius: 4px;
      padding: 0;
      line-height: 1;
    }
    .compartment-remove:hover { color: #dc2626; background: rgba(220, 38, 38, 0.1); }
    .resize-handle {
      position: absolute;
      bottom: 0;
      right: 0;
      width: 16px;
      height: 16px;
      cursor: nwse-resize;
      border-right: 3px solid #93c5fd;
      border-bottom: 3px solid #93c5fd;
      border-radius: 0 0 10px 0;
      pointer-events: auto;
    }
  `],
})
export class CompartmentOverlayComponent {
  @Input() compartment!: TopologyCompartment;
  @Input() selected = false;
  @Input() readOnly = false;

  @Output() select = new EventEmitter<string>();
  @Output() remove = new EventEmitter<string>();
  @Output() resize = new EventEmitter<{ id: string; width: number; height: number }>();
  @Output() move = new EventEmitter<{ id: string; x: number; y: number }>();

  private resizing = false;
  private startX = 0;
  private startY = 0;
  private startWidth = 0;
  private startHeight = 0;

  onSelect(event: MouseEvent): void {
    this.select.emit(this.compartment.id);
    event.stopPropagation();

    if (this.readOnly) return;

    const startX = event.clientX;
    const startY = event.clientY;
    const origX = this.compartment.position.x;
    const origY = this.compartment.position.y;
    let moved = false;

    const onMouseMove = (e: MouseEvent) => {
      const dx = e.clientX - startX;
      const dy = e.clientY - startY;
      if (!moved && Math.abs(dx) < 3 && Math.abs(dy) < 3) return;
      moved = true;
      this.move.emit({ id: this.compartment.id, x: origX + dx, y: origY + dy });
    };

    const onMouseUp = () => {
      document.removeEventListener('mousemove', onMouseMove);
      document.removeEventListener('mouseup', onMouseUp);
    };

    document.addEventListener('mousemove', onMouseMove);
    document.addEventListener('mouseup', onMouseUp);
  }

  onResizeStart(event: MouseEvent): void {
    this.resizing = true;
    this.startX = event.clientX;
    this.startY = event.clientY;
    this.startWidth = this.compartment.size.width;
    this.startHeight = this.compartment.size.height;
    event.stopPropagation();
    event.preventDefault();

    const onMouseMove = (e: MouseEvent) => {
      if (!this.resizing) return;
      const newWidth = Math.max(200, this.startWidth + (e.clientX - this.startX));
      const newHeight = Math.max(150, this.startHeight + (e.clientY - this.startY));
      this.resize.emit({ id: this.compartment.id, width: newWidth, height: newHeight });
    };

    const onMouseUp = () => {
      this.resizing = false;
      document.removeEventListener('mousemove', onMouseMove);
      document.removeEventListener('mouseup', onMouseUp);
    };

    document.addEventListener('mousemove', onMouseMove);
    document.addEventListener('mouseup', onMouseUp);
  }
}
