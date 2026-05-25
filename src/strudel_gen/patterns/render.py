"""Render a PatternSpec into a Strudel .js string using Jinja2 templates."""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from strudel_gen.patterns.model import Layer, PatternSpec

_TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
_ENV = Environment(
    loader=FileSystemLoader(str(_TEMPLATE_DIR)),
    trim_blocks=True,
    lstrip_blocks=True,
)


def _effect_chain(layer: Layer) -> str:
    """Build the method chain for a layer's effects."""
    parts = []
    if layer.lpf is not None:
        parts.append(f".lpf({layer.lpf})")
    parts.append(f".room({layer.room})")
    if layer.delay is not None:
        parts.append(f".delay({layer.delay})")
    if layer.delayt is not None:
        parts.append(f".delayt({layer.delayt})")
    if layer.delayfb is not None:
        parts.append(f".delayfb({layer.delayfb})")
    parts.append(f".gain({layer.gain})")
    parts.append(f".slow({layer.slow_factor})")
    parts.append(f".orbit({layer.orbit})")
    return "".join(parts)


def render_pattern(spec: PatternSpec, *, template_name: str = "default.j2") -> str:
    """Render a PatternSpec into a Strudel .js string.

    Args:
        spec: The pattern specification to render.
        template_name: Jinja2 template name (without path).

    Returns:
        Valid Strudel JavaScript code as a string.
    """
    template = _ENV.get_template(template_name)

    # Build per-layer code
    layer_strings: list[str] = []
    for layer in spec.layers:
        note_str = layer.notes
        sound_str = layer.sound.value if hasattr(layer.sound, "value") else layer.sound
        chain = _effect_chain(layer)
        layer_code = f'  note("{note_str}").s("{sound_str}"){chain}'
        layer_strings.append(layer_code)

    layers_joined = ",\n".join(layer_strings)

    return template.render(
        cpm=spec.cpm,
        layers=layers_joined,
    )
