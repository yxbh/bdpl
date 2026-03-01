# AGENTS.md — bdpl Copilot Agent Guide

## Project Overview

**bdpl** is a Python CLI tool that analyzes Blu-ray disc (`BDMV/`) backup structures to automatically identify episode playlists, map segment graphs, and optionally remux episodes to MKV files.

## Architecture

```
bdpl/
├── bdpl/
│   ├── __init__.py          # Package root, version
│   ├── cli.py               # Typer CLI (scan, explain, playlist, remux, archive)
│   ├── model.py             # Dataclasses: Playlist, PlayItem, Episode, etc.
│   ├── bdmv/
│   │   ├── reader.py        # BinaryReader — big-endian binary parser
│   │   ├── mpls.py          # MPLS (Movie PlayList) parser
│   │   ├── clpi.py          # CLPI (Clip Information) parser
│   │   ├── index_bdmv.py    # index.bdmv parser (title→movie object mapping)
│   │   ├── movieobject_bdmv.py # MovieObject.bdmv parser (navigation commands)
│   │   └── ig_stream.py     # [EXPERIMENTAL] IG menu stream parser (button→action)
│   ├── analyze/
│   │   ├── __init__.py      # scan_disc() — main analysis pipeline
│   │   ├── signatures.py    # Playlist signature computation & dedup
│   │   ├── clustering.py    # Duration-based playlist clustering
│   │   ├── segment_graph.py # Segment frequency & Play All detection
│   │   ├── classify.py      # Segment labeling (OP/ED/BODY) & playlist classification
│   │   ├── ordering.py      # Episode ordering & inference
│   │   └── explain.py       # Human-readable analysis explanation
│   ├── export/
│   │   ├── json_out.py      # JSON export (disc.json schema v1)
│   │   ├── text_report.py   # Plain text summary report
│   │   ├── m3u.py           # M3U debug playlist generation
│   │   ├── mkv_chapters.py  # MKV with chapters + track names (needs mkvmerge)
│   │   └── digital_archive.py # Digital archive image extraction (needs ffmpeg)
│   └── remux/               # (v0.3) mkvmerge/ffmpeg integration
│       └── __init__.py
│   └── util/
│       └── __init__.py      # (placeholder) hashing/log helpers planned
├── tests/
│   ├── conftest.py          # Shared fixtures (bdmv_path, disc analysis helpers)
│   ├── builders.py          # Shared test-data builders for model objects
│   ├── test_reader.py       # BinaryReader unit tests
│   ├── test_mpls_parse.py   # MPLS parser tests (real BDMV data)
│   ├── test_clpi_parse.py   # CLPI parser tests (real BDMV data)
│   ├── test_index_bdmv.py   # index.bdmv parser tests
│   ├── test_movieobject_bdmv.py # MovieObject.bdmv parser tests
│   ├── test_ig_stream.py    # IG stream parser tests (ICS fixture)
│   ├── test_ordering.py     # Episode ordering unit tests
│   ├── test_disc1_scan.py   # disc1 integration tests
│   ├── test_disc14_scan.py  # disc14 chapter-splitting tests
│   ├── test_disc3_scan.py   # disc3 integration tests
│   ├── test_disc4_scan.py   # disc4 single-main-title + archive tests
│   ├── test_disc5_scan.py   # disc5 visible/hidden specials tests
│   ├── test_disc6_scan.py   # disc6 title-hint specials tests
│   ├── test_disc_matrix.py  # Cross-disc compatibility matrix tests
│   ├── test_fixture_integrity.py # Fixture validation tests
│   ├── test_special_visibility_heuristics.py # Visibility heuristic tests
│   ├── test_specials_visible_only.py # --visible-only export tests
│   ├── test_digital_archive.py # digital archive detection/extraction tests
│   └── test_cli.py          # CLI subprocess tests
├── pyproject.toml           # Build config, deps (typer, rich, pytest)
├── PLAN.md                  # Full project roadmap (v0.1–v0.4)
└── AGENTS.md                # This file
```

## Key Concepts

