"""Tests for patterns/model.py — Pydantic validation."""

from typing import Any

import pytest
from pydantic import ValidationError

from strudel_gen.patterns.model import Layer, LayerType, OscillatorType, PatternSpec


class TestLayerValidation:
    def test_minimal_layer(self) -> None:
        layer = Layer(type=LayerType.drone, notes="<c2 g2>")
        assert layer.slow_factor >= 4
        assert layer.room >= 0.7

    def test_layer_slow_too_low(self) -> None:
        with pytest.raises(ValidationError) as exc:
            Layer(type=LayerType.drone, notes="<c2 g2>", slow_factor=1)
        assert "slow_factor" in str(exc.value)

    def test_layer_room_too_low(self) -> None:
        with pytest.raises(ValidationError) as exc:
            Layer(type=LayerType.drone, notes="<c2 g2>", room=0.5)
        assert "room" in str(exc.value)


class TestPatternSpecValidation:
    def test_minimal_valid_spec(self, sample_pattern_spec: dict[str, Any]) -> None:
        spec = PatternSpec.model_validate(sample_pattern_spec)
        assert spec.cpm == 20
        assert len(spec.layers) == 2

    def test_duplicate_orbits_raises(self, sample_pattern_spec: dict[str, Any]) -> None:
        sample_pattern_spec["layers"][1]["orbit"] = 0
        with pytest.raises(ValidationError) as exc:
            PatternSpec.model_validate(sample_pattern_spec)
        assert "Duplicate orbit" in str(exc.value)

    def test_zero_layers_raises(self, sample_pattern_spec: dict[str, Any]) -> None:
        sample_pattern_spec["layers"] = []
        with pytest.raises(ValidationError) as exc:
            PatternSpec.model_validate(sample_pattern_spec)
        assert "too_short" in str(exc.value)

    def test_default_values_applied(self, sample_pattern_spec: dict[str, Any]) -> None:
        spec = PatternSpec.model_validate(sample_pattern_spec)
        for layer in spec.layers:
            assert layer.slow_factor >= 4
            assert layer.room >= 0.7

    def test_oscillator_type_enum(self, sample_pattern_spec: dict[str, Any]) -> None:
        spec = PatternSpec.model_validate(sample_pattern_spec)
        assert spec.layers[0].sound == OscillatorType.sawtooth
