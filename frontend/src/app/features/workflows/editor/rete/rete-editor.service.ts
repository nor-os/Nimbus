/**
 * Overview: Rete.js v2 editor service — wraps canvas initialization, graph serialization, node management.
 * Architecture: Core editor service for visual workflow canvas (Section 3.2)
 * Dependencies: rete, rete-area-plugin, rete-connection-plugin, rete-angular-plugin
 * Concepts: Rete.js editor, node editor, graph serialization, signal-based state
 */
import { Injectable, Injector, signal } from '@angular/core';
import { NodeEditor, ClassicPreset, GetSchemes } from 'rete';
import { AreaPlugin, AreaExtensions } from 'rete-area-plugin';
import { ConnectionPlugin, Presets as ConnectionPresets } from 'rete-connection-plugin';
import { AngularPlugin, Presets as AngularPresets } from 'rete-angular-plugin/17';
import { MinimapPlugin } from 'rete-minimap-plugin';
import { WorkflowGraph, WorkflowNode, WorkflowConnection, NodeTypeInfo, PortDef } from '@shared/models/workflow.model';
import { CustomNodeComponent } from './custom-node.component';
import { CustomSocketComponent } from './custom-socket.component';
import { CustomConnectionComponent } from './custom-connection.component';

type Schemes = GetSchemes<ClassicPreset.Node, ClassicPreset.Connection<ClassicPreset.Node, ClassicPreset.Node>>;

@Injectable()
export class ReteEditorService {
  private editor: NodeEditor<Schemes> | null = null;
  private area: AreaPlugin<Schemes, any> | null = null;
  private nodeTypeMap = new Map<string, NodeTypeInfo>();

  readonly selectedNodeId = signal<string | null>(null);
  readonly graphChanged = signal<number>(0);

  setNodeTypes(types: NodeTypeInfo[]): void {
    this.nodeTypeMap.clear();
    for (const t of types) {
      this.nodeTypeMap.set(t.typeId, t);
    }
  }

  async initialize(container: HTMLElement, injector: Injector): Promise<void> {
    this.editor = new NodeEditor<Schemes>();
    this.area = new AreaPlugin<Schemes, any>(container);

    const connection = new ConnectionPlugin<Schemes, any>();
    const angularPlugin = new AngularPlugin<Schemes, any>({ injector });

    connection.addPreset(ConnectionPresets.classic.setup());
    angularPlugin.addPreset(AngularPresets.classic.setup({
      customize: {
        node: () => CustomNodeComponent as any,
        socket: () => CustomSocketComponent as any,
        connection: () => CustomConnectionComponent as any,
      },
    }));

    this.editor.use(this.area);
    this.area.use(connection);
    this.area.use(angularPlugin);

    // Minimap
    const minimap = new MinimapPlugin<any>();
    this.area.use(minimap);

    // Selection
    AreaExtensions.selectableNodes(this.area, AreaExtensions.selector(), {
      accumulating: AreaExtensions.accumulateOnCtrl(),
    });

    // Track selection changes
    this.area.addPipe(context => {
      if ('type' in context && context.type === 'nodepicked') {
        this.selectedNodeId.set((context as any).data?.id ?? null);
      }
      return context;
    });

    // Track graph changes
    this.editor.addPipe(context => {
      if (['nodecreated', 'noderemoved', 'connectioncreated', 'connectionremoved'].includes((context as any).type)) {
        this.graphChanged.update(v => v + 1);
      }
      return context;
    });

    AreaExtensions.simpleNodesOrder(this.area);
  }

  async loadGraph(graph: WorkflowGraph): Promise<void> {
    if (!this.editor || !this.area) return;

    await this.editor.clear();

    const nodeMap = new Map<string, ClassicPreset.Node>();

    for (const wfNode of graph.nodes) {
      const node = this.createReteNode(wfNode);
      if (node) {
        await this.editor.addNode(node);
        if (wfNode.position) {
          await this.area.translate(node.id, wfNode.position);
        }
        nodeMap.set(wfNode.id, node);
      }
    }

    for (const conn of graph.connections) {
      const sourceNode = nodeMap.get(conn.source);
      const targetNode = nodeMap.get(conn.target);
      if (sourceNode && targetNode) {
        const sourceOutput = sourceNode.outputs[conn.sourcePort];
        const targetInput = targetNode.inputs[conn.targetPort];
        if (sourceOutput && targetInput) {
          const connection = new ClassicPreset.Connection(sourceNode, conn.sourcePort, targetNode, conn.targetPort);
          await this.editor.addConnection(connection);
        }
      }
    }

    AreaExtensions.zoomAt(this.area, this.editor.getNodes());
  }

