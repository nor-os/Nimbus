"""
Overview: Tests for the workflow expression engine — tokenizer, parser, evaluator.
Architecture: Unit tests for expression engine (Section 5)
Dependencies: pytest, app.services.workflow.expression_engine
Concepts: Tokenizer, parser, AST evaluation, variable resolution, safety, string interpolation
"""

import pytest

from app.services.workflow.expression_engine import (
    EvaluationError,
    ExpressionContext,
    Evaluator,
    Literal,
    ParseError,
    Parser,
    Tokenizer,
    TokenizerError,
    Variable,
    evaluate_expression,
    interpolate_string,
    validate_expression,
)
from app.services.workflow.expression_functions import BUILTIN_FUNCTIONS


# ── Tokenizer Tests ──────────────────────────────────────


class TestTokenizer:
    def test_number_integer(self):
        tokens = Tokenizer("42").tokenize()
        assert tokens[0].value == 42

    def test_number_float(self):
        tokens = Tokenizer("3.14").tokenize()
        assert tokens[0].value == 3.14

    def test_string_single_quote(self):
        tokens = Tokenizer("'hello'").tokenize()
        assert tokens[0].value == "hello"

    def test_string_double_quote(self):
        tokens = Tokenizer('"world"').tokenize()
        assert tokens[0].value == "world"

    def test_string_escape_sequences(self):
        tokens = Tokenizer(r"'hello\nworld'").tokenize()
        assert tokens[0].value == "hello\nworld"

    def test_boolean_true(self):
        tokens = Tokenizer("true").tokenize()
        assert tokens[0].value is True

    def test_boolean_false(self):
        tokens = Tokenizer("false").tokenize()
        assert tokens[0].value is False

    def test_null(self):
        tokens = Tokenizer("null").tokenize()
        assert tokens[0].value is None

    def test_operators(self):
        tokens = Tokenizer("== != < > <= >= && || !").tokenize()
        values = [t.value for t in tokens[:-1]]  # exclude EOF
        assert values == ["==", "!=", "<", ">", "<=", ">=", "&&", "||", "!"]

    def test_arithmetic_operators(self):
        tokens = Tokenizer("+ - * / %").tokenize()
        values = [t.value for t in tokens[:-1]]
        assert values == ["+", "-", "*", "/", "%"]

    def test_dollar_variable(self):
        tokens = Tokenizer("$vars.foo").tokenize()
        assert tokens[0].value == "$"
        assert tokens[1].value == "vars"
        assert tokens[2].value == "."
        assert tokens[3].value == "foo"

    def test_unterminated_string(self):
        with pytest.raises(TokenizerError):
            Tokenizer("'unterminated").tokenize()

    def test_unexpected_character(self):
        with pytest.raises(TokenizerError):
            Tokenizer("@").tokenize()

    def test_keyword_and_or_not(self):
        tokens = Tokenizer("and or not").tokenize()
        assert tokens[0].value == "&&"
        assert tokens[1].value == "||"
        assert tokens[2].value == "!"


# ── Parser Tests ─────────────────────────────────────────


