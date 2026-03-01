---
name: batch-add-disc-fixtures
description: 'Batch-process a folder of Blu-ray ISOs: mount each, run analysis, generate a summary report for user review, then create fixtures for confirmed discs. Use when given a folder of ISOs or asked to add multiple discs at once.'
---

# Batch Add Disc Fixtures

## Overview

Orchestration workflow for processing multiple Blu-ray ISOs in one pass.
Instead of the single-disc back-and-forth (mount → analyze → user confirms
→ fixture → repeat), this skill:

1. Mounts and analyzes every ISO in a folder
2. Generates a summary report with IG menu cross-checks
3. User reviews and confirms/corrects counts in one pass
4. Creates all fixtures, tests, and matrix entries

Delegates per-disc fixture creation to the
[add-disc-fixture](../add-disc-fixture/SKILL.md) skill.

## When to Use This Skill

- User provides a folder path containing multiple ISOs
- User asks to "add all discs from …" or "batch add"
- User wants to process an entire series at once

## Prerequisites

- Windows (uses `Mount-DiskImage` / `Dismount-DiskImage`)
- ISOs accessible via local path or UNC share
- Python environment with bdpl installed (`pip install -e ".[dev]"`)
- Existing test infrastructure (conftest.py, test_disc_matrix.py)

## Step-by-Step Workflow

### 1. Enumerate ISOs

```powershell
$folder = "\\server\share\SERIES NAME"
Get-ChildItem $folder -Filter "*.ISO" | Select-Object Name, Length |
    Sort-Object Name
```

List the ISOs found and confirm with the user before proceeding.

### 2. Determine Next Disc Number

Check existing fixtures to find the next available disc number:

```python
import re
from pathlib import Path

fixtures = Path("tests/fixtures")
existing = sorted(
    int(m.group(1))
    for d in fixtures.iterdir()
    if d.is_dir() and (m := re.match(r"disc(\d+)", d.name))
)
next_disc = existing[-1] + 1 if existing else 1
print(f"Next disc number: {next_disc}")
```

### 3. Mount and Analyze All ISOs

For each ISO, mount it, find the BDMV directory, and run analysis.
Collect results into a structured report.

**IMPORTANT**: Always dismount ISOs after analysis, even if errors occur.
Use try/finally to guarantee cleanup.

```python
import json
from pathlib import Path
from bdpl.analyze import scan_disc
from bdpl.bdmv.mpls import parse_mpls_dir
from bdpl.bdmv.clpi import parse_clpi_dir

results = []

for iso_path in iso_files:
    # Mount
    # $vol = (Mount-DiskImage -ImagePath $iso -PassThru | Get-Volume)
    # $drive = "$($vol.DriveLetter):\"

    try:
        bdmv = Path(f"{drive}/BDMV")
        if not bdmv.exists():
            # Some discs have BDMV directly at root, others nested
            results.append({"iso": iso_path.name, "error": "No BDMV found"})
            continue

        playlists = parse_mpls_dir(bdmv / "PLAYLIST")
        clips = parse_clpi_dir(bdmv / "CLIPINF")
        result = scan_disc(bdmv, playlists, clips)

        results.append({
            "iso": iso_path.name,
            "episodes": len(result.episodes),
            "episode_details": [
                {
                    "num": ep.episode,
                    "playlist": ep.playlist,
                    "duration_min": round(ep.duration_ms / 60000, 1),
                }
                for ep in result.episodes
            ],
            "specials": len(result.special_features),
            "special_details": [
                {
                    "index": sf.index,
                    "playlist": sf.playlist,
                    "category": sf.category,
                    "duration_min": round(sf.duration_ms / 60000, 1),
                }
                for sf in result.special_features
            ],
            "classifications": result.analysis.get("classifications", {}),
        })
    finally:
        # Always dismount
        # Dismount-DiskImage -ImagePath $iso
        pass
```

### 4. Collect IG Menu Cross-Check Data

For each disc, extract IG menu button counts per page and compare
against detected episode/special counts. This provides a confidence
signal — if the menu says 4 episode buttons but analysis found 5
episodes, flag it.

```python
from bdpl.bdmv.ig_stream import parse_ics

def ig_cross_check(bdmv_path, result):
    """Return per-page button summary for cross-checking."""
    ics_path = bdmv_path.parent / "ics_menu.bin"
    # During batch analysis, use the live ICS from the mounted disc
    # (the fixture ics_menu.bin doesn't exist yet)
    hints = result.analysis.get("disc_hints", {})
    ig_raw = hints.get("ig_hints_raw", [])

    if not ig_raw:
        return {"pages": [], "note": "No IG data available"}

    # Group buttons by page
    pages = {}
    for h in ig_raw:
        pid = h.page_id
        if pid not in pages:
            pages[pid] = {"page_id": pid, "buttons": 0, "targets": set()}
        pages[pid]["buttons"] += 1
        if h.jump_title is not None:
            pages[pid]["targets"].add(f"JT({h.jump_title})")
        elif h.playlist is not None:
            pages[pid]["targets"].add(f"PL({h.playlist})")

    # Convert sets to sorted lists for display
    for p in pages.values():
        p["targets"] = sorted(p["targets"])
        p["unique_targets"] = len(p["targets"])

    return {"pages": sorted(pages.values(), key=lambda x: x["page_id"])}
```

