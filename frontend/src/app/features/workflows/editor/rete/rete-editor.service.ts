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
  private socketRegistry = new Map<string, ClassicPreset.Socket>();

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

    // Debug: log connection events
    this.editor.addPipe(context => {
      if ('type' in context) {
        const t = (context as any).type;
        if (t === 'connectioncreated' || t === 'connectionremoved') {
          console.log(`[rete-debug] ${t}`, (context as any).data);
        }
      }
      return context;
    });

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
      // Normalize legacy field: data → config
      if ((wfNode as any).data && !wfNode.config) {
        wfNode.config = (wfNode as any).data;
        delete (wfNode as any).data;
      }
      const node = this.createReteNode(wfNode);
      if (node) {
        await this.editor.addNode(node);
        if (wfNode.position) {
          await this.area.translate(node.id, wfNode.position);
        }
        nodeMap.set(wfNode.id, node);
      }
    }

    // Wait for Angular to render node DOM so port positions are available
    await new Promise<void>(resolve => {
      requestAnimationFrame(() => requestAnimationFrame(() => resolve()));
    });

    for (const conn of graph.connections) {
      // Normalize legacy fields: sourceOutput → sourcePort, targetInput → targetPort
      if ((conn as any).sourceOutput && !conn.sourcePort) {
        conn.sourcePort = (conn as any).sourceOutput;
        delete (conn as any).sourceOutput;
      }
      if ((conn as any).targetInput && !conn.targetPort) {
        conn.targetPort = (conn as any).targetInput;
        delete (conn as any).targetInput;
      }

      const sourceNode = nodeMap.get(conn.source);
      const targetNode = nodeMap.get(conn.target);
      if (!sourceNode) {
        console.warn(`[loadGraph] Connection skipped: source node "${conn.source}" not found`);
        continue;
      }
      if (!targetNode) {
        console.warn(`[loadGraph] Connection skipped: target node "${conn.target}" not found`);
        continue;
      }

      let srcPort = conn.sourcePort || 'out';
      let tgtPort = conn.targetPort || 'in';

      // Fallback: if exact port not found, try first available port of same direction
      if (!sourceNode.outputs[srcPort]) {
        const available = Object.keys(sourceNode.outputs || {});
        const fallback = available.find(k => k !== 'result') || available[0];
        if (fallback) {
          console.warn(`[loadGraph] Port fallback: source "${srcPort}" → "${fallback}" on "${conn.source}"`);
          srcPort = fallback;
        }
      }
      if (!targetNode.inputs[tgtPort]) {
        const available = Object.keys(targetNode.inputs || {});
        const fallback = available[0];
        if (fallback) {
          console.warn(`[loadGraph] Port fallback: target "${tgtPort}" → "${fallback}" on "${conn.target}"`);
          tgtPort = fallback;
        }
      }

      const sourceOutput = sourceNode.outputs[srcPort];
      const targetInput = targetNode.inputs[tgtPort];

      if (!sourceOutput) {
        console.warn(`[loadGraph] Connection skipped: source port "${srcPort}" not found on "${conn.source}" (available: ${Object.keys(sourceNode.outputs || {})})`);
        continue;
      }
      if (!targetInput) {
        console.warn(`[loadGraph] Connection skipped: target port "${tgtPort}" not found on "${conn.target}" (available: ${Object.keys(targetNode.inputs || {})})`);
        continue;
      }

      console.log(`[loadGraph] Adding connection: ${conn.source}:${srcPort} → ${conn.target}:${tgtPort}`);
      const connection = new ClassicPreset.Connection(sourceNode, srcPort, targetNode, tgtPort);
      try {
        await this.editor.addConnection(connection);
        console.log(`[loadGraph] Connection added OK: ${connection.id}`);
      } catch (e) {
        console.error(`[loadGraph] Connection add FAILED:`, e);
      }
    }

    console.log(`[loadGraph] Loaded ${this.editor.getNodes().length} nodes, ${this.editor.getConnections().length} connections`);
    console.log(`[loadGraph] Connection views: ${this.area.connectionViews.size}`);
    console.log(`[loadGraph] Node views: ${this.area.nodeViews.size}`);

    // Debug: check SVG paths after render
    setTimeout(() => {
      const container = this.area!.container;
      const paths = container.querySelectorAll('svg path');
      console.log(`[loadGraph] SVG paths found: ${paths.length}`);
      paths.forEach((p, i) => {
        console.log(`[loadGraph] path[${i}] d="${p.getAttribute('d')}" visible=${getComputedStyle(p).display}`);
      });
      // Check if connection wrapper got position data
      this.area!.connectionViews.forEach((view, id) => {
        const svg = view.element.querySelector('svg path');
        const d = svg?.getAttribute('d');
        console.log(`[loadGraph] conn ${id}: path d="${d || 'EMPTY'}"`);
      });
    }, 2000);

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
    this.socketRegistry.clear();
  }

  private getSocket(portType: string): ClassicPreset.Socket {
    let socket = this.socketRegistry.get(portType);
    if (!socket) {
      socket = new ClassicPreset.Socket(portType);
      this.socketRegistry.set(portType, socket);
    }
    return socket;
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
        const socket = this.getSocket(port.portType);
        if (port.direction === 'INPUT') {
          node.addInput(port.name, new ClassicPreset.Input(socket, port.label, port.multiple));
        } else {
          node.addOutput(port.name, new ClassicPreset.Output(socket, port.label));
        }
      }
    } else {
      // Fallback: generic in/out
      const socket = this.getSocket('FLOW');
      node.addInput('in', new ClassicPreset.Input(socket, 'Input'));
      node.addOutput('out', new ClassicPreset.Output(socket, 'Output'));
    }

    return node;
  }
}
