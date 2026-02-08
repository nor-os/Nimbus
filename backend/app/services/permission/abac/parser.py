"""
Overview: Recursive descent parser for ABAC DSL expressions.
Architecture: AST construction from token stream (Section 5.2)
Dependencies: app.services.permission.abac.tokenizer
Concepts: ABAC, recursive descent parsing, AST, expression precedence
"""

from dataclasses import dataclass, field

from app.services.permission.abac.tokenizer import Token, TokenType


# ── AST Nodes ────────────────────────────────────────────────────────


@dataclass
class ASTNode:
    pass


@dataclass
class Literal(ASTNode):
    value: object


@dataclass
class ListLiteral(ASTNode):
    items: list[ASTNode] = field(default_factory=list)


@dataclass
class Attribute(ASTNode):
    parts: list[str] = field(default_factory=list)

    @property
    def path(self) -> str:
        return ".".join(self.parts)


@dataclass
class BinaryOp(ASTNode):
    op: str
    left: ASTNode = None
    right: ASTNode = None


@dataclass
class UnaryOp(ASTNode):
    op: str
    operand: ASTNode = None


@dataclass
class MethodCall(ASTNode):
    obj: ASTNode = None
    method: str = ""
    args: list[ASTNode] = field(default_factory=list)


# ── Parser ───────────────────────────────────────────────────────────


class ParseError(Exception):
    def __init__(self, message: str, position: int = 0):
        self.position = position
        super().__init__(f"{message} at position {position}")


class Parser:
    """Recursive descent parser for ABAC DSL.

    Precedence (low to high): OR > AND > NOT > comparison > primary
    """

    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.pos = 0

    def parse(self) -> ASTNode:
        """Parse the full expression and return the AST root."""
        node = self._parse_or()
        if self._current().type != TokenType.EOF:
            raise ParseError(
                f"Unexpected token: {self._current().value}", self._current().position
            )
        return node

    def _current(self) -> Token:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else self.tokens[-1]

    def _advance(self) -> Token:
        token = self._current()
        self.pos += 1
        return token

    def _expect(self, token_type: TokenType) -> Token:
        token = self._current()
        if token.type != token_type:
            raise ParseError(
                f"Expected {token_type.value}, got {token.type.value}", token.position
            )
        return self._advance()

    # ── Precedence levels ────────────────────────────────────────────

    def _parse_or(self) -> ASTNode:
        left = self._parse_and()
        while self._current().type == TokenType.OR:
            self._advance()
            right = self._parse_and()
            left = BinaryOp(op="or", left=left, right=right)
        return left

    def _parse_and(self) -> ASTNode:
        left = self._parse_not()
        while self._current().type == TokenType.AND:
            self._advance()
            right = self._parse_not()
            left = BinaryOp(op="and", left=left, right=right)
        return left

    def _parse_not(self) -> ASTNode:
        if self._current().type == TokenType.NOT:
            self._advance()
            operand = self._parse_not()
            return UnaryOp(op="not", operand=operand)
        return self._parse_comparison()

    def _parse_comparison(self) -> ASTNode:
        left = self._parse_primary()

        comparison_ops = {
            TokenType.EQ: "==",
            TokenType.NE: "!=",
            TokenType.LT: "<",
            TokenType.GT: ">",
            TokenType.LE: "<=",
            TokenType.GE: ">=",
            TokenType.IN: "in",
            TokenType.CONTAINS: "contains",
        }

        if self._current().type in comparison_ops:
            op_token = self._advance()
            op = comparison_ops[op_token.type]
            right = self._parse_primary()
            return BinaryOp(op=op, left=left, right=right)

        return left

    def _parse_primary(self) -> ASTNode:
        token = self._current()

        if token.type == TokenType.NUMBER:
            self._advance()
            return Literal(value=token.value)

        if token.type == TokenType.STRING:
            self._advance()
            return Literal(value=token.value)

        if token.type == TokenType.BOOLEAN:
            self._advance()
            return Literal(value=token.value)

        if token.type == TokenType.LPAREN:
            self._advance()
            node = self._parse_or()
            self._expect(TokenType.RPAREN)
            return node

        if token.type == TokenType.LBRACKET:
            return self._parse_list()

        if token.type == TokenType.IDENTIFIER:
            return self._parse_attribute_or_method()

        raise ParseError(f"Unexpected token: {token.value}", token.position)

    def _parse_attribute_or_method(self) -> ASTNode:
        """Parse an attribute path (a.b.c) or method call (a.b.method(args))."""
        parts = [self._advance().value]

        while self._current().type == TokenType.DOT:
            self._advance()
            parts.append(self._expect(TokenType.IDENTIFIER).value)

        # Check for method call: last part followed by '('
        if self._current().type == TokenType.LPAREN:
            method_name = parts.pop()
            obj = Attribute(parts=parts) if parts else None
            self._advance()  # consume '('

            args = []
            if self._current().type != TokenType.RPAREN:
                args.append(self._parse_or())
                while self._current().type == TokenType.COMMA:
                    self._advance()
                    args.append(self._parse_or())

            self._expect(TokenType.RPAREN)
            return MethodCall(obj=obj, method=method_name, args=args)

        return Attribute(parts=parts)

    def _parse_list(self) -> ASTNode:
        """Parse a list literal [a, b, c]."""
        self._advance()  # consume '['
        items = []
        if self._current().type != TokenType.RBRACKET:
            items.append(self._parse_or())
            while self._current().type == TokenType.COMMA:
                self._advance()
                items.append(self._parse_or())
        self._expect(TokenType.RBRACKET)
        return ListLiteral(items=items)
