"""
Overview: Tokenizer for ABAC DSL expressions.
Architecture: Lexical analysis for ABAC expression engine (Section 5.2)
Dependencies: None (pure Python)
Concepts: ABAC, DSL tokenizer, lexical analysis
"""

import enum
import re
from dataclasses import dataclass


class TokenType(enum.Enum):
    NUMBER = "NUMBER"
    STRING = "STRING"
    BOOLEAN = "BOOLEAN"
    IDENTIFIER = "IDENTIFIER"
    DOT = "DOT"
    EQ = "EQ"
    NE = "NE"
    LT = "LT"
    GT = "GT"
    LE = "LE"
    GE = "GE"
    IN = "IN"
    AND = "AND"
    OR = "OR"
    NOT = "NOT"
    LPAREN = "LPAREN"
    RPAREN = "RPAREN"
    LBRACKET = "LBRACKET"
    RBRACKET = "RBRACKET"
    COMMA = "COMMA"
    CONTAINS = "CONTAINS"
    EOF = "EOF"


@dataclass
class Token:
    type: TokenType
    value: object
    position: int


class TokenizerError(Exception):
    def __init__(self, message: str, position: int):
        self.position = position
        super().__init__(f"{message} at position {position}")


class Tokenizer:
    KEYWORDS = {
        "and": TokenType.AND,
        "or": TokenType.OR,
        "not": TokenType.NOT,
        "in": TokenType.IN,
        "true": TokenType.BOOLEAN,
        "false": TokenType.BOOLEAN,
        "contains": TokenType.CONTAINS,
    }

    def __init__(self, source: str):
        self.source = source
        self.pos = 0
        self.tokens: list[Token] = []

    def tokenize(self) -> list[Token]:
        """Tokenize the full source expression."""
        self.tokens = []
        while self.pos < len(self.source):
            self._skip_whitespace()
            if self.pos >= len(self.source):
                break

            ch = self.source[self.pos]

            if ch == "(":
                self.tokens.append(Token(TokenType.LPAREN, "(", self.pos))
                self.pos += 1
            elif ch == ")":
                self.tokens.append(Token(TokenType.RPAREN, ")", self.pos))
                self.pos += 1
            elif ch == "[":
                self.tokens.append(Token(TokenType.LBRACKET, "[", self.pos))
                self.pos += 1
            elif ch == "]":
                self.tokens.append(Token(TokenType.RBRACKET, "]", self.pos))
                self.pos += 1
            elif ch == ",":
                self.tokens.append(Token(TokenType.COMMA, ",", self.pos))
                self.pos += 1
            elif ch == ".":
                self.tokens.append(Token(TokenType.DOT, ".", self.pos))
                self.pos += 1
            elif ch == "=" and self._peek(1) == "=":
                self.tokens.append(Token(TokenType.EQ, "==", self.pos))
                self.pos += 2
            elif ch == "!" and self._peek(1) == "=":
                self.tokens.append(Token(TokenType.NE, "!=", self.pos))
                self.pos += 2
            elif ch == "<" and self._peek(1) == "=":
                self.tokens.append(Token(TokenType.LE, "<=", self.pos))
                self.pos += 2
            elif ch == ">" and self._peek(1) == "=":
                self.tokens.append(Token(TokenType.GE, ">=", self.pos))
                self.pos += 2
            elif ch == "<":
                self.tokens.append(Token(TokenType.LT, "<", self.pos))
                self.pos += 1
            elif ch == ">":
                self.tokens.append(Token(TokenType.GT, ">", self.pos))
                self.pos += 1
            elif ch == '"' or ch == "'":
                self._read_string(ch)
            elif ch.isdigit() or (ch == "-" and self._peek(1) and self._peek(1).isdigit()):
                self._read_number()
            elif ch.isalpha() or ch == "_":
                self._read_identifier()
            else:
                raise TokenizerError(f"Unexpected character: {ch}", self.pos)

        self.tokens.append(Token(TokenType.EOF, None, self.pos))
        return self.tokens

    def _skip_whitespace(self) -> None:
        while self.pos < len(self.source) and self.source[self.pos] in " \t\r\n":
            self.pos += 1

    def _peek(self, offset: int = 1) -> str | None:
        pos = self.pos + offset
        return self.source[pos] if pos < len(self.source) else None

    def _read_string(self, quote: str) -> None:
        start = self.pos
        self.pos += 1  # skip opening quote
        value = ""
        while self.pos < len(self.source) and self.source[self.pos] != quote:
            if self.source[self.pos] == "\\":
                self.pos += 1
                if self.pos < len(self.source):
                    value += self.source[self.pos]
            else:
                value += self.source[self.pos]
            self.pos += 1

        if self.pos >= len(self.source):
            raise TokenizerError("Unterminated string", start)

        self.pos += 1  # skip closing quote
        self.tokens.append(Token(TokenType.STRING, value, start))

    def _read_number(self) -> None:
        start = self.pos
        if self.source[self.pos] == "-":
            self.pos += 1
        while self.pos < len(self.source) and self.source[self.pos].isdigit():
            self.pos += 1
        if self.pos < len(self.source) and self.source[self.pos] == ".":
            self.pos += 1
            while self.pos < len(self.source) and self.source[self.pos].isdigit():
                self.pos += 1
            self.tokens.append(Token(TokenType.NUMBER, float(self.source[start:self.pos]), start))
        else:
            self.tokens.append(Token(TokenType.NUMBER, int(self.source[start:self.pos]), start))

    def _read_identifier(self) -> None:
        start = self.pos
        while self.pos < len(self.source) and (
            self.source[self.pos].isalnum() or self.source[self.pos] == "_"
        ):
            self.pos += 1

        word = self.source[start:self.pos]
        lower = word.lower()

        if lower in self.KEYWORDS:
            token_type = self.KEYWORDS[lower]
            if token_type == TokenType.BOOLEAN:
                self.tokens.append(Token(TokenType.BOOLEAN, lower == "true", start))
            else:
                self.tokens.append(Token(token_type, lower, start))
        else:
            self.tokens.append(Token(TokenType.IDENTIFIER, word, start))
