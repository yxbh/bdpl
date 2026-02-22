"""Tests for CLI commands via subprocess."""

import json
import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration


class TestScanStdout:
    def test_scan_stdout(
        self,
        bdmv_path: Path,
        cli_runner: Callable[..., subprocess.CompletedProcess[str]],
    ) -> None:
        """Run `bdpl scan --stdout` and verify JSON output."""
        result = cli_runner("scan", str(bdmv_path), "--stdout")
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = json.loads(result.stdout)
        assert "episodes" in data
        assert "playlists" in data
        assert len(data["episodes"]) > 0


class TestExplainOutput:
    def test_explain_output(
        self,
        bdmv_path: Path,
        cli_runner: Callable[..., subprocess.CompletedProcess[str]],
    ) -> None:
        """Run `bdpl explain` and verify text output contains expected sections."""
        result = cli_runner("explain", str(bdmv_path))
        assert result.returncode == 0, f"stderr: {result.stderr}"
        output: str = result.stdout
        assert "Episodes" in output
        assert "Playlists" in output


class TestArchiveDryRun:
    def test_archive_dry_run(
        self,
        bdmv_path: Path,
        cli_runner: Callable[..., subprocess.CompletedProcess[str]],
    ) -> None:
        """Run `bdpl archive --dry-run` and verify command exits cleanly."""
        result = cli_runner("archive", str(bdmv_path), "--dry-run")
        assert result.returncode == 0, f"stderr: {result.stderr}"

    def test_archive_invalid_format(
        self,
        bdmv_path: Path,
        cli_runner: Callable[..., subprocess.CompletedProcess[str]],
    ) -> None:
        """Run `bdpl archive --format gif` and verify CLI rejects invalid value."""
        result = cli_runner(
            "archive",
            str(bdmv_path),
            "--format",
            "gif",
            "--dry-run",
        )
        assert result.returncode != 0
        assert "Invalid value" in result.stderr

    def test_archive_visible_only_dry_run(
        self,
        bdmv_path: Path,
        cli_runner: Callable[..., subprocess.CompletedProcess[str]],
    ) -> None:
        """Run `bdpl archive --visible-only --dry-run` and verify it exits cleanly."""
        result = cli_runner("archive", str(bdmv_path), "--visible-only", "--dry-run")
        assert result.returncode == 0, f"stderr: {result.stderr}"


class TestRemuxDryRun:
    def test_remux_specials_visible_only_dry_run(
        self,
        bdmv_path: Path,
        cli_runner: Callable[..., subprocess.CompletedProcess[str]],
    ) -> None:
        """Run `bdpl remux --specials --visible-only --dry-run` and verify it succeeds."""
        result = cli_runner(
            "remux",
            str(bdmv_path),
            "--specials",
            "--visible-only",
            "--dry-run",
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
