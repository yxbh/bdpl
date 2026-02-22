import os
from pathlib import Path

import pytest

from bdpl.analyze import scan_disc
from bdpl.bdmv.clpi import parse_clpi_dir
from bdpl.bdmv.mpls import parse_mpls_dir

_FIXTURE_DIR: Path = Path(__file__).parent / "fixtures" / "disc1"
_DISC5_FIXTURE_DIR: Path = Path(__file__).parent / "fixtures" / "disc5"


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
def disc5_analysis():
    """Run and cache full analysis for the bundled disc5 fixture."""
    if not (_DISC5_FIXTURE_DIR / "PLAYLIST").is_dir():
        pytest.skip("disc5 fixture not available")

    playlists = parse_mpls_dir(_DISC5_FIXTURE_DIR / "PLAYLIST")
    clips = parse_clpi_dir(_DISC5_FIXTURE_DIR / "CLIPINF")
    return scan_disc(_DISC5_FIXTURE_DIR, playlists, clips)
