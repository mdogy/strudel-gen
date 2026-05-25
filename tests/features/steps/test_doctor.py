"""pytest-bdd steps for doctor.feature."""

from pathlib import Path
from typing import Any
from unittest.mock import patch

from pytest_bdd import given, parsers, scenario, then, when
from typer.testing import CliRunner

from strudel_gen.cli import app
from strudel_gen.detect import DetectionResult

runner = CliRunner()


class DoctorContext:
    def __init__(self) -> None:
        self.result: Any = None
        self._sclang: str | None = None
        self._node: str | None = None
        self._pnpm: str | None = None
        self._strudel_dir: str | None = "/home/user/devel/strudel"

    def _build_detection(self) -> DetectionResult:
        return DetectionResult(
            sclang=self._sclang,
            node=self._node,
            pnpm=self._pnpm,
            strudel_dir=Path(self._strudel_dir) if self._strudel_dir else None,
            os_name="Linux",
            is_wsl=False,
        )

    def start(self) -> None:
        self._patches = [
            patch("strudel_gen.cli.detect", return_value=self._build_detection()),
        ]
        for p in self._patches:
            p.start()

    def stop(self) -> None:
        if hasattr(self, "_patches"):
            for p in self._patches:
                p.stop()


_context = DoctorContext()


@given("the strudel-gen CLI is installed")
def given_cli_installed() -> None:
    pass


@scenario("../../features/doctor.feature", "All prerequisites present")
def test_doctor_all_present() -> None:
    pass


@scenario("../../features/doctor.feature", "Missing SuperCollider")
def test_doctor_missing_sc() -> None:
    pass


@scenario("../../features/doctor.feature", "All missing")
def test_doctor_all_missing() -> None:
    pass


@given(parsers.parse('SuperCollider is installed at "{path}"'))
def given_sclang_installed(path: str) -> None:
    _context._sclang = path


@given("SuperCollider is not installed")
def given_sclang_missing() -> None:
    _context._sclang = None


@given(parsers.parse('Node.js is installed at "{path}"'))
def given_node_installed(path: str) -> None:
    _context._node = path


@given("Node.js is not installed")
def given_node_missing() -> None:
    _context._node = None


@given(parsers.parse('pnpm is installed at "{path}"'))
def given_pnpm_installed(path: str) -> None:
    _context._pnpm = path


@given("pnpm is not installed")
def given_pnpm_missing() -> None:
    _context._pnpm = None


@given(parsers.parse('Strudel is cloned at "{path}"'))
def given_strudel_cloned(path: str) -> None:
    _context._strudel_dir = path


@given("Strudel is not cloned")
def given_strudel_missing() -> None:
    _context._strudel_dir = None


@when(parsers.parse('I run "{cmd}"'))
def when_run_doctor(cmd: str) -> None:
    _context.start()
    parts = cmd.split()
    args = parts[1:] if len(parts) > 1 else []
    try:
        _context.result = runner.invoke(app, args)
    finally:
        _context.stop()


@then("the exit code should be 0")
def then_exit_zero() -> None:
    assert _context.result is not None
    assert _context.result.exit_code == 0, _context.result.output


@then("the exit code should be 1")
def then_exit_one() -> None:
    assert _context.result is not None
    assert _context.result.exit_code == 1, _context.result.output


@then(parsers.parse('the output should contain "{text}"'))
def then_output_contains(text: str) -> None:
    assert _context.result is not None
    assert text in _context.result.output, f"Expected '{text}' in output:\n{_context.result.output}"
