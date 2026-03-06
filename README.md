# bdpl

CLI tool to analyze Blu-ray `BDMV/` folders, detect episodic playlists, explain disc structure, and remux one MKV per episode.

Anime Blu-ray discs hide episodes behind complex playlist structures — shared OP/ED segments, "Play All" concatenations, duplicate variants with different streams, and menus. **bdpl** parses the raw disc metadata to figure out which playlists are actual episodes and in what order.

## Installation

Requires Python 3.10+.

```bash
pip install -e .
```

Optional external tools:
- [MKVToolNix](https://mkvtoolnix.download/) (`mkvmerge` on PATH) for `bdpl remux`
- [FFmpeg](https://ffmpeg.org/) (`ffmpeg` on PATH) for `bdpl archive`

## Quick Start

Point `bdpl` at a `BDMV/` directory (or a parent directory containing `BDMV/`) from a disc backup:

```bash
# Detect episodes and write structured JSON
bdpl scan /path/to/BDMV -o disc.json

# See what bdpl found and why
bdpl explain /path/to/BDMV

# Generate debug playlists for previewing in a media player
bdpl playlist /path/to/BDMV --out ./Playlists

# Extract menu-driven digital archive stills as images
bdpl archive /path/to/BDMV --out ./DigitalArchive

# Remux episodes to MKV with chapters and named tracks
bdpl remux /path/to/BDMV --out ./Episodes
```

### Example: `bdpl explain`

```
============================================================
Disc Summary
============================================================
  Path:       /mnt/bluray/BDMV
  Playlists:  11
  Clips:      15

------------------------------------------------------------
Playlists
------------------------------------------------------------
  Name               Duration  Items  Class
  ----               --------  -----  -----
  00000.mpls            00:46      2  extra
  00001.mpls            00:01      1  bumper
  00002.mpls         01:21:06      4  play_all
  00003.mpls            01:06      1  creditless_op
  00004.mpls            01:43      1  creditless_ed
  ...

------------------------------------------------------------
Episodes
------------------------------------------------------------
  Ep  1       26:15  conf=0.80  clips=[00007]
  Ep  2       27:16  conf=0.80  clips=[00008]
  Ep  3       27:22  conf=0.80  clips=[00009]

------------------------------------------------------------
Special Features (9 total, 5 visible)
------------------------------------------------------------
   1. 00003.mpls       01:06  creditless_op  [visible]
   2. 00004.mpls       01:43  creditless_ed  [visible]
   3. 00005.mpls       02:00  creditless_ed  [hidden]
   ...
   6. 00008.mpls  ch.0       01:22  creditless_ed  [visible]
   7. 00008.mpls  ch.1       00:16  creditless_ed  [visible]
   8. 00009.mpls       00:16  extra  [hidden]
   9. 00010.mpls       00:17  extra  [hidden]

------------------------------------------------------------
Warnings
------------------------------------------------------------
  [PLAY_ALL_ONLY] Episodes were inferred by decomposing Play All playlist

------------------------------------------------------------
Disc Hints
------------------------------------------------------------
  index.bdmv:       9 title(s)
  MovieObject.bdmv: 11 object(s), 11 with playlist refs
    Title 0 -> 00002.mpls
    Title 1 -> 00003.mpls
    ...
  IG menu:          59 button action(s), chapter marks=[0, 1, 6, 11]
```

## Commands

### `bdpl scan`

Detect episode playlists and emit a structured JSON mapping.

```bash
bdpl scan /path/to/BDMV -o disc.json        # Write to file
bdpl scan /path/to/BDMV --stdout --pretty    # Print to terminal
bdpl scan /path/to/BDMV --stdout --compact   # Machine-readable
```

Output includes:
- Full playlist inventory with durations, streams, and chapters
- Episode candidates with confidence scores
- Episode scene segments (menu-scene boundaries when available)
- Special features (creditless OP/ED, commentary, extras, previews) with `menu_visible` flag
- Playlist classifications (episode, play_all, bumper, creditless_op, etc.)
- Disc title (extracted from `META/DL/bdmt_eng.xml` when available, falls back to other `bdmt_*.xml`)
- Warnings for ambiguous or low-confidence results

### `bdpl explain`

Human-readable breakdown of the disc structure and analysis reasoning.

```bash
bdpl explain /path/to/BDMV
bdpl explain /path/to/BDMV --playlist 00002.mpls   # Detail for one playlist
```

### `bdpl playlist`

Generate `.m3u` debug playlists for previewing episodes in a media player.

```bash
bdpl playlist /path/to/BDMV --out ./Playlists
```

### `bdpl remux`

Remux episodes to MKV with chapters and named tracks. Requires `mkvmerge` (MKVToolNix).

```bash
bdpl remux /path/to/BDMV --out ./Episodes
bdpl remux /path/to/BDMV --pattern "My Show (2024) - S01E{ep:02d}.mkv"
bdpl remux /path/to/BDMV --mkvmerge-path /path/to/mkvmerge
bdpl remux /path/to/BDMV --dry-run

# Also remux special features (creditless OP/ED, commentary, extras, previews)
bdpl remux /path/to/BDMV --specials
bdpl remux /path/to/BDMV --specials --specials-pattern "My Show - S00E{idx:02d} - {category}.mkv"

# Only include specials visible in the disc menu (exclude hidden extras)
bdpl remux /path/to/BDMV --specials --visible-only
```

Default filenames use Plex/Jellyfin-compatible `SxxExx` format with the disc title
extracted from `META/DL/bdmt_eng.xml` (falls back to other `bdmt_*.xml`, then the
BDMV parent folder name).
Pattern variables: `{name}` (disc title), `{ep}` (episode #), `{idx}` (special #), `{category}` (special type).

### `bdpl archive`

Extract still images for digital archive playlists (menu/gallery-style content).

```bash
bdpl archive /path/to/BDMV --out ./DigitalArchive
bdpl archive /path/to/BDMV --format png
bdpl archive /path/to/BDMV --ffmpeg-path /path/to/ffmpeg
bdpl archive /path/to/BDMV --dry-run

# Only include archives visible in the disc menu
bdpl archive /path/to/BDMV --visible-only
```

The command detects playlists classified as `digital_archive` and captures one
frame per archive item via `ffmpeg`, naming outputs as
`{stem}-{index:03d}-{clip_id}.{ext}` (e.g., `00008-001-00005.jpg`).
Requires `ffmpeg` on PATH (or use `--ffmpeg-path`).

## How It Works

bdpl reads the raw BDMV binary structures — no external tools needed for analysis:

1. **Parse** `PLAYLIST/*.mpls` files to extract play items (clip references with in/out timestamps), chapters, and stream tables
2. **Parse** `CLIPINF/*.clpi` files for stream metadata (codecs, languages)
3. **Parse disc hints** from `index.bdmv` (title→playlist mapping), `MovieObject.bdmv` (navigation commands), IG menu streams (button→chapter mappings), and disc title from `META/DL/bdmt_eng.xml` (falls back to other `bdmt_*.xml`)
4. **Analyze** the playlist graph:
   - Compute segment signatures and deduplicate near-identical playlists
   - Detect "Play All" playlists (concatenations of other playlists)
   - Label shared segments as OP, ED, BODY, PREVIEW, LEGAL
   - Classify playlists by duration and segment structure (episode, play_all, bumper, etc.)
5. **Infer** episode order using multiple strategies (see below)
6. **Boost confidence** when navigation hints and IG menu data confirm episode boundaries
7. **Detect special features** from IG menu `JumpTitle` buttons pointing to non-episode playlists (creditless OP/ED, commentary, extras, previews)
8. **Extract scenes** for each episode from IG menu chapter marks and chapter anchors
9. **Export** results as JSON, text reports, M3U playlists, or MKV remux (including specials)

### Episode Inference Strategies

- **Individual episode playlists**: Each episode has its own MPLS with a unique "body" segment, plus shared OP/ED. Episodes are ordered by body clip ID.
- **Play All decomposition**: Some discs (common in anime) only have a single "Play All" playlist. bdpl decomposes it — each play item ≥5 minutes becomes an episode.
- **Chapter-based splitting**: When a disc has a single long m2ts with multiple chapters but no separate playlists, bdpl splits into episodes using chapter boundaries and target duration heuristics.

When disc hints show a single main title plus a separate digital archive title,
bdpl keeps the main title as one episode instead of forcing chapter-based splits.

### Confidence Scoring

Each detected episode gets a confidence score (0–1) based on how it was identified:

| Source | Base | Possible boosts |
|--------|------|-----------------|
| Individual playlists | 0.9 | +0.1 title hint, +0.1 IG chapter marks |
| Play All decomposition | 0.7 | +0.1 title hint, +0.1 IG chapter marks |
| Chapter splitting | 0.6 | +0.1 title hint, +0.1 IG chapter marks |
| Title-hint collapse (single main + archive) | 0.85 | +0.1 title hint, +0.1 IG chapter marks |
| Variant-dedup collapse | 0.85 | +0.1 title hint, +0.1 IG chapter marks |

All boosts are capped at 1.0.

## JSON Schema

The `scan` output uses schema version `bdpl.disc.v1`:

```json
{
  "schema_version": "bdpl.disc.v1",
  "disc": { "path": "...", "title": "My Anime Vol.1", "generated_at": "2026-02-08T..." },
  "playlists": [
    {
      "mpls": "00002.mpls",
      "duration_ms": 4866528.3,
      "play_items": [
        {
          "clip_id": "00007",
          "m2ts": "00007.m2ts",
          "in_time": 0,
          "out_time": 70878307,
          "duration_ms": 1575073.5,
          "label": "BODY",
          "segment_key": ["00007", 0.0, 1575000.0],
          "streams": [
            { "pid": 4113, "codec": "H.264/AVC", "lang": "" },
            { "pid": 4352, "codec": "LPCM", "lang": "jpn" }
          ]
        }
      ],
      "chapters": [
        { "mark_id": 0, "mark_type": 1, "play_item_ref": 0, "timestamp": 188955000, "duration_ms": 0.0 }
      ],
      "streams": [
        { "pid": 4113, "codec": "H.264/AVC", "lang": "" },
        { "pid": 4352, "codec": "LPCM", "lang": "jpn" }
      ]
    }
  ],
  "episodes": [
    {
      "episode": 1,
      "playlist": "00002.mpls",
      "duration_ms": 1575073.5,
      "confidence": 0.70,
      "segments": [
        {
          "key": ["00007", 0.0, 1575000.0],
          "clip_id": "00007",
          "in_ms": 0.0,
          "out_ms": 1575073.5,
          "duration_ms": 1575073.5,
          "label": "BODY"
        }
      ],
      "scenes": [
        {
          "key": ["SCENE", "00002.mpls", 1],
          "clip_id": "00007",
          "in_ms": 0.0,
          "out_ms": 393768.1,
          "duration_ms": 393768.1,
          "label": "SCENE"
        }
      ]
    }
  ],
  "special_features": [
    {
      "index": 1,
      "playlist": "00003.mpls",
      "category": "creditless_op",
      "duration_ms": 89400.0,
      "menu_visible": true
    }
  ],
  "warnings": [{ "code": "PLAY_ALL_ONLY", "message": "...", "context": {} }],
  "analysis": { "classifications": { "00002.mpls": "play_all" } }
}
```

Special features may also include `chapter_start` (integer chapter index) when the
feature is a chapter-window slice of a multi-feature playlist.

## Development

```bash
pip install -e ".[dev]"       # Installs ruff, pytest, etc.
ruff check . && ruff format . # Lint and format
pytest tests/ -v              # 452 tests, all bundled (no env var needed)
```

### Project Structure

```
bdpl/
  bdpl/
    __init__.py            # Package root, version (v0.1.0)
    cli.py                 # Typer CLI (scan, explain, playlist, remux, archive)
    model.py               # Dataclasses (Playlist, Episode, SpecialFeature, etc.)
    bdmv/
      reader.py            # Big-endian binary reader
      mpls.py              # MPLS playlist parser
      clpi.py              # CLPI clip info parser
      index_bdmv.py        # index.bdmv title mapping parser
      movieobject_bdmv.py  # MovieObject.bdmv navigation command parser
      ig_stream.py         # [Experimental] IG menu stream parser
    analyze/
      __init__.py          # scan_disc() pipeline
      signatures.py        # Deduplication
      clustering.py        # Duration clustering
      segment_graph.py     # Segment reuse & Play All detection
      classify.py          # Segment & playlist labeling
      ordering.py          # Episode ordering (individual, Play All, chapter split)
      explain.py           # Human-readable reports
    export/
      json_out.py          # JSON output (bdpl.disc.v1)
      text_report.py       # Text reports
      m3u.py               # M3U playlists
      mkv_chapters.py      # MKV remux with chapters (via mkvmerge)
      digital_archive.py   # Digital archive image extraction (via ffmpeg)
    remux/                 # (placeholder) direct remux integration
    util/                  # (placeholder) hashing/log helpers
  tests/
    fixtures/              # 28 bundled BDMV metadata fixtures (no copyrighted media)
  .github/
    instructions/          # Copilot coding instructions
    skills/                # Copilot agent skills
  pyproject.toml
```

## Assumptions

- You have a **decrypted** BDMV backup (bdpl does not handle copy protection)
- The disc follows the BD-ROM spec (magic `MPLS` / `HDMV`, big-endian, 45 kHz timestamps)
- Episode detection is heuristic — results include confidence scores and warnings when uncertain

## License

MIT

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, validation steps,
and fixture safety rules.
