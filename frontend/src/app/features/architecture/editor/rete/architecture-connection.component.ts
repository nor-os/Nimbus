/**
 * Overview: Custom connection line rendering for architecture topology — light theme SVG paths.
 * Architecture: Visual connection component for architecture canvas (Section 3.2)
 * Dependencies: @angular/core
 * Concepts: Connection rendering, SVG paths, Rete.js connection contract
 */
import { Component, Input, ChangeDetectionStrategy } from '@angular/core';

@Component({
  selector: 'nimbus-architecture-connection',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <svg data-testid="connection">
      <path [attr.d]="path" />
    </svg>
  `,
  styles: [`
    :host {
      position: absolute;
      pointer-events: none;
      overflow: visible;
      width: 9999px;
      height: 9999px;
    }
    svg {
      overflow: visible;
    }
    path {
      stroke: #94a3b8;
      stroke-width: 2;
      fill: none;
      pointer-events: auto;
      transition: stroke 0.15s;
    }
    path:hover {
      stroke: #3b82f6;
      stroke-width: 2.5;
    }
  `],
})
export class ArchitectureConnectionComponent {
  @Input() data!: any;
  @Input() start: any;
  @Input() end: any;
  @Input() path!: string;
}
