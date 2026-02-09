/**
 * Overview: Client-side graph validation service mirroring backend validation.
 * Architecture: Frontend validation for immediate feedback (Section 3.2)
 * Dependencies: @angular/core
 * Concepts: Client-side validation, graph structure checks, immediate feedback
 */
import { Injectable } from '@angular/core';
import { ValidationResult, ValidationError, WorkflowGraph } from '@shared/models/workflow.model';

@Injectable({ providedIn: 'root' })
export class GraphValidatorService {

  validate(graph: WorkflowGraph | null): ValidationResult {
    const errors: ValidationError[] = [];
    const warnings: ValidationError[] = [];

    if (!graph || !graph.nodes.length) {
      errors.push({ nodeId: null, message: 'Graph has no nodes', severity: 'error' });
      return { valid: false, errors, warnings };
    }

    const startNodes = graph.nodes.filter(n => n.type === 'start');
    const endNodes = graph.nodes.filter(n => n.type === 'end');

    if (startNodes.length === 0) {
      errors.push({ nodeId: null, message: 'Graph must have exactly one Start node', severity: 'error' });
    } else if (startNodes.length > 1) {
      errors.push({ nodeId: null, message: 'Graph must have exactly one Start node', severity: 'error' });
    }

    if (endNodes.length === 0) {
      errors.push({ nodeId: null, message: 'Graph must have at least one End node', severity: 'error' });
    }

    // Check for disconnected nodes
    const connectedNodes = new Set<string>();
    for (const conn of graph.connections) {
      connectedNodes.add(conn.source);
      connectedNodes.add(conn.target);
    }

    for (const node of graph.nodes) {
      if (!connectedNodes.has(node.id) && node.type !== 'start' && graph.nodes.length > 1) {
        warnings.push({ nodeId: node.id, message: 'Node is not connected', severity: 'warning' });
      }
    }

    // Check self-connections
    for (const conn of graph.connections) {
      if (conn.source === conn.target) {
        errors.push({ nodeId: conn.source, message: 'Self-connections are not allowed', severity: 'error' });
      }
    }

    return {
      valid: errors.length === 0,
      errors,
      warnings,
    };
  }
}