### Binary Formats
- **MPLS** files (`BDMV/PLAYLIST/*.mpls`): Define playback order — which clips to play, in what order, with what in/out times. Start with magic `MPLS` + version string.
- **CLPI** files (`BDMV/CLIPINF/*.clpi`): Clip metadata — stream types (video/audio/subtitle), codecs, languages. Start with magic `HDMV` + version string.
- **index.bdmv**: Disc title table — maps title numbers to MovieObject IDs. Start with magic `INDX`.
- **MovieObject.bdmv**: Navigation commands — bytecode that references playlists and titles. Start with magic `MOBJ`.
- **M2TS** files (`BDMV/STREAM/*.m2ts`): The actual media transport streams.
- All BDMV binary structures are **big-endian**. Timestamps are in **45 kHz ticks**.

### Analysis Pipeline (`scan_disc()`)
1. Parse index.bdmv and MovieObject.bdmv for navigation hints (title→playlist mapping)
2. Parse IG menu streams for button→action hints (experimental)
3. Parse all MPLS and CLPI files
4. Compute playlist signatures for deduplication
5. Cluster by duration to find episode-length playlists
6. Detect "Play All" playlists (supersets of other playlists)
7. Label segments (LEGAL, OP, ED, BODY, PREVIEW)
8. Classify playlists (episode, play_all, bumper, creditless_op, etc.)
9. Infer episode order — individual playlists, Play All decomposition, or chapter splitting
10. Boost confidence when navigation hints confirm episode playlists

### Episode Inference Strategies
- **Individual episodes**: When each episode has its own MPLS playlist
- **Play All decomposition**: When only a concatenated playlist exists, decompose its play items into separate episodes (common on anime BDs)
- **Chapter-based splitting**: When a disc has a single long m2ts with multiple chapters, split into episodes using chapter boundaries and target duration heuristics

### IG Menu Parsing (Experimental)
Blu-ray IG (Interactive Graphics) menus contain buttons with HDMV navigation commands.
These can reveal episode→chapter mappings embedded in the disc menu structure:
- **Direct PlayPL**: Button plays a specific playlist (possibly at a specific mark)
- **Register-based**: Buttons SET GPR registers to values that map to episodes/chapters, then other buttons use those registers for playback
- Parsed from PID 0x1400-0x141F in menu m2ts clips
- ICS (Interactive Composition Segment) contains pages → BOGs → buttons → nav commands
- Nav commands use the same 12-byte HDMV instruction set as MovieObject.bdmv

## Development

### Python Setup
```bash
# Python 3.10+ required (3.12 recommended)
pip install -e ".[dev]"
```

### Running
```bash
bdpl scan /path/to/BDMV -o disc.json
bdpl scan /path/to/BDMV --stdout --pretty
bdpl explain /path/to/BDMV
bdpl playlist /path/to/BDMV --out ./Playlists
bdpl archive /path/to/BDMV --out ./DigitalArchive
```

### Testing
```bash
pytest tests/ -v
```

Tests use bundled fixture data from `tests/fixtures/disc1/` and `tests/fixtures/disc14/` by default. Set `BDPL_TEST_BDMV` to override with a real BDMV directory.

```bash
# Run all tests (unit tests always run; integration tests need a BDMV)
export BDPL_TEST_BDMV=/path/to/disc/BDMV   # or parent dir
pytest tests/ -v
```

### Data Model (model.py)
- `PlayItem`: References a clip segment with in/out times, streams, labels
- `Playlist`: Collection of PlayItems from an MPLS file
- `Episode`: Inferred episode with confidence score and segment references
- `DiscAnalysis`: Complete analysis result (playlists, clips, episodes, warnings)

### JSON Schema (`bdpl.disc.v1`)
Output includes: `schema_version`, `disc`, `playlists`, `episodes`, `special_features`, `warnings`, `analysis`

## Coding Conventions
- Python 3.10+, use `from __future__ import annotations`
- `dataclasses` with `slots=True` for models
- `struct` module for binary parsing (no external deps)
- `typer` for CLI, `rich` for terminal output
- Robust error handling — parsers should not crash on malformed data
- All times in models: 45 kHz ticks (raw) or milliseconds (derived)

