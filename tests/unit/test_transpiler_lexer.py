"""Tests for transpiler/lexer.py — tokenization."""

import pytest

from strudel_gen.transpiler.lexer import Token, tokenize


class TestTokenize:
    def test_empty_source(self) -> None:
        assert tokenize("") == []

    def test_whitespace_skipped(self) -> None:
        assert tokenize("   \n\t  ") == []

    def test_line_comment_skipped(self) -> None:
        assert tokenize("// this is a comment\n") == []

    def test_block_comment_skipped(self) -> None:
        assert tokenize("/* comment */") == []

    def test_number_token(self) -> None:
        tokens = tokenize("42")
        assert tokens == [Token(kind="NUMBER", value="42")]

    def test_float_token(self) -> None:
        tokens = tokenize("0.85")
        assert tokens == [Token(kind="NUMBER", value="0.85")]

    def test_string_token(self) -> None:
        tokens = tokenize('"c2 g2"')
        assert len(tokens) == 1
        assert tokens[0].kind == "STRING"

    def test_ident_and_parens(self) -> None:
        tokens = tokenize("setcpm(20)")
        kinds = [t.kind for t in tokens]
        assert kinds == ["IDENT", "LPAREN", "NUMBER", "RPAREN"]

    def test_dot_and_comma(self) -> None:
        tokens = tokenize(".slow(4),")
        kinds = [t.kind for t in tokens]
        assert kinds == ["DOT", "IDENT", "LPAREN", "NUMBER", "RPAREN", "COMMA"]

    def test_arrow_token(self) -> None:
        tokens = tokenize("x => x.rev()")
        kinds = [t.kind for t in tokens]
        assert "ARROW" in kinds

    def test_unexpected_char_raises(self) -> None:
        with pytest.raises(SyntaxError, match="unexpected char"):
            tokenize("@bad")

    def test_single_quoted_string(self) -> None:
        tokens = tokenize("'hello'")
        assert len(tokens) == 1
        assert tokens[0].kind == "STRING"

    def test_backtick_string(self) -> None:
        tokens = tokenize("`c2 g2`")
        assert len(tokens) == 1
        assert tokens[0].kind == "STRING"
        assert tokens[0].value == "`c2 g2`"

    def test_backtick_multi_line_string(self) -> None:
        tokens = tokenize("`c2\n g2`")
        assert len(tokens) == 1
        assert tokens[0].kind == "STRING"

    def test_arithmetic_operators(self) -> None:
        tokens = tokenize("135/4")
        kinds = [t.kind for t in tokens]
        assert kinds == ["NUMBER", "SLASH", "NUMBER"]

    def test_plus_operator(self) -> None:
        tokens = tokenize("1+2")
        kinds = [t.kind for t in tokens]
        assert kinds == ["NUMBER", "PLUS", "NUMBER"]

    def test_star_operator(self) -> None:
        tokens = tokenize("2*3")
        kinds = [t.kind for t in tokens]
        assert kinds == ["NUMBER", "STAR", "NUMBER"]

    def test_assign_and_semicolon(self) -> None:
        tokens = tokenize("let x = 42;")
        kinds = [t.kind for t in tokens]
        assert kinds == ["IDENT", "IDENT", "ASSIGN", "NUMBER", "SEMICOLON"]

    def test_brackets(self) -> None:
        tokens = tokenize("[4, a]")
        kinds = [t.kind for t in tokens]
        assert kinds == ["LBRACKET", "NUMBER", "COMMA", "IDENT", "RBRACKET"]

    def test_braces(self) -> None:
        tokens = tokenize("{}")
        kinds = [t.kind for t in tokens]
        assert kinds == ["LBRACE", "RBRACE"]

    def test_colon(self) -> None:
        assert tokenize("a:b")[0].kind == "IDENT"
        assert tokenize("a:b")[1].kind == "COLON"
        assert tokenize("a:b")[2].kind == "IDENT"

    def test_negative_number(self) -> None:
        tokens = tokenize("-3")
        kinds = [t.kind for t in tokens]
        assert kinds == ["NUMBER"]
