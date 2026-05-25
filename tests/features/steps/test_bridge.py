"""pytest-bdd steps for bridge.feature."""

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

from pytest_bdd import given, parsers, scenario, then, when
from typer.testing import CliRunner

from strudel_gen.cli import app
from strudel_gen.detect import DetectionResult

runner = CliRunner()


class BridgeContext:
    def __init__(self) -> None:
        self.result: Any = None


_context = BridgeContext()


@given("the strudel-gen CLI is installed")
def given_cli_installed() -> None:
    pass


@given("sclang is available on the system")
def given_sclang_available() -> None:
    pass


@given("a Strudel clone is available")
def given_strudel_available() -> None:
    pass


@scenario("../../features/bridge.feature", "Start and stop both services")
def test_bridge_session_lifecycle() -> None:
    pass


@scenario("../../features/bridge.feature", "Doctor shows sclang before session")
def test_bridge_doctor() -> None:
    pass


def _detection() -> DetectionResult:
    return DetectionResult(
        sclang="/usr/bin/sclang",
        node="/usr/bin/node",
        pnpm="/usr/bin/pnpm",
        strudel_dir=Path("/tmp/strudel"),
        os_name="Linux",
        is_wsl=False,
    )


@when(parsers.parse('I run "{cmd}"'))
def when_run_command(cmd: str) -> None:
    mock_sc = MagicMock()
    mock_bridge = MagicMock()
    parts = cmd.split()
    args = parts[1:] if len(parts) > 1 else []

    with (
        patch("strudel_gen.cli.detect", return_value=_detection()),
        patch("strudel_gen.cli.SCManager", return_value=mock_sc),
        patch("strudel_gen.cli.BridgeManager", return_value=mock_bridge),
        patch("time.sleep"),
    ):
        _context.result = runner.invoke(app, args)


@then("the exit code should be 0")
def then_exit_zero() -> None:
    assert _context.result is not None
    assert _context.result.exit_code == 0, _context.result.output


@then(parsers.parse('the output should contain "{text}"'))
def then_output_contains(text: str) -> None:
    assert _context.result is not None
    assert text in _context.result.output, f"Expected '{text}' in output:\n{_context.result.output}"
