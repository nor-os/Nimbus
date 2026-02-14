/**
 * Overview: Subtle connection socket for architecture topology nodes — small dot at card edge.
 * Architecture: Visual socket component for architecture canvas (Section 3.2)
 * Dependencies: @angular/core
 * Concepts: Port sockets, connection endpoints, Rete.js socket contract, minimal visual
 */
import {
  Component,
  Input,
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  HostBinding,
  OnChanges,
} from '@angular/core';

@Component({
  selector: 'nimbus-architecture-socket',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: ``,
  styles: [`
    :host {
      display: block;
      width: 10px;
      height: 10px;
      border-radius: 50%;
      background: #cbd5e1;
      border: 2px solid #fff;
      box-shadow: 0 0 0 1px #e2e8f0;
      cursor: crosshair;
      transition: background 0.15s, transform 0.15s, box-shadow 0.15s;
    }
    :host:hover {
      background: #3b82f6;
      box-shadow: 0 0 0 1px #3b82f6;
      transform: scale(1.4);
    }
  `],
})
export class ArchitectureSocketComponent implements OnChanges {
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
