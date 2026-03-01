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
def disc14_path() -> Path:
    """Return path to bundled disc14 fixture."""
    return _fixture_path("disc14")


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
def disc14_analysis(disc14_path):
    """Run and cache full analysis for bundled disc14 fixture."""
    return _analyze_fixture(disc14_path)


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


@pytest.fixture(scope="session")
def disc7_path() -> Path:
    """Return path to bundled disc7 fixture."""
    return _fixture_path("disc7")


@pytest.fixture(scope="session")
def disc7_analysis(disc7_path):
    """Run and cache full analysis for the bundled disc7 fixture."""
    return _analyze_fixture(disc7_path)


@pytest.fixture(scope="session")
def disc8_path() -> Path:
    """Return path to bundled disc8 fixture."""
    return _fixture_path("disc8")


@pytest.fixture(scope="session")
def disc8_analysis(disc8_path):
    """Run and cache full analysis for the bundled disc8 fixture."""
    return _analyze_fixture(disc8_path)


@pytest.fixture(scope="session")
def disc9_path() -> Path:
    """Return path to bundled disc9 fixture."""
    return _fixture_path("disc9")


@pytest.fixture(scope="session")
def disc9_analysis(disc9_path):
    """Run and cache full analysis for the bundled disc9 fixture."""
    return _analyze_fixture(disc9_path)


@pytest.fixture(scope="session")
def disc10_path() -> Path:
    """Return path to bundled disc10 fixture."""
    return _fixture_path("disc10")


@pytest.fixture(scope="session")
def disc10_analysis(disc10_path):
    """Run and cache full analysis for the bundled disc10 fixture."""
    return _analyze_fixture(disc10_path)


@pytest.fixture(scope="session")
def disc11_path() -> Path:
    """Return path to bundled disc11 fixture."""
    return _fixture_path("disc11")


@pytest.fixture(scope="session")
def disc11_analysis(disc11_path):
    """Run and cache full analysis for the bundled disc11 fixture."""
    return _analyze_fixture(disc11_path)


@pytest.fixture(scope="session")
def disc12_path() -> Path:
    """Return path to bundled disc12 fixture."""
    return _fixture_path("disc12")


@pytest.fixture(scope="session")
def disc12_analysis(disc12_path):
    """Run and cache full analysis for the bundled disc12 fixture."""
    return _analyze_fixture(disc12_path)


@pytest.fixture(scope="session")
def disc13_path() -> Path:
    """Return path to bundled disc13 fixture."""
    return _fixture_path("disc13")


@pytest.fixture(scope="session")
def disc13_analysis(disc13_path):
    """Run and cache full analysis for the bundled disc13 fixture."""
    return _analyze_fixture(disc13_path)


@pytest.fixture(scope="session")
def disc15_path() -> Path:
    """Return path to bundled disc15 fixture."""
    return _fixture_path("disc15")


@pytest.fixture(scope="session")
def disc15_analysis(disc15_path):
    """Run and cache full analysis for the bundled disc15 fixture."""
    return _analyze_fixture(disc15_path)


@pytest.fixture(scope="session")
def disc16_path() -> Path:
    """Return path to bundled disc16 fixture."""
    return _fixture_path("disc16")


@pytest.fixture(scope="session")
def disc16_analysis(disc16_path):
    """Run and cache full analysis for the bundled disc16 fixture."""
    return _analyze_fixture(disc16_path)


@pytest.fixture(scope="session")
def disc17_path() -> Path:
    """Return path to bundled disc17 fixture."""
    return _fixture_path("disc17")


@pytest.fixture(scope="session")
def disc17_analysis(disc17_path):
    """Run and cache full analysis for the bundled disc17 fixture."""
    return _analyze_fixture(disc17_path)


@pytest.fixture(scope="session")
def disc18_path() -> Path:
    """Return path to bundled disc18 fixture."""
    return _fixture_path("disc18")


@pytest.fixture(scope="session")
def disc18_analysis(disc18_path):
    """Run and cache full analysis for the bundled disc18 fixture."""
    return _analyze_fixture(disc18_path)


@pytest.fixture(scope="session")
def disc19_path() -> Path:
    """Return path to bundled disc19 fixture."""
    return _fixture_path("disc19")


@pytest.fixture(scope="session")
def disc19_analysis(disc19_path):
    """Run and cache full analysis for the bundled disc19 fixture."""
    return _analyze_fixture(disc19_path)


@pytest.fixture(scope="session")
def disc20_path() -> Path:
    """Return path to bundled disc20 fixture."""
    return _fixture_path("disc20")


@pytest.fixture(scope="session")
def disc20_analysis(disc20_path):
    """Run and cache full analysis for the bundled disc20 fixture."""
    return _analyze_fixture(disc20_path)


@pytest.fixture(scope="session")
def disc21_path() -> Path:
    """Return path to bundled disc21 fixture."""
    return _fixture_path("disc21")


@pytest.fixture(scope="session")
def disc21_analysis(disc21_path):
    """Run and cache full analysis for the bundled disc21 fixture."""
    return _analyze_fixture(disc21_path)


@pytest.fixture(scope="session")
def disc22_path() -> Path:
    """Return path to bundled disc22 fixture."""
    return _fixture_path("disc22")


@pytest.fixture(scope="session")
def disc22_analysis(disc22_path):
    """Run and cache full analysis for the bundled disc22 fixture."""
    return _analyze_fixture(disc22_path)


@pytest.fixture(scope="session")
def disc23_path() -> Path:
    """Return path to bundled disc23 fixture."""
    return _fixture_path("disc23")


@pytest.fixture(scope="session")
def disc23_analysis(disc23_path):
    """Run and cache full analysis for the bundled disc23 fixture."""
    return _analyze_fixture(disc23_path)


@pytest.fixture(scope="session")
def disc24_path() -> Path:
    """Return path to bundled disc24 fixture."""
    return _fixture_path("disc24")


@pytest.fixture(scope="session")
def disc24_analysis(disc24_path):
    """Run and cache full analysis for the bundled disc24 fixture."""
    return _analyze_fixture(disc24_path)


@pytest.fixture(scope="session")
def disc25_path() -> Path:
    """Return path to bundled disc25 fixture."""
    return _fixture_path("disc25")


@pytest.fixture(scope="session")
def disc25_analysis(disc25_path):
    """Run and cache full analysis for the bundled disc25 fixture."""
    return _analyze_fixture(disc25_path)


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