### 5. Generate Summary Report

Present results in a table format. Flag any rows where IG cross-check
disagrees with detected counts.

```
┌──────────────────────┬──────┬─────────┬────────────┬───────────────────────┐
│ ISO                  │  Eps │ Specials│ IG Check   │ Notes                 │
├──────────────────────┼──────┼─────────┼────────────┼───────────────────────┤
│ SERIES_D1.ISO        │    4 │       0 │ ✅ 4 btns  │ ch-split, 24min each  │
│ SERIES_D2.ISO        │    4 │       4 │ ✅ 4+4     │ 24min eps, <3min spc  │
│ SERIES_SD.ISO        │    1 │       1 │ ⚠️ no IG   │ 1 ep + 1 dig.archive  │
└──────────────────────┴──────┴─────────┴────────────┴───────────────────────┘

Episode details:
  SERIES_D1.ISO:
    ep1: 00002.mpls 24.0min | ep2: 00002.mpls 24.0min | ...
  ...

Special details:
  SERIES_D2.ISO:
    #1: 00005.mpls creditless_op 1.5min | #2: 00006.mpls creditless_ed 1.5min | ...
  ...
```

**Key indicators:**
- ✅ = IG button count matches detected count
- ⚠️ = No IG data or inconclusive (common for SD/archive discs)
- ❌ = IG button count disagrees — needs user attention

### 6. User Review

Present the summary and ask the user to confirm or correct. Use
`ask_user` for each disc that needs attention:

- For ✅ discs: batch confirm ("These N discs look correct?")
- For ⚠️ discs: ask for expected counts individually
- For ❌ discs: flag disagreement, ask user to provide correct counts

After review, you'll have a confirmed list:
```
disc22: SERIES_D1.ISO → 4 episodes, 0 specials
disc23: SERIES_D2.ISO → 4 episodes, 4 specials
disc24: SERIES_SD.ISO → 1 episode, 1 digital_archive
```

### 7. Create Fixtures (Batch)

For each confirmed disc, follow the [add-disc-fixture](../add-disc-fixture/SKILL.md)
workflow steps 5–8:

1. Re-mount the ISO (if dismounted after step 3)
2. Extract ICS menu data
3. Copy PLAYLIST/, CLIPINF/, index.bdmv, MovieObject.bdmv
4. Create generic bdmt_eng.xml with `TEST DISC {N}`
5. Verify size < 100KB
6. Create integration test file
7. Add conftest.py fixtures
8. Add to test_disc_matrix.py (all 6 parametrizations)
9. Dismount ISO

**Tip**: Process all fixture file copies first (steps 1-5 for all discs),
then create all test files (steps 6-8 for all discs). This minimizes
mount/dismount cycles.

### 8. Handle Analysis Mismatches

If user-confirmed counts don't match analysis results for any disc:

1. **Don't fix yet** — create fixtures for all matching discs first
2. Run tests for matching discs to establish a green baseline
3. Then debug mismatches one at a time using the
   [debug-analysis guide](../add-disc-fixture/references/debug-analysis.md)
4. Follow the structural-signals-over-thresholds approach (see AGENTS.md)
5. After each fix, re-run ALL tests to verify no regressions

### 9. Validate and PR

```bash
python -m pytest tests/ -x -q      # All tests pass
python -m ruff check .              # No lint issues
python -m ruff format --check .     # No format issues
```

Create a single PR for all new fixtures using the
[make-repo-contribution](../make-repo-contribution/SKILL.md) skill.
The PR should list all discs added and any analysis fixes made.

### 10. Clean Up

- Dismount all ISOs
- Delete temporary scripts
- Verify no copyrighted content in fixtures

## Execution Notes

### Mount/Dismount Pattern (PowerShell)

```powershell
# Mount — returns drive letter
$vol = Mount-DiskImage -ImagePath $isoPath -PassThru | Get-Volume
$drive = "$($vol.DriveLetter):\"

# ... do work ...

# Dismount — use original ISO path
Dismount-DiskImage -ImagePath $isoPath
```

**Gotchas:**
- UNC paths may need to be copied locally first for Mount-DiskImage
- Always use `-PassThru` to get the volume object
- Some ISOs mount slowly — add a small delay or retry if drive not ready
- `Dismount-DiskImage` uses the ISO path, not the drive letter

### Parallel vs Sequential

Mount ISOs **one at a time**. Windows can mount multiple, but:
- Fewer drive letters to track
- Cleaner error handling
- Lower risk of forgetting to dismount

### Fixture Numbering

Disc numbers are assigned sequentially from the next available number.
The order should match the ISO sort order (typically alphabetical).
Document the ISO→disc mapping in the PR description.

## Comparison with add-disc-fixture

| Aspect | add-disc-fixture | batch-add-disc-fixtures |
|--------|-----------------|------------------------|
| Input | Single disc path | Folder of ISOs |
| User interaction | Per-disc confirm | Bulk review table |
| IG cross-check | Not included | Included in report |
| When to use | One-off disc | Multiple discs/series |
| Debugging | Inline | After green baseline |
