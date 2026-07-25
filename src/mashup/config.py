"""Runtime configuration.

Chat goes through the fleet free-ai gateway (OpenAI-compatible), so this
project holds no provider keys of its own — only a gateway key.

Embeddings default to a local model instead. They are re-run constantly while
tuning retrieval, they are the one stage where the gateway's provider
fallback can silently corrupt results, and a transformer small enough to
embed a whole archive in seconds removes both problems for free.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

DEFAULT_GATEWAY_URL = "https://ai-gateway.sassmaker.com"
# The gateway rejects `auto` for embeddings; it must be an explicit model.
DEFAULT_EMBED_MODEL = "gemini-embedding-001"
DEFAULT_CHAT_MODEL = "auto"
DEFAULT_EMBED_BACKEND = "local"
DEFAULT_LOCAL_EMBED_MODEL = "bge-base"


class ConfigError(RuntimeError):
    pass


@dataclass(frozen=True)
class Config:
    gateway_url: str
    gateway_api_key: str
    project_id: str
    chat_model: str
    embed_model: str
    workdir: Path
    # "local" runs a HuggingFace encoder in-process; "gateway" calls out.
    embed_backend: str = DEFAULT_EMBED_BACKEND
    local_embed_model: str = DEFAULT_LOCAL_EMBED_MODEL

    @property
    def db_path(self) -> Path:
        return self.workdir / "mashup.db"

    @property
    def cache_dir(self) -> Path:
        return self.workdir / "cache"

    @property
    def media_dir(self) -> Path:
        return self.workdir / "media"

    def ensure_dirs(self) -> None:
        for d in (self.workdir, self.cache_dir, self.media_dir):
            d.mkdir(parents=True, exist_ok=True)


def load_config(workdir: Path | str | None = None, *, require_key: bool = True) -> Config:
    key = os.getenv("MASHUP_GATEWAY_API_KEY") or os.getenv("GATEWAY_API_KEY") or ""
    backend = os.getenv("MASHUP_EMBED_BACKEND") or DEFAULT_EMBED_BACKEND
    if require_key and not key:
        raise ConfigError(
            "No gateway key. Set MASHUP_GATEWAY_API_KEY (or GATEWAY_API_KEY).\n"
            "Fleet operators can pull it with:\n"
            "  infisical run --projectId <free-ai> -- mashup ..."
        )
    wd = Path(workdir or os.getenv("MASHUP_WORKDIR") or ".mashup").expanduser().resolve()
    return Config(
        gateway_url=(os.getenv("MASHUP_GATEWAY_URL") or DEFAULT_GATEWAY_URL).rstrip("/"),
        gateway_api_key=key,
        project_id=os.getenv("MASHUP_PROJECT_ID") or "mashup",
        chat_model=os.getenv("MASHUP_CHAT_MODEL") or DEFAULT_CHAT_MODEL,
        embed_model=os.getenv("MASHUP_EMBED_MODEL") or DEFAULT_EMBED_MODEL,
        workdir=wd,
        embed_backend=backend,
        local_embed_model=(os.getenv("MASHUP_LOCAL_EMBED_MODEL") or DEFAULT_LOCAL_EMBED_MODEL),
    )
