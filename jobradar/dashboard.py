"""Local read-only dashboard: `jobradar dashboard` serves the DB as one page on 127.0.0.1."""

from __future__ import annotations

import json
import re
import sqlite3
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from jobradar.config import ROOT, load_profile
from jobradar.db import DEFAULT_PATH
from jobradar.outreach import local_midnight_utc

LOGS = ROOT / "out" / "logs"
PAGE = Path(__file__).with_name("dashboard.html")


def _rows(conn: sqlite3.Connection, sql: str, args: tuple = ()) -> list[dict[str, Any]]:
    return [dict(r) for r in conn.execute(sql, args)]


def _tally(items: Any) -> list[list[Any]]:
    counts: dict[str, int] = {}
    for k in items:
        counts[k] = counts.get(k, 0) + 1
    return sorted(([k, n] for k, n in counts.items()), key=lambda kv: -kv[1])


def _grab(rx: str, text: str) -> str | None:
    m = re.search(rx, text)
    return m.group(1) if m else None


# ATS / board names as they appear in outbox refs and apply URLs -> display label.
_ATS = [
    ("workable", "Workable"), ("greenhouse", "Greenhouse"), ("ashby", "Ashby"), ("lever", "Lever"),
    ("wuzzuf", "Wuzzuf"), ("teamtailor", "Teamtailor"), ("smartrecruiters", "SmartRecruiters"),
    ("applytojob", "JazzHR"), ("jazzhr", "JazzHR"), ("breezy", "Breezy"), ("bamboohr", "BambooHR"),
    ("workday", "Workday"), ("successfactors", "SuccessFactors"), ("recruitee", "Recruitee"),
    ("personio", "Personio"), ("easy apply", "LinkedIn Easy Apply"),
]
_CHANNELS = {"email": "Cold email", "whatsapp": "WhatsApp", "linkedin": "LinkedIn DM"}
FOUND_BY = {"pipeline": "Agent (JobRadar pipeline)", "agent": "Agent (Claude search)", "you": "You"}


def method_of(channel: str, ref: str | None, url: str | None) -> str:
    """How the application went out: cold email, a named ATS form, a DM..."""
    if channel in _CHANNELS:
        return _CHANNELS[channel]
    hay = f"{ref or ''} {url or ''}".lower()
    for key, label in _ATS:
        if key in hay:
            return label if label.startswith("LinkedIn") else f"{label} form"
    return "Careers-page form"


_BOARDS = {
    "wuzzuf": "Wuzzuf", "greenhouse": "Greenhouse board", "ashby": "Ashby board",
    "lever": "Lever board", "workable": "Workable board", "wwr": "We Work Remotely",
    "remoteok": "RemoteOK", "himalayas": "Himalayas", "careers": "Careers pages",
    "smartrecruiters": "SmartRecruiters board",
}


def found_on_of(source: str, ref: str | None, url: str | None) -> str:
    """Best guess at where a posting was discovered, for rows recorded without `found_on`."""
    hay = f"{ref or ''} {url or ''}".lower()
    if "linkedin" in hay:
        return "LinkedIn post" if re.search(r"post|feed", hay) else "LinkedIn Jobs"
    if source in _BOARDS:
        return _BOARDS[source]
    if "cold email" in hay:
        return "Company research"
    if "wuzzuf" in hay:
        return "Wuzzuf"
    if "jobs.workable.com" in hay:
        return "Workable board"
    return "Web search"


def _log_runs(limit: int = 14) -> list[dict[str, Any]]:
    """One entry per daily log: what each run fetched, scored, drafted and sent."""
    runs = []
    for f in sorted(LOGS.glob("*.log"), reverse=True)[:limit]:
        text = f.read_text(encoding="utf-8", errors="replace")
        runs.append(
            {
                "date": f.stem,
                "started": _grab(r"=== run (\S+)", text),
                "fetched": _grab(r"fetched (\d+)", text),
                "new": _grab(r"new (\d+)", text),
                "failed": _grab(r"failed sources (\d+)", text),
                "scored": _grab(r"scored (\d+)", text),
                "drafted": _grab(r"drafted (\{[^}]*\})", text),
                "send": _grab(r"=== send [^\n]*\n([^\n]+)", text),
            }
        )
    return runs


