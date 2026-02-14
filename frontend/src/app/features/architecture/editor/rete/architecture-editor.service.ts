/**
 * Overview: Rete.js v2 editor service for architecture topologies — canvas init, graph serialization,
 *     node management, property tracking, selection state, clipboard operations.
 * Architecture: Core editor service for visual architecture canvas (Section 3.2)
 * Dependencies: rete, rete-area-plugin, rete-connection-plugin, rete-angular-plugin
 * Concepts: Rete.js editor, topology graph, semantic type nodes, signal-based state, clipboard
 */
import { Injectable, Injector, signal } from '@angular/core';
import { NodeEditor, ClassicPreset, GetSchemes } from 'rete';
import { AreaPlugin, AreaExtensions } from 'rete-area-plugin';
import { ConnectionPlugin, Presets as ConnectionPresets } from 'rete-connection-plugin';
import { AngularPlugin, Presets as AngularPresets } from 'rete-angular-plugin/17';
import { MinimapPlugin } from 'rete-minimap-plugin';
import {
  TopologyGraph,
  TopologyNode,
  TopologyConnection,
  TopologyCompartment,
  TopologyStackInstance,
} from '@shared/models/architecture.model';
import { SemanticResourceType } from '@shared/models/semantic.model';
import { ArchitectureNodeComponent } from './architecture-node.component';
import { ArchitectureSocketComponent } from './architecture-socket.component';
import { ArchitectureConnectionComponent } from './architecture-connection.component';

type Schemes = GetSchemes<
  ClassicPreset.Node,
  ClassicPreset.Connection<ClassicPreset.Node, ClassicPreset.Node>
>;

export interface ClipboardEntry {
  node: TopologyNode;
  semanticType?: SemanticResourceType;
}

@Injectable()
export class ArchitectureEditorService {
  private editor: NodeEditor<Schemes> | null = null;
  private area: AreaPlugin<Schemes, any> | null = null;
  private semanticTypeMap = new Map<string, SemanticResourceType>();
  private nodePropertiesMap = new Map<string, Record<string, unknown>>();
  private nodeSemanticTypeMap = new Map<string, string>();
  private connectionKindMap = new Map<string, string>();
  private compartmentMap = new Map<string, TopologyCompartment>();
  private stackMap = new Map<string, TopologyStackInstance>();

  readonly selectedNodeId = signal<string | null>(null);
  readonly selectedCompartmentId = signal<string | null>(null);
  readonly selectedStackId = signal<string | null>(null);
  readonly graphChanged = signal<number>(0);

  /** Clipboard for copy/cut/paste operations */
  clipboard = signal<ClipboardEntry | null>(null);

  setSemanticTypes(types: SemanticResourceType[]): void {
    this.semanticTypeMap.clear();
    for (const t of types) {
      this.semanticTypeMap.set(t.id, t);
    }
  }

  getSemanticType(nodeId: string): SemanticResourceType | undefined {
    const typeId = this.nodeSemanticTypeMap.get(nodeId);
    return typeId ? this.semanticTypeMap.get(typeId) : undefined;
  }

  getSemanticTypeById(typeId: string): SemanticResourceType | undefined {
    return this.semanticTypeMap.get(typeId);
  }

  async initialize(container: HTMLElement, injector: Injector): Promise<void> {
    this.editor = new NodeEditor<Schemes>();
    this.area = new AreaPlugin<Schemes, any>(container);

    const connection = new ConnectionPlugin<Schemes, any>();
    const angularPlugin = new AngularPlugin<Schemes, any>({ injector });

    connection.addPreset(ConnectionPresets.classic.setup());
    angularPlugin.addPreset(AngularPresets.classic.setup({
      customize: {
        node: () => ArchitectureNodeComponent as any,
        socket: () => ArchitectureSocketComponent as any,
        connection: () => ArchitectureConnectionComponent as any,
      },
    }));

    this.editor.use(this.area);
    this.area.use(connection);
    this.area.use(angularPlugin);

    const minimap = new MinimapPlugin<any>();
    this.area.use(minimap);

    AreaExtensions.selectableNodes(this.area, AreaExtensions.selector(), {
      accumulating: AreaExtensions.accumulateOnCtrl(),
    });

    this.area.addPipe(context => {
      if ('type' in context && context.type === 'nodepicked') {
        this.selectedNodeId.set((context as any).data?.id ?? null);
      }
      return context;
    });

    this.editor.addPipe(context => {
      if (
        ['nodecreated', 'noderemoved', 'connectioncreated', 'connectionremoved'].includes(
          (context as any).type,
        )
      ) {
        this.graphChanged.update(v => v + 1);
      }
      return context;
    });

    AreaExtensions.simpleNodesOrder(this.area);
  }

