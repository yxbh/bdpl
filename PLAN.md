# bdpl — Project Plan (Python)

Version: v0.1 → v0.3 roadmap  
Goal: Given a Blu-ray `BDMV/` folder (full disc backup), automatically identify *episode playlists* and map **Episode → ordered media segments**, then optionally remux to **one MKV per episode** and/or generate debug playlists.

---

## 1. Problem Statement

Anime Blu-ray discs frequently implement “episodes” as **playlists** that stitch together reusable clips:

- Shared segments: legal bumpers, OP, ED, recap, next-episode preview
- Unique segments: episode body for each episode
- Extra playlists: OP-only, ED-only, PVs, “Play All”, duplicated variants differing by streams/angles

MakeMKV output can be misleading because it may dump per-title/per-segment titles rather than per-episode.

**bdpl** should use disc structure as the source of truth:

- `BDMV/PLAYLIST/*.mpls` (playback program)
- `BDMV/CLIPINF/*.clpi` (clip metadata: streams, timing, etc.)
- `BDMV/STREAM/*.m2ts` (media)
- Optional hints: `BDMV/index.bdmv`, `BDMV/MovieObject.bdmv`

---

## 2. User-Facing CLI

### 2.1 Commands

#### `bdpl scan`
Detect episode-like playlists and emit a structured mapping.

```bash
bdpl scan /path/to/BDMV -o disc.json
bdpl scan /path/to/BDMV --pretty --stdout
```

Key outputs:
- Full playlist inventory
- Episode candidates
- Segment graph summary (shared OP/ED candidates)
- Confidence & ambiguity reporting

#### `bdpl explain`
Explain why certain playlists were chosen/rejected.

```bash
bdpl explain /path/to/BDMV
bdpl explain /path/to/BDMV --playlist 00012.mpls
```

Must answer:
- How many playlists exist and durations
- Which are episode candidates, ordered list
- Which are excluded (short, duplicate, play-all, odd structure)
- Shared segments detected (likely OP/ED/preview) and reasoning
- Any “low confidence” flags and alternative orderings

#### `bdpl remux`
Produce one MKV per episode using an external muxer (default: `mkvmerge`).

```bash
bdpl remux /path/to/BDMV --episodes disc.json --out ./Episodes
bdpl remux /path/to/BDMV --out ./Episodes --pattern "S01E{ep:02d}.mkv"
bdpl remux /path/to/BDMV --dry-run
```

Behavior:
- Uses episode mapping from `disc.json` (or runs scan internally if not provided)
- Generates and executes mux commands
- Copies/creates chapters when possible
- Allows track preference selection (language, commentary, signs/songs subs)

#### `bdpl playlist` (debug)
Generate `.m3u` playlists for previewing in players.

```bash
bdpl playlist /path/to/BDMV --episodes disc.json --out ./Playlists
```

Notes:
- Intended for debugging; seamless joins depend on player/codec continuity
- “Real” consumption is via remux

---

## 3. Outputs and Data Model

### 3.1 Output JSON schema (disc.json)

Top-level:
- `schema_version` (e.g., `"bdpl.disc.v1"`)
- `disc`:
  - `path`
  - `fingerprint` (hash of playlist filenames + sizes + maybe first bytes)
  - `generated_at`
- `playlists`: list of all playlists parsed
- `episodes`: inferred ordered episodes (may be empty if not confident)
- `analysis`: cluster and shared-segment stats
- `warnings`: list of warning objects

Playlist object:
- `mpls` (filename)
- `duration_ms`
- `play_items`: ordered list of segment references
- `streams`: derived from CLPI (video/audio/sub PIDs, languages if available)
- `chapters`: optional
- `signature`: normalized signature for clustering (stable)

Play item (segment ref):
- `m2ts` (filename)
- `clip_id` (numeric string)
- `in_time_ms`, `out_time_ms`, `duration_ms`
- `label`: optional inferred label (`OP`, `ED`, `BODY`, `PREVIEW`, `LEGAL`, `UNKNOWN`)
- `key`: canonical segment key used for graphing (see below)

Episode object:
- `episode` (1-based)
- `playlist` (mpls filename chosen as representative)
- `duration_ms`
- `confidence` (0–1)
- `segments`: ordered segment refs
- `alternates`: optional list of alternative playlists with notes

Warning object:
- `code` (e.g., `LOW_CONFIDENCE_ORDER`, `NO_CLPI_FOUND`, `DUPLICATE_VARIANTS`)
- `message`
- `context` (optional)

### 3.2 Canonical segment key
To deduplicate reused segments across playlists:

- `segment_key = (clip_id, quantize(in_ms), quantize(out_ms))`

Quantization tolerance:
- default `±250ms` bucket to avoid tiny timing variances.

---

## 4. Architecture (Python)

### 4.1 Repo layout