def snapshot(db_path: Path = DEFAULT_PATH) -> dict[str, Any]:
    profile = load_profile()
    o = profile.outreach
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        status = {
            r["status"]: r["n"]
            for r in _rows(conn, "SELECT status, COUNT(*) n FROM jobs GROUP BY status")
        }
        outbox = _rows(
            conn,
            "SELECT o.id, o.channel, o.recipient, o.status, o.created_at, o.sent_at, o.ref, "
            "o.found_on, "
            "j.company, j.title, j.location, j.llm_score, j.url, j.source "
            "FROM outbox o JOIN jobs j ON j.uid = o.uid ORDER BY o.id DESC",
        )
        shortlist = _rows(
            conn,
            "SELECT j.company, j.title, j.location, j.llm_score, j.url, j.source, j.llm_json, "
            "o.status AS outreach FROM jobs j LEFT JOIN outbox o ON o.uid = j.uid "
            "WHERE j.status='scored' ORDER BY j.llm_score DESC, j.posted_at DESC LIMIT 60",
        )
        for r in outbox:
            r["method"] = method_of(r["channel"], r["ref"], r["url"])
            source = r.pop("source")
            r["found_on"] = r["found_on"] or found_on_of(source, r["ref"], r["url"])
            r["found_by"] = FOUND_BY["agent" if source == "manual" else "pipeline"]
        processes = _rows(
            conn,
            "SELECT p.*, j.url, j.source, o.ref, o.found_on AS outbox_found_on "
            "FROM processes p LEFT JOIN outbox o ON o.id = p.outbox_id "
            "LEFT JOIN jobs j ON j.uid = o.uid ORDER BY p.active DESC, p.updated_at DESC",
        )
        for r in processes:
            r["found_by"] = FOUND_BY.get(r["found_by"], r["found_by"])
            guess = found_on_of(r["source"] or "", r["ref"], r["url"]) if r["outbox_id"] else None
            r["found_on"] = r["found_on"] or r.pop("outbox_found_on") or guess
        sent = [r for r in outbox if r["status"] == "sent"]
        for r in shortlist:
            res = json.loads(r.pop("llm_json") or "{}")
            r["fit"] = res.get("location_fit")
            r["pitch"] = res.get("pitch_angle", "")
        return {
            "today": date.today().isoformat(),
            "status": status,
            "total": sum(status.values()),
            "last_fetch": conn.execute("SELECT MAX(first_seen) FROM jobs").fetchone()[0],
            "sources": _rows(
                conn,
                "SELECT source, COUNT(*) total, SUM(status='scored') scored "
                "FROM jobs GROUP BY source ORDER BY total DESC",
            ),
            "scores": _rows(
                conn,
                "SELECT CAST(llm_score AS INT) bucket, COUNT(*) n FROM jobs "
                "WHERE status='scored' GROUP BY bucket ORDER BY bucket",
            ),
            "outbox": outbox,
            "processes": processes,
            "by_method": _tally(r["method"] for r in sent),
            "by_found": _tally(r["found_by"] for r in sent),
            "by_found_on": _tally(r["found_on"] for r in sent),
            "outbox_counts": {
                r["status"]: r["n"]
                for r in _rows(conn, "SELECT status, COUNT(*) n FROM outbox GROUP BY status")
            },
            "sent_today": conn.execute(
                "SELECT COUNT(*) FROM outbox WHERE status='sent' AND sent_at >= ?",
                (local_midnight_utc(),),
            ).fetchone()[0],
            "shortlist": shortlist,
            "config": {
                "min_score": o.min_score,
                "daily_cap": o.daily_cap,
                "dry_run_until": o.dry_run_until.isoformat() if o.dry_run_until else None,
                "dry_run": o.dry_run(),
            },
            "runs": _log_runs(),
        }
    finally:
        conn.close()


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        if self.path in ("/", "/index.html"):
            self._send(200, "text/html; charset=utf-8", PAGE.read_bytes())
        elif self.path == "/api/snapshot":
            body = json.dumps(snapshot(), ensure_ascii=False, default=str).encode()
            self._send(200, "application/json", body)
        else:
            self._send(404, "text/plain", b"not found")

    def _send(self, code: int, ctype: str, body: bytes) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args: Any) -> None:
        pass


def serve(port: int = 0) -> ThreadingHTTPServer:
    """Bind to localhost only; port 0 lets the OS pick a free random port."""
    return ThreadingHTTPServer(("127.0.0.1", port), Handler)
