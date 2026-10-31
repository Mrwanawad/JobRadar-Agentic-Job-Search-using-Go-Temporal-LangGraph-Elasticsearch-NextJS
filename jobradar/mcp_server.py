"""MCP server: drive JobRadar from Claude Code, Claude Desktop or any MCP client.

A thin client over the gateway HTTP API, so it has exactly the gateway's powers and checks
(demo drafts can never be approved, duplicate runs return 409). It holds the gateway token,
so it is an operator tool for the profile owner; it is never exposed to web visitors.

    JOBRADAR_GATEWAY_URL=http://localhost:8080 GATEWAY_TOKEN=... uv run --extra mcp jobradar-mcp

Claude Code:

    claude mcp add jobradar -e GATEWAY_TOKEN=... -- \\
        uv run --directory <repo> --extra mcp jobradar-mcp
"""

from __future__ import annotations

import os
from typing import Any

import httpx
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

READ_ONLY = ToolAnnotations(read_only_hint=True, open_world_hint=False)

server = MCPServer(
    name="jobradar",
    instructions=(
        "JobRadar ranks live job postings against a candidate profile and drafts applications. "
        "Typical flow: start_run(profile_id) -> poll get_run(workflow_id) until status is not "
        "'running' (or stage is STAGE_AWAITING_APPROVAL) -> search_jobs / get_outbox -> "
        "approve_draft. Always show the draft to the user and get their explicit yes before "
        "approving: an approved draft becomes sendable."
    ),
)


def _client() -> httpx.Client:
    token = os.environ.get("GATEWAY_TOKEN", "")
    if not token:
        raise ToolError("GATEWAY_TOKEN is not set for the MCP server")
    return httpx.Client(
        base_url=os.environ.get("JOBRADAR_GATEWAY_URL", "http://localhost:8080").rstrip("/"),
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )


def _call(method: str, path: str, **kw: Any) -> Any:
    try:
        with _client() as c:
            r = c.request(method, path, **kw)
    except httpx.HTTPError as e:
        raise ToolError(f"gateway unreachable: {e}") from e
    if r.status_code >= 400:
        try:
            msg = r.json().get("error", r.text)
        except ValueError:
            msg = r.text
        raise ToolError(f"gateway {r.status_code}: {msg}")
    return r.json()


def _results(profile_id: str) -> list[dict[str, Any]]:
    return _call("GET", f"/v1/profiles/{profile_id}/results", params={"limit": 100})["results"]


def _job(r: dict[str, Any]) -> dict[str, Any]:
    a = r.get("assessment") or {}
    return {
        "job_uid": r["job_uid"],
        "title": r["title"],
        "company": r["company"],
        "location": r["location"],
        "url": r["url"],
        "score": r["score"],
        "pitch_angle": a.get("pitch_angle", ""),
        "reasons": a.get("reasons", []),
        "red_flags": a.get("red_flags", []),
        "location_fit": a.get("location_fit"),
        "outbox_id": r.get("outbox_id"),
        "draft_status": r.get("draft_status"),
    }


@server.tool(
    annotations=ToolAnnotations(read_only_hint=False, idempotent_hint=False, open_world_hint=True)
)
def start_run(profile_id: str) -> dict[str, Any]:
    """Start a radar run for a profile: fetch all sources, prefilter, hybrid match, LLM-score
    and draft. Returns the workflow_id to poll with get_run. Takes minutes to tens of minutes."""
    return _call("POST", "/v1/runs", json={"profile_id": profile_id})


@server.tool(annotations=READ_ONLY)
def get_run(workflow_id: str) -> dict[str, Any]:
    """Status ('running', 'completed', 'failed') and live progress of one run: stage, sources
    done, jobs fetched, candidates, matched, scored, drafted, per-source errors."""
    return _call("GET", f"/v1/runs/{workflow_id}")


@server.tool(annotations=READ_ONLY)
def get_summary(profile_id: str) -> dict[str, Any]:
    """Pipeline counts for a profile (matches and drafts by status, total jobs) and its
    recent runs."""
    return _call("GET", f"/v1/profiles/{profile_id}/summary")


@server.tool(annotations=READ_ONLY)
def search_jobs(
    profile_id: str, query: str = "", min_score: float = 0, limit: int = 20
) -> list[dict[str, Any]]:
    """Scored jobs for a profile, best first. `query` filters by words in title, company or
    location (all words must match, case-insensitive); `min_score` is 0-10."""
    words = query.lower().split()
    out = []
    for r in _results(profile_id):
        hay = f"{r['title']} {r['company']} {r['location']}".lower()
        if (r["score"] or 0) >= min_score and all(w in hay for w in words):
            out.append(_job(r))
    return out[: max(1, min(limit, 100))]


@server.tool(annotations=READ_ONLY)
def get_outbox(profile_id: str, status: str = "draft") -> list[dict[str, Any]]:
    """Drafted applications for a profile with full subject and body. `status` filters by
    draft status ('draft', 'approved', 'rejected', 'sent', ...); empty string returns all."""
    out = []
    for r in _results(profile_id):
        if r.get("outbox_id") is None or (status and r.get("draft_status") != status):
            continue
        out.append(
            _job(r)
            | {"channel": r.get("channel"), "subject": r.get("subject"), "body": r.get("body")}
        )
    return out


@server.tool(
    annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, open_world_hint=False)
)
def approve_draft(
    profile_id: str, outbox_id: int, approve: bool, workflow_id: str = "", edited_body: str = ""
) -> dict[str, Any]:
    """Approve or reject one draft (personal profiles only). Pass the run's workflow_id to
    signal a run that is still waiting for approvals; otherwise the decision is stored
    directly. `edited_body` replaces the draft text. Only call after the user said yes."""
    return _call(
        "POST",
        f"/v1/outbox/{outbox_id}/decision",
        json={
            "profile_id": profile_id,
            "workflow_id": workflow_id,
            "approve": approve,
            "body": edited_body,
        },
    )


def main() -> None:
    server.run("stdio")


if __name__ == "__main__":
    main()
