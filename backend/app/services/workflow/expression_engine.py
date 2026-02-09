"""
Overview: Safe expression engine — tokenizer, recursive-descent parser, AST evaluator.
Architecture: Expression evaluation for workflow node configurations (Section 5)
Dependencies: None (pure Python)
Concepts: Tokenizer, parser, AST, safe evaluation, variable resolution, string interpolation
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any


# ── Safety Limits ────────────────────────────────────────

MAX_AST_DEPTH = 50
MAX_STRING_LENGTH = 100_000
FORBIDDEN_NAMES = frozenset({
    "import", "exec", "eval", "compile", "__import__",
    "globals", "locals", "getattr", "setattr", "delattr",
    "open", "breakpoint", "__builtins__",
})


# ── Token Types ──────────────────────────────────────────


class TokenType(Enum):
    NUMBER = auto()
    STRING = auto()
    BOOLEAN = auto()
    NULL = auto()
    IDENTIFIER = auto()
    DOLLAR = auto()
    DOT = auto()
    LBRACKET = auto()
    RBRACKET = auto()
    LPAREN = auto()
    RPAREN = auto()
    COMMA = auto()
    PLUS = auto()
    MINUS = auto()
    STAR = auto()
    SLASH = auto()
    PERCENT = auto()
    EQ = auto()
    NE = auto()
    LT = auto()
    GT = auto()
    LE = auto()
    GE = auto()
    AND = auto()
    OR = auto()
    NOT = auto()
    EOF = auto()


@dataclass
class Token:
    type: TokenType
    value: Any
    position: int


# ── Tokenizer ────────────────────────────────────────────

KEYWORDS = {
    "true": (TokenType.BOOLEAN, True),
    "false": (TokenType.BOOLEAN, False),
    "null": (TokenType.NULL, None),
    "and": (TokenType.AND, "&&"),
    "or": (TokenType.OR, "||"),
    "not": (TokenType.NOT, "!"),
}


class TokenizerError(Exception):
    def __init__(self, message: str, position: int):
        self.position = position
        super().__init__(f"Tokenizer error at position {position}: {message}")


class Tokenizer:
    def __init__(self, source: str):
        self._source = source
        self._pos = 0
        self._length = len(source)

    def tokenize(self) -> list[Token]:
        tokens: list[Token] = []
        while self._pos < self._length:
            self._skip_whitespace()
            if self._pos >= self._length:
                break

            ch = self._source[self._pos]

            if ch == "$":
                tokens.append(Token(TokenType.DOLLAR, "$", self._pos))
                self._pos += 1
            elif ch == ".":
                tokens.append(Token(TokenType.DOT, ".", self._pos))
                self._pos += 1
            elif ch == ",":
                tokens.append(Token(TokenType.COMMA, ",", self._pos))
                self._pos += 1
            elif ch == "(":
                tokens.append(Token(TokenType.LPAREN, "(", self._pos))
                self._pos += 1
            elif ch == ")":
                tokens.append(Token(TokenType.RPAREN, ")", self._pos))
                self._pos += 1
            elif ch == "[":
                tokens.append(Token(TokenType.LBRACKET, "[", self._pos))
                self._pos += 1
            elif ch == "]":
                tokens.append(Token(TokenType.RBRACKET, "]", self._pos))
                self._pos += 1
            elif ch == "+":
                tokens.append(Token(TokenType.PLUS, "+", self._pos))
                self._pos += 1
            elif ch == "-":
                tokens.append(Token(TokenType.MINUS, "-", self._pos))
                self._pos += 1
            elif ch == "*":
                tokens.append(Token(TokenType.STAR, "*", self._pos))
                self._pos += 1
            elif ch == "/":
                tokens.append(Token(TokenType.SLASH, "/", self._pos))
                self._pos += 1
            elif ch == "%":
                tokens.append(Token(TokenType.PERCENT, "%", self._pos))
                self._pos += 1
            elif ch == "=" and self._peek(1) == "=":
                tokens.append(Token(TokenType.EQ, "==", self._pos))
                self._pos += 2
            elif ch == "!" and self._peek(1) == "=":
                tokens.append(Token(TokenType.NE, "!=", self._pos))
                self._pos += 2
            elif ch == "!":
                tokens.append(Token(TokenType.NOT, "!", self._pos))
                self._pos += 1
            elif ch == "<" and self._peek(1) == "=":
                tokens.append(Token(TokenType.LE, "<=", self._pos))
                self._pos += 2
            elif ch == ">" and self._peek(1) == "=":
                tokens.append(Token(TokenType.GE, ">=", self._pos))
                self._pos += 2
            elif ch == "<":
                tokens.append(Token(TokenType.LT, "<", self._pos))
                self._pos += 1
            elif ch == ">":
                tokens.append(Token(TokenType.GT, ">", self._pos))
                self._pos += 1
            elif ch == "&" and self._peek(1) == "&":
                tokens.append(Token(TokenType.AND, "&&", self._pos))
                self._pos += 2
            elif ch == "|" and self._peek(1) == "|":
                tokens.append(Token(TokenType.OR, "||", self._pos))
                self._pos += 2
            elif ch in ("'", '"'):
                tokens.append(self._read_string())
            elif ch.isdigit():
                tokens.append(self._read_number())
            elif ch.isalpha() or ch == "_":
                tokens.append(self._read_identifier())
            else:
                raise TokenizerError(f"Unexpected character '{ch}'", self._pos)

        tokens.append(Token(TokenType.EOF, None, self._pos))
        return tokens

    def _skip_whitespace(self) -> None:
        while self._pos < self._length and self._source[self._pos] in " \t\r\n":
            self._pos += 1

    def _peek(self, offset: int = 0) -> str | None:
        idx = self._pos + offset
        return self._source[idx] if idx < self._length else None

    def _read_string(self) -> Token:
        start = self._pos
        quote = self._source[self._pos]
        self._pos += 1
        result: list[str] = []

        while self._pos < self._length:
            ch = self._source[self._pos]
            if ch == "\\":
                self._pos += 1
                if self._pos < self._length:
                    escaped = self._source[self._pos]
                    escape_map = {"n": "\n", "t": "\t", "r": "\r", "\\": "\\"}
                    result.append(escape_map.get(escaped, escaped))
                    self._pos += 1
            elif ch == quote:
                self._pos += 1
                return Token(TokenType.STRING, "".join(result), start)
            else:
                result.append(ch)
                self._pos += 1

        raise TokenizerError("Unterminated string", start)

    def _read_number(self) -> Token:
        start = self._pos
        has_dot = False
        while self._pos < self._length:
            ch = self._source[self._pos]
            if ch == "." and not has_dot:
                has_dot = True
                self._pos += 1
            elif ch.isdigit():
                self._pos += 1
            else:
                break

        text = self._source[start:self._pos]
        value: int | float = float(text) if has_dot else int(text)
        return Token(TokenType.NUMBER, value, start)

    def _read_identifier(self) -> Token:
        start = self._pos
        while self._pos < self._length and (
            self._source[self._pos].isalnum() or self._source[self._pos] == "_"
        ):
            self._pos += 1

        text = self._source[start:self._pos]
        if text in KEYWORDS:
            tt, val = KEYWORDS[text]
            return Token(tt, val, start)
        return Token(TokenType.IDENTIFIER, text, start)


# ── AST Nodes ────────────────────────────────────────────


@dataclass
class Literal:
    value: Any
    depth: int = 0


@dataclass
class Variable:
    """$vars.x, $nodes.id.output.y, $loop.index, $input.z"""
    scope: str  # "vars", "nodes", "loop", "input"
    path: list[str] = field(default_factory=list)
    depth: int = 0


@dataclass
class BinaryOp:
    op: str
    left: Any
    right: Any
    depth: int = 0


@dataclass
class UnaryOp:
    op: str
    operand: Any
    depth: int = 0


@dataclass
class FunctionCall:
    name: str
    args: list[Any] = field(default_factory=list)
    depth: int = 0


@dataclass
class ArrayAccess:
    target: Any
    index: Any
    depth: int = 0


# ── Parser ───────────────────────────────────────────────


class ParseError(Exception):
    def __init__(self, message: str, position: int | None = None):
        self.position = position
        super().__init__(f"Parse error at position {position}: {message}")


class Parser:
    def __init__(self, tokens: list[Token]):
        self._tokens = tokens
        self._pos = 0
        self._depth = 0

    def parse(self) -> Any:
        result = self._parse_or()
        if self._current().type != TokenType.EOF:
            raise ParseError(
                f"Unexpected token {self._current().type.name}",
                self._current().position,
            )
        return result

    def _current(self) -> Token:
        return self._tokens[self._pos] if self._pos < len(self._tokens) else self._tokens[-1]

    def _advance(self) -> Token:
        token = self._current()
        self._pos += 1
        return token

    def _expect(self, tt: TokenType) -> Token:
        token = self._current()
        if token.type != tt:
            raise ParseError(
                f"Expected {tt.name}, got {token.type.name}", token.position
            )
        return self._advance()

    def _check_depth(self) -> None:
        self._depth += 1
        if self._depth > MAX_AST_DEPTH:
            raise ParseError("Expression too deeply nested", self._current().position)

    def _parse_or(self) -> Any:
        self._check_depth()
        left = self._parse_and()
        while self._current().type == TokenType.OR:
            self._advance()
            right = self._parse_and()
            left = BinaryOp("||", left, right, self._depth)
        self._depth -= 1
        return left

    def _parse_and(self) -> Any:
        self._check_depth()
        left = self._parse_not()
        while self._current().type == TokenType.AND:
            self._advance()
            right = self._parse_not()
            left = BinaryOp("&&", left, right, self._depth)
        self._depth -= 1
        return left

    def _parse_not(self) -> Any:
        self._check_depth()
        if self._current().type == TokenType.NOT:
            self._advance()
            operand = self._parse_not()
            self._depth -= 1
            return UnaryOp("!", operand, self._depth)
        result = self._parse_comparison()
        self._depth -= 1
        return result

    def _parse_comparison(self) -> Any:
        self._check_depth()
        left = self._parse_addition()
        comp_ops = {
            TokenType.EQ, TokenType.NE, TokenType.LT,
            TokenType.GT, TokenType.LE, TokenType.GE,
        }
        while self._current().type in comp_ops:
            op_token = self._advance()
            right = self._parse_addition()
            left = BinaryOp(op_token.value, left, right, self._depth)
        self._depth -= 1
        return left

    def _parse_addition(self) -> Any:
        self._check_depth()
        left = self._parse_multiplication()
        while self._current().type in (TokenType.PLUS, TokenType.MINUS):
            op_token = self._advance()
            right = self._parse_multiplication()
            left = BinaryOp(op_token.value, left, right, self._depth)
        self._depth -= 1
        return left

    def _parse_multiplication(self) -> Any:
        self._check_depth()
        left = self._parse_unary()
        while self._current().type in (TokenType.STAR, TokenType.SLASH, TokenType.PERCENT):
            op_token = self._advance()
            right = self._parse_unary()
            left = BinaryOp(op_token.value, left, right, self._depth)
        self._depth -= 1
        return left

    def _parse_unary(self) -> Any:
        self._check_depth()
        if self._current().type == TokenType.MINUS:
            self._advance()
            operand = self._parse_unary()
            self._depth -= 1
            return UnaryOp("-", operand, self._depth)
        result = self._parse_postfix()
        self._depth -= 1
        return result

    def _parse_postfix(self) -> Any:
        """Parse primary then handle [] array access."""
        self._check_depth()
        node = self._parse_primary()
        while self._current().type == TokenType.LBRACKET:
            self._advance()
            index = self._parse_or()
            self._expect(TokenType.RBRACKET)
            node = ArrayAccess(node, index, self._depth)
        self._depth -= 1
        return node

    def _parse_primary(self) -> Any:
        self._check_depth()
        token = self._current()

        if token.type == TokenType.NUMBER:
            self._advance()
            self._depth -= 1
            return Literal(token.value, self._depth)

        if token.type == TokenType.STRING:
            self._advance()
            self._depth -= 1
            return Literal(token.value, self._depth)

        if token.type == TokenType.BOOLEAN:
            self._advance()
            self._depth -= 1
            return Literal(token.value, self._depth)

        if token.type == TokenType.NULL:
            self._advance()
            self._depth -= 1
            return Literal(None, self._depth)

        if token.type == TokenType.DOLLAR:
            result = self._parse_variable()
            self._depth -= 1
            return result

        if token.type == TokenType.IDENTIFIER:
            result = self._parse_identifier_or_function()
            self._depth -= 1
            return result

        if token.type == TokenType.LPAREN:
            self._advance()
            expr = self._parse_or()
            self._expect(TokenType.RPAREN)
            self._depth -= 1
            return expr

        raise ParseError(
            f"Unexpected token {token.type.name}", token.position
        )

    def _parse_variable(self) -> Variable:
        """Parse $scope.path.segments"""
        self._expect(TokenType.DOLLAR)
        scope_token = self._expect(TokenType.IDENTIFIER)
        scope = scope_token.value

        if scope in FORBIDDEN_NAMES:
            raise ParseError(f"Forbidden scope '{scope}'", scope_token.position)

        path: list[str] = []
        while self._current().type == TokenType.DOT:
            self._advance()
            seg = self._expect(TokenType.IDENTIFIER)
            path.append(seg.value)

        return Variable(scope, path, self._depth)

    def _parse_identifier_or_function(self) -> Any:
        name_token = self._advance()
        name = name_token.value

        if name in FORBIDDEN_NAMES:
            raise ParseError(f"Forbidden identifier '{name}'", name_token.position)

        if self._current().type == TokenType.LPAREN:
            self._advance()
            args: list[Any] = []
            if self._current().type != TokenType.RPAREN:
                args.append(self._parse_or())
                while self._current().type == TokenType.COMMA:
                    self._advance()
                    args.append(self._parse_or())
            self._expect(TokenType.RPAREN)
            return FunctionCall(name, args, self._depth)

        return Literal(name, self._depth)


# ── Evaluator ────────────────────────────────────────────


class EvaluationError(Exception):
    pass


class ExpressionContext:
    """Context for expression evaluation with variable scopes."""

    def __init__(
        self,
        variables: dict[str, Any] | None = None,
        nodes: dict[str, dict[str, Any]] | None = None,
        loop: dict[str, Any] | None = None,
        input_data: dict[str, Any] | None = None,
    ):
        self.variables = variables or {}
        self.nodes = nodes or {}
        self.loop = loop or {}
        self.input_data = input_data or {}

    def resolve_variable(self, var: Variable) -> Any:
        scope_map = {
            "vars": self.variables,
            "nodes": self.nodes,
            "loop": self.loop,
            "input": self.input_data,
        }

        data = scope_map.get(var.scope)
        if data is None:
            raise EvaluationError(f"Unknown scope '${var.scope}'")

        current: Any = data
        for segment in var.path:
            if isinstance(current, dict):
                if segment not in current:
                    raise EvaluationError(
                        f"Key '{segment}' not found in ${var.scope}.{'.'.join(var.path)}"
                    )
                current = current[segment]
            else:
                raise EvaluationError(
                    f"Cannot access '{segment}' on non-dict value"
                )
        return current


class Evaluator:
    """Safe AST evaluator with pluggable functions."""

    def __init__(self, functions: dict[str, Any] | None = None):
        self._functions = functions or {}

    def evaluate(self, node: Any, context: ExpressionContext) -> Any:
        if isinstance(node, Literal):
            return node.value
        if isinstance(node, Variable):
            return context.resolve_variable(node)
        if isinstance(node, BinaryOp):
            return self._eval_binary(node, context)
        if isinstance(node, UnaryOp):
            return self._eval_unary(node, context)
        if isinstance(node, FunctionCall):
            return self._eval_function(node, context)
        if isinstance(node, ArrayAccess):
            return self._eval_array_access(node, context)
        raise EvaluationError(f"Unknown AST node type: {type(node).__name__}")

    def _eval_binary(self, node: BinaryOp, ctx: ExpressionContext) -> Any:
        op = node.op

        # Short-circuit logical operators
        if op == "&&":
            left = self.evaluate(node.left, ctx)
            return self.evaluate(node.right, ctx) if left else left
        if op == "||":
            left = self.evaluate(node.left, ctx)
            return left if left else self.evaluate(node.right, ctx)

        left = self.evaluate(node.left, ctx)
        right = self.evaluate(node.right, ctx)

        if op == "+":
            if isinstance(left, str) or isinstance(right, str):
                return str(left) + str(right)
            return left + right
        if op == "-":
            return left - right
        if op == "*":
            return left * right
        if op == "/":
            if right == 0:
                raise EvaluationError("Division by zero")
            return left / right
        if op == "%":
            if right == 0:
                raise EvaluationError("Modulo by zero")
            return left % right
        if op == "==":
            return left == right
        if op == "!=":
            return left != right
        if op == "<":
            return left < right
        if op == ">":
            return left > right
        if op == "<=":
            return left <= right
        if op == ">=":
            return left >= right

        raise EvaluationError(f"Unknown operator '{op}'")

    def _eval_unary(self, node: UnaryOp, ctx: ExpressionContext) -> Any:
        val = self.evaluate(node.operand, ctx)
        if node.op == "!":
            return not val
        if node.op == "-":
            return -val
        raise EvaluationError(f"Unknown unary operator '{node.op}'")

    def _eval_function(self, node: FunctionCall, ctx: ExpressionContext) -> Any:
        if node.name not in self._functions:
            raise EvaluationError(f"Unknown function '{node.name}'")
        args = [self.evaluate(arg, ctx) for arg in node.args]
        return self._functions[node.name](*args)

    def _eval_array_access(self, node: ArrayAccess, ctx: ExpressionContext) -> Any:
        target = self.evaluate(node.target, ctx)
        index = self.evaluate(node.index, ctx)
        if isinstance(target, dict):
            if index not in target:
                raise EvaluationError(f"Key '{index}' not found")
            return target[index]
        if isinstance(target, (list, tuple)):
            if not isinstance(index, int):
                raise EvaluationError(f"List index must be integer, got {type(index).__name__}")
            if index < 0 or index >= len(target):
                raise EvaluationError(f"Index {index} out of range")
            return target[index]
        raise EvaluationError(f"Cannot index into {type(target).__name__}")


# ── String Interpolation ─────────────────────────────────

_INTERPOLATION_RE = re.compile(r"\$\{([^}]+)\}")


def interpolate_string(
    template: str,
    context: ExpressionContext,
    functions: dict[str, Any] | None = None,
) -> str:
    """Resolve ${expression} placeholders in a template string."""

    def _replace(match: re.Match) -> str:
        expr = match.group(1)
        result = evaluate_expression(expr, context, functions)
        return str(result) if result is not None else ""

    return _INTERPOLATION_RE.sub(_replace, template)


# ── Public API ───────────────────────────────────────────


def evaluate_expression(
    source: str,
    context: ExpressionContext | None = None,
    functions: dict[str, Any] | None = None,
) -> Any:
    """Tokenize, parse, and evaluate an expression string."""
    if context is None:
        context = ExpressionContext()
    tokens = Tokenizer(source).tokenize()
    ast = Parser(tokens).parse()
    evaluator = Evaluator(functions)
    return evaluator.evaluate(ast, context)


def validate_expression(
    source: str,
    functions: dict[str, Any] | None = None,
) -> list[str]:
    """Validate expression syntax without evaluating. Returns list of errors."""
    errors: list[str] = []
    try:
        tokens = Tokenizer(source).tokenize()
        Parser(tokens).parse()
    except (TokenizerError, ParseError) as e:
        errors.append(str(e))
    return errors