```
bdpl/
  bdpl/
    __init__.py
    cli.py
    model.py
    bdmv/
      __init__.py
      mpls.py
      clpi.py
      index_bdmv.py         # optional hints v0.2
      movieobject_bdmv.py   # optional hints v0.2
      reader.py             # BinaryReader
    analyze/
      __init__.py
      signatures.py
      clustering.py
      segment_graph.py
      classify.py
      ordering.py
      explain.py
    export/
      __init__.py
      json_out.py
      text_report.py
      m3u.py
    remux/
      __init__.py
      mkvmerge.py
      ffmpeg.py             # optional alternative
      naming.py
    util/
      __init__.py
      hashing.py
      log.py
  tests/
    test_reader.py
    test_mpls_parse_minimal.py
    test_clpi_parse_minimal.py
    test_scan_golden.py
    fixtures/
      synthetic/
      real_small/
  pyproject.toml
  README.md
  LICENSE
```

### 4.2 Key dependencies
- CLI: `typer` (nice UX) or `click` (both fine); recommend `typer`
- Parsing: standard library only (`struct`, `dataclasses`, `pathlib`)
- JSON: stdlib
- Optional: `rich` for pretty terminal output
- Testing: `pytest`

---

## 5. Parsing Layer

### 5.1 BinaryReader (`bdpl/bdmv/reader.py`)
Requirements:
- Big-endian reads: `u8/u16/u32/u64`, `read_bytes(n)`
- Cursor: `seek`, `tell`, `skip`
- Slices without copies
- Guards: `require(n)`, `require_at(offset, n)`
- Helpful exceptions with offset context

### 5.2 MPLS Parser (`bdpl/bdmv/mpls.py`)
Extract:
- playlist header and version
- play items list:
  - clip ID (maps to `.m2ts` and `.clpi`)
  - in/out times
  - angle/multi-angle data if present
- marks/chapters if present

Output: `Playlist` model + raw sections (for debugging)

### 5.3 CLPI Parser (`bdpl/bdmv/clpi.py`)
Extract:
- stream PID table
- video/audio/sub stream attributes
- language codes if present
- clip timing / EP map where useful

Goal: enough to:
- choose best duplicate variant (more streams, preferred language)
- report streams in `explain`

### 5.4 Optional hints (v0.2)
- `index.bdmv`: title mappings, top menu references (limited)
- `MovieObject.bdmv`: navigation commands referencing titles/playlists (limited)
These are *hints* only; do not make them required for v0.1.

---

## 6. Analysis & Episode Inference

### 6.1 Compute playlist signatures
Normalize playlist into:
- list of canonical segment keys
- optionally include stream set hash

Store:
- `signature_exact`
- `signature_loose` (after quantization)

### 6.2 Clustering duplicates
Group playlists that are:
- identical segment sequences but differ in streams/angles
- near-identical sequences with small timing differences

Pick a representative using heuristics:
- prefer more audio/sub streams
- prefer higher video bitrate (if available) or primary angle
- prefer presence of chapters

Track cluster members to show in `explain`.

### 6.3 Segment graph
Build:
- segment frequency across all playlists
- common prefix/suffix detection among episode candidates
- label repeated segments:
  - `LEGAL` very short intro
  - `OP` common prefix of ~60–120s
  - `ED` common suffix of similar duration
  - `PREVIEW` small suffix after ED, etc.
Labeling is heuristic; store confidence.

### 6.4 Episode candidate selection (core heuristic)
Steps:
1. Filter out obviously non-episodes:
   - duration < 3–5 minutes
2. Find duration clusters (e.g., histogram binning):
   - identify dominant cluster (anime episodes cluster strongly)
3. In that cluster, prefer playlists that:
   - share common prefix/suffix segments with others
   - have at least one unique “body” segment
4. Exclude “play all”:
   - playlists whose segment sequence is concatenation/superset of others
5. Produce ordered list + confidence

### 6.5 Ordering episodes
Primary:
- Sort by unique body segment key (clip ID tends to increase)
Secondary:
- Graph-based ordering by maximizing continuity and minimizing inversions
Fallback:
- playlist filename numeric order (low confidence)

Always produce an order confidence and alternatives if ambiguous.

---

## 7. Remux Implementation

### 7.1 Tool selection
Default: `mkvmerge` (MKVToolNix)
- reliable, fast, preserves streams well

Fallback option: `ffmpeg` concat demuxer (more fragile with seamless joins)

### 7.2 Remux strategy
For each episode:
- Create a temporary concat list (m2ts paths in order)
- Invoke mkvmerge to concatenate segments into one MKV
- Apply track selection rules:
  - `--prefer-audio jpn`
  - `--prefer-subs eng`
- Write chapters if available:
  - if chapter marks exist in playlist, translate to mkv chapters
- Name files using `--pattern`

### 7.3 Dry-run and reproducibility
- `--dry-run` prints commands only
- Write a `remux_plan.json` capturing exact commands and inputs

---

## 8. Explain / Reporting

### 8.1 `bdpl explain` sections
- Disc summary:
  - playlist count, stream count, detected languages
- Candidate breakdown:
  - episode-like playlists with confidence
  - excluded playlists with reasons (short, duplicate cluster, playall)
- Shared segment analysis:
  - top repeated segments, inferred labels OP/ED/etc.
