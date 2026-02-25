"""
Overview: Config mutation engine — declarative rules to update deployment parameters on activity success.
Architecture: Mutation processing for automated activities (Section 11.5)
Dependencies: sqlalchemy, app.models.automated_activity, app.models.deployment
Concepts: Declarative mutations, dot-notation path traversal, JSONB patching, rollback support
"""

from __future__ import annotations

import copy
import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.automated_activity import ConfigurationChange, MutationType

logger = logging.getLogger(__name__)


class MutationEngineError(Exception):
    def __init__(self, message: str, code: str = "MUTATION_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


def _get_nested(obj: dict, path: str) -> Any:
    """Get a value from a nested dict using dot-notation path."""
    keys = path.split(".")
    current = obj
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return None
    return current


def _set_nested(obj: dict, path: str, value: Any) -> dict:
    """Set a value in a nested dict using dot-notation path. Creates intermediate dicts."""
    keys = path.split(".")
    current = obj
    for key in keys[:-1]:
        if key not in current or not isinstance(current[key], dict):
            current[key] = {}
        current = current[key]
    current[keys[-1]] = value
    return obj


def _delete_nested(obj: dict, path: str) -> dict:
    """Delete a key from a nested dict using dot-notation path."""
    keys = path.split(".")
    current = obj
    for key in keys[:-1]:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return obj
    if isinstance(current, dict) and keys[-1] in current:
        del current[keys[-1]]
    return obj


class MutationEngine:
    """Processes declarative config mutation rules against deployment parameters."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def apply_mutations(
        self,
        deployment_id: str,
        tenant_id: str,
        execution_id: str,
        mutations: list[dict[str, Any]],
        activity_output: dict[str, Any] | None = None,
        applied_by: str | None = None,
    ) -> list[ConfigurationChange]:
        """Apply a list of mutation rules to a deployment's parameters.

        Each mutation rule has: parameter_path, mutation_type, and optionally value/output_key.
        """
        from app.models.deployment import Deployment

        result = await self.db.execute(
            select(Deployment).where(Deployment.id == deployment_id)
        )
        deployment = result.scalar_one_or_none()
        if not deployment:
            raise MutationEngineError(
                f"Deployment {deployment_id} not found", "DEPLOYMENT_NOT_FOUND"
            )

        parameters = copy.deepcopy(deployment.parameters or {})

        # Get next version number for this deployment
        ver_result = await self.db.execute(
            select(func.coalesce(func.max(ConfigurationChange.version), 0)).where(
                ConfigurationChange.deployment_id == deployment_id
            )
        )
        next_version = ver_result.scalar_one()

        changes: list[ConfigurationChange] = []

        for rule in mutations:
            path = rule["parameter_path"]
            mutation_type = rule["mutation_type"].upper()
            old_value = _get_nested(parameters, path)
            new_value = self._compute_new_value(
                mutation_type, old_value, rule, activity_output or {}
            )

            # Apply the mutation to parameters
            if mutation_type == MutationType.REMOVE.value:
                _delete_nested(parameters, path)
            else:
                _set_nested(parameters, path, new_value)

            next_version += 1
            change = ConfigurationChange(
                tenant_id=tenant_id,
                deployment_id=deployment_id,
                activity_execution_id=execution_id,
                version=next_version,
                parameter_path=path,
                mutation_type=mutation_type,
                old_value=old_value,
                new_value=new_value,
                applied_by=applied_by,
            )
            self.db.add(change)
            changes.append(change)

        # Update deployment parameters
        deployment.parameters = parameters
        await self.db.flush()

        logger.info(
            "Applied %d mutations to deployment %s", len(changes), deployment_id
        )
        return changes

    async def rollback_mutations(
        self,
        deployment_id: str,
        tenant_id: str,
        execution_id: str,
        rollback_mutations: list[dict[str, Any]],
        original_changes: list[ConfigurationChange],
        applied_by: str | None = None,
    ) -> list[ConfigurationChange]:
        """Rollback mutations by applying inverse operations."""
        from app.models.deployment import Deployment

        result = await self.db.execute(
            select(Deployment).where(Deployment.id == deployment_id)
        )
        deployment = result.scalar_one_or_none()
        if not deployment:
            raise MutationEngineError(
                f"Deployment {deployment_id} not found", "DEPLOYMENT_NOT_FOUND"
            )

        parameters = copy.deepcopy(deployment.parameters or {})

        ver_result = await self.db.execute(
            select(func.coalesce(func.max(ConfigurationChange.version), 0)).where(
                ConfigurationChange.deployment_id == deployment_id
            )
        )
        next_version = ver_result.scalar_one()

        changes: list[ConfigurationChange] = []

        if rollback_mutations:
            # Use explicit rollback rules
            for rule in rollback_mutations:
                path = rule["parameter_path"]
                mutation_type = rule["mutation_type"].upper()
                old_value = _get_nested(parameters, path)
                new_value = self._compute_new_value(mutation_type, old_value, rule, {})
                _set_nested(parameters, path, new_value)

                next_version += 1
                change = ConfigurationChange(
                    tenant_id=tenant_id,
                    deployment_id=deployment_id,
                    activity_execution_id=execution_id,
                    version=next_version,
                    parameter_path=path,
                    mutation_type=mutation_type,
                    old_value=old_value,
                    new_value=new_value,
                    applied_by=applied_by,
                    rollback_of=original_changes[0].id if original_changes else None,
                )
                self.db.add(change)
                changes.append(change)
        else:
            # Auto-rollback: restore old values from original changes (reverse order)
            for orig in reversed(original_changes):
                path = orig.parameter_path
                current = _get_nested(parameters, path)
                if orig.old_value is not None:
                    _set_nested(parameters, path, orig.old_value)
                else:
                    _delete_nested(parameters, path)

                next_version += 1
                change = ConfigurationChange(
                    tenant_id=tenant_id,
                    deployment_id=deployment_id,
                    activity_execution_id=execution_id,
                    version=next_version,
                    parameter_path=path,
                    mutation_type=MutationType.SET.value,
                    old_value=current,
                    new_value=orig.old_value,
                    applied_by=applied_by,
                    rollback_of=orig.id,
                )
                self.db.add(change)
                changes.append(change)

        deployment.parameters = parameters
        await self.db.flush()

        logger.info(
            "Rolled back %d mutations for deployment %s", len(changes), deployment_id
        )
        return changes

    def validate_mutations(
        self, mutations: list[dict[str, Any]]
    ) -> list[str]:
        """Validate mutation rules. Returns list of error messages (empty = valid)."""
        errors: list[str] = []
        valid_types = {t.value for t in MutationType}

        for i, rule in enumerate(mutations):
            if "parameter_path" not in rule or not rule["parameter_path"]:
                errors.append(f"Rule {i}: missing parameter_path")
            if "mutation_type" not in rule:
                errors.append(f"Rule {i}: missing mutation_type")
            elif rule["mutation_type"].upper() not in valid_types:
                errors.append(
                    f"Rule {i}: invalid mutation_type '{rule['mutation_type']}'"
                )

            mt = rule.get("mutation_type", "").upper()
            if mt == MutationType.SET.value and "value" not in rule:
                errors.append(f"Rule {i}: SET requires 'value'")
            if mt == MutationType.SET_FROM_INPUT.value and "output_key" not in rule:
                errors.append(f"Rule {i}: SET_FROM_INPUT requires 'output_key'")
            if mt in (MutationType.INCREMENT.value, MutationType.DECREMENT.value):
                if "value" not in rule:
                    errors.append(f"Rule {i}: {mt} requires 'value'")
                elif not isinstance(rule.get("value"), (int, float)):
                    errors.append(f"Rule {i}: {mt} requires numeric 'value'")
            if mt == MutationType.APPEND.value and "value" not in rule:
                errors.append(f"Rule {i}: APPEND requires 'value'")
            if mt == MutationType.REMOVE.value and "value" not in rule:
                errors.append(
                    f"Rule {i}: REMOVE requires 'value' (item to remove from list)"
                )

        return errors

    def _compute_new_value(
        self,
        mutation_type: str,
        old_value: Any,
        rule: dict[str, Any],
        activity_output: dict[str, Any],
    ) -> Any:
        """Compute the new value based on mutation type."""
        if mutation_type == MutationType.SET.value:
            return rule["value"]

        if mutation_type == MutationType.SET_FROM_INPUT.value:
            output_key = rule["output_key"]
            return _get_nested(activity_output, output_key)

        if mutation_type == MutationType.INCREMENT.value:
            base = old_value if isinstance(old_value, (int, float)) else 0
            return base + rule["value"]

        if mutation_type == MutationType.DECREMENT.value:
            base = old_value if isinstance(old_value, (int, float)) else 0
            return base - rule["value"]

        if mutation_type == MutationType.APPEND.value:
            base = list(old_value) if isinstance(old_value, list) else []
            base.append(rule["value"])
            return base

        if mutation_type == MutationType.REMOVE.value:
            if isinstance(old_value, list):
                return [x for x in old_value if x != rule["value"]]
            return old_value

        raise MutationEngineError(f"Unknown mutation type: {mutation_type}")
