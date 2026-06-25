"""Parse a token stream into a PatternFile AST."""

from __future__ import annotations

from dataclasses import dataclass, field

from .lexer import Token

# ---------------------------------------------------------------------------
# AST nodes
# ---------------------------------------------------------------------------


@dataclass
class Arg:
    kind: str
    value: object


@dataclass
class ChainCall:
    name: str
    args: list[Arg]


@dataclass
class Layer:
    head: str
    head_arg: str
    chain: list[ChainCall] = field(default_factory=list)


@dataclass
class CatExpr:
    """cat(string, string, ...)  optionally followed by .chain() calls."""

    args: list[Arg]
    chain: list[ChainCall] = field(default_factory=list)


StackItem = Layer | str | tuple[str, list[ChainCall]]


@dataclass
class StackExpr:
    """stack(layer_or_var, ...)  optionally followed by .chain() calls."""

    items: list[StackItem]
    chain: list[ChainCall] = field(default_factory=list)


@dataclass
class ArrangeExpr:
    """arrange([N, var], [N, var], ...)  optionally with .cpm(N) chain."""

    items: list[tuple[int, str]]
    chain: list[ChainCall] = field(default_factory=list)


@dataclass
class Assign:
    name: str
    value: Layer | CatExpr | StackExpr | str  # str = inline pattern


AssignValue = Layer | CatExpr | StackExpr | str
TopLevel = Assign | ArrangeExpr | Layer  # statements at file top level


@dataclass
class PatternFile:
    """The parsed representation of a Strudel file.

    For old-style code (setcpm + layers):
      cpm = int, layers = non-empty

    For new-style code (let + arrange):
      cpm = float, statements = [...], arrange = ArrangeExpr
    """

    cpm: float | None
    layers: list[Layer] = field(default_factory=list)
    statements: list[Assign] = field(default_factory=list)
    arrange: ArrangeExpr | None = None


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


class ParseError(ValueError):
    pass


def _clean_pattern_string(s: str) -> str:
    """Clean a multi-line pattern string: collapse newlines and trim indentation."""
    if "\n" not in s and "\r" not in s:
        return s
    lines = s.strip().splitlines()
    cleaned = [line.strip() for line in lines]
    return " ".join(cleaned)