  serializeGraph(): WorkflowGraph {
    if (!this.editor || !this.area) {
      return { nodes: [], connections: [] };
    }

    const nodes: WorkflowNode[] = this.editor.getNodes().map(node => {
      const view = this.area?.nodeViews.get(node.id);
      return {
        id: node.id,
        type: (node as any)._workflowType || 'unknown',
        config: (node as any)._config || {},
        position: view ? { x: view.position.x, y: view.position.y } : { x: 0, y: 0 },
        label: node.label,
      };
    });

    const connections: WorkflowConnection[] = this.editor.getConnections().map(conn => ({
      source: conn.source,
      target: conn.target,
      sourcePort: conn.sourceOutput as string,
      targetPort: conn.targetInput as string,
    }));

    return { nodes, connections };
  }

  async addNode(typeId: string, position: { x: number; y: number }): Promise<string | null> {
    if (!this.editor || !this.area) return null;

    const wfNode: WorkflowNode = {
      id: `node_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
      type: typeId,
      config: {},
      position,
    };

    const node = this.createReteNode(wfNode);
    if (!node) return null;

    await this.editor.addNode(node);
    await this.area.translate(node.id, position);
    return node.id;
  }

  async removeSelected(): Promise<void> {
    if (!this.editor) return;
    const selected = this.selectedNodeId();
    if (selected) {
      // Remove connections first
      const connections = this.editor.getConnections().filter(
        c => c.source === selected || c.target === selected
      );
      for (const conn of connections) {
        await this.editor.removeConnection(conn.id);
      }
      await this.editor.removeNode(selected);
      this.selectedNodeId.set(null);
    }
  }

  async zoomToFit(): Promise<void> {
    if (!this.area || !this.editor) return;
    AreaExtensions.zoomAt(this.area, this.editor.getNodes());
  }

  getNodeConfig(nodeId: string): Record<string, unknown> | null {
    if (!this.editor) return null;
    const node = this.editor.getNode(nodeId);
    return node ? (node as any)._config || {} : null;
  }

  updateNodeConfig(nodeId: string, config: Record<string, unknown>): void {
    if (!this.editor) return;
    const node = this.editor.getNode(nodeId);
    if (node) {
      (node as any)._config = config;
      this.graphChanged.update(v => v + 1);
    }
  }

  getNodeType(nodeId: string): string | null {
    if (!this.editor) return null;
    const node = this.editor.getNode(nodeId);
    return node ? (node as any)._workflowType || null : null;
  }

  destroy(): void {
    this.area?.destroy();
    this.editor = null;
    this.area = null;
  }

  private createReteNode(wfNode: WorkflowNode): ClassicPreset.Node | null {
    const typeDef = this.nodeTypeMap.get(wfNode.type);
    const label = wfNode.label || typeDef?.label || wfNode.type;
    const node = new ClassicPreset.Node(label);

    // Store workflow metadata on the node
    (node as any)._workflowType = wfNode.type;
    (node as any)._config = { ...wfNode.config };
    (node as any)._category = typeDef?.category || 'Utility';
    (node as any)._icon = typeDef?.icon || '';
    // Override the auto-generated ID with our stable ID
    (node as any).id = wfNode.id;

    if (typeDef) {
      for (const port of typeDef.ports) {
        const socket = new ClassicPreset.Socket(port.portType);
        if (port.direction === 'INPUT') {
          node.addInput(port.name, new ClassicPreset.Input(socket, port.label, port.multiple));
        } else {
          node.addOutput(port.name, new ClassicPreset.Output(socket, port.label));
        }
      }
    } else {
      // Fallback: generic in/out
      const socket = new ClassicPreset.Socket('FLOW');
      node.addInput('in', new ClassicPreset.Input(socket, 'Input'));
      node.addOutput('out', new ClassicPreset.Output(socket, 'Output'));
    }

    return node;
  }
}
