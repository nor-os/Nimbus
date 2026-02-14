/**
 * Overview: Custom connection line rendering for the workflow canvas — light theme SVG paths.
 * Architecture: Visual connection component (Section 3.2)
 * Dependencies: @angular/core
 * Concepts: Connection rendering, SVG paths, Rete.js connection contract
 */
import { Component, Input, ChangeDetectionStrategy, ChangeDetectorRef, OnChanges } from '@angular/core';

@Component({
  selector: 'nimbus-custom-connection',
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
      stroke-width: 2.5;
      fill: none;
      pointer-events: auto;
      transition: stroke 0.15s;
    }
    path:hover {
      stroke: #3b82f6;
    }
  `],
})
export class CustomConnectionComponent implements OnChanges {
  @Input() data!: any;
  @Input() start: any;
  @Input() end: any;
  @Input() path!: string;

  constructor(private cdr: ChangeDetectorRef) {
    this.cdr.detach();
  }

  ngOnChanges(): void {
    this.cdr.detectChanges();
  }
}