class _Parser:
    def __init__(self, tokens: list[Token]) -> None:
        self.tokens = tokens
        self.pos = 0

    def peek(self) -> Token | None:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def _consume(self, kind: str) -> Token:
        tok = self.peek()
        if tok is None or tok.kind != kind:
            got = f"{tok.kind}={tok.value!r}" if tok else "EOF"
            raise ParseError(f"expected {kind}, got {got}")
        self.pos += 1
        return tok

    def _skip(self, kind: str) -> bool:
        tok = self.peek()
        if tok and tok.kind == kind:
            self.pos += 1
            return True
        return False

    # ----------------------------------------------------------------
    #  Top-level dispatch
    # ----------------------------------------------------------------

    def parse_file(self) -> PatternFile:
        cpm: float | None = None
        layers: list[Layer] = []
        statements: list[Assign] = []
        arrange: ArrangeExpr | None = None

        # Collect everything at the top level
        while True:
            tok = self.peek()
            if not tok:
                break
            # skip discarded constructs
            _discard = {"samples", "stack" if self._is_stack_call() else ""}
            if tok.kind == "IDENT" and tok.value in _discard and tok.value == "samples":
                self._skip_samples()
                continue
            if tok.kind == "IDENT" and tok.value == "setcpm":
                cpm = float(self._parse_setcpm())
                continue
            if tok.kind == "IDENT" and tok.value == "let":
                stmt = self._parse_let()
                if stmt.name == "cpm":
                    cpm = self._eval_cpm(stmt)
                else:
                    statements.append(stmt)
                self._skip("SEMICOLON")
                continue
            if tok.kind == "IDENT" and tok.value == "arrange":
                arrange = self._parse_arrange()
                continue
            # Old-style: standalone layer or stack
            if tok.kind == "IDENT" and tok.value == "stack":
                layers = self._parse_stack_layers()
                continue
            if tok.kind == "IDENT":
                layers.append(self._parse_single_layer())
                continue
            # anything else skip token (e.g. stray commas, semicolons)
            if tok.kind in {"SEMICOLON", "COMMA"}:
                self.pos += 1
                continue
            raise ParseError(f"unexpected top-level token: {tok.kind}={tok.value!r}")

        if arrange is not None:
            return PatternFile(cpm=cpm, statements=statements, arrange=arrange)
        return PatternFile(cpm=cpm, layers=layers, statements=statements)

    def _is_stack_call(self) -> bool:
        """Check if the current IDENT 'stack' is followed by '(' meaning it's a call."""
        # We already know tok.value == "stack"
        saved = self.pos
        try:
            self.pos += 1  # skip 'stack'
            return self._skip("LPAREN")
        finally:
            self.pos = saved

    def _skip_samples(self) -> None:
        """Skip samples({...}) entirely."""
        self._consume("IDENT")  # samples
        self._consume("LPAREN")
        depth = 1
        while depth > 0:
            tok = self.peek()
            if not tok:
                raise ParseError("unterminated samples()")
            if tok.kind == "LPAREN":
                depth += 1
            elif tok.kind == "RPAREN":
                depth -= 1
            self.pos += 1
        self._skip("SEMICOLON")

    # ----------------------------------------------------------------
    #  setcpm
    # ----------------------------------------------------------------

    def _parse_setcpm(self) -> float:
        self._consume("IDENT")  # setcpm
        self._consume("LPAREN")
        val = self._parse_arith_or_number()
        self._consume("RPAREN")
        return val

    def _parse_arith_or_number(self) -> float:
        """Parse a number or a simple arithmetic expression (e.g. 135/4)."""
        tok = self.peek()
        if not tok:
            raise ParseError("expected number or arithmetic expression")
        if tok.kind == "NUMBER":
            self.pos += 1
            val = float(tok.value)
            # Check for following operator
            while True:
                op = self.peek()
                if op and op.kind in {"PLUS", "STAR", "SLASH"}:
                    self.pos += 1
                    rhs = self._consume("NUMBER")
                    rhs_val = float(rhs.value)
                    if op.kind == "PLUS":
                        val = val + rhs_val
                    elif op.kind == "STAR":
                        val = val * rhs_val
                    elif op.kind == "SLASH":
                        val = val / rhs_val
                else:
                    break
            return val
        raise ParseError(f"expected number, got {tok.kind}={tok.value!r}")

    # ----------------------------------------------------------------
    #  let declarations
    # ----------------------------------------------------------------

    def _parse_let(self) -> Assign:
        self._consume("IDENT")  # let
        name_tok = self._consume("IDENT")
        name = name_tok.value
        self._consume("ASSIGN")
        value = self._parse_assign_value()
        return Assign(name=name, value=value)

    def _parse_assign_value(self) -> AssignValue:
        tok = self.peek()
        if not tok:
            raise ParseError("expected value in assignment")
        if tok.kind == "IDENT" and tok.value == "stack":
            return self._parse_stack_assign()
        if tok.kind == "IDENT" and tok.value == "cat":
            return self._parse_cat_assign()
        if tok.kind == "IDENT" and tok.value in {"s", "sound", "note"}:
            layer = self._parse_single_layer()
            return layer
        if tok.kind == "STRING":
            self.pos += 1
            val = tok.value[1:-1]
            return val
        if tok.kind == "NUMBER":
            # Handle numeric assignments like cpm = 135 or cpm = 135/4
            val_str = tok.value
            self.pos += 1
            # Check for arithmetic operator
            op = self.peek()
            if op and op.kind in {"PLUS", "STAR", "SLASH"}:
                self.pos += 1
                rhs = self._consume("NUMBER")
                lhs = float(val_str)
                rhs_val = float(rhs.value)
                if op.kind == "PLUS":
                    return str(lhs + rhs_val)
                elif op.kind == "STAR":
                    return str(lhs * rhs_val)
                elif op.kind == "SLASH":
                    return str(lhs / rhs_val)
            return val_str
        raise ParseError(f"unexpected value kind in assignment: {tok.kind}={tok.value!r}")

    def _parse_stack_assign(self) -> StackExpr:
        self._consume("IDENT")  # stack
        self._consume("LPAREN")
        items: list[Layer | str | tuple[str, list[ChainCall]]] = []
        while True:
            t = self.peek()
            if not t or t.kind == "RPAREN":
                break
            if t.kind == "IDENT" and t.value in {"s", "sound", "note"}:
                items.append(self._parse_single_layer())
            elif t.kind == "IDENT":
                # variable reference, possibly with chain calls
                name = t.value
                self.pos += 1
                chain = self._parse_chain_calls()
                if chain:
                    items.append((name, chain))
                else:
                    items.append(name)
            else:
                raise ParseError(f"unexpected item in stack: {t.kind}={t.value!r}")
            if not self._skip("COMMA"):
                break
        self._consume("RPAREN")
        chain = self._parse_chain_calls()
        return StackExpr(items=items, chain=chain)

    def _parse_cat_assign(self) -> CatExpr:
        self._consume("IDENT")  # cat
        self._consume("LPAREN")
        args: list[Arg] = []
        while True:
            t = self.peek()
            if not t or t.kind == "RPAREN":
                break
            if t.kind == "STRING":
                self.pos += 1
                args.append(Arg(kind="STRING", value=_clean_pattern_string(t.value[1:-1])))
            else:
                raise ParseError(f"unexpected item in cat: {t.kind}={t.value!r}")
            if not self._skip("COMMA"):
                break
        self._consume("RPAREN")
        chain = self._parse_chain_calls()
        return CatExpr(args=args, chain=chain)

    def _eval_cpm(self, stmt: Assign) -> float:
        """Try to evaluate the value of a cpm assignment to a number."""
        val = stmt.value
        if isinstance(val, str):
            try:
                return float(val)
            except ValueError:
                return 0.0
        if isinstance(val, (Layer, StackExpr, CatExpr)):
            return 0.0
        return 0.0

    # ----------------------------------------------------------------
    #  arrange
    # ----------------------------------------------------------------

    def _parse_arrange(self) -> ArrangeExpr:
        self._consume("IDENT")  # arrange
        self._consume("LPAREN")
        items: list[tuple[int, str]] = []
        while True:
            t = self.peek()
            if not t or t.kind == "RPAREN":
                break
            # Parse [N, var]
            self._consume("LBRACKET")
            count_str = self._consume("NUMBER")
            count = int(float(count_str.value))
            self._skip("COMMA")
            name_tok = self._consume("IDENT")
            items.append((count, name_tok.value))
            self._consume("RBRACKET")
            if not self._skip("COMMA"):
                break
        self._consume("RPAREN")
        chain = self._parse_chain_calls()
        return ArrangeExpr(items=items, chain=chain)

    # ----------------------------------------------------------------
    #  Old-style stack / layer parsing
    # ----------------------------------------------------------------

    def _parse_stack_layers(self) -> list[Layer]:
        self._consume("IDENT")  # stack
        self._consume("LPAREN")
        layers: list[Layer] = []
        while True:
            t = self.peek()
            if not t or t.kind == "RPAREN":
                break
            layers.append(self._parse_single_layer())
            if not self._skip("COMMA"):
                break
        self._consume("RPAREN")
        return layers

    def _parse_single_layer(self) -> Layer:
        ident = self._consume("IDENT")
        head = ident.value
        if head == "sound":
            head = "s"
        self._consume("LPAREN")
        str_tok = self._consume("STRING")
        head_arg = _clean_pattern_string(str_tok.value[1:-1])
        self._consume("RPAREN")
        chain = self._parse_chain_calls()
        return Layer(head=head, head_arg=head_arg, chain=chain)

    # ----------------------------------------------------------------
    #  Chain calls  .method(args)
    # ----------------------------------------------------------------

    def _parse_chain_calls(self) -> list[ChainCall]:
        chain: list[ChainCall] = []
        while True:
            tok = self.peek()
            if not tok or tok.kind != "DOT":
                break
            self._consume("DOT")
            name_tok = self._consume("IDENT")
            name = name_tok.value
            self._consume("LPAREN")
            args = self._parse_args()
            self._consume("RPAREN")
            chain.append(ChainCall(name=name, args=args))
        return chain

    # ----------------------------------------------------------------
    #  Arguments
    # ----------------------------------------------------------------

    def _parse_args(self) -> list[Arg]:
        args: list[Arg] = []
        tok = self.peek()
        if tok and tok.kind == "RPAREN":
            return args
        args.append(self._parse_arg())
        while self._skip("COMMA"):
            args.append(self._parse_arg())
        return args

    def _parse_arg(self) -> Arg:
        tok = self.peek()
        if tok is None:
            raise ParseError("unexpected EOF in args")
        if tok.kind == "NUMBER":
            return self._parse_number_or_arith()
        if tok.kind == "STRING":
            self.pos += 1
            return Arg(kind="STRING", value=tok.value[1:-1])
        if tok.kind == "IDENT":
            # Could be a lambda or a variable ref
            saved = self.pos
            self.pos += 1
            next_tok = self.peek()
            if next_tok and next_tok.kind == "ARROW":
                self.pos = saved  # rewind
                return self._parse_lambda()
            # It's a variable reference (like `cpm` in arrange chain calls)
            self.pos = saved
            self._consume("IDENT")
            return Arg(kind="IDENT", value=tok.value)
        if tok.kind in {"PLUS", "STAR", "SLASH"}:
            return self._parse_arith_arg()
        raise ParseError(f"unexpected token in args: {tok.kind}={tok.value!r}")

    def _parse_number_or_arith(self) -> Arg:
        """Parse a number arg that may be followed by arithmetic operators."""
        num_tok = self._consume("NUMBER")
        next_tok = self.peek()
        if next_tok and next_tok.kind in {"PLUS", "STAR", "SLASH"}:
            # Full arithmetic expression
            self.pos -= 1  # put number back, _parse_arith_arg will re-parse
            return self._parse_arith_arg()
        raw = num_tok.value
        val: float | int = float(raw) if "." in raw else int(float(raw))
        return Arg(kind="NUMBER", value=val)

    def _parse_arith_arg(self) -> Arg:
        """Parse a leading operator as part of arithmetic e.g. .end(.25 + (.25 * .25 * .5)).
        We evaluate the full parenthesized expression."""
        # Collect the arithmetic expression into a string and evaluate
        expr_chars: list[str] = []
        depth = 0
        while True:
            tok = self.peek()
            if not tok:
                break
            if tok.kind == "RPAREN" and depth == 0:
                break
            if tok.kind == "COMMA" and depth == 0:
                break
            if tok.kind == "LPAREN":
                depth += 1
                expr_chars.append("(")
                self.pos += 1
            elif tok.kind == "RPAREN":
                depth -= 1
                expr_chars.append(")")
                self.pos += 1
            elif tok.kind == "NUMBER":
                expr_chars.append(tok.value)
                self.pos += 1
            elif tok.kind in {"PLUS", "STAR", "SLASH"}:
                expr_chars.append({"PLUS": "+", "STAR": "*", "SLASH": "/"}[tok.kind])
                self.pos += 1
            else:
                break
        expr_str = "".join(expr_chars)
        if not expr_str:
            raise ParseError("expected arithmetic expression")
        try:
            result = float(eval(expr_str, {"__builtins__": {}}, {}))
        except Exception as e:
            raise ParseError(f"invalid arithmetic: {expr_str!r}") from e
        return Arg(kind="NUMBER", value=result)

    def _parse_lambda(self) -> Arg:
        self._consume("IDENT")
        self._consume("ARROW")
        self._consume("IDENT")
        self._consume("DOT")
        method = self._consume("IDENT").value
        self._consume("LPAREN")
        sub_args: list[Arg] = []
        t = self.peek()
        if not (t and t.kind == "RPAREN"):
            sub_args.append(self._parse_arg())
        self._consume("RPAREN")
        return Arg(kind="LAMBDA_CALL", value=(method, sub_args))


# ---------------------------------------------------------------------------
# public API
# ---------------------------------------------------------------------------


def parse(tokens: list[Token]) -> PatternFile:
    return _Parser(tokens).parse_file()
