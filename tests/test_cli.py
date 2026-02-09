"""Tests for CLI commands via subprocess."""

import json
import os
import subprocess
import sys

import pytest

PYTHON = sys.executable


@pytest.fixture(autouse=True)
def _skip_if_no_bdmv():
    if not os.environ.get("BDPL_TEST_BDMV"):
        pytest.skip("BDPL_TEST_BDMV not set – skipping CLI integration test")


def _bdmv() -> str:
    """Resolve BDMV path from env var."""
    from pathlib import Path

    p = Path(os.environ["BDPL_TEST_BDMV"])
    if (p / "BDMV" / "PLAYLIST").is_dir():
        return str(p / "BDMV")
    return str(p)


class TestScanStdout:
    def test_scan_stdout(self):
        """Run `bdpl scan --stdout` and verify JSON output."""
        result = subprocess.run(
            [PYTHON, "-m", "bdpl.cli", "scan", _bdmv(), "--stdout"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = json.loads(result.stdout)
        assert "episodes" in data
        assert "playlists" in data
        assert len(data["episodes"]) > 0


class TestExplainOutput:
    def test_explain_output(self):
        """Run `bdpl explain` and verify text output contains expected sections."""
        result = subprocess.run(
            [PYTHON, "-m", "bdpl.cli", "explain", _bdmv()],
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        output = result.stdout
        assert "Episodes" in output
        assert "Playlists" in output