  async loadGraph(graph: TopologyGraph): Promise<void> {
    if (!this.editor || !this.area) return;

    await this.editor.clear();
    this.nodePropertiesMap.clear();
    this.nodeSemanticTypeMap.clear();
    this.connectionKindMap.clear();
    this.compartmentMap.clear();
    this.stackMap.clear();

    // Load compartments
    for (const comp of graph.compartments || []) {
      this.compartmentMap.set(comp.id, { ...comp });
    }

    // Load stacks
    for (const stack of graph.stacks || []) {
      this.stackMap.set(stack.id, { ...stack });
    }

    const nodeMap = new Map<string, ClassicPreset.Node>();

    for (const topoNode of graph.nodes) {
      const node = this.createReteNode(topoNode);
      if (node) {
        await this.editor.addNode(node);
        if (topoNode.position) {
          await this.area.translate(node.id, topoNode.position);
        }
        nodeMap.set(topoNode.id, node);
      }
    }

    for (const conn of graph.connections) {
      const sourceNode = nodeMap.get(conn.source);
      const targetNode = nodeMap.get(conn.target);
      if (sourceNode && targetNode) {
        const sourceOutput = sourceNode.outputs['out'];
        const targetInput = targetNode.inputs['in'];
        if (sourceOutput && targetInput) {
          const connection = new ClassicPreset.Connection(sourceNode, 'out', targetNode, 'in');
          (connection as any).id = conn.id;
          this.connectionKindMap.set(conn.id, conn.relationshipKindId);
          await this.editor.addConnection(connection);
        }
      }
    }

    AreaExtensions.zoomAt(this.area, this.editor.getNodes());
  }

  serializeGraph(): TopologyGraph {
    if (!this.editor || !this.area) {
      return { nodes: [], connections: [], compartments: [], stacks: [] };
    }

    const nodes: TopologyNode[] = this.editor.getNodes().map(node => {
      const view = this.area?.nodeViews.get(node.id);
      return {
        id: node.id,
        semanticTypeId: this.nodeSemanticTypeMap.get(node.id) || '',
        label: node.label,
        position: view ? { x: view.position.x, y: view.position.y } : { x: 0, y: 0 },
        properties: this.nodePropertiesMap.get(node.id) || {},
        compartmentId: (node as any)._compartmentId || null,
      };
    });

    const connections: TopologyConnection[] = this.editor.getConnections().map(conn => ({
      id: conn.id,
      source: conn.source,
      target: conn.target,
      relationshipKindId: this.connectionKindMap.get(conn.id) || '',
      label: null,
    }));

    const compartments = Array.from(this.compartmentMap.values());
    const stacks = Array.from(this.stackMap.values());

    return { nodes, connections, compartments, stacks };
  }

