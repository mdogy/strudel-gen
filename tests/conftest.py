"""Shared pytest fixtures."""

from pathlib import Path

import pytest


@pytest.fixture
def fixture_dir() -> Path:
    """Path to test fixture data."""
    return Path(__file__).resolve().parent / "fixtures"


@pytest.fixture
def sample_pattern_spec() -> dict:
    """A minimal valid PatternSpec for testing."""
    return {
        "cpm": 20,
        "layers": [
            {
                "type": "drone",
                "notes": "<c2 g2>",
                "sound": "sawtooth",
                "orbit": 0,
                "slow_factor": 8,
                "room": 0.9,
                "gain": 0.4,
                "lpf": 400,
            },
            {
                "type": "pad",
                "notes": "<c4 ~ eb4>",
                "sound": "sine",
                "orbit": 1,
                "slow_factor": 4,
                "room": 0.8,
                "gain": 0.3,
            },
        ],
    }
