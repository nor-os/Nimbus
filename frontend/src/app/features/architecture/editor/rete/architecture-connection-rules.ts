/**
 * Overview: Connection validation rules based on semantic relationship kinds.
 * Architecture: Connection rule engine for architecture editor (Section 3.2)
 * Dependencies: None
 * Concepts: Validates that connections use relationship kinds allowed by both source and target types
 */

import { SemanticRelationshipKind, SemanticResourceType } from '@shared/models/semantic.model';

export interface ConnectionRuleResult {
  allowed: boolean;
  availableKinds: SemanticRelationshipKind[];
  message?: string;
}

export function checkConnectionRules(
  sourceType: SemanticResourceType | undefined,
  targetType: SemanticResourceType | undefined,
  allKinds: SemanticRelationshipKind[],
): ConnectionRuleResult {
  if (!sourceType || !targetType) {
    return { allowed: false, availableKinds: [], message: 'Unknown source or target type' };
  }

  const sourceAllowed = sourceType.allowedRelationshipKinds as string[] | null;
  const targetAllowed = targetType.allowedRelationshipKinds as string[] | null;

  // If no restrictions on either side, all kinds are allowed
  if (!sourceAllowed?.length && !targetAllowed?.length) {
    return { allowed: allKinds.length > 0, availableKinds: allKinds };
  }

  // Filter to kinds allowed by both source and target
  const available = allKinds.filter(kind => {
    const sourceOk = !sourceAllowed?.length ||
      sourceAllowed.includes(kind.id) || sourceAllowed.includes(kind.name);
    const targetOk = !targetAllowed?.length ||
      targetAllowed.includes(kind.id) || targetAllowed.includes(kind.name);
    return sourceOk && targetOk;
  });

  if (available.length === 0) {
    return {
      allowed: false,
      availableKinds: [],
      message: `No compatible relationship kinds between ${sourceType.displayName} and ${targetType.displayName}`,
    };
  }

  return { allowed: true, availableKinds: available };
}
