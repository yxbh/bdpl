import os
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

from bdpl.analyze import scan_disc
from bdpl.bdmv.clpi import parse_clpi_dir
from bdpl.bdmv.mpls import parse_mpls_dir

_FIXTURE_DIR: Path = Path(__file__).parent / "fixtures" / "disc1"
_FIXTURES_ROOT: Path = Path(__file__).parent / "fixtures"
_DISC5_FIXTURE_DIR: Path = Path(__file__).parent / "fixtures" / "disc5"


def _fixture_path(name: str) -> Path:
    """Resolve and validate a bundled disc fixture path by name."""
    path = _FIXTURES_ROOT / name
    if not (path / "PLAYLIST").is_dir():
        pytest.skip(f"{name} fixture not available")
    return path


def _analyze_fixture(path: Path):
    """Parse and analyze one fixture directory."""
    playlists = parse_mpls_dir(path / "PLAYLIST")
    clips = parse_clpi_dir(path / "CLIPINF")
    return scan_disc(path, playlists, clips)


@pytest.fixture
def bdmv_path() -> Path:
    """Path to a BDMV directory for integration tests.

    Uses BDPL_TEST_BDMV env var if set, otherwise falls back to the
    bundled fixtures (stripped metadata-only copies of real disc files).
    """
    env: str | None = os.environ.get("BDPL_TEST_BDMV")
    if env:
        p = Path(env)
        # Accept a parent dir that contains BDMV/
        if (p / "BDMV" / "PLAYLIST").is_dir():
            p: Path = p / "BDMV"
        if not (p / "PLAYLIST").is_dir():
            pytest.skip(f"No PLAYLIST/ found at {p}")
        return p

    # Fall back to bundled fixtures
    if (_FIXTURE_DIR / "PLAYLIST").is_dir():
        return _FIXTURE_DIR
    pytest.skip("No BDMV fixtures available")


@pytest.fixture(scope="session")
def disc1_path() -> Path:
    """Return path to bundled disc1 fixture."""
    return _fixture_path("disc1")


@pytest.fixture(scope="session")
def disc2_path() -> Path:
    """Return path to bundled disc2 fixture."""
    return _fixture_path("disc2")


@pytest.fixture(scope="session")
def disc3_path() -> Path:
    """Return path to bundled disc3 fixture."""
    return _fixture_path("disc3")


@pytest.fixture(scope="session")
def disc4_path() -> Path:
    """Return path to bundled disc4 fixture."""
    return _fixture_path("disc4")


@pytest.fixture(scope="session")
def disc5_path() -> Path:
    """Return path to bundled disc5 fixture."""
    return _fixture_path("disc5")


@pytest.fixture(scope="session")
def disc6_path() -> Path:
    """Return path to bundled disc6 fixture."""
    return _fixture_path("disc6")


@pytest.fixture(scope="session")
def disc1_analysis(disc1_path):
    """Run and cache full analysis for bundled disc1 fixture."""
    return _analyze_fixture(disc1_path)


@pytest.fixture(scope="session")
def disc2_analysis(disc2_path):
    """Run and cache full analysis for bundled disc2 fixture."""
    return _analyze_fixture(disc2_path)


@pytest.fixture(scope="session")
def disc3_analysis(disc3_path):
    """Run and cache full analysis for bundled disc3 fixture."""
    return _analyze_fixture(disc3_path)


@pytest.fixture(scope="session")
def disc4_analysis(disc4_path):
    """Run and cache full analysis for bundled disc4 fixture."""
    return _analyze_fixture(disc4_path)


@pytest.fixture(scope="session")
def disc5_analysis(disc5_path):
    """Run and cache full analysis for the bundled disc5 fixture."""
    return _analyze_fixture(disc5_path)


@pytest.fixture(scope="session")
def disc6_analysis(disc6_path):
    """Run and cache full analysis for the bundled disc6 fixture."""
    return _analyze_fixture(disc6_path)


@pytest.fixture
def cli_runner() -> Callable[..., subprocess.CompletedProcess[str]]:
    """Return helper to invoke `python -m bdpl.cli` consistently in tests."""

    def _run(*args: str, timeout: int = 60) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "bdpl.cli", *args],
            capture_output=True,
            text=True,
            timeout=timeout,
        )

    return _run
