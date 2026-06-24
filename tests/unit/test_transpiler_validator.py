"""Tests for transpiler/validator.py — construct rejection."""
import pytest

from strudel_gen.transpiler import transpile
from strudel_gen.transpiler.parser import ParseError
from strudel_gen.transpiler.validator import UnsupportedConstructError as UnsupportedConstruct
from strudel_gen.transpiler.validator import resolve_synth


class TestSynthResolution:
    def test_gm_synth_mapped_to_superdirt(self) -> None:
        assert resolve_synth("gm_synth_bass_1") == "supersaw"
        assert resolve_synth("gm_pad_poly") == "superpiano"
        assert resolve_synth("gm_pad_metallic") == "supergong"

    def test_known_synth_passes_through(self) -> None:
        assert resolve_synth("supersaw") == "supersaw"
        assert resolve_synth("superhammond") == "superhammond"

    def test_unknown_synth_passes_through(self) -> None:
        assert resolve_synth("vox") == "vox"
        assert resolve_synth("custom_sample") == "custom_sample"


class TestValidator:
    def test_unknown_method_rejected(self) -> None:
        with pytest.raises(UnsupportedConstruct, match="csound"):
            transpile('setcpm(20)\nnote("c").csound("foo").slow(4).room(0.8)')

    def test_missing_cpm_rejected(self) -> None:
        with pytest.raises(UnsupportedConstruct, match="setcpm"):
            transpile('note("c").s("sine").slow(4).room(0.8)')

    def test_unsupported_head_rejected(self) -> None:
        with pytest.raises(UnsupportedConstruct, match="unsupported head"):
            transpile('setcpm(20)\nbad("c").slow(4)')

    def test_empty_layer_rejected(self) -> None:
        with pytest.raises(UnsupportedConstruct, match="at least one layer"):
            transpile("setcpm(20)")

    def test_allowed_methods_pass(self) -> None:
        src = 'setcpm(20)\nnote("c2").s("supersaw").lpf(280).room(0.9).gain(0.5).slow(8).orbit(0)'
        result = transpile(src)
        assert "setcps" in result

    def test_unknown_synth_rejected(self) -> None:
        with pytest.raises(UnsupportedConstruct, match="unknown synth.*supersine"):
            transpile('setcpm(20)\ns("supersine").slow(4).room(0.8)')

    def test_unknown_synth_with_hint(self) -> None:
        with pytest.raises(UnsupportedConstruct, match="did you mean.*supersaw"):
            transpile('setcpm(20)\ns("superswa").slow(4).room(0.8)')

    def test_unknown_synth_without_hint(self) -> None:
        with pytest.raises(UnsupportedConstruct, match="unknown synth.*foobar"):
            transpile('setcpm(20)\ns("foobar").slow(4).room(0.8)')

    def test_known_synth_passes(self) -> None:
        for synth in ["supersaw", "superhammond", "superpiano", "supermandolin"]:
            result = transpile(f'setcpm(20)\ns("{synth}").slow(4).room(0.8)')
            assert "setcps" in result

    def test_new_chain_methods_pass(self) -> None:
        src = 'setcpm(20)\nnote("c2").s("sine").mask("1 0").begin(0.25).end(0.75).attack(0.01).decay(0.1).release(0.3).rsize(0.5).slow(4)'
        result = transpile(src)
        assert "mask" in result

    def test_lpenv_chain_methods_pass(self) -> None:
        src = 'setcpm(20)\nnote("c2").s("sine").lpenv(0.5).lpa(0.7).lps(0.3).lpd(0.2).lpr(0.4).slow(4)'
        result = transpile(src)
        assert "lpenv" in result

    def test_delay_and_bank_pass(self) -> None:
        src = 'setcpm(20)\nnote("c2").s("sine").delay(0.4).bank("RolandTR909").slow(4)'
        result = transpile(src)
        assert "delay" in result

    def test_cat_expr_validated(self) -> None:
        src = 'let cpm = 135; let x = cat("c2", "e2", "g2").note(); arrange([4, x])'
        result = transpile(src)
        assert "cat" in result

    def test_let_stack_validated(self) -> None:
        src = 'let cpm = 135; let x = stack(s("supersaw").slow(4), note("c2").s("supersaw").slow(6)).slow(2); arrange([4, x])'
        result = transpile(src)
        assert "stack" in result

    def test_unsupported_method_in_let_rejected(self) -> None:
        with pytest.raises(UnsupportedConstruct, match="unsupported method"):
            transpile('let cpm = 135; let x = note("c2").badmethod("foo").slow(4); arrange([4, x])')

    def test_sound_head_validated(self) -> None:
        src = 'setcpm(20)\nsound("supersaw").slow(4)'
        result = transpile(src)
        assert "sine" not in result

    def test_empty_file_emits_setcps_zero(self) -> None:
        result = transpile("")
        assert "setcps" in result
        assert "(0/60/4)" in result

    def test_just_cpm_rejected(self) -> None:
        with pytest.raises(UnsupportedConstruct, match="at least one layer"):
            transpile("setcpm(20)")

    def test_drum_bank_passes(self) -> None:
        src = 'setcpm(20)\ns("RolandTR909").slow(4).room(0.8)'
        result = transpile(src)
        assert "RolandTR909" in result

    def test_unsupported_head_rejected_let_style(self) -> None:
        with pytest.raises((ParseError, UnsupportedConstruct)):
            transpile('let cpm = 135; let x = bad("c2").slow(4); arrange([4, x])')

    def test_arrange_without_cpm_rejected(self) -> None:
        with pytest.raises(UnsupportedConstruct, match="missing cpm"):
            transpile('let x = note("c2").s("supersaw").slow(4); arrange([4, x])')

    def test_stack_var_ref_with_chain_validated(self) -> None:
        src = 'let cpm = 135; let a = note("c2").s("supersaw").slow(8); let b = stack(a.slow(2), note("eb3").s("supersaw").slow(6)); arrange([4, b])'
        result = transpile(src)
        assert "stack" in result

    def test_inline_pattern_validated(self) -> None:
        src = 'let cpm = 135; let x = "c2 eb2 g2"; arrange([4, x])'
        result = transpile(src)
        assert "c2" in result
