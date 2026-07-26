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
from mashup.pipeline import DEFAULT_POOL
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
    """Counter-style progress, for the staged pipeline commands."""

    def cb(done: int, total: int) -> None:
        err.print(f"  {label}: {done}/{total}", end="\r")

    return cb


def _status(label: str):
    """Message-style progress. `render()` reports status strings, not counts —
    passing the counter callback to it raises a TypeError deep in the render."""

    def cb(message: str) -> None:
        err.print(f"  {label}: {message}")

    return cb


def _config(workdir: Path | None, *, require_key: bool = True):
    try:
        return load_config(workdir, require_key=require_key)
    except ConfigError as exc:
        err.print(f"[red]{exc}[/red]")
        raise typer.Exit(2) from exc


def _runnable(
    workdir: Path | None,
    *,
    chat: bool = False,
    embed: bool = False,
):
    """Load config, requiring a key only from backends that will actually
    call out. With both backends local, every command runs uncredentialled."""
    cfg = _config(workdir, require_key=False)
    gateway_stages = [
        name
        for name, enabled, backend in (
            ("chat", chat, cfg.chat_backend),
            ("embed", embed, cfg.embed_backend),
        )
        if enabled and backend == "gateway"
    ]
    if gateway_stages and not cfg.gateway_api_key:
        which = [f"MASHUP_{n.upper()}_BACKEND=gateway" for n in gateway_stages]
        err.print(
            f"[red]{' and '.join(which)} needs MASHUP_GATEWAY_API_KEY.[/red]\n"
            "Unset it to run that stage locally instead."
        )
        raise typer.Exit(2)
    return cfg


def _notice(message: str) -> None:
    err.print(f"[yellow]{message}[/yellow]")


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
    """Extract topic/role/energy/context metadata for each segment.

    Runs a local mlx model on Apple silicon by default; set
    MASHUP_CHAT_BACKEND=gateway to use the fleet gateway instead.
    """
    cfg = _runnable(workdir, chat=True)
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
    """Embed segments for retrieval.

    Runs a local HuggingFace encoder by default. Set MASHUP_LOCAL_EMBED_MODEL
    to pick another (`mashup models` lists them), or MASHUP_EMBED_BACKEND=gateway
    to embed through the fleet gateway instead.
    """
    cfg = _runnable(workdir, embed=True)
    counts = pipeline.embed(cfg, progress=_progress("embed"), reset=reset, notice=_notice)
    _show_counts(counts)


@app.command()
def models(workdir: WORKDIR_OPT = None) -> None:
    """Show which models this run would use, and the local aliases available."""
    from mashup.embedding import DEFAULT_LOCAL_MODEL, LOCAL_MODELS

    cfg = _config(workdir, require_key=False)
    active = Table(box=None)
    active.add_column("stage")
    active.add_column("backend")
    active.add_column("model")
    active.add_row(
        "chat",
        cfg.chat_backend,
        cfg.local_chat_model if _local(cfg.chat_backend) else cfg.chat_model,
    )
    active.add_row(
        "embed",
        cfg.embed_backend,
        cfg.local_embed_model if _local(cfg.embed_backend) else cfg.embed_model,
    )
    console.print(active)
    console.print(f"\n[dim]gateway needed: {'yes' if cfg.needs_gateway else 'no'}[/dim]\n")

    table = Table(box=None)
    table.add_column("embed alias")
    table.add_column("repo")
    table.add_column("dim", justify="right")
    table.add_column("pooling")
    for alias, spec in LOCAL_MODELS.items():
        mark = " [green](default)[/green]" if alias == DEFAULT_LOCAL_MODEL else ""
        table.add_row(alias + mark, spec.repo, str(spec.dim), spec.pooling)
    console.print(table)
    console.print(
        "\n[dim]Any HuggingFace repo id also works for embeddings (mean pooling\n"
        "assumed). Chat takes any mlx-lm repo id via MASHUP_LOCAL_CHAT_MODEL.[/dim]"
    )


def _local(backend: str) -> bool:
    return backend == "local"


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
        # More than one line here means retrieval is comparing vectors from
        # different models, which is silently meaningless.
        used = store.embedding_models()
        if used:
            console.print()
            for model, n in sorted(used.items()):
                console.print(f"  {model or '[dim](model not recorded)[/dim]'}  {n}")
            if len(used) > 1:
                err.print("[red]Mixed embedding models — run `mashup embed --reset`.[/red]")


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
    # Planning needs embeddings; the brief parser degrades to regex without a
    # key, so with the local backend this runs entirely offline.
    cfg = _runnable(workdir, embed=True)
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
                progress=_status(edl.strategy),
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
        progress=_status("render"),
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


def _report_order_stats(outdir: Path) -> None:
    """Show whether the planner's order is even ahead on its own objective.

    Printed before anyone is recruited: if the planned arm is mid-pack among
    arbitrary orders, viewers cannot be expected to prefer it, and the thing
    to fix is the planner rather than the study.
    """
    import json as _json

    stats = _json.loads((outdir / "KEY.json").read_text()).get("order_stats")
    if not stats:
        return
    pct = stats["planned_percentile"]
    console.print(
        f"\n[dim]planner order scores {stats['planned_score']:.4f}, ahead of {pct:.0f}% of "
        f"{stats['shuffles']} arbitrary orders of the same clips\n"
        f"comparator (median shuffle) scores {stats['shuffled_score']:.4f}[/dim]"
    )
    if pct < 75:
        err.print(
            f"[yellow]the planner's own objective ranks its order in the top {100 - pct:.0f}% "
            f"only — a null result here would be the planner's fault, not the thesis's.[/yellow]"
        )


