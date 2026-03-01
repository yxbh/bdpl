# Debugging Analysis Mismatches

When bdpl analysis returns wrong episode or special feature counts,
follow this systematic debugging approach.

## Episode Count Wrong

### Too few episodes

1. **Check play_all detection**: Is the longest playlist classified as
   `play_all`? Look at `classifications` in the analysis output.

2. **Check IG chapter marks**: Play_all decomposition uses IG menu hints
   to find episode boundaries. Verify `ig_menu.chapter_marks` in the
   analysis output matches expected episode start chapters.

3. **Play_all-subset ordering**: If individual playlists exist alongside
   a play_all, check whether the individual playlists' clips are a subset
   of the play_all clips. If `len(pa_episodes) > len(individual_eps)` and
   individual clips ⊆ play_all clips, play_all should be preferred.
   See `ordering.py` ~line 271.

### Too many episodes

1. **Duplicate detection**: Check `duplicate_groups` in analysis output.
   Playlists with identical segment signatures should be deduplicated.

2. **Stream variant filtering**: Variant playlists (same content, different
   audio codec) should be in `variant_mpls` set and excluded.

## Special Feature Count Wrong

### Missing specials

1. **Check IG hints for the specials page**: Extract and inspect IG menu
   hints, particularly page 4+ (specials pages):

   ```python
   from bdpl.bdmv.ig_stream import parse_ig_from_m2ts, extract_menu_hints
   m2ts = Path('D:/BDMV/STREAM/00003.m2ts')  # menu clip
   ics = parse_ig_from_m2ts(m2ts)
   hints = extract_menu_hints(ics)
   for h in hints:
       if h.jump_title is not None:
           print(f'page={h.page_id} btn={h.button_id} JT({h.jump_title})')
   ```

2. **Chapter-selection page filtering**: Pages where ALL buttons have the
   same JumpTitle value are treated as chapter-selection pages. Their
   buttons are added to `chapter_selection_jt` and skipped during
   commentary detection. This can cause false negatives when specials
   pages also happen to route through a single title.

3. **Register-indirect JumpTitle**: `extract_menu_hints` reads `cmd.operand1`
   as the JumpTitle value, but does NOT resolve register-indirect values
   (when `imm_op1=False`, operand1 is a GPR number, not the title). All
   buttons may show the same JT value even though they route differently
   at runtime via MovieObject register checks.

4. **Title-hint supplement**: After IG-based detection, the code supplements
   with title-hint entries. But playlists classified as `"episode"` or
   `"play_all"` are skipped (line ~368 in `__init__.py`). If a playlist is
   classified as `"episode"` but NOT actually used as an episode source
   (episodes came from play_all), it should be treated as `"commentary"`.

5. **Variant filtering**: Check if the missing special's playlist is in the
   `variant_mpls` set. Variant playlists are excluded from special detection.

### Extra specials

1. **Duplicate keys**: Check if multiple IG buttons reference the same
   (playlist, chapter_start) combination. The `seen` set should deduplicate.

2. **Bumper/logo playlists**: Very short playlists (<30s) classified as
   `bumper` should not appear as specials.

## Tracing the Detection Pipeline

For detailed tracing, inspect intermediate state:

```python
result = scan_disc(p, playlists, clips)

# Key analysis fields
hints = result.analysis.get('disc_hints', {})
cls = result.analysis.get('classifications', {})
ig = hints.get('ig_menu', {})
title_pl = hints.get('title_playlists', {})

# Episode source playlists
ep_playlists = {ep.playlist for ep in result.episodes}

# What the IG buttons target
ig_raw = hints.get('ig_hints_raw', [])
for h in sorted(ig_raw, key=lambda x: (x.page_id, x.button_id)):
    if h.jump_title:
        title_idx = h.jump_title - 1
        target_pl = title_pl.get(title_idx)
        print(f'p{h.page_id} b{h.button_id}: JT({h.jump_title}) -> title {title_idx} -> pl {target_pl}')
```

## Key Code Locations

| Component | File | Key Lines |
|-----------|------|-----------|
| Special feature detection | `analyze/__init__.py` | `_detect_special_features()` |
| Chapter-selection heuristic | `analyze/__init__.py` | `chapter_selection_jt` set |
| Title-hint supplement | `analyze/__init__.py` | After IG hints loop |
| Commentary relabeling | `analyze/__init__.py` | Post-loop `f.category == "episode"` |
| Play_all-subset ordering | `analyze/ordering.py` | `indiv_clips <= pa_clips` check |
| IG hint extraction | `bdmv/ig_stream.py` | `extract_menu_hints()` |
| ICS fallback loading | `analyze/__init__.py` | `_parse_ig_hints()` |

## Known Limitations

- **Register-indirect JumpTitle** is not resolved. When all IG buttons use
  `SET GPR[n] = value; JumpTitle(GPR[n])`, the code reads the register
  number as the title, not the value. The MovieObject handles routing via
  PSR[10] (selected button ID) at runtime.

- **Multi-feature playlists** with register-based chapter selection
  (SET reg2 before JumpTitle) are supported, but only when `imm_op2=True`
  (immediate value). Register-indirect chapter indices are not resolved.

## How to Fix Mismatches — Structural Signals, Not Thresholds

When analysis returns wrong counts, resist the urge to add a numeric
threshold or ratio guard that fixes the immediate disc.  Thresholds are
"just happens to work" — they break on the next disc.

### The right process

1. **Dump data across fixtures** — compare the failing disc against
   fixtures that work.  Key data to examine:
   - Chapter durations (look for repeating OP/body/ED cycles)
   - IG menu buttons per page (episode pages ~5 buttons, scene grids ~10)
   - IG chapter marks (JT + reg2 patterns)
   - Segment labels, play item structure, title counts

2. **Find a structural signal** — something the disc data says about
   itself.  Ask: "What makes the working discs structurally different
   from the failing disc?"

3. **Require positive evidence** — the code should ask "does the data
   say this IS an episode compilation?" not "does the data say this is
   NOT a movie?".  Positive detection produces zero false positives
   when the signal is absent.

4. **Validate across ALL fixtures** — run the new logic against every
   fixture, not just the one that broke.

### Anti-patterns to avoid

- `if count <= N: return []` — arbitrary threshold, will break
- `if ratio > X: return []` — same problem
- Lowering/raising an existing threshold to accommodate one more disc
- Any fix that only looks at the failing disc without comparing others

### Example: Chapter-split detection

Bad (threshold): `if chapters_per_episode > 7: don't split`
Good (structural): detect repeating OP/body/ED chapter cycle via
`_detect_episode_periodicity()` — only split when positive evidence
of episode structure exists.
