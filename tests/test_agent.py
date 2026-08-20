from __future__ import annotations

import json
from pathlib import Path

import pytest

from mashup.agent import AGENT_SCHEMA, AgentError, run_agent
from mashup.media_receipt import build_media_receipt, validate_media_receipt


def request(operation: str, input_: dict | None = None, **extra) -> dict:
    return {
        "schema": AGENT_SCHEMA,
        "product": "mashup",
        "operation": operation,
        "operationId": "op-test",
        "input": input_ or {},
        **extra,
    }


def test_manifest_exposes_every_supported_operation() -> None:
    result = run_agent(request("manifest"))

    assert result["state"] == "completed"
    assert {item["id"] for item in result["result"]["operations"]} == {
        "manifest",
        "models",
        "status",
        "ingest",
        "enrich",
        "embed",
        "plan",
        "short-plan",
        "validate-edl",
        "export-podcast-edit",
        "validate-render",
        "render",
        "media-receipt",
        "inspect-receipt",
    }
    assert result["result"]["safety"]["arbitraryExecution"] is False


def test_status_is_safe_before_a_store_exists(tmp_path: Path) -> None:
    result = run_agent(request("status", {"workdir": str(tmp_path)}))

    assert result["result"]["ready"] is False
    assert result["result"]["counts"] == {}


@pytest.mark.parametrize("field", ["command", "shell", "script", "code", "plugin"])
def test_arbitrary_execution_fields_are_rejected(field: str) -> None:
    with pytest.raises(AgentError, match="is not accepted") as exc:
        run_agent(request("manifest", {field: "echo unsafe"}))

    assert exc.value.code == "ARBITRARY_EXECUTION_REJECTED"


def test_unknown_fields_are_rejected() -> None:
    with pytest.raises(AgentError, match="unknown field") as exc:
        run_agent({**request("manifest"), "surprise": True})

    assert exc.value.code == "UNKNOWN_FIELD"


def test_validate_render_requires_approved_edit(tmp_path: Path) -> None:
    edit = tmp_path / "edit.json"
    edit.write_text(
        json.dumps({"schema": "fleet.podcast-edit.v1", "approval": {"status": "proposed"}}),
        encoding="utf-8",
    )

    with pytest.raises(AgentError) as exc:
        run_agent(request("validate-render", {"podcastEditPath": str(edit)}))

    assert exc.value.code == "APPROVAL_REQUIRED"


def test_receipt_accepts_and_checks_agent_operation_linkage(tmp_path: Path) -> None:
    video = tmp_path / "video.mp4"
    video.write_bytes(b"fixture-video")
    operation = {
        "schema": AGENT_SCHEMA,
        "id": "op-test",
        "requestHash": "abc123",
        "state": "completed",
    }
    podcast_edit = {
        "schema": "fleet.podcast-edit.v1",
        "id": "edit-test",
        "approval": {"status": "approved", "approvedBy": "operator"},
        "sources": [
            {
                "id": "source-test",
                "title": "Owned source",
                "sourceUrl": "https://example.com/source",
                "license": "creator-owned",
                "licenseUrl": "https://example.com/rights",
            }
        ],
    }
    receipt = build_media_receipt(
        podcast_edit,
        video_path=video,
        duration_seconds=3,
        width=1080,
        height=1920,
        operation=operation,
    )

    validate_media_receipt(receipt)
    receipt["operation"]["state"] = "failed"
    with pytest.raises(ValueError, match="completed request"):
        validate_media_receipt(receipt)
