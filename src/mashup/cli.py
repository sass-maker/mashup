"""mashup — assemble themed mashups from a creator's own archive."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from mashup import pipeline
from mashup.config import ConfigError, load_config
from mashup.models import EDL
from mashup.plan.prompt import parse_duration
from mashup.render import edl_to_transcript, load_edl, render, save_edl

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help=__doc__,
    invoke_without_command=True,
)
console = Console()
err = Console(stderr=True)

WORKDIR_OPT = Annotated[
    Path | None, typer.Option("--workdir", help="State directory (default .mashup)")
]


def _progress(label: str):
    def cb(done: int, total: int) -> None:
        err.print(f"  {label}: {done}/{total}", end="\r")

    return cb


def _config(workdir: Path | None, *, require_key: bool = True):
    try:
        return load_config(workdir, require_key=require_key)
    except ConfigError as exc:
        err.print(f"[red]{exc}[/red]")
        raise typer.Exit(2) from exc


def _show_counts(counts: dict[str, int]) -> None:
    table = Table(show_header=False, box=None)
    for key, value in counts.items():
        table.add_row(key, str(value))
    console.print(table)


def _summarise(edl: EDL) -> None:
    console.print(
        f"[bold]{edl.strategy}[/bold]  "
        f"{len(edl.clips)} clips  {edl.duration:.0f}s  score {edl.score:.3f}"
    )
    terms = edl.terms.model_dump()
    console.print("  " + "  ".join(f"{k}={v:.2f}" for k, v in terms.items()))
    for line in edl.rationale:
        console.print(f"  [dim]{line}[/dim]")


# ---- stages -------------------------------------------------------------


@app.command()
def ingest(
    input_dir: Annotated[Path, typer.Option("--input", "-i", help="Archive directory")],
    workdir: WORKDIR_OPT = None,
    transcribe: Annotated[
        bool, typer.Option("--transcribe/--no-transcribe", help="Generate missing subtitles")
    ] = True,
) -> None:
    """Ingest media + subtitles and split into segments."""
    cfg = _config(workdir, require_key=False)
    counts = pipeline.ingest(input_dir, cfg, allow_transcribe=transcribe)
    _show_counts(counts)


@app.command()
def enrich(
    workdir: WORKDIR_OPT = None,
    concurrency: Annotated[int, typer.Option("--concurrency", "-c")] = 4,
) -> None:
    """Extract topic/role/energy/context metadata for each segment."""
    cfg = _config(workdir)
    counts = pipeline.enrich(cfg, concurrency=concurrency, progress=_progress("enrich"))
    _show_counts(counts)


@app.command()
def embed(
    workdir: WORKDIR_OPT = None,
    reset: Annotated[
        bool,
        typer.Option("--reset", help="Drop existing vectors first (use after a model change)"),
    ] = False,
) -> None:
    """Embed segments for retrieval."""
    cfg = _config(workdir)
    counts = pipeline.embed(cfg, progress=_progress("embed"), reset=reset)
    _show_counts(counts)


@app.command()
def status(workdir: WORKDIR_OPT = None) -> None:
    """Show what has been ingested, enriched, and embedded."""
    from mashup.store import Store

    cfg = _config(workdir, require_key=False)
    if not cfg.db_path.exists():
        err.print(f"No archive at {cfg.db_path}. Run `mashup ingest` first.")
        raise typer.Exit(1)
    with Store(cfg.db_path) as store:
        _show_counts(store.counts())


# ---- planning -----------------------------------------------------------


@app.command()
def build(
    prompt: Annotated[str, typer.Option("--prompt", "-p", help="What the mashup is about")],
    output: Annotated[Path, typer.Option("--output", "-o")] = Path("output"),
    duration: Annotated[float, typer.Option("--duration", "-d", help="Target seconds")] = 420.0,
    variants: Annotated[int, typer.Option("--variants", "-n", min=1, max=3)] = 3,
    workdir: WORKDIR_OPT = None,
    do_render: Annotated[bool, typer.Option("--render/--no-render")] = True,
    crossfade: Annotated[float, typer.Option("--crossfade", help="Seconds; 0 = hard cuts")] = 0.0,
    snap: Annotated[bool, typer.Option("--snap/--no-snap", help="Snap cuts to pauses")] = True,
    subtitles: Annotated[str, typer.Option("--subtitles", help="none|sidecar|burn")] = "sidecar",
    baselines: Annotated[
        bool, typer.Option("--baselines", help="Also emit semantic + random controls")
    ] = False,
) -> None:
    """Plan mashup variants and render them."""
    cfg = _config(workdir)
    target = parse_duration(prompt, duration)
    strategies = pipeline.AI_STRATEGIES[:variants]

    edls = pipeline.make_mashups(
        prompt,
        cfg,
        target=target,
        strategies=strategies,
        include_baselines=baselines,
        snap=snap,
        crossfade=crossfade,
    )

    output.mkdir(parents=True, exist_ok=True)
    for edl in edls:
        _summarise(edl)
        save_edl(edl, output / f"{edl.strategy}.json")
        if do_render:
            out = output / f"{edl.strategy}.mp4"
            render(
                edl,
                out,
                crossfade=crossfade,
                subtitles=subtitles,
                workdir=cfg.workdir,
                progress=_progress(edl.strategy),
            )
            console.print(f"  -> {out}")
    console.print(f"\n[green]Wrote {len(edls)} variants to {output}[/green]")


@app.command()
def preview(edl_path: Annotated[Path, typer.Argument()]) -> None:
    """Print the assembled transcript with source timestamps."""
    console.print(edl_to_transcript(load_edl(edl_path)))


@app.command(name="render")
def render_cmd(
    edl_path: Annotated[Path, typer.Argument()],
    output: Annotated[Path, typer.Option("--output", "-o")],
    workdir: WORKDIR_OPT = None,
    crossfade: Annotated[float, typer.Option("--crossfade")] = 0.0,
    subtitles: Annotated[str, typer.Option("--subtitles")] = "sidecar",
) -> None:
    """Render an (optionally hand-edited) EDL to MP4."""
    cfg = _config(workdir, require_key=False)
    edl = load_edl(edl_path)
    render(
        edl,
        output,
        crossfade=crossfade,
        subtitles=subtitles,
        workdir=cfg.workdir,
        progress=_progress("render"),
    )
    console.print(f"[green]{output}[/green]")


@app.command(name="serve")
def serve_cmd(
    edl_path: Annotated[Path, typer.Argument(help="EDL JSON to edit")],
    workdir: WORKDIR_OPT = None,
    host: Annotated[str, typer.Option("--host", help="Loopback only")] = "127.0.0.1",
    port: Annotated[int, typer.Option("--port")] = 8765,
) -> None:
    """Open the transcript editor for an EDL (Ctrl-C to stop)."""
    from mashup.serve import serve as serve_editor

    cfg = _config(workdir, require_key=False)
    if not edl_path.exists():
        err.print(f"[red]No EDL at {edl_path}[/red]")
        raise typer.Exit(1)
    console.print(f"[green]http://{host}:{port}[/green]  editing {edl_path}")
    try:
        serve_editor(edl_path, cfg, host=host, port=port)
    except ValueError as exc:
        err.print(f"[red]{exc}[/red]")
        raise typer.Exit(2) from exc


# ---- validation ---------------------------------------------------------


@app.command()
def experiment(
    prompt: Annotated[str, typer.Option("--prompt", "-p")],
    output: Annotated[Path, typer.Option("--output", "-o")] = Path("experiment"),
    duration: Annotated[float, typer.Option("--duration", "-d")] = 420.0,
    workdir: WORKDIR_OPT = None,
    seed: Annotated[int, typer.Option("--seed", help="Shuffles the blind labels")] = 0,
    do_render: Annotated[bool, typer.Option("--render/--no-render")] = True,
    subtitles: Annotated[str, typer.Option("--subtitles")] = "sidecar",
) -> None:
    """Generate the five blind conditions for the validation experiment."""
    from mashup.experiment import run_experiment

    cfg = _config(workdir)
    target = parse_duration(prompt, duration)
    blinds = run_experiment(prompt, cfg, outdir=output, target=target, seed=seed)

    for blind in blinds:
        edl = load_edl(blind.edl_path)
        console.print(f"[bold]{blind.label}[/bold]  {len(edl.clips)} clips  {edl.duration:.0f}s")
        if do_render:
            out = output / f"{blind.label}.mp4"
            render(
                edl,
                out,
                subtitles=subtitles,
                workdir=cfg.workdir,
                progress=_progress(blind.label),
            )
    console.print(
        f"\n[green]Wrote 5 blind variants to {output}[/green]\n"
        f"Rate them in {output / 'ratings.csv'} — do not open KEY.json first.\n"
        f"Then run: mashup evaluate {output}"
    )


@app.command()
def evaluate(
    outdir: Annotated[Path, typer.Argument(help="Experiment directory")],
) -> None:
    """Unblind a completed rating sheet and check the PRD's criteria."""
    from mashup.experiment import summarise_ratings

    try:
        result = summarise_ratings(outdir)
    except (OSError, RuntimeError) as exc:
        err.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc

    console.print(f"viewers: {result['viewers']}")
    console.print("beats semantic baseline: " + str(result["beats_semantic"]))
    console.print(f"best AI condition: [bold]{result['best_ai_condition']}[/bold]")
    for name, passed in result["criteria"].items():
        mark = "[green]PASS[/green]" if passed else "[red]FAIL[/red]"
        console.print(f"  {mark}  {name}")