@app.command()
def coverage(
    prompt: Annotated[str, typer.Option("--prompt", "-p")],
    workdir: WORKDIR_OPT = None,
) -> None:
    """Does the archive hold material on this topic, or only noise?

    Run this before an experiment. Similarity from an asymmetric embedding
    model has a floor well above zero, so a brief the archive cannot serve
    still returns confident-looking clips.
    """
    cfg = _runnable(workdir, embed=True)
    cov = pipeline.check_coverage(prompt, cfg)
    verdict = (
        "[green]archive supports this brief[/green]"
        if cov.viable
        else "[red]not supported by this archive[/red]"
    )
    console.print(f"{verdict}\n  {cov.explain()}")
    console.print(
        f"\n  top {cov.top_k} mean {cov.top_k_mean:.3f}   "
        f"nonsense floor {cov.floor:.3f}   lift {cov.lift:+.3f}"
    )
    if not cov.viable:
        raise typer.Exit(1)


@app.command()
def experiment(
    prompt: Annotated[str, typer.Option("--prompt", "-p")],
    output: Annotated[Path, typer.Option("--output", "-o")] = Path("experiment"),
    duration: Annotated[float, typer.Option("--duration", "-d")] = 420.0,
    workdir: WORKDIR_OPT = None,
    seed: Annotated[int, typer.Option("--seed", help="Shuffles the blind labels")] = 0,
    pool: Annotated[
        int,
        typer.Option(
            "--pool",
            help="Candidates retrieved before planning; widen if a variant comes back short",
        ),
    ] = DEFAULT_POOL,
    matched: Annotated[
        bool,
        typer.Option(
            "--matched",
            help="Two arms with identical clips in different orders — tests sequencing alone",
        ),
    ] = False,
    strategy: Annotated[
        str, typer.Option("--strategy", help="Which planner the matched pair uses")
    ] = "escalation",
    do_render: Annotated[bool, typer.Option("--render/--no-render")] = True,
    subtitles: Annotated[str, typer.Option("--subtitles")] = "sidecar",
) -> None:
    """Generate the blind conditions for the validation experiment.

    Five conditions by default, which measures the pipeline end to end.
    `--matched` generates two instead, from one clip set in two orders, which
    is the only design here that attributes a preference to sequencing.
    """
    from mashup.experiment import run_experiment, run_matched_experiment

    cfg = _runnable(workdir, embed=True)
    target = parse_duration(prompt, duration)

    cov = pipeline.check_coverage(prompt, cfg)
    if not cov.viable:
        err.print(f"[red]this archive cannot serve that brief[/red]\n  {cov.explain()}")
        err.print("  Run `mashup coverage --prompt ...` to find one it can.")
        raise typer.Exit(1)
    err.print(f"[dim]coverage: {cov.explain()}[/dim]")

    if matched:
        blinds = run_matched_experiment(
            prompt, cfg, outdir=output, target=target, strategy=strategy, seed=seed, pool=pool
        )
        _report_order_stats(output)
    else:
        blinds = run_experiment(prompt, cfg, outdir=output, target=target, seed=seed, pool=pool)

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
                progress=_status(blind.label),
            )
    console.print(
        f"\n[green]Wrote {len(blinds)} blind variants to {output}[/green]\n"
        f"Rate them in {output / 'ratings.csv'} — do not open KEY.json first.\n"
        f"Hand raters the .mp4 files only: the .json and .srt name the condition.\n"
        f"Then run: mashup evaluate {output}"
    )


@app.command()
def evaluate(
    outdir: Annotated[Path, typer.Argument(help="Experiment directory")],
) -> None:
    """Unblind a completed rating sheet and check the PRD's criteria."""
    import json as _json

    from mashup.experiment import summarise_matched, summarise_ratings

    try:
        design = _json.loads((outdir / "KEY.json").read_text()).get("design", "five-condition")
        result = (summarise_matched if design == "matched" else summarise_ratings)(outdir)
    except (OSError, RuntimeError, ValueError) as exc:
        err.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc

    if design == "matched":
        console.print(f"viewers: {result['viewers']}  ({result['decided']} expressed a preference)")
        console.print(f"[bold]{result['verdict']}[/bold]")
        mark = (
            "[green]significant[/green]"
            if result["significant"]
            else "[yellow]not significant[/yellow]"
        )
        console.print(f"  {mark} at p < 0.05")
        return

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

    cfg = _runnable(workdir, chat=True, embed=True)
    err.print("[dim]ingesting…[/dim]")
    pipeline.ingest(input_dir, cfg)
    err.print("[dim]enriching…[/dim]")
    pipeline.enrich(cfg, progress=_progress("enrich"))
    err.print("[dim]embedding…[/dim]")
    pipeline.embed(cfg, progress=_progress("embed"), notice=_notice)

    target = parse_duration(prompt, duration)
    edls = pipeline.make_mashups(
        prompt, cfg, target=target, strategies=pipeline.AI_STRATEGIES[:variants]
    )
    output.mkdir(parents=True, exist_ok=True)
    for edl in edls:
        _summarise(edl)
        save_edl(edl, output / f"{edl.strategy}.json")
        out = output / f"{edl.strategy}.mp4"
        render(edl, out, workdir=cfg.workdir, progress=_status(edl.strategy))
        console.print(f"  -> {out}")


if __name__ == "__main__":
    app()