class TestParser:
    def _parse(self, source: str):
        tokens = Tokenizer(source).tokenize()
        return Parser(tokens).parse()

    def test_literal_number(self):
        ast = self._parse("42")
        assert isinstance(ast, Literal)
        assert ast.value == 42

    def test_literal_string(self):
        ast = self._parse("'hello'")
        assert isinstance(ast, Literal)
        assert ast.value == "hello"

    def test_variable(self):
        ast = self._parse("$vars.name")
        assert isinstance(ast, Variable)
        assert ast.scope == "vars"
        assert ast.path == ["name"]

    def test_nested_variable(self):
        ast = self._parse("$nodes.myNode.output.result")
        assert isinstance(ast, Variable)
        assert ast.scope == "nodes"
        assert ast.path == ["myNode", "output", "result"]

    def test_binary_op(self):
        ast = self._parse("1 + 2")
        assert ast.op == "+"
        assert ast.left.value == 1
        assert ast.right.value == 2

    def test_comparison(self):
        ast = self._parse("$vars.x > 10")
        assert ast.op == ">"

    def test_logical_and(self):
        ast = self._parse("true && false")
        assert ast.op == "&&"

    def test_logical_or(self):
        ast = self._parse("true || false")
        assert ast.op == "||"

    def test_unary_not(self):
        ast = self._parse("!true")
        assert ast.op == "!"
        assert ast.operand.value is True

    def test_unary_negation(self):
        ast = self._parse("-42")
        assert ast.op == "-"
        assert ast.operand.value == 42

    def test_function_call(self):
        ast = self._parse("len('hello')")
        assert ast.name == "len"
        assert len(ast.args) == 1
        assert ast.args[0].value == "hello"

    def test_function_call_multiple_args(self):
        ast = self._parse("contains('hello world', 'hello')")
        assert ast.name == "contains"
        assert len(ast.args) == 2

    def test_parenthesized_expression(self):
        ast = self._parse("(1 + 2) * 3")
        assert ast.op == "*"
        assert ast.left.op == "+"

    def test_operator_precedence(self):
        ast = self._parse("1 + 2 * 3")
        assert ast.op == "+"
        assert ast.right.op == "*"

    def test_forbidden_identifier(self):
        with pytest.raises(ParseError, match="Forbidden"):
            self._parse("import()")

    def test_forbidden_scope(self):
        with pytest.raises(ParseError, match="Forbidden"):
            self._parse("$eval.code")

    def test_unexpected_token(self):
        with pytest.raises(ParseError):
            self._parse("1 +")

    def test_ast_depth_limit(self):
        # Create deeply nested expression
        deep = "(" * 60 + "1" + ")" * 60
        with pytest.raises(ParseError, match="deeply nested"):
            self._parse(deep)


# ── Evaluator Tests ──────────────────────────────────────


class TestEvaluator:
    def test_literal(self):
        assert evaluate_expression("42") == 42

    def test_string_literal(self):
        assert evaluate_expression("'hello'") == "hello"

    def test_boolean_literal(self):
        assert evaluate_expression("true") is True
        assert evaluate_expression("false") is False

    def test_null_literal(self):
        assert evaluate_expression("null") is None

    def test_addition(self):
        assert evaluate_expression("2 + 3") == 5

    def test_subtraction(self):
        assert evaluate_expression("10 - 4") == 6

    def test_multiplication(self):
        assert evaluate_expression("3 * 7") == 21

    def test_division(self):
        assert evaluate_expression("10 / 4") == 2.5

    def test_modulo(self):
        assert evaluate_expression("10 % 3") == 1

    def test_division_by_zero(self):
        with pytest.raises(EvaluationError, match="Division by zero"):
            evaluate_expression("10 / 0")

    def test_modulo_by_zero(self):
        with pytest.raises(EvaluationError, match="Modulo by zero"):
            evaluate_expression("10 % 0")

    def test_string_concatenation(self):
        assert evaluate_expression("'hello' + ' ' + 'world'") == "hello world"

    def test_string_number_concatenation(self):
        assert evaluate_expression("'count: ' + 42") == "count: 42"

    def test_comparison_equal(self):
        assert evaluate_expression("1 == 1") is True
        assert evaluate_expression("1 == 2") is False

    def test_comparison_not_equal(self):
        assert evaluate_expression("1 != 2") is True

    def test_comparison_less_than(self):
        assert evaluate_expression("1 < 2") is True
        assert evaluate_expression("2 < 1") is False

    def test_comparison_greater_than(self):
        assert evaluate_expression("2 > 1") is True

    def test_comparison_less_equal(self):
        assert evaluate_expression("1 <= 1") is True
        assert evaluate_expression("1 <= 2") is True

    def test_comparison_greater_equal(self):
        assert evaluate_expression("2 >= 2") is True

    def test_logical_and_short_circuit(self):
        assert evaluate_expression("false && true") is False
        assert evaluate_expression("true && true") is True

    def test_logical_or_short_circuit(self):
        assert evaluate_expression("true || false") is True
        assert evaluate_expression("false || false") is False

    def test_logical_not(self):
        assert evaluate_expression("!true") is False
        assert evaluate_expression("!false") is True

    def test_negation(self):
        assert evaluate_expression("-5") == -5

    def test_complex_expression(self):
        assert evaluate_expression("(2 + 3) * 4 - 1") == 19


