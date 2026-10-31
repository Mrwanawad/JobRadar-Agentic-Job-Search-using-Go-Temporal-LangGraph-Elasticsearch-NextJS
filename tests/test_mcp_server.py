import json

import anyio
import httpx
import pytest
import respx

pytest.importorskip("mcp")

from mcp.server.mcpserver.exceptions import ToolError  # noqa: E402

from jobradar import mcp_server as m  # noqa: E402

GW = "http://gw.test"

RESULTS = {
    "results": [
        {
            "job_uid": "a",
            "title": "Senior AI Engineer",
            "company": "Acme",
            "location": "Remote EMEA",
            "url": "https://x/a",
            "score": 8.5,
            "assessment": {
                "pitch_angle": "RAG in prod",
                "reasons": ["LLM"],
                "red_flags": [],
                "location_fit": "eligible",
            },
            "outbox_id": 7,
            "channel": "email",
            "subject": "AI Engineer",
            "body": "Hi",
            "draft_status": "draft",
        },
        {
            "job_uid": "b",
            "title": "Data Analyst",
            "company": "Beta",
            "location": "Cairo",
            "url": "https://x/b",
            "score": 4.0,
            "assessment": None,
            "outbox_id": None,
            "channel": None,
            "subject": None,
            "body": None,
            "draft_status": None,
        },
    ]
}


@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setenv("JOBRADAR_GATEWAY_URL", GW)
    monkeypatch.setenv("GATEWAY_TOKEN", "t0k")


def test_registers_tools():
    tools = anyio.run(m.server.list_tools)
    assert {t.name for t in tools} == {
        "start_run",
        "get_run",
        "get_summary",
        "search_jobs",
        "get_outbox",
        "approve_draft",
    }
    by = {t.name: t for t in tools}
    assert by["search_jobs"].annotations.read_only_hint is True
    assert by["approve_draft"].annotations.read_only_hint is False


@respx.mock
def test_start_run_sends_token_and_profile():
    route = respx.post(f"{GW}/v1/runs").respond(202, json={"workflow_id": "radar-p1-x"})
    assert m.start_run("p1") == {"workflow_id": "radar-p1-x"}
    req = route.calls.last.request
    assert req.headers["Authorization"] == "Bearer t0k"
    assert json.loads(req.content) == {"profile_id": "p1"}


@respx.mock
def test_search_filters_by_words_and_score():
    respx.get(f"{GW}/v1/profiles/p1/results").respond(200, json=RESULTS)
    assert [j["job_uid"] for j in m.search_jobs("p1")] == ["a", "b"]
    assert [j["job_uid"] for j in m.search_jobs("p1", query="ai remote")] == ["a"]
    assert [j["job_uid"] for j in m.search_jobs("p1", min_score=5)] == ["a"]
    assert m.search_jobs("p1", query="ai")[0]["pitch_angle"] == "RAG in prod"


@respx.mock
def test_outbox_only_drafts_with_body():
    respx.get(f"{GW}/v1/profiles/p1/results").respond(200, json=RESULTS)
    out = m.get_outbox("p1")
    assert [(o["outbox_id"], o["body"]) for o in out] == [(7, "Hi")]
    assert m.get_outbox("p1", status="sent") == []


@respx.mock
def test_approve_posts_decision():
    route = respx.post(f"{GW}/v1/outbox/7/decision").respond(202, json={"via": "signal"})
    assert m.approve_draft("p1", 7, True, workflow_id="radar-p1-x", edited_body="Hello") == {
        "via": "signal"
    }
    assert json.loads(route.calls.last.request.content) == {
        "profile_id": "p1",
        "workflow_id": "radar-p1-x",
        "approve": True,
        "body": "Hello",
    }


@respx.mock
def test_gateway_errors_become_tool_errors():
    respx.post(f"{GW}/v1/outbox/7/decision").respond(
        403, json={"error": "demo drafts are never sent"}
    )
    with pytest.raises(ToolError, match="403: demo drafts are never sent"):
        m.approve_draft("demo-1", 7, True)
    respx.get(f"{GW}/v1/runs/x").mock(side_effect=httpx.ConnectError("refused"))
    with pytest.raises(ToolError, match="unreachable"):
        m.get_run("x")


def test_missing_token(monkeypatch):
    monkeypatch.delenv("GATEWAY_TOKEN")
    with pytest.raises(ToolError, match="GATEWAY_TOKEN"):
        m.get_run("x")
