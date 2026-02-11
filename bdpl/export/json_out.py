"""JSON export for disc analysis results."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from bdpl.model import DiscAnalysis


def analysis_to_dict(analysis: DiscAnalysis) -> dict:
    """Convert a DiscAnalysis to a JSON-serializable dict."""
    playlists = []
    for pl in analysis.playlists:
        play_items = []
        for pi in pl.play_items:
            play_items.append(
                {
                    "clip_id": pi.clip_id,
                    "m2ts": pi.m2ts,
                    "in_time": pi.in_time,
                    "out_time": pi.out_time,
                    "duration_ms": pi.duration_ms,
                    "label": pi.label,
                    "segment_key": list(pi.segment_key()),
                    "streams": [
                        {"pid": s.pid, "codec": s.codec, "lang": s.lang} for s in pi.streams
                    ],
                }
            )
        chapters = []
        for ch in pl.chapters:
            chapters.append(
                {
                    "mark_id": ch.mark_id,
                    "mark_type": ch.mark_type,
                    "play_item_ref": ch.play_item_ref,
                    "timestamp": ch.timestamp,
                    "duration_ms": ch.duration_ms,
                }
            )
        streams_flat = []
        for pi in pl.play_items:
            for s in pi.streams:
                streams_flat.append({"pid": s.pid, "codec": s.codec, "lang": s.lang})
        playlists.append(
            {
                "mpls": pl.mpls,
                "duration_ms": pl.duration_ms,
                "play_items": play_items,
                "chapters": chapters,
                "streams": streams_flat,
            }
        )

    episodes = []
    for ep in analysis.episodes:
        segments = []
        for seg in ep.segments:
            segments.append(
                {
                    "key": list(seg.key),
                    "clip_id": seg.clip_id,
                    "in_ms": seg.in_ms,
                    "out_ms": seg.out_ms,
                    "duration_ms": seg.duration_ms,
                    "label": seg.label,
                }
            )
        episodes.append(
            {
                "episode": ep.episode,
                "playlist": ep.playlist,
                "duration_ms": ep.duration_ms,
                "confidence": ep.confidence,
                "segments": segments,
            }
        )

    warnings = []
    for w in analysis.warnings:
        warnings.append(
            {
                "code": w.code,
                "message": w.message,
                "context": w.context,
            }
        )

    special_features = []
    for sf in analysis.special_features:
        entry: dict = {
            "index": sf.index,
            "playlist": sf.playlist,
            "duration_ms": sf.duration_ms,
            "category": sf.category,
        }
        if sf.chapter_start is not None:
            entry["chapter_start"] = sf.chapter_start
        special_features.append(entry)

    return {
        "schema_version": "bdpl.disc.v1",
        "disc": {
            "path": analysis.path,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
        "playlists": playlists,
        "episodes": episodes,
        "special_features": special_features,
        "warnings": warnings,
        "analysis": analysis.analysis,
    }


def export_json(analysis: DiscAnalysis, path: str | Path | None = None, pretty: bool = True) -> str:
    """Export analysis to JSON. If path given, write to file. Always returns JSON string."""
    data = analysis_to_dict(analysis)
    indent = 2 if pretty else None
    text = json.dumps(data, indent=indent, default=str)
    if path is not None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    return text
