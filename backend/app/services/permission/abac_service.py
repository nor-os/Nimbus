"""
Overview: ABAC policy management service for CRUD and validation.
Architecture: Service layer for ABAC policy lifecycle (Section 3.1, 5.2)
Dependencies: sqlalchemy, app.models, app.services.permission.abac
Concepts: ABAC, policy management, expression validation
"""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.abac_policy import ABACPolicy, PolicyEffect
from app.services.permission.abac.evaluator import EvaluationContext, Evaluator
from app.services.permission.abac.parser import ParseError, Parser
from app.services.permission.abac.tokenizer import Tokenizer, TokenizerError


class ABACError(Exception):
    def __init__(self, message: str, code: str = "ABAC_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class ABACService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_policies(self, tenant_id: str) -> list[ABACPolicy]:
        """List all ABAC policies for a tenant."""
        result = await self.db.execute(
            select(ABACPolicy)
            .where(ABACPolicy.tenant_id == tenant_id)
            .order_by(ABACPolicy.priority.desc())
        )
        return list(result.scalars().all())

    async def get_policy(self, policy_id: str, tenant_id: str) -> ABACPolicy | None:
        """Get a single ABAC policy."""
        result = await self.db.execute(
            select(ABACPolicy).where(
                ABACPolicy.id == policy_id, ABACPolicy.tenant_id == tenant_id
            )
        )
        return result.scalar_one_or_none()

    async def create_policy(
        self,
        tenant_id: str,
        name: str,
        expression: str,
        effect: str,
        priority: int = 0,
        is_enabled: bool = True,
        target_permission_id: str | None = None,
    ) -> ABACPolicy:
        """Create a new ABAC policy."""
        # Validate expression
        error = self.validate_expression(expression)
        if error:
            raise ABACError(f"Invalid expression: {error}", "INVALID_EXPRESSION")

        policy = ABACPolicy(
            tenant_id=tenant_id,
            name=name,
            expression=expression,
            effect=PolicyEffect(effect),
            priority=priority,
            is_enabled=is_enabled,
            target_permission_id=target_permission_id,
        )
        self.db.add(policy)
        await self.db.flush()
        return policy

    async def update_policy(
        self,
        policy_id: str,
        tenant_id: str,
        name: str | None = None,
        expression: str | None = None,
        effect: str | None = None,
        priority: int | None = None,
        is_enabled: bool | None = None,
        target_permission_id: str | None = None,
    ) -> ABACPolicy:
        """Update an ABAC policy."""
        policy = await self.get_policy(policy_id, tenant_id)
        if not policy:
            raise ABACError("Policy not found", "POLICY_NOT_FOUND")

        if expression is not None:
            error = self.validate_expression(expression)
            if error:
                raise ABACError(f"Invalid expression: {error}", "INVALID_EXPRESSION")
            policy.expression = expression

        if name is not None:
            policy.name = name
        if effect is not None:
            policy.effect = PolicyEffect(effect)
        if priority is not None:
            policy.priority = priority
        if is_enabled is not None:
            policy.is_enabled = is_enabled
        if target_permission_id is not None:
            policy.target_permission_id = target_permission_id

        await self.db.flush()
        return policy

    async def delete_policy(self, policy_id: str, tenant_id: str) -> None:
        """Delete an ABAC policy."""
        policy = await self.get_policy(policy_id, tenant_id)
        if not policy:
            raise ABACError("Policy not found", "POLICY_NOT_FOUND")

        await self.db.delete(policy)
        await self.db.flush()

    @staticmethod
    def validate_expression(expression: str) -> str | None:
        """Validate an ABAC expression. Returns error message or None if valid."""
        try:
            tokens = Tokenizer(expression).tokenize()
            Parser(tokens).parse()
            return None
        except (TokenizerError, ParseError) as e:
            return str(e)
        except Exception as e:
            return f"Unexpected error: {e}"

    @staticmethod
    def evaluate_expression(
        expression: str, user: dict, resource: dict, context: dict
    ) -> bool:
        """Evaluate an ABAC expression against a context."""
        tokens = Tokenizer(expression).tokenize()
        ast = Parser(tokens).parse()
        eval_context = EvaluationContext(user=user, resource=resource, context=context)
        return bool(Evaluator(eval_context).evaluate(ast))
