---
name: add-disc-fixture
description: 'Add a new Blu-ray disc fixture for testing bdpl analysis. Use when asked to add a new disc, mount an ISO, create test fixtures, or analyze a new BDMV directory. Covers: (1) Surveying disc structure, (2) Running analysis and comparing against expected counts, (3) Debugging mismatches in episode/special detection, (4) Extracting ICS and copying metadata-only fixture files, (5) Creating integration tests and updating conftest/matrix.'
---

# Add Disc Fixture

## Overview

Step-by-step workflow for adding a new Blu-ray disc test fixture to bdpl.
Each fixture captures metadata-only files from a real disc, enabling
integration tests without copyrighted media content.

## When to Use This Skill

- User asks to "add a new disc" or "add disc N"
- User mounts an ISO and wants to create a test fixture
- User provides expected episode/special counts for a disc
- Analysis results don't match expected counts and need debugging

## Prerequisites

- Disc must be accessible (mounted ISO or network path)
- BDMV directory with PLAYLIST/, CLIPINF/, index.bdmv, MovieObject.bdmv
- Python environment with bdpl installed (`pip install -e ".[dev]"`)

## Step-by-Step Workflow

### 1. Survey Disc Structure

Check file counts and sizes to understand disc complexity:

```python
# List MPLS, CLPI files with sizes
Get-ChildItem D:\BDMV\PLAYLIST -Filter "*.mpls" | Select-Object Name, Length
Get-ChildItem D:\BDMV\CLIPINF -Filter "*.clpi" | Select-Object Name, Length
```

### 2. Run Analysis

Create a temporary analysis script or run inline:

```python
from bdpl.analyze import scan_disc
from bdpl.bdmv.mpls import parse_mpls_dir
from bdpl.bdmv.clpi import parse_clpi_dir
from pathlib import Path

p = Path("D:/BDMV")
playlists = parse_mpls_dir(p / "PLAYLIST")
clips = parse_clpi_dir(p / "CLIPINF")
result = scan_disc(p, playlists, clips)

print(f"Episodes: {len(result.episodes)}")
for ep in result.episodes:
    print(f"  ep{ep.episode}: {ep.playlist} dur={ep.duration_ms/60000:.1f}min")
print(f"Specials: {len(result.special_features)}")
for sf in result.special_features:
    print(f"  #{sf.index}: {sf.playlist} cat={sf.category} dur={sf.duration_ms/60000:.1f}min")
print(f"Classifications: {result.analysis.get('classifications')}")
```

### 3. Compare Against Expected Counts

If counts match → proceed to step 5 (extract fixture).
If counts don't match → proceed to step 4 (debug).

### 4. Debug Mismatches

See [debugging guide](./references/debug-analysis.md) for systematic
investigation of episode/special count mismatches.

**Important**: When fixing mismatches, prefer structural signals over
numeric thresholds.  Study chapter durations, IG menu structure, and
navigation data across multiple fixtures — don't just look at the one
that broke.  The debugging guide's "How to Fix" section has details.

### 5. Extract ICS Menu Data

Find the menu clip (usually a short m2ts with IG streams, often clip 00003
or similar — check CLPI sizes, menu clips have small CLPIs ~292 bytes):

```python
from bdpl.bdmv.ig_stream import demux_ig_stream, _extract_ics_data
from pathlib import Path

# Try likely menu clips
for clip in ['00003', '00004', '00005']:
    m2ts = Path(f'D:/BDMV/STREAM/{clip}.m2ts')
    if not m2ts.exists():
        continue
    raw = demux_ig_stream(m2ts)
    if raw:
        ics_data = _extract_ics_data(raw)
        if ics_data:
            print(f'{clip}: ICS data {len(ics_data)} bytes')
```

Save the largest ICS as `ics_menu.bin`:

```python
out = Path('tests/fixtures/discN/ics_menu.bin')
out.parent.mkdir(parents=True, exist_ok=True)
out.write_bytes(ics_data)
```

### 6. Create Fixture Directory

**CRITICAL**: Files go directly under `disc{N}/`, NOT under `disc{N}/BDMV/`.
The `_fixture_path()` helper checks for `(path / "PLAYLIST").is_dir()`.