@app.command()
def churn(
    original: Annotated[Path, typer.Argument(help="Generated EDL")],
    edited: Annotated[Path, typer.Argument(help="EDL after human editing")],
) -> None:
    """Measure how much of the generated timeline a creator had to change."""
    from mashup.experiment import timeline_churn

    result = timeline_churn(load_edl(original), load_edl(edited))
    _show_counts({k: v for k, v in result.items() if isinstance(v, int)})
    verdict = (
        "[green]within the kill criterion[/green]"
        if result["passes_kill_criterion"]
        else "[red]exceeds the 30% kill criterion[/red]"
    )
    console.print(f"churn {result['churn']:.1%} — {verdict}")


@app.callback()
def main(
    ctx: typer.Context,
    input_dir: Annotated[Path | None, typer.Option("--input", "-i")] = None,
    prompt: Annotated[str | None, typer.Option("--prompt", "-p")] = None,
    duration: Annotated[float, typer.Option("--duration", "-d")] = 420.0,
    variants: Annotated[int, typer.Option("--variants", "-n", min=1, max=3)] = 3,
    output: Annotated[Path, typer.Option("--output", "-o")] = Path("output"),
    workdir: WORKDIR_OPT = None,
) -> None:
    """Run the whole pipeline in one shot when called without a subcommand.

    mashup --input ./archive --prompt "..." --duration 420 --variants 3
    """
    if ctx.invoked_subcommand is not None:
        return
    if input_dir is None or prompt is None:
        console.print(ctx.get_help())
        raise typer.Exit(0)

    cfg = _config(workdir)
    err.print("[dim]ingesting…[/dim]")
    pipeline.ingest(input_dir, cfg)
    err.print("[dim]enriching…[/dim]")
    pipeline.enrich(cfg, progress=_progress("enrich"))
    err.print("[dim]embedding…[/dim]")
    pipeline.embed(cfg, progress=_progress("embed"))

    target = parse_duration(prompt, duration)
    edls = pipeline.make_mashups(
        prompt, cfg, target=target, strategies=pipeline.AI_STRATEGIES[:variants]
    )
    output.mkdir(parents=True, exist_ok=True)
    for edl in edls:
        _summarise(edl)
        save_edl(edl, output / f"{edl.strategy}.json")
        out = output / f"{edl.strategy}.mp4"
        render(edl, out, workdir=cfg.workdir, progress=_progress(edl.strategy))
        console.print(f"  -> {out}")


if __name__ == "__main__":
    app()
