"""Tests for transpiler/parser.py — AST construction."""
import pytest

from strudel_gen.transpiler.lexer import tokenize
from strudel_gen.transpiler.parser import (
    CatExpr,
    ChainCall,
    Layer,
    ParseError,
    StackExpr,
    parse,
)


class TestParse:
    def test_setcpm_only(self) -> None:
        tree = parse(tokenize("setcpm(20)"))
        assert tree.cpm == 20
        assert tree.layers == []

    def test_setcpm_with_stack(self) -> None:
        src = 'setcpm(20)\nstack(note("c").s("sine"))'
        tree = parse(tokenize(src))
        assert tree.cpm == 20
        assert len(tree.layers) == 1
        assert tree.layers[0].head == "note"
        assert tree.layers[0].head_arg == "c"

    def test_multi_layer_stack(self) -> None:
        src = 'setcpm(20)\nstack(note("c2").orbit(0), note("e3").orbit(1))'
        tree = parse(tokenize(src))
        assert len(tree.layers) == 2
        assert tree.layers[0].head_arg == "c2"
        assert tree.layers[1].head_arg == "e3"

    def test_chained_calls(self) -> None:
        src = 'note("c2").s("sawtooth").lpf(280).room(0.9).slow(8)'
        tree = parse(tokenize(src))
        layer = tree.layers[0]
        names = [c.name for c in layer.chain]
        assert names == ["s", "lpf", "room", "slow"]

    def test_every_modifier(self) -> None:
        src = 'note("c2").every(4, x => x.rev()).slow(4)'
        tree = parse(tokenize(src))
        layer = tree.layers[0]
        every_call = layer.chain[0]
        assert every_call.name == "every"
        assert len(every_call.args) == 2
        assert every_call.args[0].kind == "NUMBER"
        assert every_call.args[1].kind == "LAMBDA_CALL"

    def test_single_layer_no_stack(self) -> None:
        src = 'setcpm(20)\nnote("c2").s("sine").slow(4)'
        tree = parse(tokenize(src))
        assert tree.cpm == 20
        assert len(tree.layers) == 1

    def test_missing_comma_raises(self) -> None:
        src = 'stack(note("c") note("e"))'
        with pytest.raises(ParseError):
            parse(tokenize(src))

    def test_parse_error_on_bad_token(self) -> None:
        with pytest.raises(ParseError):
            parse(tokenize("setcpm(twenty)"))

    def test_arithmetic_in_setcpm(self) -> None:
        tree = parse(tokenize("setcpm(135/4)"))
        assert tree.cpm == pytest.approx(33.75)

    def test_arithmetic_multiple_ops(self) -> None:
        tree = parse(tokenize("setcpm(20*3+5)"))
        expected = 20 * 3 + 5
        assert tree.cpm == expected

    def test_sound_head(self) -> None:
        src = 'setcpm(20)\nsound("sawtooth").slow(4)'
        tree = parse(tokenize(src))
        assert tree.layers[0].head == "s"
        assert tree.layers[0].head_arg == "sawtooth"

    def test_let_assign_pattern_string(self) -> None:
        src = 'let a = "c2 e2 g2";'
        tree = parse(tokenize(src))
        assert len(tree.statements) == 1
        assert tree.statements[0].name == "a"
        assert tree.statements[0].value == "c2 e2 g2"

    def test_let_assign_layer(self) -> None:
        src = 'let x = note("c2").s("sine").slow(4);'
        tree = parse(tokenize(src))
        assert tree.statements[0].name == "x"
        val = tree.statements[0].value
        assert isinstance(val, Layer)
        assert val.head == "note"
        assert val.head_arg == "c2"

    def test_cat_assignment(self) -> None:
        src = 'let x = cat("c2", "e2", "g2").note();'
        tree = parse(tokenize(src))
        val = tree.statements[0].value
        assert isinstance(val, CatExpr)
        assert len(val.args) == 3
        assert val.args[0].value == "c2"
        assert val.args[1].value == "e2"
        assert val.args[2].value == "g2"

    def test_arrange_sections(self) -> None:
        src = 'let x = note("c2").s("sine"); arrange([4, x], [2, y])'
        tree = parse(tokenize(src))
        assert tree.arrange is not None
        assert tree.arrange.items == [(4, "x"), (2, "y")]

    def test_chain_mask_begin_end(self) -> None:
        src = 'note("c2").s("sine").mask("0 0 1 0").begin(0.25).end(0.75).slow(4)'
        tree = parse(tokenize(src))
        names = [c.name for c in tree.layers[0].chain]
        assert "mask" in names
        assert "begin" in names
        assert "end" in names

    def test_chain_attack_decay_release_rsize(self) -> None:
        src = 'note("c2").s("sine").attack(0.01).decay(0.1).release(0.3).rsize(0.5).slow(4)'
        tree = parse(tokenize(src))
        names = [c.name for c in tree.layers[0].chain]
        assert "attack" in names
        assert "decay" in names
        assert "release" in names
        assert "rsize" in names

    def test_chain_lpenv(self) -> None:
        src = 'note("c2").s("sine").lpenv(0.5).lpa(0.7).lps(0.3).lpd(0.2).lpr(0.4).slow(4)'
        tree = parse(tokenize(src))
        names = [c.name for c in tree.layers[0].chain]
        assert "lpenv" in names
        assert "lpa" in names
        assert "lps" in names
        assert "lpd" in names
        assert "lpr" in names

    def test_chain_delay_bank(self) -> None:
        src = 'note("c2").s("sine").delay(0.4).bank("RolandTR909").slow(4)'
        tree = parse(tokenize(src))
        names = [c.name for c in tree.layers[0].chain]
        assert "delay" in names
        assert "bank" in names

    def test_note_with_string_arg(self) -> None:
        src = 's("sine").note("0 2 4 7").slow(4)'
        tree = parse(tokenize(src))
        layer = tree.layers[0]
        assert layer.head == "s"
        note_call = next(c for c in layer.chain if c.name == "note")
        assert note_call.args[0].kind == "STRING"
        assert note_call.args[0].value == "0 2 4 7"

    def test_stack_with_variable_ref(self) -> None:
        src = 'let cpm = 135; let a = note("c2").s("supersaw").slow(8); let b = stack(a, note("eb3").s("supersaw").slow(6));'
        tree = parse(tokenize(src))
        assert tree.statements[1].name == "b"
        val = tree.statements[1].value
        assert isinstance(val, StackExpr)
        assert len(val.items) == 2
        assert val.items[0] == "a"
        assert isinstance(val.items[1], Layer)

    def test_chain_calls_on_stack_expr(self) -> None:
        src = 'let x = stack(note("c2").s("sine"), note("e2").s("sine")).slow(4).room(0.8);'
        tree = parse(tokenize(src))
        val = tree.statements[0].value
        assert isinstance(val, StackExpr)
        assert len(val.chain) == 2
        assert val.chain[0].name == "slow"
        assert val.chain[1].name == "room"

    def test_samples_skipped(self) -> None:
        src = 'setcpm(20)\nsamples({bd: "path"});\nnote("c2").s("sine").slow(4)'
        tree = parse(tokenize(src))
        assert len(tree.layers) == 1

    def test_stray_semicolons(self) -> None:
        src = 'setcpm(20);\nnote("c2").s("sine").slow(4);'
        tree = parse(tokenize(src))
        assert tree.cpm == 20

    def test_variable_ref_in_stack_no_chain(self) -> None:
        src = 'let cpm = 135; let a = note("c2").s("supersaw").slow(8); let b = stack(a);'
        tree = parse(tokenize(src))
        val = tree.statements[1].value
        assert isinstance(val, StackExpr)
        assert val.items == ["a"]

    def test_blank_line_comma_tolerance(self) -> None:
        src = ',\nsetcpm(20)\nnote("c2").s("sine").slow(4)'
        tree = parse(tokenize(src))
        assert tree.cpm == 20

    def test_cpm_arith_in_let(self) -> None:
        src = 'let cpm = 135/4; let x = note("c2").s("supersaw").slow(4); arrange([4, x])'
        tree = parse(tokenize(src))
        assert tree.cpm == pytest.approx(33.75)

    def test_n_head_layer(self) -> None:
        src = 'setcpm(20)\nn("supersaw").slow(4)'
        tree = parse(tokenize(src))
        assert tree.layers[0].head == "n"
        assert tree.layers[0].head_arg == "supersaw"

    def test_cpm_assigned_to_layer_eval_fallback(self) -> None:
        src = 'let cpm = note("c2").s("supersaw").slow(4); let x = note("c2").s("supersaw").slow(4); arrange([4, x])'
        tree = parse(tokenize(src))
        assert tree.cpm == 0.0

    def test_top_level_unexpected_token_raises(self) -> None:
        with pytest.raises((SyntaxError, ParseError)):
            parse(tokenize("@bad"))

    def test_empty_stack_parens(self) -> None:
        tree = parse(tokenize("setcpm(20)\nstack()"))
        assert tree.layers == []

    def test_empty_arrange_parens(self) -> None:
        tree = parse(tokenize("arrange()"))
        assert tree.arrange is not None
        assert tree.arrange.items == []

    def test_stack_unexpected_item_raises(self) -> None:
        src = 'let cpm = 135; let x = stack(42);'
        with pytest.raises(ParseError):
            parse(tokenize(src))

    def test_cat_unexpected_item_raises(self) -> None:
        src = 'let cpm = 135; let x = cat(42);'
        with pytest.raises(ParseError):
            parse(tokenize(src))

    def test_delay_one_part_string(self) -> None:
        src = 'setcpm(20)\nnote("c2").s("sine").delay("0.5").slow(4).orbit(0)'
        tree = parse(tokenize(src))
        delay_call = [c for c in tree.layers[0].chain if c.name == "delay"][0]
        assert delay_call.args[0].kind == "STRING"
        assert delay_call.args[0].value == "0.5"

    def test_arith_expression_in_arg(self) -> None:
        src = 'setcpm(20)\nnote("c2").s("sine").end(.25 + .1).slow(4)'
        tree = parse(tokenize(src))
        end_call = [c for c in tree.layers[0].chain if c.name == "end"][0]
        assert end_call.args[0].kind == "NUMBER"
        assert end_call.args[0].value == pytest.approx(0.35)
