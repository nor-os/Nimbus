/**
 * Overview: Custom port socket rendering for workflow nodes.
 * Architecture: Visual socket component (Section 3.2)
 * Dependencies: @angular/core
 * Concepts: Port sockets, connection endpoints
 */
import { Component, ChangeDetectionStrategy } from '@angular/core';

@Component({
  selector: 'nimbus-custom-socket',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `<div class="socket"></div>`,
  styles: [`
    .socket {
      width: 12px; height: 12px; border-radius: 50%;
      background: #475569; border: 2px solid #64748b;
      cursor: crosshair; transition: background 0.15s, transform 0.15s;
    }
    .socket:hover { background: #3b82f6; border-color: #60a5fa; transform: scale(1.3); }
  `],
})
export class CustomSocketComponent {}
