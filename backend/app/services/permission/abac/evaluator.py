"""
Overview: Evaluator for ABAC DSL AST nodes with context resolution.
Architecture: Expression evaluation engine for ABAC policies (Section 5.2)
Dependencies: app.services.permission.abac.parser
Concepts: ABAC, expression evaluation, attribute resolution, CIDR matching
"""

import ipaddress
from dataclasses import dataclass, field
from datetime import datetime

from app.services.permission.abac.parser import (
    ASTNode,
    Attribute,
    BinaryOp,
    Literal,
    ListLiteral,
    MethodCall,
    UnaryOp,
)


@dataclass
class EvaluationContext:
    user: dict = field(default_factory=dict)
    resource: dict = field(default_factory=dict)
    context: dict = field(default_factory=dict)

    def resolve(self, parts: list[str]) -> object:
        """Resolve a dotted attribute path against the evaluation context."""
        if not parts:
            return None

        root = parts[0]
        rest = parts[1:]

        if root == "user":
            obj = self.user
        elif root == "resource":
            obj = self.resource
        elif root == "context":
            obj = self.context
        else:
            return None

        for part in rest:
            if isinstance(obj, dict):
                obj = obj.get(part)
            else:
                obj = getattr(obj, part, None)

            if obj is None:
                return None

        return obj


class EvaluationError(Exception):
    pass


class Evaluator:
    def __init__(self, context: EvaluationContext):
        self.context = context

    def evaluate(self, node: ASTNode) -> object:
        """Evaluate an AST node and return the result."""
        if isinstance(node, Literal):
            return node.value

        if isinstance(node, ListLiteral):
            return [self.evaluate(item) for item in node.items]

        if isinstance(node, Attribute):
            return self.context.resolve(node.parts)

        if isinstance(node, UnaryOp):
            return self._eval_unary(node)

        if isinstance(node, BinaryOp):
            return self._eval_binary(node)

        if isinstance(node, MethodCall):
            return self._eval_method(node)

        raise EvaluationError(f"Unknown node type: {type(node).__name__}")

    def _eval_unary(self, node: UnaryOp) -> object:
        operand = self.evaluate(node.operand)
        if node.op == "not":
            return not bool(operand)
        raise EvaluationError(f"Unknown unary operator: {node.op}")

    def _eval_binary(self, node: BinaryOp) -> object:
        if node.op in ("and", "or"):
            return self._eval_logical(node)

        left = self.evaluate(node.left)
        right = self.evaluate(node.right)

        if node.op == "==":
            return left == right
        elif node.op == "!=":
            return left != right
        elif node.op == "<":
            return self._compare(left, right) < 0
        elif node.op == ">":
            return self._compare(left, right) > 0
        elif node.op == "<=":
            return self._compare(left, right) <= 0
        elif node.op == ">=":
            return self._compare(left, right) >= 0
        elif node.op == "in":
            if isinstance(right, list):
                return left in right
            return False
        elif node.op == "contains":
            if isinstance(left, (list, str)):
                return right in left
            return False

        raise EvaluationError(f"Unknown binary operator: {node.op}")

    def _eval_logical(self, node: BinaryOp) -> bool:
        left = bool(self.evaluate(node.left))
        if node.op == "and":
            return left and bool(self.evaluate(node.right))
        elif node.op == "or":
            return left or bool(self.evaluate(node.right))
        raise EvaluationError(f"Unknown logical operator: {node.op}")

    def _eval_method(self, node: MethodCall) -> object:
        if node.method == "cidr_match":
            return self._cidr_match(node)
        elif node.method == "time_between":
            return self._time_between(node)
        elif node.method == "has_tag":
            return self._has_tag(node)

        raise EvaluationError(f"Unknown method: {node.method}")

    def _cidr_match(self, node: MethodCall) -> bool:
        """Check if an IP address matches a CIDR range."""
        if len(node.args) < 2:
            raise EvaluationError("cidr_match requires 2 arguments: ip, cidr")

        ip_str = self.evaluate(node.args[0])
        cidr_str = self.evaluate(node.args[1])

        if not ip_str or not cidr_str:
            return False

        try:
            ip = ipaddress.ip_address(str(ip_str))
            network = ipaddress.ip_network(str(cidr_str), strict=False)
            return ip in network
        except ValueError:
            return False

    def _time_between(self, node: MethodCall) -> bool:
        """Check if current time is between two hours (0-23)."""
        if len(node.args) < 2:
            raise EvaluationError("time_between requires 2 arguments: start_hour, end_hour")

        start = int(self.evaluate(node.args[0]))
        end = int(self.evaluate(node.args[1]))

        now = self.context.context.get("current_hour")
        if now is None:
            now = datetime.utcnow().hour

        if start <= end:
            return start <= now <= end
        else:
            return now >= start or now <= end

    def _has_tag(self, node: MethodCall) -> bool:
        """Check if a resource has a specific tag."""
        if len(node.args) < 1:
            raise EvaluationError("has_tag requires 1 argument: tag_name")

        tag_name = str(self.evaluate(node.args[0]))

        if node.obj:
            obj = self.evaluate(node.obj)
        else:
            obj = self.context.resource

        if isinstance(obj, dict):
            tags = obj.get("tags", {})
            return tag_name in tags

        return False

    @staticmethod
    def _compare(left, right) -> int:
        """Safe comparison for potentially mismatched types."""
        try:
            if left is None and right is None:
                return 0
            if left is None:
                return -1
            if right is None:
                return 1

            left_num = float(left) if not isinstance(left, (int, float)) else left
            right_num = float(right) if not isinstance(right, (int, float)) else right

            if left_num < right_num:
                return -1
            elif left_num > right_num:
                return 1
            return 0
        except (ValueError, TypeError):
            left_str = str(left)
            right_str = str(right)
            if left_str < right_str:
                return -1
            elif left_str > right_str:
                return 1
            return 0
