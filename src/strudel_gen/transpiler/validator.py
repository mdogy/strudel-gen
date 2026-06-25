"""Reject unsupported Strudel constructs with a clear error."""

from __future__ import annotations

from difflib import get_close_matches

from .parser import (
    Assign,
    CatExpr,
    ChainCall,
    Layer,
    PatternFile,
    StackExpr,
)

_ALLOWED_CHAIN_CALLS = frozenset(
    {
        "s",
        "n",
        "room",
        "lpf",
        "hpf",
        "gain",
        "delay",
        "delayt",
        "delayfb",
        "vib",
        "vibdepth",
        "speed",
        "pan",
        "crush",
        "shape",
        "slow",
        "fast",
        "rev",
        "orbit",
        "every",
        "sometimes",
        "often",
        "rarely",
        "mask",
        "begin",
        "end",
        "attack",
        "decay",
        "release",
        "rsize",
        "lpenv",
        "lpa",
        "lps",
        "lpd",
        "lpr",
        "bank",
        "note",
        "scale",
        "scaleTranspose",
        "cpm",
        "sound",
    }
)

_ALLOWED_HEADS = frozenset({"note", "s", "n", "sound"})

_KNOWN_SYNTHS = frozenset(
    {
        "super808",
        "superchip",
        "superclap",
        "supercomparator",
        "superfm",
        "superfork",
        "supergong",
        "supergrind",
        "superhammond",
        "superhat",
        "superhex",
        "superhoover",
        "superkick",
        "supermandolin",
        "supernoise",
        "superpiano",
        "superprimes",
        "superpwm",
        "superreese",
        "supersaw",
        "supersiren",
        "supersnare",
        "supersquare",
        "superstatic",
        "supertron",
        "supervibe",
        "superwavemechanics",
        "superzow",
        # GM synths
        "gm_synth_bass_1",
        "gm_pad_poly",
        "gm_pad_metallic",
    }
)

_KNOWN_SAMPLE_BANKS = frozenset(
    {
        "RolandTR909",
        "RolandTR808",
        "LinnDrum",
    }
)

# GM → SuperDirt synth mapping for sample-name bridge
_GM_TO_SUPERDIRT = {
    "gm_synth_bass_1": "supersaw",
    "gm_pad_poly": "superpiano",
    "gm_pad_metallic": "supergong",
}


class UnsupportedConstructError(ValueError):
    pass


def _closest_synth(bad_name: str) -> str | None:
    matches = get_close_matches(bad_name, _KNOWN_SYNTHS, n=1, cutoff=0.4)
    return matches[0] if matches else None


def resolve_synth(name: str) -> str:
    """Map a GM or unknown sample name to the closest SuperDirt synth.

    Returns the mapped synth name if a mapping exists, otherwise
    returns the original name.
    """
    return _GM_TO_SUPERDIRT.get(name, name)


def _validate_chain_calls(chain: list[ChainCall], context: str = "") -> None:
    for call in chain:
        if call.name not in _ALLOWED_CHAIN_CALLS:
            raise UnsupportedConstructError(f"unsupported method .{call.name}(){context}")


def _is_simple_name(s: str) -> bool:
    """Check if a string looks like a simple identifier name (not a pattern)."""
    import re

    return bool(re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", s.strip()))


def _validate_layer(layer: Layer) -> None:
    head = layer.head if layer.head != "sound" else "s"
    if head not in _ALLOWED_HEADS:
        raise UnsupportedConstructError(
            f"unsupported head '{layer.head}()' — expected one of note/s/n"
        )
    unknown = (
        head == "s"
        and _is_simple_name(layer.head_arg)
        and layer.head_arg not in _KNOWN_SYNTHS
        and layer.head_arg not in _KNOWN_SAMPLE_BANKS
    )
    if unknown:
        hint = _closest_synth(layer.head_arg)
        if hint:
            msg = f"unknown synth '{layer.head_arg}' — not registered in SuperDirt"
            msg += f" (did you mean '{hint}'?)"
            raise UnsupportedConstructError(msg)
        # If no close match found, allow it as a custom sample name
    _validate_chain_calls(layer.chain, context=f" in layer {layer.head}({layer.head_arg!r})")


def validate(tree: PatternFile) -> None:
    if tree.layers:
        # Old-style validation
        if tree.cpm is None:
            raise UnsupportedConstructError("missing setcpm(N) at top level")
        if not tree.layers:
            raise UnsupportedConstructError("at least one layer required")
        for layer in tree.layers:
            _validate_layer(layer)
        return

    if tree.arrange is None and not tree.statements:
        # No statements = empty file or just setcpm
        if tree.cpm is not None:
            raise UnsupportedConstructError("at least one layer required")
        return

    # New-style validation
    if tree.cpm is None:
        raise UnsupportedConstructError("missing cpm — add 'let cpm = N;' or 'setcpm(N)'")

    for stmt in tree.statements:
        _validate_assign(stmt)

    if tree.arrange:
        _validate_chain_calls(tree.arrange.chain, context=" in arrange()")


def _validate_assign(stmt: Assign) -> None:
    val = stmt.value
    if isinstance(val, Layer):
        _validate_layer(val)
    elif isinstance(val, StackExpr):
        for item in val.items:
            if isinstance(item, Layer):
                _validate_layer(item)
            elif isinstance(item, tuple):
                _validate_chain_calls(item[1], context=f" in stack item .{item[0]}")
        _validate_chain_calls(val.chain, context=f" in stack assigned to {stmt.name!r}")
    elif isinstance(val, CatExpr):
        _validate_chain_calls(val.chain, context=f" in cat assigned to {stmt.name!r}")
    elif isinstance(val, str):
        pass  # inline pattern string
