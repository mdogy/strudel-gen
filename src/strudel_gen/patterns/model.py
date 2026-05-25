"""Pydantic models for pattern specification."""

from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class LayerType(StrEnum):
    drone = "drone"
    pad = "pad"
    texture = "texture"
    bass = "bass"
    melody = "melody"
    fx = "fx"


class OscillatorType(StrEnum):
    sine = "sine"
    sawtooth = "sawtooth"
    square = "square"
    triangle = "triangle"
    pad = "pad"
    noise = "noise"


class Effect(BaseModel):
    type: str = Field(..., description="Effect type: reverb, delay, lpf, hpf, gain")
    value: float = Field(default=0.0)


class Layer(BaseModel):
    type: LayerType
    notes: str = Field(..., description="Strudel note pattern string, e.g. '<c2 g2>'")
    sound: OscillatorType | str = Field(default=OscillatorType.sine)
    orbit: int = Field(default=0, ge=0, le=11)
    slow_factor: int = Field(default=4, ge=4, description=".slow factor (>=4 per SWED)")
    room: float = Field(default=0.8, ge=0.7, le=1.0, description=".room (>=0.7 per SWED)")
    gain: float = Field(default=0.4, ge=0.0, le=1.0)
    lpf: int | None = Field(default=None, ge=20, le=20000)
    delay: float | None = Field(default=None, ge=0.0, le=1.0)
    delayt: float | None = Field(default=None, ge=0.0, le=2.0)
    delayfb: float | None = Field(default=None, ge=0.0, le=1.0)
    effects: list[Effect] = Field(default_factory=list)


class PatternSpec(BaseModel):
    cpm: int = Field(default=20, ge=1, description="Cycles per minute (tempo)")
    layers: list[Layer] = Field(..., min_length=1, description="At least 1 layer")

    @model_validator(mode="after")
    def check_unique_orbits(self) -> "PatternSpec":
        orbits = [layer.orbit for layer in self.layers]
        used = set()
        for o in orbits:
            if o in used:
                raise ValueError(f"Duplicate orbit {o}; each layer must have a unique orbit")
            used.add(o)
        return self

    @model_validator(mode="after")
    def check_slow_ge4(self) -> "PatternSpec":
        for i, layer in enumerate(self.layers):
            if layer.slow_factor < 4:
                raise ValueError(f"Layer {i}: slow_factor must be >= 4, got {layer.slow_factor}")
        return self

    @model_validator(mode="after")
    def check_room_ge07(self) -> "PatternSpec":
        for i, layer in enumerate(self.layers):
            if layer.room < 0.7:
                raise ValueError(f"Layer {i}: room must be >= 0.7, got {layer.room}")
        return self
