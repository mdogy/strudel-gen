"""Golden-file tests and full transpile integration."""
from pathlib import Path

import pytest

from strudel_gen.transpiler import transpile
from strudel_gen.transpiler.validator import UnsupportedConstructError as UnsupportedConstruct

FIXTURES = Path(__file__).parent / "fixtures" / "transpiler"


@pytest.mark.parametrize("name", [
    "bare_layer",
    "stack_two",
    "stack_three_with_orbits",
    "every_rev",
    "sometimes_speed",
    "delaytime_rename",
    "comment_line",
    "single_layer_no_stack",
    "fractional_room",
    "pattern_value",
    "slow_fast_combo",
    "dr_who",
    "sound_head",
    "new_chain_methods",
    "lpenv_chain",
    "note_string_arg",
    "delay_expand",
    "arith_setcpm",
    "cat_in_arrange",
    "arrange_sections",
    "let_and_vars",
])
def test_golden(name: str) -> None:
    src = (FIXTURES / f"{name}.js").read_text()
    expected = (FIXTURES / f"{name}.tidal").read_text()
    assert transpile(src) == expected


def test_unknown_method_rejected() -> None:
    with pytest.raises(UnsupportedConstruct, match="csound"):
        transpile('setcpm(20)\nnote("c").csound("foo").slow(4).room(0.8)')


def test_missing_cpm_rejected() -> None:
    with pytest.raises(UnsupportedConstruct, match="setcpm"):
        transpile('note("c").s("sine").slow(4).room(0.8)')
