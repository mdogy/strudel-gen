"""AST → .tidal source."""
from __future__ import annotations

from .parser import (
    Arg,
    Assign,
    CatExpr,
    ChainCall,
    Layer,
    PatternFile,
    StackExpr,
)
from .validator import resolve_synth

_RENAME = {
    "delayt": "delaytime",
    "delayfb": "delayfeedback",
    "sound": "s",
}


def _emit_arg(a: Arg) -> str:
    if a.kind == "NUMBER":
        return str(a.value)
    if a.kind == "STRING":
        return f'"{a.value}"'
    if a.kind == "IDENT":
        return a.value
    if a.kind == "LAMBDA_CALL":
        pair = a.value
        assert isinstance(pair, tuple)
        method, sub_args = pair
        assert isinstance(method, str)
        assert isinstance(sub_args, list)
        sub = " ".join(_emit_arg(x) for x in sub_args) if sub_args else ""
        return f"{method}" if not sub else f"(|+ {method} {sub})"
    raise ValueError(a.kind)


def _emit_chain_call(c: ChainCall) -> str:
    name = _RENAME.get(c.name, c.name)
    # Special handling for delay with "l:t:fb" string
    if c.name == "delay" and c.args and c.args[0].kind == "STRING":
        val = c.args[0].value
        parts = val.split(":")
        if len(parts) == 3:
            l, t, fb = parts
            return f"# delay {l} # delaytime {t} # delayfeedback {fb}"
        return f'# delay {_emit_arg(c.args[0])}'
    args = " ".join(_emit_arg(a) for a in c.args)
    return f"# {name} {args}".rstrip()


def _emit_layer_body(layer: Layer) -> str:
    """Emit the body of a layer (no orbit prefix)."""
    head = "s" if layer.head == "sound" else layer.head
    head_arg = resolve_synth(layer.head_arg) if head == "s" else layer.head_arg
    head_str = f'{head} "{head_arg}"'
    prefix_calls: list[ChainCall] = []
    param_calls: list[ChainCall] = []
    for c in layer.chain:
        if c.name == "orbit":
            continue
        if c.name in {"every", "sometimes", "often", "rarely", "rev"}:
            prefix_calls.append(c)
        else:
            param_calls.append(c)

    params = " ".join(_emit_chain_call(c) for c in param_calls)
    body = f"{head_str} {params}".strip()

    for c in reversed(prefix_calls):
        name = _RENAME.get(c.name, c.name)
        args = " ".join(_emit_arg(a) for a in c.args)
        body = f"{name} {args} $ {body}".strip()

    return body


def _emit_layer(layer: Layer, orbit_idx: int) -> str:
    return f"d{orbit_idx + 1} $ {_emit_layer_body(layer)}"


def _emit_cat_expr(expr: CatExpr) -> str:
    """Emit a CatExpr to a Tidal expression string."""
    parts = ", ".join(f'"{a.value}"' for a in expr.args)
    cat_expr = f"cat [{parts}]"
    body = cat_expr
    # Check if .note() is in chain — if so wrap in note
    has_note = any(c.name == "note" and not c.args for c in expr.chain)
    other_chain = [c for c in expr.chain if not (c.name == "note" and not c.args)]
    if has_note:
        body = f"note $ {cat_expr}"
    for c in other_chain:
        body = f"{body} {_emit_chain_call(c)}"
    # Wrap in parens if used in stack
    return f"({body})"


def _emit_stack_body(items: list, symtab: dict[str, str]) -> str:
    """Emit stack items as a single Tidal stack expression."""
    parts: list[str] = []
    for item in items:
        if isinstance(item, Layer):
            parts.append(_emit_layer_body(item))
        elif isinstance(item, tuple):
            # Variable reference with chain calls: (name, [ChainCall, ...])
            name, chain = item
            ref = symtab.get(name, f's "{name}"')
            for c in chain:
                ref = f"{ref} {_emit_chain_call(c)}"
            parts.append(ref)
        else:
            # Plain variable reference — look up in symtab
            ref = symtab.get(item)
            if ref:
                parts.append(ref)
            else:
                parts.append(f's "{item}"')
    if len(parts) == 1:
        return parts[0]
    return f"stack({', '.join(parts)})"


def _build_symtab(assignments: list[Assign]) -> dict[str, str]:
    """Build a symbol table mapping var names → Tidal expression strings."""
    symtab: dict[str, str] = {}
    # First pass: collect all assignment names
    names = {a.name for a in assignments}
    # Multiple passes until stable (for forward references)
    changed = True
    while changed:
        changed = False
        for a in assignments:
            if a.name in symtab:
                continue
            try:
                symtab[a.name] = _assign_to_tidal(a, symtab, names)
                changed = True
            except KeyError:
                pass  # forward reference, try next pass
    return symtab


def _assign_to_tidal(a: Assign, symtab: dict[str, str], all_names: set[str]) -> str:
    """Convert an assignment to a Tidal expression."""
    val = a.value
    if isinstance(val, Layer):
        return _emit_layer_body(val)
    if isinstance(val, StackExpr):
        body = _emit_stack_body(val.items, symtab)
        if val.chain:
            for c in val.chain:
                body = f"{body} {_emit_chain_call(c)}"
        return body
    if isinstance(val, CatExpr):
        return _emit_cat_expr(val)
    if isinstance(val, str):
        # Inline pattern string
        return f's "{val}"'
    raise ValueError(f"unknown assign value type: {type(val)}")


def _fmt_cpm(cpm: float) -> str:
    """Format cpm as int if whole, else as float without trailing zeros."""
    if cpm == int(cpm):
        return str(int(cpm))
    s = f"{cpm:.10f}".rstrip("0").rstrip(".")
    return s


def emit(tree: PatternFile) -> str:
    lines: list[str] = []
    cpm_str = _fmt_cpm(tree.cpm) if tree.cpm is not None else "0"
    lines.append(f"setcps ({cpm_str}/60/4)")
    lines.append("")

    if tree.layers:
        # Old-style: emit layers as separate orbits
        for i, layer in enumerate(tree.layers):
            orbit = next((c for c in layer.chain if c.name == "orbit"), None)
            idx = i
            if orbit and orbit.args:
                val = orbit.args[0].value
                idx = int(val) if isinstance(val, (int, float)) else i
            lines.append(_emit_layer(layer, idx))
    elif tree.arrange is not None:
        # New-style: build symtab and emit arrange as slowcat
        symtab = _build_symtab(tree.statements)
        arrange_items = tree.arrange.items
        section_exprs: list[str] = []
        for count, var_name in arrange_items:
            expanded = symtab.get(var_name, f's "{var_name}"')
            section_exprs.append(f"  slow {count} {expanded}")
        lines.append("d1 $ slowcat [")
        lines.append(",\n".join(section_exprs))
        lines.append("]")
    else:
        # No layers and no arrange — emit nothing after setcps
        pass

    return "\n".join(lines) + "\n"
