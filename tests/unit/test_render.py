"""Tests for patterns/render.py — Jinja2 template rendering."""

from pathlib import Path
from typing import Any

from strudel_gen.patterns.model import PatternSpec
from strudel_gen.patterns.render import render_pattern


class TestRenderPattern:
    def test_renders_valid_spec(self, sample_pattern_spec: dict[str, Any]) -> None:
        spec = PatternSpec.model_validate(sample_pattern_spec)
        result = render_pattern(spec)

        assert result.startswith("setcpm(")
        assert "stack(" in result
        assert ".slow(" in result
        assert ".room(" in result
        assert ".orbit(" in result

    def test_rendered_output_matches_golden(
        self, sample_pattern_spec: dict[str, Any], fixture_dir: Path
    ) -> None:
        golden = (fixture_dir / "simple-drone.golden.js").read_text()
        spec = PatternSpec.model_validate(sample_pattern_spec)
        result = render_pattern(spec)
        assert result == golden

    def test_structural_validators_satisfied(self, sample_pattern_spec: dict[str, Any]) -> None:
        spec = PatternSpec.model_validate(sample_pattern_spec)
        rendered = render_pattern(spec)

        assert "setcpm(20)" in rendered
        assert ".slow(4)" in rendered or ".slow(8)" in rendered
        assert ".room(0." in rendered
        assert ".orbit(" in rendered
