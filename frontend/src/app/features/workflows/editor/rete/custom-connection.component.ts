/**
 * Overview: Custom connection line rendering for the workflow canvas.
 * Architecture: Visual connection component (Section 3.2)
 * Dependencies: @angular/core
 * Concepts: Connection rendering, SVG paths
 */
import { Component, ChangeDetectionStrategy } from '@angular/core';

@Component({
  selector: 'nimbus-custom-connection',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `<svg class="connection-svg"><path class="connection-path" /></svg>`,
  styles: [`
    :host { position: absolute; pointer-events: none; }
    .connection-svg { overflow: visible; }
    .connection-path {
      stroke: #475569; stroke-width: 2; fill: none;
      transition: stroke 0.15s;
    }
    .connection-path:hover { stroke: #3b82f6; }
  `],
})
export class CustomConnectionComponent {}
