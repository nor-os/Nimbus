/**
 * Overview: Properties panel container — shows node properties when selected, topology-level otherwise.
 * Architecture: Right sidebar panel for architecture editor (Section 3.2)
 * Dependencies: @angular/core, @angular/common, node-properties-form.component
 * Concepts: Context-aware properties panel, semantic type lookup, node/topology-level properties
 */
import { Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { NodePropertiesFormComponent } from './node-properties-form.component';
import { CompartmentPropertiesComponent } from './compartment-properties.component';
import { ParameterBindingEditorComponent } from './parameter-binding-editor.component';
import { SemanticResourceType } from '@shared/models/semantic.model';
import { TopologyCompartment, TopologyStackInstance, ParameterOverride } from '@shared/models/architecture.model';
import { StackBlueprintParameter } from '@shared/models/cluster.model';
import { iconNameToSymbol } from '@shared/utils/icon-map';

@Component({
  selector: 'nimbus-topology-properties-panel',
  standalone: true,
  imports: [CommonModule, NodePropertiesFormComponent, CompartmentPropertiesComponent, ParameterBindingEditorComponent],
  template: `
    <div class="properties-panel">
      @if (selectedNodeId && selectedType) {
        <!-- Node properties -->
        <div class="panel-header">
          <div class="panel-title">
            <span class="type-icon">{{ resolveIcon(selectedType.icon) }}</span>
            {{ selectedType.displayName }}
          </div>
          <div class="node-id">{{ selectedNodeId }}</div>
        </div>
        <div class="panel-body">
          <nimbus-node-properties-form
            [propertiesSchema]="$any(selectedType.propertiesSchema)"
            [properties]="nodeProperties"
            [label]="nodeLabel"
            [readOnly]="readOnly"
            (labelChange)="labelChange.emit($event)"
            (propertyChange)="propertyChange.emit($event)"
          />
        </div>
      } @else if (selectedCompartment) {
        <!-- Compartment properties -->
        <div class="panel-header">
          <div class="panel-title">
            <span class="type-icon">&#9633;</span>
            Compartment
          </div>
          <div class="node-id">{{ selectedCompartment.id }}</div>
        </div>
        <div class="panel-body">
          <nimbus-compartment-properties
            [compartment]="selectedCompartment"
            [parentOptions]="compartmentParentOptions"
            [topologyId]="topologyId"
            [readOnly]="readOnly"
            (update)="compartmentUpdate.emit({ id: selectedCompartment.id, updates: $event })"
          />
        </div>
      } @else if (selectedStack) {
        <!-- Stack properties -->
        <div class="panel-header">
          <div class="panel-title">
            <span class="type-icon">&#9881;</span>
            Stack Instance
          </div>
          <div class="node-id">{{ selectedStack.id }}</div>
        </div>
        <div class="panel-body">
          <div class="stack-label-row">
            <label class="form-label-sm">Label</label>
            <input
              type="text"
              class="form-input-sm"
              [value]="selectedStack.label"
              (change)="stackLabelChange.emit({ id: selectedStack.id, label: $any($event.target).value })"
              [disabled]="readOnly"
            />
          </div>
          <nimbus-parameter-binding-editor
            [stack]="selectedStack"
            [blueprintParameters]="stackBlueprintParams"
            [readOnly]="readOnly"
            (overridesChange)="stackOverridesChange.emit({ id: selectedStack.id, overrides: $event })"
          />
        </div>
      } @else {
        <!-- Topology summary -->
        <div class="panel-header">
          <div class="panel-title">Topology Properties</div>
        </div>
        <div class="panel-body">
          <div class="hint">Select a node, compartment, or stack to view its properties.</div>
          <div class="topology-stats">
            <div class="stat">
              <span class="stat-value">{{ nodeCount }}</span>
              <span class="stat-label">Nodes</span>
            </div>
            <div class="stat">
              <span class="stat-value">{{ connectionCount }}</span>
              <span class="stat-label">Connections</span>
            </div>
            <div class="stat">
              <span class="stat-value">{{ compartmentCount }}</span>
              <span class="stat-label">Comparts</span>
            </div>
            <div class="stat">
              <span class="stat-value">{{ stackCount }}</span>
              <span class="stat-label">Stacks</span>
            </div>
          </div>
        </div>
      }
    </div>
  `,
  styles: [`
    :host { display: block; flex-shrink: 0; width: 300px; height: 100%; }
    .properties-panel {
      width: 100%;
      height: 100%;
      background: #fff;
      border-left: 1px solid #e2e8f0;
      display: flex;
      flex-direction: column;
      overflow-y: auto;
    }
    .panel-header {
      padding: 12px;
      border-bottom: 1px solid #e2e8f0;
    }
    .panel-title {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 0.875rem;
      font-weight: 600;
      color: #1e293b;
    }
    .type-icon { font-size: 1rem; width: 18px; height: 18px; line-height: 18px; text-align: center; overflow: hidden; flex-shrink: 0; }
    .node-id {
      margin-top: 4px;
      font-size: 0.6875rem;
      color: #94a3b8;
      font-family: monospace;
    }
    .panel-body { padding: 12px; flex: 1; }
    .hint {
      font-size: 0.8125rem;
      color: #94a3b8;
      padding: 12px 0;
    }
    .topology-stats {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
      margin-top: 16px;
    }
    .stat {
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 12px;
      background: #f8fafc;
      border-radius: 8px;
    }
    .stat-value { font-size: 1.5rem; font-weight: 700; color: #1e293b; }
    .stat-label { font-size: 0.6875rem; color: #94a3b8; margin-top: 2px; }
    .stack-label-row {
      display: flex;
      flex-direction: column;
      gap: 4px;
      margin-bottom: 12px;
    }
    .form-label-sm {
      font-size: 0.6875rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      color: #64748b;
    }
    .form-input-sm {
      padding: 6px 8px;
      border: 1px solid #e2e8f0;
      border-radius: 6px;
      font-size: 0.8125rem;
      color: #1e293b;
      background: #fff;
      font-family: inherit;
      outline: none;
    }
    .form-input-sm:focus { border-color: #3b82f6; }
    .form-input-sm:disabled { background: #f8fafc; color: #94a3b8; }
  `],
})
export class TopologyPropertiesPanelComponent {
  @Input() selectedNodeId: string | null = null;
  @Input() selectedType: SemanticResourceType | null = null;
  @Input() nodeProperties: Record<string, unknown> = {};
  @Input() nodeLabel = '';
  @Input() nodeCount = 0;
  @Input() connectionCount = 0;
  @Input() compartmentCount = 0;
  @Input() stackCount = 0;
  @Input() readOnly = false;

  // Compartment selection
  @Input() selectedCompartment: TopologyCompartment | null = null;
  @Input() compartmentParentOptions: { id: string; label: string }[] = [];
  @Input() topologyId: string = '';

  // Stack selection
  @Input() selectedStack: TopologyStackInstance | null = null;
  @Input() stackBlueprintParams: StackBlueprintParameter[] = [];

  @Output() labelChange = new EventEmitter<string>();
  @Output() propertyChange = new EventEmitter<{ name: string; value: unknown }>();
  @Output() compartmentUpdate = new EventEmitter<{ id: string; updates: Partial<TopologyCompartment> }>();
  @Output() stackLabelChange = new EventEmitter<{ id: string; label: string }>();
  @Output() stackOverridesChange = new EventEmitter<{ id: string; overrides: Record<string, ParameterOverride> }>();

  resolveIcon(icon: string | null | undefined): string {
    return iconNameToSymbol(icon);
  }
}
