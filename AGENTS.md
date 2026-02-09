# AGENTS.md — bdpl Copilot Agent Guide

## Project Overview

**bdpl** is a Python CLI tool that analyzes Blu-ray disc (`BDMV/`) backup structures to automatically identify episode playlists, map segment graphs, and optionally remux episodes to MKV files.

## Architecture

```
bdpl/
├── bdpl/
│   ├── __init__.py          # Package root, version
│   ├── cli.py               # Typer CLI (scan, explain, playlist, remux)
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
│   │   └── mkv_chapters.py  # MKV with chapters + track names (needs mkvmerge)
│   └── remux/               # (v0.3) mkvmerge/ffmpeg integration
│       └── __init__.py
├── tests/
│   ├── conftest.py          # Shared fixtures (bdmv_path)
│   ├── test_reader.py       # BinaryReader unit tests
│   ├── test_mpls_parse.py   # MPLS parser tests (real BDMV data)
│   ├── test_clpi_parse.py   # CLPI parser tests (real BDMV data)
│   ├── test_index_bdmv.py   # index.bdmv parser tests
│   ├── test_movieobject_bdmv.py # MovieObject.bdmv parser tests
│   ├── test_ig_stream.py    # IG stream parser tests (ICS fixture)
│   ├── test_chapter_split.py # Chapter-based episode splitting tests
│   ├── test_scan.py         # Full scan pipeline integration tests
│   └── test_cli.py          # CLI subprocess tests
├── pyproject.toml           # Build config, deps (typer, rich, pytest)
├── PLAN.md                  # Full project roadmap (v0.1–v0.3)
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
# Python 3.12+ required
pip install -e ".[dev]"
```

### Running
```bash
bdpl scan /path/to/BDMV -o disc.json
bdpl scan /path/to/BDMV --stdout --pretty
bdpl explain /path/to/BDMV
bdpl playlist /path/to/BDMV --out ./Playlists
```

### Testing
```bash
pytest tests/ -v
```

Tests use bundled fixture data from `tests/fixtures/disc1/` and `tests/fixtures/disc2/` by default. Set `BDPL_TEST_BDMV` to override with a real BDMV directory.

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
Output includes: `schema_version`, `disc`, `playlists`, `episodes`, `warnings`, `analysis`

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
- ✅ JSON export, text reports, M3U playlists
- ✅ MKV remux with chapters + track names (via mkvmerge)
- ✅ Chapter-based episode splitting with mkvmerge `--split parts:`
- ✅ Bundled test fixtures (62 tests, no env var needed)
- ✅ CLI commands: `scan`, `explain`, `playlist`, `remux`

## Agent Tips
- When modifying parsers, test against real BDMV data (set `BDPL_TEST_BDMV` env var)
- The analysis pipeline is in `analyze/__init__.py:scan_disc()` — this orchestrates everything
- Playlist classifications are heuristic-based; new disc patterns may need new rules
- Segment keys use quantization (default ±250ms) to handle tiny timing variances

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