- Ambiguities:
  - duplicates, alternate orderings, missing CLPI data

Use `rich` tables optionally for readability.

---

## 9. Testing Strategy

### 9.1 Unit tests
- `BinaryReader` read/seek/guard correctness
- MPLS minimal parse: header + play items
- CLPI minimal parse: stream PIDs and language tags

### 9.2 Golden tests
- `scan` output compared to a committed JSON snapshot for fixtures

### 9.3 Fixtures
- Synthetic tiny fixtures crafted from known structures (best for parser correctness)
- A small real disc sample (if licensing permits: avoid distributing copyrighted m2ts; include only MPLS/CLPI or redacted)
  - Alternatively, allow users to download fixture metadata via scripts (no media)

---

## 10. Milestones

### v0.1 — MVP (playlist inventory + episode inference) ✅ Complete
- [x] CLI skeleton (`scan`, `explain`)
- [x] MPLS parser sufficient to list:
  - playlist duration, play item list, in/out
- [x] Signature + duplicate clustering
- [x] Duration clustering and episode candidate inference
- [x] JSON output

### v0.2 — Better metadata + ordering ✅ Complete (delivered with v0.1)
- [x] CLPI parser for stream tables + languages
- [x] Improved representative selection among duplicates
- [x] Stronger episode ordering logic + confidence scoring
- [x] Explain improvements (reasons, alternative clusters)

### v0.3 — Remux + playlists (in progress)
- [ ] `remux` with mkvmerge integration (`remux/mkvmerge.py`)
- [ ] Track preference selection (`--prefer-audio`, `--prefer-subs`)
- [ ] Chapter export when available
- [x] `playlist` command (.m3u debug playlists)
- [ ] `--dry-run` and `remux_plan.json`
- [ ] `remux/naming.py` — output file naming from `--pattern`
- [ ] `remux/ffmpeg.py` — optional ffmpeg concat fallback

### v0.4 — Robustness + extras
- [x] `index.bdmv` parser — title mappings and top menu hints
- [x] `MovieObject.bdmv` parser — navigation command hints
- [x] Navigation hints integrated into analysis pipeline (confidence boost)
- [ ] `util/hashing.py` — disc fingerprint (hash of playlist filenames + sizes)
- [ ] Synthetic test fixtures (no dependency on real BDMV for unit tests)
- [ ] `CONTRIBUTING.md`

### Later / Optional
- UI/interactive TUI for resolving ambiguous cases
- Plugin system for known-disc quirks
- Golden test snapshots (`test_scan_golden.py`)

---

## 11. Non-Goals (for sanity)
- BD-J (Java menu) reverse engineering/emulation in v0.x
- Copy protection circumvention (assumes you already have a decrypted backup)
- Perfect labeling of OP/ED on all discs (heuristic and optional)

---

## 12. Licensing & Contribution Notes
- [x] MIT license
- [x] Do not include copyrighted streams in repo
- [ ] Provide "how to capture metadata-only fixtures" instructions for contributors
- [ ] Add `CONTRIBUTING.md` with:
  - how to run tests
  - how to add new fixtures safely
  - how to report discs that fail (share only MPLS/CLPI + scan output)

---

## 13. Implementation Status

Completed 2026-02-08. All v0.1 + v0.2 items shipped. v0.4 parsers added. 48 tests passing.

Files implemented:
- `bdpl/cli.py` — Typer CLI (`scan`, `explain`, `playlist`, `remux` stub)
- `bdpl/model.py` — Dataclasses (Playlist, PlayItem, Episode, DiscAnalysis, etc.)
- `bdpl/bdmv/reader.py` — Big-endian BinaryReader with zero-copy slicing
- `bdpl/bdmv/mpls.py` — MPLS parser (play items, chapters, STN streams)
- `bdpl/bdmv/clpi.py` — CLPI parser (stream PIDs, codecs, languages)
- `bdpl/bdmv/index_bdmv.py` — index.bdmv parser (title→movie object mapping)
- `bdpl/bdmv/movieobject_bdmv.py` — MovieObject.bdmv parser (navigation commands, playlist refs)
- `bdpl/analyze/__init__.py` — `scan_disc()` orchestrator + disc hint integration
- `bdpl/analyze/signatures.py` — Signature computation + duplicate finding
- `bdpl/analyze/clustering.py` — Duration-based clustering + representative picking
- `bdpl/analyze/segment_graph.py` — Segment frequency + Play All detection
- `bdpl/analyze/classify.py` — Segment labeling (OP/ED/BODY) + playlist classification
- `bdpl/analyze/ordering.py` — Episode ordering (individual + Play All decomposition)
- `bdpl/analyze/explain.py` — Human-readable explanation generator
- `bdpl/export/json_out.py` — JSON export (`bdpl.disc.v1` schema)
- `bdpl/export/text_report.py` — Plain text summary report
- `bdpl/export/m3u.py` — M3U debug playlist generation
- `tests/` — 48 tests (reader, mpls, clpi, index, movieobject, scan pipeline, CLI)
