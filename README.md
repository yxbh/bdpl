# bdpl

CLI tool to analyze Blu-ray `BDMV/` folders, detect episodic playlists, explain disc structure, and remux one MKV per episode.

Anime Blu-ray discs hide episodes behind complex playlist structures — shared OP/ED segments, "Play All" concatenations, duplicate variants with different streams, and menus. **bdpl** parses the raw disc metadata to figure out which playlists are actual episodes and in what order.

## Installation

Requires Python 3.10+.

```bash
pip install -e .
```

For remuxing, you also need [MKVToolNix](https://mkvtoolnix.download/) (`mkvmerge` on PATH).

## Quick Start

Point `bdpl` at a `BDMV/` directory from a disc backup:

```bash
# Detect episodes and write structured JSON
bdpl scan /path/to/BDMV -o disc.json

# See what bdpl found and why
bdpl explain /path/to/BDMV

# Generate debug playlists for previewing in a media player
bdpl playlist /path/to/BDMV --out ./Playlists

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
- Playlist classifications (episode, play_all, bumper, creditless_op, etc.)
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
bdpl remux /path/to/BDMV --pattern "S01E{ep:02d}.mkv"
bdpl remux /path/to/BDMV --dry-run
```

## How It Works

bdpl reads the raw BDMV binary structures — no external tools needed for analysis:

1. **Parse** `PLAYLIST/*.mpls` files to extract play items (clip references with in/out timestamps), chapters, and stream tables
2. **Parse** `CLIPINF/*.clpi` files for stream metadata (codecs, languages)
3. **Parse disc hints** from `index.bdmv` (title→playlist mapping), `MovieObject.bdmv` (navigation commands), and IG menu streams (button→chapter mappings)
4. **Analyze** the playlist graph:
   - Compute segment signatures and deduplicate near-identical playlists
   - Cluster playlists by duration to find episode-length candidates
   - Detect "Play All" playlists (concatenations of other playlists)
   - Label shared segments as OP, ED, BODY, PREVIEW, LEGAL
5. **Infer** episode order using multiple strategies (see below)
6. **Boost confidence** when navigation hints and IG menu data confirm episode boundaries
7. **Export** results as JSON, text reports, or M3U playlists

### Episode Inference Strategies

- **Individual episode playlists**: Each episode has its own MPLS with a unique "body" segment, plus shared OP/ED. Episodes are ordered by body clip ID.
- **Play All decomposition**: Some discs (common in anime) only have a single "Play All" playlist. bdpl decomposes it — each long play item (>10 min) becomes an episode.
- **Chapter-based splitting**: When a disc has a single long m2ts with multiple chapters but no separate playlists, bdpl splits into episodes using chapter boundaries and target duration heuristics.

### Confidence Scoring

Each detected episode gets a confidence score (0–1) based on how it was identified:

| Source | Base | Possible boosts |
|--------|------|-----------------|
| Individual playlists | 0.9 | +0.1 title hint |
| Play All decomposition | 0.7 | +0.1 title hint |
| Chapter splitting | 0.6 | +0.1 title hint, +0.1 IG chapter marks |

## JSON Schema

The `scan` output uses schema version `bdpl.disc.v1`:

```json
{
  "schema_version": "bdpl.disc.v1",
  "disc": { "path": "...", "generated_at": "2026-02-08T..." },
  "playlists": [
    {
      "mpls": "00002.mpls",
      "duration_ms": 4866528.3,
      "play_items": [
        {
          "clip_id": "00007",
          "m2ts": "00007.m2ts",
          "duration_ms": 1575073.5,
          "label": "BODY",
          "streams": [
            { "pid": 4113, "codec": "H.264/AVC", "lang": "" },
            { "pid": 4352, "codec": "LPCM", "lang": "jpn" },
            { "pid": 4608, "codec": "PGS", "lang": "jpn" },
            { "pid": 4609, "codec": "PGS", "lang": "eng" }
          ]
        }
      ],
      "chapters": [{ "mark_id": 0, "mark_type": 1, "timestamp": 188955000 }]
    }
  ],
  "episodes": [
    { "episode": 1, "playlist": "00002.mpls", "duration_ms": 1575073.5, "confidence": 0.70 }
  ],
  "warnings": [{ "code": "PLAY_ALL_ONLY", "message": "..." }],
  "analysis": { "classifications": { "00002.mpls": "play_all" } }
}
```

## Development

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

### Project Structure

```
bdpl/
  bdpl/
    cli.py               # Typer CLI
    model.py             # Dataclasses (Playlist, Episode, etc.)
    bdmv/
      reader.py          # Big-endian binary reader
      mpls.py            # MPLS playlist parser
      clpi.py            # CLPI clip info parser
      index_bdmv.py      # index.bdmv title mapping parser
      movieobject_bdmv.py # MovieObject.bdmv navigation command parser
      ig_stream.py       # [Experimental] IG menu stream parser
    analyze/
      __init__.py        # scan_disc() pipeline
      signatures.py      # Deduplication
      clustering.py      # Duration clustering
      segment_graph.py   # Segment reuse & Play All detection
      classify.py        # Segment & playlist labeling
      ordering.py        # Episode ordering (individual, Play All, chapter split)
      explain.py         # Human-readable reports
    export/
      json_out.py        # JSON output
      text_report.py     # Text reports
      m3u.py             # M3U playlists
      mkv_chapters.py    # MKV remux with chapters (via mkvmerge)
  tests/
    fixtures/            # Bundled BDMV metadata for portable tests
  pyproject.toml
```

## Assumptions

- You have a **decrypted** BDMV backup (bdpl does not handle copy protection)
- The disc follows the BD-ROM spec (magic `MPLS` / `HDMV`, big-endian, 45 kHz timestamps)
- Episode detection is heuristic — results include confidence scores and warnings when uncertain

## License

MIT
