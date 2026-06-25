"""Strudel JS → Tidal Cycles .tidal transpiler.

Public API:
    transpile(src: str) -> str
    transpile_file(in_path: Path, out_path: Path) -> None
"""

from pathlib import Path

from .emitter import emit
from .lexer import tokenize
from .parser import parse
from .validator import validate


def transpile(src: str) -> str:
    """Strudel source → Tidal source."""
    tokens = tokenize(src)
    tree = parse(tokens)
    validate(tree)
    return emit(tree)


def transpile_file(in_path: Path, out_path: Path) -> None:
    out_path.write_text(transpile(in_path.read_text()))
