/**
 * Overview: Custom Rete.js node renderer for architecture topology — clean card with icon, label,
 *     type badge, and subtle edge-mounted connection sockets.
 * Architecture: Visual node component for architecture canvas (Section 3.2)
 * Dependencies: @angular/core, @angular/common, rete-angular-plugin/17, rete
 * Concepts: Rete.js component contract, architecture node rendering, hidden port sockets
 */
import {
  Component,
  Input,
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  HostBinding,
  OnChanges,
} from '@angular/core';
import { CommonModule, KeyValue } from '@angular/common';
import { ReteModule } from 'rete-angular-plugin/17';
import { iconNameToSymbol } from '@shared/utils/icon-map';

@Component({
  selector: 'nimbus-architecture-node',
  standalone: true,
  imports: [CommonModule, ReteModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="arch-node" [class.selected]="selected">
      <!-- Input sockets (left edge) -->
      <div class="edge-sockets edge-left" *ngIf="data.inputs">
        <div *ngFor="let input of data.inputs | keyvalue : sortByIndex"
          class="edge-socket-wrapper"
          refComponent
          [data]="{ type: 'socket', side: 'input', key: input.key, nodeId: data.id, payload: input.value?.socket, seed: seed }"
          [emit]="emit"
        ></div>
      </div>

      <div class="node-content">
        <div class="node-header">
          <span class="node-icon">{{ resolvedIcon }}</span>
          <span class="node-label">{{ data.label }}</span>
        </div>
        <div class="node-type-badge" *ngIf="typeName">{{ typeName }}</div>
      </div>

      <!-- Output sockets (right edge) -->
      <div class="edge-sockets edge-right" *ngIf="data.outputs">
        <div *ngFor="let output of data.outputs | keyvalue : sortByIndex"
          class="edge-socket-wrapper"
          refComponent
          [data]="{ type: 'socket', side: 'output', key: output.key, nodeId: data.id, payload: output.value?.socket, seed: seed }"
          [emit]="emit"
        ></div>
      </div>
    </div>
  `,
  styles: [`
    :host {
      display: block;
    }
    .arch-node {
      position: relative;
      min-width: 160px;
      background: #fff;
      border: 1.5px solid #e2e8f0;
      border-radius: 8px;
      box-shadow: 0 1px 4px rgba(0,0,0,0.06);
      overflow: visible;
      transition: border-color 0.15s, box-shadow 0.15s;
    }
    .arch-node.selected {
      border-color: #3b82f6;
      box-shadow: 0 0 0 2px rgba(59,130,246,0.2);
    }
    .node-content {
      pointer-events: none;
    }
    .node-header {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 10px 12px 6px;
    }
    .node-icon {
      font-size: 1.125rem;
      width: 20px;
      height: 20px;
      line-height: 20px;
      text-align: center;
      flex-shrink: 0;
      overflow: hidden;
    }
    .node-label {
      font-size: 0.8125rem;
      font-weight: 600;
      color: #1e293b;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .node-type-badge {
      padding: 4px 12px 8px;
      font-size: 0.6875rem;
      color: #64748b;
      font-weight: 500;
    }
    /* Edge-mounted sockets — positioned at card edges */
    .edge-sockets {
      position: absolute;
      top: 50%;
      transform: translateY(-50%);
      display: flex;
      flex-direction: column;
      gap: 6px;
      z-index: 5;
    }
    .edge-left {
      left: -5px;
    }
    .edge-right {
      right: -5px;
    }
    .edge-socket-wrapper {
      display: flex;
      align-items: center;
    }
  `],
})
export class ArchitectureNodeComponent implements OnChanges {
  @Input() data!: any;
  @Input() emit!: (data: any) => void;
  @Input() rendered!: () => void;

  seed = 0;

  @HostBinding('class.selected')
  get selected(): boolean {
    return this.data?.selected ?? false;
  }

  @HostBinding('style.width.px')
  get width(): number | undefined {
    return this.data?.width;
  }

  @HostBinding('style.height.px')
  get height(): number | undefined {
    return this.data?.height;
  }

  get typeName(): string {
    return this.data?._typeName || '';
  }

  get resolvedIcon(): string {
    return iconNameToSymbol(this.data?._icon);
  }

  constructor(private cdr: ChangeDetectorRef) {
    this.cdr.detach();
  }

  ngOnChanges(): void {
    this.seed++;
    this.cdr.detectChanges();
    requestAnimationFrame(() => this.rendered());
  }

  sortByIndex(a: KeyValue<string, any>, b: KeyValue<string, any>): number {
    const ai = a.value?.index ?? 0;
    const bi = b.value?.index ?? 0;
    return ai - bi;
  }
}