  async addNode(
    semanticTypeId: string,
    position: { x: number; y: number },
  ): Promise<string | null> {
    if (!this.editor || !this.area) return null;

    const typeDef = this.semanticTypeMap.get(semanticTypeId);
    const nodeId = `node_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;

    // Pre-populate default property values from semantic type schema
    const defaultProperties: Record<string, unknown> = {};
    if (typeDef?.propertiesSchema && Array.isArray(typeDef.propertiesSchema)) {
      for (const prop of typeDef.propertiesSchema) {
        if (prop.default_value != null) {
          defaultProperties[prop.name] = prop.default_value;
        }
      }
    }

    const topoNode: TopologyNode = {
      id: nodeId,
      semanticTypeId,
      label: typeDef?.displayName || semanticTypeId,
      position,
      properties: defaultProperties,
    };

    const node = this.createReteNode(topoNode);
    if (!node) return null;

    await this.editor.addNode(node);
    await this.area.translate(node.id, position);
    return node.id;
  }

  async addConnection(
    sourceId: string,
    targetId: string,
    relationshipKindId: string,
  ): Promise<string | null> {
    if (!this.editor) return null;

    const sourceNode = this.editor.getNode(sourceId);
    const targetNode = this.editor.getNode(targetId);
    if (!sourceNode || !targetNode) return null;

    const connection = new ClassicPreset.Connection(sourceNode, 'out', targetNode, 'in');
    this.connectionKindMap.set(connection.id, relationshipKindId);
    await this.editor.addConnection(connection);
    return connection.id;
  }

  async removeSelected(): Promise<void> {
    if (!this.editor) return;
    const selected = this.selectedNodeId();
    if (selected) {
      const connections = this.editor
        .getConnections()
        .filter(c => c.source === selected || c.target === selected);
      for (const conn of connections) {
        this.connectionKindMap.delete(conn.id);
        await this.editor.removeConnection(conn.id);
      }
      this.nodePropertiesMap.delete(selected);
      this.nodeSemanticTypeMap.delete(selected);
      await this.editor.removeNode(selected);
      this.selectedNodeId.set(null);
    }
  }

  // ── Clipboard Operations ──────────────────────────────────────

  copySelected(): void {
    const nodeId = this.selectedNodeId();
    if (!nodeId) return;

    const semanticTypeId = this.nodeSemanticTypeMap.get(nodeId);
    const properties = this.nodePropertiesMap.get(nodeId) || {};
    const view = this.area?.nodeViews.get(nodeId);
    const node = this.editor?.getNode(nodeId);

    if (!node) return;

    const topoNode: TopologyNode = {
      id: nodeId,
      semanticTypeId: semanticTypeId || '',
      label: node.label,
      position: view ? { x: view.position.x, y: view.position.y } : { x: 0, y: 0 },
      properties: { ...properties },
      compartmentId: (node as any)._compartmentId || null,
    };

    this.clipboard.set({
      node: topoNode,
      semanticType: semanticTypeId ? this.semanticTypeMap.get(semanticTypeId) : undefined,
    });
  }

  async cutSelected(): Promise<void> {
    this.copySelected();
    await this.removeSelected();
  }

  async pasteFromClipboard(offset = 40): Promise<string | null> {
    const entry = this.clipboard();
    if (!entry || !this.editor || !this.area) return null;

    const newId = `node_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
    const topoNode: TopologyNode = {
      ...entry.node,
      id: newId,
      label: `${entry.node.label} (copy)`,
      position: {
        x: entry.node.position.x + offset,
        y: entry.node.position.y + offset,
      },
    };

    const node = this.createReteNode(topoNode);
    if (!node) return null;

    await this.editor.addNode(node);
    await this.area.translate(node.id, topoNode.position);
    this.selectedNodeId.set(node.id);
    return node.id;
  }

  async duplicateSelected(): Promise<string | null> {
    this.copySelected();
    return this.pasteFromClipboard(60);
  }

  async zoomToFit(): Promise<void> {
    if (!this.area || !this.editor) return;
    AreaExtensions.zoomAt(this.area, this.editor.getNodes());
  }

  getNodeProperties(nodeId: string): Record<string, unknown> {
    return this.nodePropertiesMap.get(nodeId) || {};
  }

  updateNodeProperties(nodeId: string, properties: Record<string, unknown>): void {
    this.nodePropertiesMap.set(nodeId, properties);
    this.graphChanged.update(v => v + 1);
  }

  updateNodeLabel(nodeId: string, label: string): void {
    if (!this.editor) return;
    const node = this.editor.getNode(nodeId);
    if (node) {
      node.label = label;
      this.graphChanged.update(v => v + 1);
    }
  }

  getNodeSemanticTypeId(nodeId: string): string | null {
    return this.nodeSemanticTypeMap.get(nodeId) || null;
  }

