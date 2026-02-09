"""Tests for CLI commands via subprocess."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

PYTHON = sys.executable
_FIXTURE_DIR = Path(__file__).parent / "fixtures" / "disc1"


def _bdmv() -> str:
    """Resolve BDMV path from env var or bundled fixtures."""
    env = os.environ.get("BDPL_TEST_BDMV")
    if env:
        p = Path(env)
        if (p / "BDMV" / "PLAYLIST").is_dir():
            return str(p / "BDMV")
        return str(p)
    if (_FIXTURE_DIR / "PLAYLIST").is_dir():
        return str(_FIXTURE_DIR)
    pytest.skip("No BDMV fixtures available")


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
