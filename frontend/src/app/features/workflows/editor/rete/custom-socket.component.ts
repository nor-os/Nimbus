/**
 * Overview: Custom port socket rendering for workflow nodes — light theme with hover effects.
 * Architecture: Visual socket component (Section 3.2)
 * Dependencies: @angular/core
 * Concepts: Port sockets, connection endpoints, Rete.js socket contract
 */
import { Component, Input, ChangeDetectionStrategy, ChangeDetectorRef, HostBinding, OnChanges } from '@angular/core';

@Component({
  selector: 'nimbus-custom-socket',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: ``,
  styles: [`
    :host {
      display: block;
      width: 14px;
      height: 14px;
      border-radius: 50%;
      background: #cbd5e1;
      border: 2px solid #ffffff;
      box-shadow: 0 0 0 1px #e2e8f0;
      cursor: crosshair;
      transition: background 0.15s, transform 0.15s, box-shadow 0.15s;
    }
    :host:hover {
      background: #3b82f6;
      box-shadow: 0 0 0 1px #3b82f6;
      transform: scale(1.25);
    }
  `],
})
export class CustomSocketComponent implements OnChanges {
  @Input() data!: any;
  @Input() rendered!: () => void;

  @HostBinding('title')
  get title(): string {
    return this.data?.name ?? '';
  }

  constructor(private cdr: ChangeDetectorRef) {
    this.cdr.detach();
  }

  ngOnChanges(): void {
    this.cdr.detectChanges();
    requestAnimationFrame(() => this.rendered());
  }
}
