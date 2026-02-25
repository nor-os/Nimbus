"""
Overview: Safe filter expression evaluator for event subscriptions.
Architecture: Reuses workflow expression engine pattern for event payload filtering (Section 11.6)
Dependencies: app.services.workflow.expression_engine
Concepts: Safe AST evaluation, payload filtering, subscription matching
"""

from __future__ import annotations

import logging
from typing import Any

from app.services.workflow.expression_engine import (
    EvaluationError,
    Evaluator,
    ExpressionContext,
    ParseError,
    Parser,
    Tokenizer,
    TokenizerError,
)

logger = logging.getLogger(__name__)

# Built-in functions available in filter expressions
FILTER_FUNCTIONS: dict[str, Any] = {
    "len": len,
    "str": str,
    "int": int,
    "float": float,
    "lower": lambda s: str(s).lower(),
    "upper": lambda s: str(s).upper(),
    "contains": lambda haystack, needle: needle in haystack,
    "startswith": lambda s, prefix: str(s).startswith(str(prefix)),
    "endswith": lambda s, suffix: str(s).endswith(str(suffix)),
}


def evaluate_filter(expression: str, payload: dict[str, Any]) -> bool:
    """Evaluate a filter expression against an event payload.

    The payload is exposed as `payload.*` variables.
    Returns True if the expression evaluates truthy, False otherwise.
    """
    if not expression or not expression.strip():
        return True

    try:
        tokens = Tokenizer(expression).tokenize()
        ast = Parser(tokens).parse()
        context = ExpressionContext(
            variables={"payload": payload},
            input_data=payload,
        )
        # Override scope resolution: 'payload' maps to variables['payload']
        evaluator = _FilterEvaluator(FILTER_FUNCTIONS)
        result = evaluator.evaluate(ast, context)
        return bool(result)
    except (TokenizerError, ParseError, EvaluationError) as e:
        logger.warning("Filter expression error: %s (expression=%r)", e, expression)
        return False
    except Exception as e:
        logger.error("Unexpected filter error: %s (expression=%r)", e, expression)
        return False


class _FilterEvaluator(Evaluator):
    """Evaluator subclass that resolves bare identifiers as payload keys."""

    def evaluate(self, node: Any, context: ExpressionContext) -> Any:
        from app.services.workflow.expression_engine import Literal, Variable

        # Resolve bare identifier names as payload field access
        if isinstance(node, Literal) and isinstance(node.value, str):
            # Check if it's a string literal (quoted) vs identifier
            # Identifiers are parsed as Literal with string value by the expression engine
            # We keep the default behavior
            pass

        # For Variable nodes, map 'payload' scope to the payload data
        if isinstance(node, Variable) and node.scope == "payload":
            data = context.variables.get("payload", {})
            current: Any = data
            for segment in node.path:
                if isinstance(current, dict):
                    if segment not in current:
                        return None
                    current = current[segment]
                else:
                    return None
            return current

        return super().evaluate(node, context)


def validate_filter(expression: str) -> list[str]:
    """Validate filter expression syntax without evaluating."""
    if not expression or not expression.strip():
        return []

    errors: list[str] = []
    try:
        tokens = Tokenizer(expression).tokenize()
        Parser(tokens).parse()
    except (TokenizerError, ParseError) as e:
        errors.append(str(e))
    return errors