  getConnectionKindId(connectionId: string): string | null {
    return this.connectionKindMap.get(connectionId) || null;
  }

  // ── Compartment Management ─────────────────────────────────────

  addCompartment(compartment: TopologyCompartment): void {
    this.compartmentMap.set(compartment.id, compartment);
    this.graphChanged.update(v => v + 1);
  }

  updateCompartment(id: string, updates: Partial<TopologyCompartment>): void {
    const existing = this.compartmentMap.get(id);
    if (existing) {
      this.compartmentMap.set(id, { ...existing, ...updates });
      this.graphChanged.update(v => v + 1);
    }
  }

  removeCompartment(id: string): void {
    this.compartmentMap.delete(id);
    // Remove compartment reference from stacks
    for (const [sid, stack] of this.stackMap) {
      if (stack.compartmentId === id) {
        this.stackMap.set(sid, { ...stack, compartmentId: null });
      }
    }
    this.graphChanged.update(v => v + 1);
  }

  getCompartment(id: string): TopologyCompartment | undefined {
    return this.compartmentMap.get(id);
  }

  getCompartments(): TopologyCompartment[] {
    return Array.from(this.compartmentMap.values());
  }

  // ── Stack Management ─────────────────────────────────────────

  addStack(stack: TopologyStackInstance): void {
    this.stackMap.set(stack.id, stack);
    this.graphChanged.update(v => v + 1);
  }

  updateStack(id: string, updates: Partial<TopologyStackInstance>): void {
    const existing = this.stackMap.get(id);
    if (existing) {
      this.stackMap.set(id, { ...existing, ...updates });
      this.graphChanged.update(v => v + 1);
    }
  }

  removeStack(id: string): void {
    this.stackMap.delete(id);
    // Remove dependsOn references from other stacks
    for (const [sid, stack] of this.stackMap) {
      if (stack.dependsOn.includes(id)) {
        this.stackMap.set(sid, {
          ...stack,
          dependsOn: stack.dependsOn.filter(d => d !== id),
        });
      }
    }
    this.graphChanged.update(v => v + 1);
  }

  getStack(id: string): TopologyStackInstance | undefined {
    return this.stackMap.get(id);
  }

  getStacks(): TopologyStackInstance[] {
    return Array.from(this.stackMap.values());
  }

  // ── Selection Helpers ────────────────────────────────────────

  selectCompartment(id: string | null): void {
    this.selectedCompartmentId.set(id);
    this.selectedStackId.set(null);
    this.selectedNodeId.set(null);
  }

  selectStack(id: string | null): void {
    this.selectedStackId.set(id);
    this.selectedCompartmentId.set(null);
    this.selectedNodeId.set(null);
  }

  clearSelection(): void {
    this.selectedNodeId.set(null);
    this.selectedCompartmentId.set(null);
    this.selectedStackId.set(null);
  }

  destroy(): void {
    this.area?.destroy();
    this.editor = null;
    this.area = null;
    this.nodePropertiesMap.clear();
    this.nodeSemanticTypeMap.clear();
    this.connectionKindMap.clear();
    this.compartmentMap.clear();
    this.stackMap.clear();
  }

  private createReteNode(topoNode: TopologyNode): ClassicPreset.Node | null {
    const typeDef = this.semanticTypeMap.get(topoNode.semanticTypeId);
    const label = topoNode.label || typeDef?.displayName || topoNode.semanticTypeId;
    const node = new ClassicPreset.Node(label);

    (node as any).id = topoNode.id;
    // Store metadata for the custom node component to access
    (node as any)._typeName = typeDef?.displayName || topoNode.semanticTypeId;
    (node as any)._icon = typeDef?.icon || '';
    (node as any)._compartmentId = topoNode.compartmentId || null;

    this.nodeSemanticTypeMap.set(topoNode.id, topoNode.semanticTypeId);
    this.nodePropertiesMap.set(topoNode.id, { ...topoNode.properties });

    const socket = new ClassicPreset.Socket('RESOURCE');
    node.addInput('in', new ClassicPreset.Input(socket, '', true));
    node.addOutput('out', new ClassicPreset.Output(socket, ''));

    return node;
  }
}
