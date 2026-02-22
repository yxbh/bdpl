"""bdpl CLI — Blu-ray disc playlist analyzer."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from bdpl.analyze import scan_disc
from bdpl.bdmv.clpi import parse_clpi_dir
from bdpl.bdmv.mpls import parse_mpls_dir
from bdpl.export import (
    export_digital_archive_images,
    export_json,
    get_digital_archive_dry_run,
    text_report,
)
from bdpl.export.m3u import export_m3u

app = typer.Typer(name="bdpl", help="Blu-ray disc playlist analyzer")
console = Console(stderr=True)


def resolve_bdmv(path_str: str) -> Path:
    """Resolve path to actual BDMV directory.

    If path points to a dir containing BDMV/, use that.
    If path IS the BDMV dir (contains PLAYLIST/), use it directly.
    Otherwise, error out.
    """
    p = Path(path_str).resolve()
    if not p.is_dir():
        console.print(f"[red]Error:[/red] {p} is not a directory")
        raise typer.Exit(1)
    # Already the BDMV dir
    if (p / "PLAYLIST").is_dir():
        return p
    # Parent containing BDMV/
    bdmv_sub = p / "BDMV"
    if bdmv_sub.is_dir() and (bdmv_sub / "PLAYLIST").is_dir():
        return bdmv_sub
    console.print(
        f"[red]Error:[/red] Cannot find BDMV structure at {p}\n"
        "  Expected a directory containing PLAYLIST/ (or a parent with BDMV/PLAYLIST/)"
    )
    raise typer.Exit(1)


def _parse_and_analyze(bdmv: str) -> "DiscAnalysis":  # noqa: F821
    """Common helper: resolve BDMV, parse files, run analysis."""
    bdmv_path = resolve_bdmv(bdmv)
    playlist_dir = bdmv_path / "PLAYLIST"
    clipinf_dir = bdmv_path / "CLIPINF"

    with console.status("[bold]Parsing BDMV structure…"):
        playlists = parse_mpls_dir(playlist_dir)
        clips = parse_clpi_dir(clipinf_dir) if clipinf_dir.is_dir() else {}

    with console.status("[bold]Analyzing disc…"):
        result = scan_disc(bdmv_path, playlists, clips)

    return result


@app.command()
def scan(
    bdmv: str = typer.Argument(..., help="Path to BDMV directory"),
    output: str = typer.Option(None, "-o", "--output", help="Output JSON file path"),
    pretty: bool = typer.Option(True, "--pretty/--compact"),
    stdout: bool = typer.Option(False, "--stdout", help="Print JSON to stdout"),
):
    """Detect episode playlists and emit structured mapping."""
    analysis = _parse_and_analyze(bdmv)
    json_str = export_json(analysis, path=output, pretty=pretty)
    if stdout or output is None:
        typer.echo(json_str)
    elif output:
        console.print(f"[green]Wrote:[/green] {output}")


@app.command()
def explain(
    bdmv: str = typer.Argument(..., help="Path to BDMV directory"),
    playlist: str = typer.Option(None, "--playlist", "-p", help="Explain specific playlist"),
):
    """Explain why certain playlists were chosen/rejected."""
    analysis = _parse_and_analyze(bdmv)
    report = text_report(analysis)

    if playlist:
        # Show detailed info for one playlist
        match = None
        for pl in analysis.playlists:
            if pl.mpls == playlist or pl.mpls == playlist + ".mpls":
                match = pl
                break
        if match is None:
            console.print(f"[red]Playlist not found:[/red] {playlist}")
            raise typer.Exit(1)
        typer.echo(f"Playlist: {match.mpls}")
        typer.echo(f"Duration: {match.duration_ms:.0f} ms ({match.duration_seconds:.1f} s)")
        typer.echo(f"Items:    {len(match.play_items)}")
        typer.echo(f"Chapters: {len(match.chapters)}")
        cls = analysis.analysis.get("classifications", {}).get(match.mpls, "unknown")
        typer.echo(f"Class:    {cls}")
        typer.echo("")
        for i, pi in enumerate(match.play_items):
            typer.echo(f"  [{i}] {pi.clip_id} ({pi.m2ts})  {pi.duration_ms:.0f}ms  [{pi.label}]")
    else:
        typer.echo(report)


@app.command(name="playlist")
def playlist_cmd(
    bdmv: str = typer.Argument(..., help="Path to BDMV directory"),
    out: str = typer.Option("./Playlists", "--out", help="Output directory"),
):
    """Generate .m3u debug playlists for quick episode preview (no dependencies)."""
    analysis = _parse_and_analyze(bdmv)

    created = export_m3u(analysis, out)
    for p in created:
        console.print(f"[green]Created:[/green] {p}")
    if not created:
        console.print("[yellow]No episodes found — no playlists generated.[/yellow]")


@app.command()
def remux(
    bdmv: str = typer.Argument(..., help="Path to BDMV directory"),
    out: str = typer.Option("./Episodes", "--out", help="Output directory"),
    pattern: str = typer.Option(
        "{name} - S01E{ep:02d}.mkv",
        "--pattern",
        help="Output filename pattern ({name}=disc folder, {ep}=episode number)",
    ),
    specials: bool = typer.Option(False, "--specials", help="Also remux special features"),
    specials_pattern: str = typer.Option(
        "{name} - S00E{idx:02d} - {category}.mkv",
        "--specials-pattern",
        help="Filename pattern for specials: {name}, {idx}, {category}",
    ),
    mkvmerge_path: str = typer.Option(None, "--mkvmerge-path", help="Path to mkvmerge executable"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print commands without executing"),
):
    """Remux episodes to MKV with chapters and track names.

    Reads the source m2ts streams and produces one MKV per episode with
    chapter markers and named audio/subtitle tracks.  Requires mkvmerge
    (MKVToolNix).

    Use --specials to also remux special features (creditless OP/ED, extras).
    """
    from bdpl.export.mkv_chapters import (
        export_chapter_mkv,
        export_specials_mkv,
        get_dry_run_commands,
        get_specials_dry_run,
    )

    analysis = _parse_and_analyze(bdmv)

    if dry_run:
        plans = get_dry_run_commands(analysis, out, pattern=pattern)
        for plan in plans:
            console.print(f"\n[bold]Episode {plan['episode']}[/bold] → {plan['output']}")
            console.print(f"  [dim]{' '.join(plan['command'])}[/dim]")
            console.print("  [dim]Chapters:[/dim]")
            for line in plan["chapters_xml"].splitlines()[:15]:
                console.print(f"    {line}")
        if specials:
            sf_plans = get_specials_dry_run(analysis, out, pattern=specials_pattern)
            for plan in sf_plans:
                console.print(
                    f"\n[bold]Special {plan['index']} ({plan['category']})[/bold]"
                    f" → {plan['output']}"
                )
                console.print(f"  [dim]{' '.join(plan['command'])}[/dim]")
        return

    try:
        from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn

        total_items = len(analysis.episodes)
        if specials:
            total_items += len(analysis.special_features)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            task_id = progress.add_task("Remuxing…", total=total_items)

            def _on_progress(current: int, total: int, name: str) -> None:
                progress.update(task_id, completed=current - 1, description=f"Remuxing {name}…")

            created = export_chapter_mkv(
                analysis,
                out,
                mkvmerge_path=mkvmerge_path,
                on_progress=_on_progress,
                pattern=pattern,
            )
            progress.update(task_id, completed=len(analysis.episodes))

            if specials and analysis.special_features:

                def _on_sf_progress(current: int, total: int, name: str) -> None:
                    progress.update(
                        task_id,
                        completed=len(analysis.episodes) + current - 1,
                        description=f"Remuxing {name}…",
                    )

                sf_created = export_specials_mkv(
                    analysis,
                    out,
                    mkvmerge_path=mkvmerge_path,
                    on_progress=_on_sf_progress,
                    pattern=specials_pattern,
                )
                created.extend(sf_created)

            progress.update(task_id, completed=total_items, description="Done")
    except RuntimeError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    for p in created:
        console.print(f"[green]Created:[/green] {p}")
    if not created:
        console.print("[yellow]No episodes found.[/yellow]")


@app.command(name="archive")
def archive_cmd(
    bdmv: str = typer.Argument(..., help="Path to BDMV directory"),
    out: str = typer.Option("./DigitalArchive", "--out", help="Output directory for images"),
    image_format: str = typer.Option("jpg", "--format", help="Image format: jpg or png"),
    ffmpeg_path: str = typer.Option(None, "--ffmpeg-path", help="Path to ffmpeg executable"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print commands without executing"),
):
    """Extract digital-archive images (menu stills) as files.

    Detects playlists classified as digital archives and captures one frame per
    archive item using ffmpeg.
    """
    analysis = _parse_and_analyze(bdmv)

    try:
        if dry_run:
            plans = get_digital_archive_dry_run(
                analysis,
                out,
                ffmpeg_path=ffmpeg_path,
                image_format=image_format,
            )
            if not plans:
                console.print("[yellow]No digital archive playlists found.[/yellow]")
                return

            for plan in plans:
                console.print(
                    f"[bold]{plan['playlist']}[/bold] item {plan['index']:03d}"
                    f" ({plan['clip_id']})"
                )
                console.print(f"  [dim]{' '.join(plan['command'])}[/dim]")
            return

        created = export_digital_archive_images(
            analysis,
            out,
            ffmpeg_path=ffmpeg_path,
            image_format=image_format,
        )
    except (RuntimeError, ValueError) as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    if not created:
        console.print("[yellow]No digital archive playlists found.[/yellow]")
        return

    for path in created:
        console.print(f"[green]Created:[/green] {path}")


if __name__ == "__main__":
    app()