class TestVariableResolution:
    def test_vars_scope(self):
        ctx = ExpressionContext(variables={"name": "Alice"})
        assert evaluate_expression("$vars.name", ctx) == "Alice"

    def test_nodes_scope(self):
        ctx = ExpressionContext(nodes={"node1": {"output": {"result": 42}}})
        assert evaluate_expression("$nodes.node1.output.result", ctx) == 42

    def test_loop_scope(self):
        ctx = ExpressionContext(loop={"index": 3, "item": "hello"})
        assert evaluate_expression("$loop.index", ctx) == 3
        assert evaluate_expression("$loop.item", ctx) == "hello"

    def test_input_scope(self):
        ctx = ExpressionContext(input_data={"server_name": "prod-1"})
        assert evaluate_expression("$input.server_name", ctx) == "prod-1"

    def test_unknown_scope(self):
        ctx = ExpressionContext()
        with pytest.raises(EvaluationError, match="Unknown scope"):
            evaluate_expression("$unknown.field", ctx)

    def test_missing_key(self):
        ctx = ExpressionContext(variables={})
        with pytest.raises(EvaluationError, match="not found"):
            evaluate_expression("$vars.missing", ctx)

    def test_nested_variable_in_expression(self):
        ctx = ExpressionContext(
            variables={"x": 10},
            input_data={"threshold": 5},
        )
        assert evaluate_expression("$vars.x > $input.threshold", ctx) is True


# ── Built-in Functions Tests ─────────────────────────────


class TestBuiltinFunctions:
    def test_len_string(self):
        assert evaluate_expression("len('hello')", functions=BUILTIN_FUNCTIONS) == 5

    def test_len_invalid(self):
        with pytest.raises(Exception):
            evaluate_expression("len(42)", functions=BUILTIN_FUNCTIONS)

    def test_contains_string(self):
        result = evaluate_expression(
            "contains('hello world', 'world')", functions=BUILTIN_FUNCTIONS
        )
        assert result is True

    def test_contains_not_found(self):
        result = evaluate_expression(
            "contains('hello', 'xyz')", functions=BUILTIN_FUNCTIONS
        )
        assert result is False

    def test_starts_with(self):
        result = evaluate_expression(
            "startsWith('hello', 'hel')", functions=BUILTIN_FUNCTIONS
        )
        assert result is True

    def test_ends_with(self):
        result = evaluate_expression(
            "endsWith('hello', 'llo')", functions=BUILTIN_FUNCTIONS
        )
        assert result is True

    def test_lower(self):
        assert evaluate_expression("lower('HELLO')", functions=BUILTIN_FUNCTIONS) == "hello"

    def test_upper(self):
        assert evaluate_expression("upper('hello')", functions=BUILTIN_FUNCTIONS) == "HELLO"

    def test_trim(self):
        assert evaluate_expression("trim('  hello  ')", functions=BUILTIN_FUNCTIONS) == "hello"

    def test_parse_int(self):
        assert evaluate_expression("parseInt('42')", functions=BUILTIN_FUNCTIONS) == 42

    def test_parse_float(self):
        assert evaluate_expression("parseFloat('3.14')", functions=BUILTIN_FUNCTIONS) == 3.14

    def test_coalesce(self):
        result = evaluate_expression("coalesce(null, null, 'found')", functions=BUILTIN_FUNCTIONS)
        assert result == "found"

    def test_coalesce_first_non_null(self):
        result = evaluate_expression("coalesce('first', 'second')", functions=BUILTIN_FUNCTIONS)
        assert result == "first"

    def test_type_of(self):
        assert evaluate_expression("typeOf(42)", functions=BUILTIN_FUNCTIONS) == "integer"
        assert evaluate_expression("typeOf('hello')", functions=BUILTIN_FUNCTIONS) == "string"
        assert evaluate_expression("typeOf(true)", functions=BUILTIN_FUNCTIONS) == "boolean"
        assert evaluate_expression("typeOf(null)", functions=BUILTIN_FUNCTIONS) == "null"
        assert evaluate_expression("typeOf(3.14)", functions=BUILTIN_FUNCTIONS) == "float"

    def test_unknown_function(self):
        with pytest.raises(EvaluationError, match="Unknown function"):
            evaluate_expression("unknown()")

    def test_now_returns_string(self):
        result = evaluate_expression("now()", functions=BUILTIN_FUNCTIONS)
        assert isinstance(result, str)
        assert "T" in result  # ISO format

    def test_to_json(self):
        result = evaluate_expression("toJson(42)", functions=BUILTIN_FUNCTIONS)
        assert result == "42"

    def test_abs(self):
        assert evaluate_expression("abs(-5)", functions=BUILTIN_FUNCTIONS) == 5

    def test_min_max(self):
        assert evaluate_expression("min(3, 1, 2)", functions=BUILTIN_FUNCTIONS) == 1
        assert evaluate_expression("max(3, 1, 2)", functions=BUILTIN_FUNCTIONS) == 3


