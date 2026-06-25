"""Tokenize Strudel source into a flat stream."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class Token:
    kind: str
    value: str


_TOKEN_RE = re.compile(
    r"""
    (?P<COMMENT_LINE> //[^\n]*              )|
    (?P<COMMENT_BLOCK>/\*.*?\*/             )|
    (?P<WS>           \s+                   )|
    (?P<STRING>       "[^"]*"|'[^']*'       )|
    (?P<BACKTICK_STRING> `(?:[^`]|\n)*`     )|
    (?P<NUMBER>       -?(?:\d+(?:\.\d+)?|\.\d+) )|
    (?P<ARROW>        =>                    )|
    (?P<ASSIGN>       =                     )|
    (?P<IDENT>        [A-Za-z_][A-Za-z0-9_]* )|
    (?P<LBRACKET>     \[                    )|
    (?P<RBRACKET>     \]                    )|
    (?P<LPAREN>       \(                    )|
    (?P<RPAREN>       \)                    )|
    (?P<DOT>          \.                    )|
    (?P<COMMA>        ,                     )|
    (?P<SEMICOLON>    ;                     )|
    (?P<PLUS>         \+                    )|
    (?P<STAR>         \*                    )|
    (?P<SLASH>        /                     )|
    (?P<COLON>        :                     )|
    (?P<LBRACE>       \{                    )|
    (?P<RBRACE>       \}                    )
    """,
    re.VERBOSE | re.DOTALL,
)


def tokenize(src: str) -> list[Token]:
    out: list[Token] = []
    pos = 0
    while pos < len(src):
        m = _TOKEN_RE.match(src, pos)
        if not m:
            raise SyntaxError(f"unexpected char at offset {pos}: {src[pos]!r}")
        kind = m.lastgroup
        assert kind is not None
        value = m.group()
        pos = m.end()
        if kind in {"WS", "COMMENT_LINE", "COMMENT_BLOCK"}:
            continue
        if kind in {"BACKTICK_STRING"}:
            kind = "STRING"
        out.append(Token(kind=kind, value=value))
    return out
