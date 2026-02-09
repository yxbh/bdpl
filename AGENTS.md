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
│   │   └── movieobject_bdmv.py # MovieObject.bdmv parser (navigation commands)
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
2. Parse all MPLS and CLPI files
3. Compute playlist signatures for deduplication
4. Cluster by duration to find episode-length playlists
5. Detect "Play All" playlists (supersets of other playlists)
6. Label segments (LEGAL, OP, ED, BODY, PREVIEW)
7. Classify playlists (episode, play_all, bumper, creditless_op, etc.)
8. Infer episode order — either from individual playlists or by decomposing Play All
9. Boost confidence when navigation hints confirm episode playlists

### Episode Inference Strategies
- **Individual episodes**: When each episode has its own MPLS playlist
- **Play All decomposition**: When only a concatenated playlist exists, decompose its play items into separate episodes (common on anime BDs)

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

Tests use the `BDPL_TEST_BDMV` environment variable to locate a real BDMV directory for integration tests. Unit tests (test_reader.py) use synthetic data and need no external files.

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

## Current Status: v0.2+
- ✅ MPLS parser (play items, chapters, streams)
- ✅ CLPI parser (stream types, codecs, languages)
- ✅ index.bdmv parser (title→movie object mapping)
- ✅ MovieObject.bdmv parser (navigation commands, playlist references)
- ✅ Full analysis pipeline with navigation hints integration
- ✅ Episode inference (individual playlists + Play All decomposition)
- ✅ JSON export, text reports, M3U playlists
- ✅ MKV remux with chapters + track names (via mkvmerge)
- ✅ CLI commands: `scan`, `explain`, `playlist`, `remux`

## Agent Tips
- When modifying parsers, test against real BDMV data (set `BDPL_TEST_BDMV` env var)
- The analysis pipeline is in `analyze/__init__.py:scan_disc()` — this orchestrates everything
- Playlist classifications are heuristic-based; new disc patterns may need new rules
- Segment keys use quantization (default ±250ms) to handle tiny timing variances