## Current Status: v0.3+
- ✅ MPLS parser (play items, chapters, streams)
- ✅ CLPI parser (stream types, codecs, languages)
- ✅ index.bdmv parser (title→movie object mapping)
- ✅ MovieObject.bdmv parser (navigation commands, playlist references)
- ✅ IG stream parser [experimental] (menu button commands, episode hints)
- ✅ Full analysis pipeline with navigation hints + IG integration
- ✅ Episode inference (individual playlists + Play All + chapter splitting)
- ✅ Special feature detection from IG menu JumpTitle buttons
- ✅ Digital archive playlist detection (`digital_archive` classification)
- ✅ JSON export, text reports, M3U playlists
- ✅ MKV remux with chapters + track names (via mkvmerge)
- ✅ `archive` extraction command for digital archive still images (via ffmpeg)
- ✅ `--specials` remux flag for creditless OP/ED, extras, previews
- ✅ Chapter-based episode splitting with mkvmerge `--split parts:`
- ✅ Bundled test fixtures (131 tests, no env var needed)
- ✅ CLI commands: `scan`, `explain`, `playlist`, `remux`, `archive`
- ✅ Plex/Jellyfin-compatible default naming (`{name} - S01Exx.mkv`, `{name} - S00Exx - {category}.mkv`)
- ✅ Special feature visibility detection (`menu_visible` labeling)
- ✅ `--visible-only` flag for remux/archive workflows
- ✅ Disc title extraction from BDMV metadata for remux naming

## Agent Tips
- When modifying parsers, test against real BDMV data (set `BDPL_TEST_BDMV` env var)
- The analysis pipeline is in `analyze/__init__.py:scan_disc()` — this orchestrates everything
- Special feature detection is in `_detect_special_features()` — uses IG JumpTitle buttons pointing to non-episode playlists
- `JumpTitle(N)` in HDMV commands is **1-based** — convert to 0-based index title with `N - 1`
- Chapter-split features: when a button sets `reg2` before `JumpTitle`, it selects a chapter within the target playlist (multi-feature playlists)
- Segment keys use quantization (default ±250ms) to handle tiny timing variances

### Fixing Analysis Mismatches — Structural Signals over Thresholds

When a new disc produces wrong episode or special counts, **do not** add numeric
thresholds or ratio guards.  Instead:

1. **Study the data** — dump chapter durations, IG menu buttons, segment labels,
   and MovieObject navigation across the failing disc AND existing fixtures that
   work correctly.  Look for structural patterns that differentiate the two cases.
2. **Identify a structural signal** — something the disc data tells you about its
   own content type (e.g. repeating OP/body/ED chapter cycle for episodes,
   IG button-per-page counts matching chapters-per-episode, title-hint references
   in navigation commands).
3. **Require positive evidence** — the code should ask "does the data say this IS
   X?" rather than "does the data say this is NOT X?".  Negative guards based on
   thresholds (like `max_chapters_per_episode = 7`) are brittle and will break on
   the next disc that doesn't match the assumed range.
4. **Combine signals** — when one signal isn't sufficient alone, combine multiple
   independent signals (e.g. IG marks + chapter periodicity + button-per-page).
   Each signal lowers the confidence bar, but at least one must be present.

Examples of structural signals already in use:
- **Chapter periodicity** (`_detect_episode_periodicity`): detects repeating
  OP (~90 s) / body / ED (~90 s) / preview (~30 s) cycle in chapter durations
- **IG chapter marks**: JT + reg2 buttons directly encode episode boundaries
- **Digital archive multi-signal**: item count + title hint + no-audio streams

## Copyright & Fixture Guidelines
- **NEVER commit copyrighted media content** (m2ts video/audio streams, full disc images, cover art, subtitle tracks, etc.) to the repository.
- **Test fixtures** in `tests/fixtures/` contain only small structural metadata files (MPLS, CLPI, index.bdmv, MovieObject.bdmv, ICS segments) — these are binary headers/indexes, not audiovisual content.
- When adding new disc fixtures, include **only** the minimum metadata needed for tests. Strip or exclude:
  - `BDMV/STREAM/*.m2ts` (media streams — never commit these)
  - `BDMV/AUXDATA/` (thumbnails, sound effects)
  - `BDMV/JAR/` (BD-J applications)
  - `BDMV/BACKUP/` (redundant copies)
- Keep fixture files small (a few KB per file, under 100KB per disc)
- Name fixture directories generically (disc1, disc2, etc.) — do not include disc titles, product codes, or other identifying information that ties fixtures to specific copyrighted works
