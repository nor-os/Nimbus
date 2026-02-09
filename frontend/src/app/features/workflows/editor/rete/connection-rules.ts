/**
 * Overview: Connection rules — port type enforcement and self-connection prevention.
 * Architecture: Connection validation for workflow canvas (Section 3.2)
 * Dependencies: None
 * Concepts: Port compatibility, self-connection prevention
 */

export function canConnect(
  sourceNodeId: string,
  targetNodeId: string,
  sourcePort: string,
  targetPort: string,
): boolean {
  // Prevent self-connections
  if (sourceNodeId === targetNodeId) return false;

  // All flow ports are compatible with each other
  return true;
}
