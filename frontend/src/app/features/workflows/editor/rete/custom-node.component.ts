/**
 * Overview: Custom Rete.js node rendering component with category-colored accent, icon, and port layout.
 * Architecture: Visual node component for workflow canvas (Section 3.2)
 * Dependencies: @angular/core, @angular/common, rete-angular-plugin/17
 * Concepts: Node rendering, category differentiation, Rete.js component contract
 */
import { Component, Input, ChangeDetectionStrategy, ChangeDetectorRef, HostBinding, OnChanges } from '@angular/core';
import { CommonModule, KeyValue } from '@angular/common';
import { ReteModule } from 'rete-angular-plugin/17';
import { ClassicPreset } from 'rete';

const CATEGORY_COLORS: Record<string, string> = {
  'Flow Control': '#3b82f6',
  'Action': '#f59e0b',
  'Integration': '#8b5cf6',
  'Data': '#10b981',
  'Utility': '#6b7280',
  'Deployment': '#f43f5e',
};

@Component({
  selector: 'nimbus-custom-node',
  standalone: true,
  imports: [CommonModule, ReteModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="node-card" [style.border-left-color]="accentColor">
      <div class="node-header">
        <span class="node-icon" [innerHTML]="nodeIcon"></span>
        <span class="node-label">{{ data.label }}</span>
        <span class="category-badge" [style.background]="badgeBg" [style.color]="accentColor">{{ nodeCategory }}</span>
      </div>

      <div class="node-body">
        <!-- Outputs -->
        <div class="outputs" *ngIf="data.outputs">
          <div class="port output-port" *ngFor="let output of data.outputs | keyvalue : sortByIndex">
            <span class="port-label">{{ output.value?.label }}</span>
            <div class="port-socket"
              refComponent
              [data]="{ type: 'socket', side: 'output', key: output.key, nodeId: data.id, payload: output.value?.socket, seed: seed }"
              [emit]="emit"
            ></div>
          </div>
        </div>

        <!-- Inputs -->
        <div class="inputs" *ngIf="data.inputs">
          <div class="port input-port" *ngFor="let input of data.inputs | keyvalue : sortByIndex">
            <div class="port-socket"
              refComponent
              [data]="{ type: 'socket', side: 'input', key: input.key, nodeId: data.id, payload: input.value?.socket, seed: seed }"
              [emit]="emit"
            ></div>
            <span class="port-label">{{ input.value?.label }}</span>
            <!-- Controls inside inputs -->
            <ng-container *ngIf="input.value?.control && !input.value?.showControl">
              <div class="input-control"
                refComponent
                [data]="{ type: 'control', payload: input.value?.control }"
                [emit]="emit"
              ></div>
            </ng-container>
          </div>
        </div>

        <!-- Standalone controls -->
        <div class="controls" *ngIf="data.controls">
          <div *ngFor="let control of data.controls | keyvalue"
            refComponent
            [data]="{ type: 'control', payload: control.value }"
            [emit]="emit"
          ></div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    :host {
      display: block;
    }
    .node-card {
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-left: 4px solid #6b7280;
      border-radius: 8px;
      min-width: 180px;
      font-size: 0.8125rem;
      box-shadow: 0 1px 3px rgba(0,0,0,0.08), 0 1px 2px rgba(0,0,0,0.04);
      transition: border-color 0.15s, box-shadow 0.15s;
      overflow: hidden;
    }
    :host(.selected) .node-card {
      border-color: #3b82f6;
      box-shadow: 0 0 0 2px rgba(59,130,246,0.25), 0 1px 3px rgba(0,0,0,0.08);
    }
    .node-header {
      display: flex;
      align-items: center;
      gap: 6px;
      padding: 8px 12px;
      border-bottom: 1px solid #f1f5f9;
      background: #f8fafc;
    }
    .node-icon {
      font-size: 1rem;
      line-height: 1;
    }
    .node-label {
      font-weight: 600;
      color: #1e293b;
      flex: 1;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .category-badge {
      font-size: 0.625rem;
      font-weight: 600;
      padding: 1px 6px;
      border-radius: 9999px;
      white-space: nowrap;
      text-transform: uppercase;
      letter-spacing: 0.025em;
    }
    .node-body {
      padding: 8px 0;
    }
    .inputs, .outputs {
      display: flex;
      flex-direction: column;
      gap: 4px;
    }
    .port {
      display: flex;
      align-items: center;
      gap: 6px;
      padding: 2px 12px;
    }
    .input-port {
      justify-content: flex-start;
    }
    .output-port {
      justify-content: flex-end;
    }
    .port-label {
      color: #64748b;
      font-size: 0.6875rem;
    }
    .port-socket {
      display: flex;
      align-items: center;
    }
    .controls {
      padding: 4px 12px;
    }
    .input-control {
      margin-left: 4px;
    }
  `],
})
export class CustomNodeComponent implements OnChanges {
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

  get nodeCategory(): string {
    return this.data?._category || 'Utility';
  }

  get nodeIcon(): string {
    return this.data?._icon || '';
  }

  get accentColor(): string {
    return CATEGORY_COLORS[this.nodeCategory] || CATEGORY_COLORS['Utility'];
  }

  get badgeBg(): string {
    return this.accentColor + '18';
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
