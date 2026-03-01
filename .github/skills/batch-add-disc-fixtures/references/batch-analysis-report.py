# Batch Analysis Report — Reference Template
#
# This script template is used by the batch-add-disc-fixtures skill.
# The agent adapts it for each batch run — it is NOT meant to be
# executed standalone.
#
# Usage: The agent will inline this logic in a Python session,
# substituting actual ISO paths and drive letters.

"""
Batch-analyze mounted Blu-ray ISOs and produce a summary report.

Expects a list of (iso_name, bdmv_path) tuples for already-mounted discs.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

# bdpl must be installed: pip install -e ".[dev]"
from bdpl.analyze import scan_disc
from bdpl.bdmv.clpi import parse_clpi_dir
from bdpl.bdmv.mpls import parse_mpls_dir


@dataclass
class DiscReport:
    iso_name: str
    episodes: int
    specials: int
    episode_details: list[dict]
    special_details: list[dict]
    classifications: dict
    ig_pages: list[dict]
    ig_note: str
    ig_match: str  # "ok", "warn", "mismatch"


def analyze_one(iso_name: str, bdmv_path: Path) -> DiscReport:
    """Analyze a single mounted BDMV and return a structured report."""
    playlists = parse_mpls_dir(bdmv_path / "PLAYLIST")
    clips = parse_clpi_dir(bdmv_path / "CLIPINF")
    result = scan_disc(bdmv_path, playlists, clips)

    # Episode details
    ep_details = [
        {
            "num": ep.episode,
            "playlist": ep.playlist,
            "duration_min": round(ep.duration_ms / 60000, 1),
        }
        for ep in result.episodes
    ]

    # Special details
    sp_details = [
        {
            "index": sf.index,
            "playlist": sf.playlist,
            "category": sf.category,
            "duration_min": round(sf.duration_ms / 60000, 1),
        }
        for sf in result.special_features
    ]

    # IG cross-check
    hints = result.analysis.get("disc_hints", {})
    ig_raw = hints.get("ig_hints_raw", [])
    ig_pages = _extract_ig_pages(ig_raw)
    ig_match, ig_note = _ig_cross_check(
        ig_pages, len(result.episodes), len(result.special_features)
    )

    return DiscReport(
        iso_name=iso_name,
        episodes=len(result.episodes),
        specials=len(result.special_features),
        episode_details=ep_details,
        special_details=sp_details,
        classifications=result.analysis.get("classifications", {}),
        ig_pages=ig_pages,
        ig_note=ig_note,
        ig_match=ig_match,
    )


def _extract_ig_pages(ig_raw: list) -> list[dict]:
    """Group IG hints by page, counting buttons and unique targets."""
    if not ig_raw:
        return []

    pages: dict[int, dict] = {}
    for h in ig_raw:
        pid = h.page_id
        if pid not in pages:
            pages[pid] = {"page_id": pid, "buttons": 0, "targets": set()}
        pages[pid]["buttons"] += 1
        if h.jump_title is not None:
            pages[pid]["targets"].add(f"JT({h.jump_title})")
        elif h.playlist is not None:
            pages[pid]["targets"].add(f"PL({h.playlist})")

    result = []
    for p in sorted(pages.values(), key=lambda x: x["page_id"]):
        result.append(
            {
                "page_id": p["page_id"],
                "buttons": p["buttons"],
                "unique_targets": len(p["targets"]),
                "targets": sorted(p["targets"]),
            }
        )
    return result


def _ig_cross_check(ig_pages: list[dict], ep_count: int, sp_count: int) -> tuple[str, str]:
    """
    Compare IG page button counts against detected episode/special counts.

    Returns (match_status, note) where match_status is one of:
    - "ok": IG data supports the detected counts
    - "warn": No IG data or inconclusive
    - "mismatch": IG data disagrees with detected counts
    """
    if not ig_pages:
        return "warn", "No IG data available"

    # Heuristic: the page with the most buttons targeting unique playlists
    # that roughly matches episode count is likely the episode page.
    # Pages with fewer buttons targeting unique playlists may be special pages.
    #
    # This is advisory only — the user makes the final call.
    notes = []
    for page in ig_pages:
        notes.append(
            f"p{page['page_id']}: {page['buttons']} btns, {page['unique_targets']} unique targets"
        )

    # Simple match check: is there a page with unique_targets == ep_count?
    ep_page_match = any(p["unique_targets"] == ep_count for p in ig_pages)
    if ep_page_match:
        return "ok", "; ".join(notes)

    # Check if any page is close (off by 1, which can happen with
    # "play all" button being counted)
    close_match = any(abs(p["unique_targets"] - ep_count) <= 1 for p in ig_pages)
    if close_match:
        return "ok", "; ".join(notes) + " (close match)"

    return "mismatch", "; ".join(notes)


def format_report(reports: list[DiscReport], start_disc: int) -> str:
    """Format batch analysis results as a readable summary table."""
    lines = []
    lines.append("=" * 72)
    lines.append("BATCH ANALYSIS REPORT")
    lines.append("=" * 72)
    lines.append("")

    # Summary table
    match_icons = {"ok": "✅", "warn": "⚠️", "mismatch": "❌"}
    lines.append(f"{'#':<5} {'ISO':<30} {'Eps':>4} {'Spc':>4} {'IG':>3} Notes")
    lines.append("-" * 72)
    for i, r in enumerate(reports):
        disc_n = start_disc + i
        icon = match_icons.get(r.ig_match, "?")
        lines.append(
            f"d{disc_n:<4} {r.iso_name:<30} {r.episodes:>4} {r.specials:>4}  {icon}  {r.ig_note}"
        )

    # Episode details
    lines.append("")
    lines.append("EPISODE DETAILS")
    lines.append("-" * 72)
    for i, r in enumerate(reports):
        disc_n = start_disc + i
        if r.episode_details:
            eps = " | ".join(
                f"ep{e['num']}: {e['playlist']} {e['duration_min']}min" for e in r.episode_details
            )
            lines.append(f"  disc{disc_n}: {eps}")

    # Special details
    lines.append("")
    lines.append("SPECIAL DETAILS")
    lines.append("-" * 72)
    for i, r in enumerate(reports):
        disc_n = start_disc + i
        if r.special_details:
            sps = " | ".join(
                f"#{s['index']}: {s['playlist']} {s['category']} {s['duration_min']}min"
                for s in r.special_details
            )
            lines.append(f"  disc{disc_n}: {sps}")

    # Classifications
    lines.append("")
    lines.append("CLASSIFICATIONS")
    lines.append("-" * 72)
    for i, r in enumerate(reports):
        disc_n = start_disc + i
        if r.classifications:
            cls_str = ", ".join(f"{k}: {v}" for k, v in sorted(r.classifications.items()))
            lines.append(f"  disc{disc_n}: {cls_str}")

    lines.append("")
    lines.append("=" * 72)
    return "\n".join(lines)


if __name__ == "__main__":
    # Example usage — agent substitutes real values
    print("This script is a reference template. See SKILL.md for usage.")