# ── String Interpolation Tests ───────────────────────────


class TestStringInterpolation:
    def test_simple_interpolation(self):
        ctx = ExpressionContext(variables={"name": "Alice"})
        result = interpolate_string("Hello, ${$vars.name}!", ctx)
        assert result == "Hello, Alice!"

    def test_expression_interpolation(self):
        ctx = ExpressionContext(variables={"x": 5})
        result = interpolate_string("Result: ${$vars.x + 10}", ctx)
        assert result == "Result: 15"

    def test_no_interpolation(self):
        result = interpolate_string("plain text", ExpressionContext())
        assert result == "plain text"

    def test_multiple_interpolations(self):
        ctx = ExpressionContext(variables={"a": "X", "b": "Y"})
        result = interpolate_string("${$vars.a} and ${$vars.b}", ctx)
        assert result == "X and Y"

    def test_null_renders_empty(self):
        ctx = ExpressionContext(variables={"x": None})
        result = interpolate_string("val=${$vars.x}", ctx)
        assert result == "val="


# ── Validation Tests ─────────────────────────────────────


class TestValidation:
    def test_valid_expression(self):
        errors = validate_expression("1 + 2")
        assert errors == []

    def test_invalid_expression(self):
        errors = validate_expression("1 +")
        assert len(errors) > 0

    def test_unterminated_string_validation(self):
        errors = validate_expression("'unterminated")
        assert len(errors) > 0

    def test_valid_variable(self):
        errors = validate_expression("$vars.x > 5")
        assert errors == []

    def test_valid_function_call(self):
        errors = validate_expression("len('hello')", BUILTIN_FUNCTIONS)
        assert errors == []


# ── Safety Tests ─────────────────────────────────────────


class TestSafety:
    def test_reject_import(self):
        with pytest.raises(ParseError, match="Forbidden"):
            evaluate_expression("import('os')")

    def test_reject_exec(self):
        with pytest.raises(ParseError, match="Forbidden"):
            evaluate_expression("exec('code')")

    def test_reject_eval(self):
        with pytest.raises(ParseError, match="Forbidden"):
            evaluate_expression("eval('code')")

    def test_reject_compile(self):
        with pytest.raises(ParseError, match="Forbidden"):
            evaluate_expression("compile('code')")

    def test_reject___import__(self):
        with pytest.raises(ParseError, match="Forbidden"):
            evaluate_expression("__import__('os')")

    def test_reject_getattr(self):
        with pytest.raises(ParseError, match="Forbidden"):
            evaluate_expression("getattr(null, 'x')")

    def test_reject___builtins__(self):
        with pytest.raises(ParseError, match="Forbidden"):
            evaluate_expression("$__builtins__.open")

    def test_array_access_out_of_range(self):
        ctx = ExpressionContext(variables={"items": [1, 2, 3]})
        with pytest.raises(EvaluationError, match="out of range"):
            evaluate_expression("$vars.items[10]", ctx)

    def test_array_access_negative_index(self):
        ctx = ExpressionContext(variables={"items": [1, 2, 3]})
        with pytest.raises(EvaluationError, match="out of range"):
            evaluate_expression("$vars.items[-1]", ctx)