```
tests/fixtures/disc{N}/
├── CLIPINF/*.clpi          # All clip info files
├── PLAYLIST/*.mpls         # All playlist files
├── META/DL/bdmt_eng.xml    # Generic disc title
├── index.bdmv              # Title table
├── MovieObject.bdmv        # Navigation commands
└── ics_menu.bin            # Pre-extracted ICS data
```

Copy files:

```powershell
$src = "D:\BDMV"
$dst = "tests\fixtures\disc{N}"
New-Item -ItemType Directory -Force "$dst\PLAYLIST", "$dst\CLIPINF", "$dst\META\DL"
Copy-Item "$src\PLAYLIST\*.mpls" "$dst\PLAYLIST\"
Copy-Item "$src\CLIPINF\*.clpi" "$dst\CLIPINF\"
Copy-Item "$src\index.bdmv" "$dst\"
Copy-Item "$src\MovieObject.bdmv" "$dst\"
```

Create generic disc title XML (never use real disc titles):

```xml
<?xml version="1.0" encoding="UTF-8"?>
<disclib>
<di:discinfo xmlns:di="urn:BDA:bdmv;discinfo">
<di:title><di:name>TEST DISC {N}</di:name></di:title>
</di:discinfo>
</disclib>
```

Verify total size is under 100KB.

### 7. Create Integration Test

Create `tests/test_disc{N}_scan.py` following this pattern:

```python
"""Integration tests for the disc{N} fixture scan results."""

import pytest
from bdpl.model import DiscAnalysis

pytestmark = pytest.mark.integration

class TestDisc{N}Episodes:
    def test_episode_count(self, disc{N}_analysis: DiscAnalysis) -> None:
        assert len(disc{N}_analysis.episodes) == EXPECTED_COUNT

    def test_episodes_are_ordered(self, disc{N}_analysis: DiscAnalysis) -> None:
        assert [ep.episode for ep in disc{N}_analysis.episodes] == list(range(1, EXPECTED_COUNT + 1))

    # Add playlist source, duration range checks as appropriate

class TestDisc{N}Specials:
    def test_special_count(self, disc{N}_analysis: DiscAnalysis) -> None:
        assert len(disc{N}_analysis.special_features) == EXPECTED_SPECIAL_COUNT

    # Add category breakdown tests as appropriate

class TestDisc{N}Metadata:
    def test_disc_title(self, disc{N}_analysis: DiscAnalysis) -> None:
        assert disc{N}_analysis.disc_title == "TEST DISC {N}"
```

### 8. Update Shared Test Infrastructure

**conftest.py** — Add path + analysis fixtures:

```python
@pytest.fixture(scope="session")
def disc{N}_path() -> Path:
    """Return path to bundled disc{N} fixture."""
    return _fixture_path("disc{N}")

@pytest.fixture(scope="session")
def disc{N}_analysis(disc{N}_path):
    """Run and cache full analysis for the bundled disc{N} fixture."""
    return _analyze_fixture(disc{N}_path)
```

**test_disc_matrix.py** — Add to ALL 6 parametrizations:

1. Episode count + playlists
2. Special visibility (total + visible)
3. Episode segment boundaries (bare list)
4. Special boundary semantics (bare list)
5. Chapter-split special count
6. Disc title extraction

### 9. Validate

```bash
python -m pytest tests/ -x -q    # All tests pass
python -m ruff check .            # No lint issues
python -m ruff format --check .   # No format issues
```

### 10. Clean Up

- Delete any temporary analysis scripts
- Delete any stray screenshots/images
- Verify no copyrighted content in the fixture

## Common Disc Patterns

| Pattern | Description | Example |
|---------|-------------|---------|
| Play_all decomposition | Single long playlist split by IG chapter marks | disc10, disc11 |
| Individual episodes | Each episode has its own MPLS playlist | disc6, disc7 |
| Chapter splitting | Single m2ts with chapter boundaries | disc14 |
| Commentary specials | Individual playlists duplicating play_all clips | disc10, disc12, disc13 |
| Creditless OP/ED | Short playlists (~1.5-2 min) | disc8, disc13 |
