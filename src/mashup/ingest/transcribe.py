"""Local subtitle generation for archives that ship without SRT/VTT.

mlx-whisper is an optional Apple-silicon extra, so it is imported inside the
function: nothing else in the pipeline should fail to import on a machine that
will never transcribe.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

DEFAULT_MODEL = "mlx-community/whisper-small.en-mlx"
# Whisper's own front end resamples to 16 kHz mono; doing it in ffmpeg keeps the
# temp file small and avoids handing whisper a video container to demux.
SAMPLE_RATE = 16000

_MISSING_EXTRA = (
    "mlx_whisper is not installed. Install the optional extra with:\n"
    "  uv sync --extra transcribe\n"
    "(Apple silicon only. Otherwise place a sibling .srt/.vtt next to the media file.)"
)


class TranscribeError(RuntimeError):
    """Raised when transcription cannot run or produce an SRT."""


def transcribe(media: Path, out_srt: Path, model: str = DEFAULT_MODEL) -> Path:
    """Transcribe `media` to `out_srt`, returning the SRT path.

    Transcription is the slowest step in the pipeline by an order of magnitude,
    so an existing output is always trusted and re-used.
    """
    if out_srt.exists():
        return out_srt
    if not media.is_file():
        raise TranscribeError(f"Media file not found: {media}")

    try:
        import mlx_whisper  # noqa: PLC0415 — optional extra, see module docstring
    except ImportError as exc:
        raise TranscribeError(_MISSING_EXTRA) from exc

    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "audio.wav"
        _extract_audio(media, wav)
        result: dict[str, Any] = mlx_whisper.transcribe(
            str(wav),
            path_or_hf_repo=model,
            # Word timings triple the runtime and the renderer only ever cuts on
            # segment boundaries.
            word_timestamps=False,
        )

    segments = result.get("segments") or []
    if not segments:
        raise TranscribeError(f"Transcription produced no segments for {media}")

    out_srt.parent.mkdir(parents=True, exist_ok=True)
    # Write via a sibling temp file: a half-written SRT left by a crash would be
    # silently trusted by the resume check above.
    staging = out_srt.with_suffix(out_srt.suffix + ".partial")
    staging.write_text(_to_srt(segments), encoding="utf-8")
    staging.replace(out_srt)
    return out_srt


def _extract_audio(media: Path, wav: Path) -> None:
    if shutil.which("ffmpeg") is None:
        raise TranscribeError("ffmpeg not found on PATH. Install FFmpeg (`brew install ffmpeg`).")
    proc = subprocess.run(
        [
            "ffmpeg",
            "-nostdin",
            "-v",
            "error",
            "-y",
            "-i",
            str(media),
            "-vn",
            "-ac",
            "1",
            "-ar",
            str(SAMPLE_RATE),
            "-f",
            "wav",
            str(wav),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0 or not wav.is_file():
        raise TranscribeError(f"ffmpeg failed to extract audio from {media}: {proc.stderr.strip()}")


def _to_srt(segments: list[dict[str, Any]]) -> str:
    blocks: list[str] = []
    for segment in segments:
        text = str(segment.get("text", "")).strip()
        if not text:
            continue
        start = float(segment.get("start", 0.0))
        end = max(float(segment.get("end", start)), start)
        blocks.append(f"{len(blocks) + 1}\n{_stamp(start)} --> {_stamp(end)}\n{text}\n")
    return "\n".join(blocks)


def _stamp(seconds: float) -> str:
    millis = int(round(max(seconds, 0.0) * 1000))
    hours, millis = divmod(millis, 3_600_000)
    minutes, millis = divmod(millis, 60_000)
    secs, millis = divmod(millis, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
