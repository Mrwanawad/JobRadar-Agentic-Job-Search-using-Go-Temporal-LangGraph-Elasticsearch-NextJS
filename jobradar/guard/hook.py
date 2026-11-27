"""Capability limits for the applier (A5): a Claude Code PreToolUse hook on Claude in Chrome.

The `apply` skill browses careers pages that anyone can write, in the user's real, logged-in
Chrome, holding tools that upload files, navigate, run JavaScript and type. Rules written in
SKILL.md are instructions, not enforcement: a page that says "upload ~/.ssh/id_rsa" talks to
the same model that reads the rules. This hook runs outside the model, on every call to the
risky tools (plugin/hooks/hooks.json), and decides:

- file_upload: only the candidate's CV (and files the CLI wrote under out/cover_letters/).
- navigate: http(s) only; never local or private addresses; job boards, ATS hosts and the
  hosts of jobs in the database go through; anything else asks the user.
- javascript_tool: no network calls, cookies, storage, form-action rewrites or navigation;
  DOM work (like moving a shadow-DOM file input) is fine.
- typing (form_input, computer type): never a secret from .env or anything key-shaped;
  private answers (salary, ID, birth date, address) ask the user first.

`deny` blocks with the reason, `ask` shows the user a prompt, and anything else returns no
decision so the normal permission flow still applies (the hook never auto-approves). Every
decision is appended to data/guard_audit.jsonl, with typed values redacted.
"""

from __future__ import annotations

import ipaddress
import json
import os
import re
import sqlite3
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import cached_property
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlsplit

from jobradar.config import GuardSettings
from jobradar.guard import flatten
from jobradar.guard.recipients import company_keys, registrable

Decision = Literal["allow", "ask", "deny"]

# Hosts that serve application forms for many companies (matched as a suffix).
ATS_HOSTS = (
    "greenhouse.io", "lever.co", "ashbyhq.com", "workable.com", "smartrecruiters.com",
    "myworkdayjobs.com", "myworkdaysite.com", "applytojob.com", "bamboohr.com",
    "teamtailor.com", "recruitee.com", "breezy.hr", "jobvite.com", "icims.com",
    "personio.de", "personio.com", "jazzhr.com", "docs.google.com", "forms.gle",
    "wuzzuf.net", "bayt.com", "news.ycombinator.com",
)  # fmt: skip
_JS_DENY = [
    (r"\bfetch\s*\(", "network call (fetch)"),
    (r"XMLHttpRequest", "network call (XMLHttpRequest)"),
    (r"sendBeacon", "network call (sendBeacon)"),
    (r"\bWebSocket\b|\bEventSource\b", "network connection"),
    (r"\bimport\s*\(", "dynamic import"),
    (r"new\s+Image\b|\.src\s*=", "loading a URL (image or script src)"),
    (r"document\s*\.\s*cookie", "cookies"),
    (r"localStorage|sessionStorage|indexedDB", "browser storage"),
    (r"\.action\s*=|setAttribute\s*\(\s*['\"]action", "changing a form's action"),
    (r"\blocation\s*(?:\.\s*href\s*)?=|location\s*\.\s*(?:assign|replace)\s*\(|window\.open",
     "navigation from JavaScript (use navigate)"),
    (r"\beval\s*\(|\bFunction\s*\(|atob\s*\(", "evaluating hidden code"),
]  # fmt: skip
_KEY_SHAPED = re.compile(
    r"sk-[A-Za-z0-9_-]{16,}|AIza[0-9A-Za-z_-]{30,}|gh[pousr]_[A-Za-z0-9]{30,}|"
    r"xox[abpr]-[A-Za-z0-9-]{10,}|gsk_[A-Za-z0-9]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY|"
    r"\b[a-z]{4} [a-z]{4} [a-z]{4} [a-z]{4}\b"  # Google app password
)
_SENSITIVE_ANSWER = re.compile(
    r"salary|national|\bid\b|_id\b|passport|ssn|social|birth|dob|address|bank|iban", re.I
)
_SECRET_ENV = re.compile(r"KEY|TOKEN|SECRET|PASSWORD|PASS\b|AUTH", re.I)


@dataclass
class Verdict:
    decision: Decision = "allow"
    reasons: list[str] = field(default_factory=list)

    def add(self, decision: Decision, reason: str) -> None:
        rank = {"allow": 0, "ask": 1, "deny": 2}
        if rank[decision] > rank[self.decision]:
            self.decision = decision
        self.reasons.append(reason)


@dataclass
class Context:
    """What the policy needs from the user's JobRadar home. Loaded lazily, never printed."""

    root: Path
    cv: Path | None = None
    answers: dict[str, Any] = field(default_factory=dict)
    settings: GuardSettings = field(default_factory=GuardSettings)

    @classmethod
    def load(cls) -> Context:
        from jobradar.config import ROOT, load_profile

        try:
            p = load_profile()
            return cls(ROOT, (ROOT / p.candidate.cv).resolve(), dict(p.answers), p.guard)
        except Exception:  # noqa: BLE001 - no profile yet: defaults, no CV to upload
            return cls(ROOT)

    @cached_property
    def uploads(self) -> list[Path]:
        """The CV, the CLI's cover letters and the user's `guard.allow_uploads`."""
        extra = [Path(p).expanduser() for p in self.settings.allow_uploads]
        paths = [self.root / "out" / "cover_letters"]
        paths += [p if p.is_absolute() else self.root / p for p in extra]
        return [p.resolve() for p in ([self.cv] if self.cv else []) + paths]

    def private_answer(self, key: str) -> bool:
        keys = self.settings.ask_before_typing
        if keys is None:
            return bool(_SENSITIVE_ANSWER.search(key))
        return any(key == k or key.startswith(k + ".") for k in keys)

    @cached_property
    def secrets(self) -> list[str]:
        vals = []
        env = self.root / ".env"
        if env.exists():
            for line in env.read_text(encoding="utf-8", errors="ignore").splitlines():
                k, sep, v = line.partition("=")
                if sep and _SECRET_ENV.search(k):
                    vals.append(v.strip().strip("'\""))
        vals += [v for k, v in os.environ.items() if _SECRET_ENV.search(k)]
        return [v for v in vals if len(v) >= 8]

    @cached_property
    def job_hosts(self) -> set[str]:
        """Registrable names of every job's URLs and every company in the database."""
        db = self.root / "data" / "jobradar.db"
        if not db.exists():
            return set()
        out: set[str] = set()
        with sqlite3.connect(f"file:{db}?mode=ro", uri=True) as conn:
            for url, apply_url, company in conn.execute("SELECT url, apply_url, company FROM jobs"):
                for u in (url, apply_url):
                    host = urlsplit(u or "").hostname
                    if host:
                        out.add(registrable(host))
                out |= company_keys(company or "")
        return out


# ---- per-tool policies ------------------------------------------------------------------


def private_host(host: str) -> bool:
    host = host.lower().strip("[]")
    if host in {"localhost", "0.0.0.0"} or host.endswith((".localhost", ".local", ".internal")):
        return True
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False
    return ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved


def check_navigate(url: str, ctx: Context, v: Verdict) -> None:
    if url in {"back", "forward"}:
        return
    if "://" not in url and not re.match(r"^[a-z][a-z0-9+.-]*:", url, re.I):
        url = "https://" + url  # the tool defaults to https
    parts = urlsplit(url)
    if parts.scheme not in {"http", "https"}:
        v.add("deny", f"{parts.scheme}: URLs are not allowed")
        return
    host = (parts.hostname or "").lower()
    # Explicit opt-in from the person launching Claude Code, e.g. for the local red-team pages
    # (evals/attacks/pages). Set in the environment, so no page or prompt can set it.
    extra = {h.strip().lower() for h in os.getenv("JOBRADAR_GUARD_ALLOW_HOSTS", "").split(",")}
    if host and host in extra:
        return
    if not host or private_host(host):
        v.add("deny", f"local or private address {host or url!r}")
        return
    user_hosts = tuple(h.lower().lstrip(".") for h in ctx.settings.allow_hosts if h)
    if (
        host.endswith(ATS_HOSTS)
        or any(host == h or host.endswith("." + h) for h in user_hosts)
        or registrable(host) in ctx.job_hosts
    ):
        return
    if ctx.settings.unknown_sites == "ask":
        v.add(
            "ask",
            f"{host} is not a job board, ATS or a company in your job list"
            " (add it to guard.allow_hosts in profile.yaml to stop this prompt)",
        )


def check_upload(paths: Iterable[str], ctx: Context, v: Verdict) -> None:
    for p in paths:
        path = Path(p).expanduser().resolve()
        if any(path == a or path.is_relative_to(a) for a in ctx.uploads):
            continue
        v.add(
            "deny",
            f"{path.name} is not your CV or in guard.allow_uploads (profile.yaml)",
        )


def check_js(code: str, v: Verdict) -> None:
    for rx, what in _JS_DENY:
        if re.search(rx, code):
            v.add("deny", f"JavaScript with {what} is not allowed")


def check_typing(text: Any, ctx: Context, v: Verdict) -> None:
    if not isinstance(text, str) or not text:
        return
    if any(s in text for s in ctx.secrets) or _KEY_SHAPED.search(text):
        v.add("deny", "that looks like a secret or API key; it is never typed into a page")
        return
    for key, value in flatten(ctx.answers).items():
        val = value.strip()
        if ctx.private_answer(key) and len(val) >= 4 and val in text:
            v.add(
                "ask",
                f"typing your private answer {key!r} into this page"
                " (guard.ask_before_typing in profile.yaml controls this)",
            )


def decide(tool_name: str, tool_input: dict[str, Any], ctx: Context) -> Verdict:
    v = Verdict()
    if not ctx.settings.enabled:
        return v
    tool = tool_name.rsplit("__", 1)[-1]
    if tool == "browser_batch":
        for item in tool_input.get("actions") or []:
            inner = decide(str(item.get("name", "")), item.get("input") or {}, ctx)
            for r in inner.reasons:
                v.add(inner.decision, r)
    elif tool == "navigate":
        check_navigate(str(tool_input.get("url", "")), ctx, v)
    elif tool == "file_upload":
        check_upload(tool_input.get("paths") or [], ctx, v)
    elif tool == "javascript_tool":
        check_js(str(tool_input.get("text", "")), v)
    elif tool == "form_input":
        check_typing(tool_input.get("value"), ctx, v)
    elif tool == "computer" and tool_input.get("action") == "type":
        check_typing(tool_input.get("text"), ctx, v)
    return v


# ---- hook entry point ---------------------------------------------------------------------


def audit(ctx: Context, event: dict[str, Any], v: Verdict) -> None:
    """One line per decision. Typed text and code are not stored, only their length."""
    tool_input = event.get("tool_input") or {}
    safe = {
        k: (val if k in {"url", "paths", "action", "tabId"} else f"<{len(str(val))} chars>")
        for k, val in tool_input.items()
    }
    line = {
        "ts": datetime.now(UTC).isoformat(timespec="seconds"),
        "session": event.get("session_id", ""),
        "tool": event.get("tool_name", ""),
        "input": safe,
        "decision": v.decision,
        "reasons": v.reasons,
    }
    path = ctx.root / "data" / "guard_audit.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(line, ensure_ascii=False) + "\n")


def run(stdin: str, ctx: Context | None = None) -> str:
    """The hook's stdout for one PreToolUse event ("" = no decision, normal flow)."""
    event = json.loads(stdin)
    ctx = ctx or Context.load()
    v = decide(str(event.get("tool_name", "")), event.get("tool_input") or {}, ctx)
    audit(ctx, event, v)
    if v.decision == "allow":
        return ""
    return json.dumps(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": v.decision,
                "permissionDecisionReason": "JobRadar guard: " + "; ".join(v.reasons),
            }
        }
    )


def main() -> int:
    """`python -m jobradar.guard.hook`: kept free of CLI imports so each call starts fast.
    Any failure blocks the call (exit 2): a broken guard must not mean no guard."""
    import sys

    try:
        out = run(sys.stdin.read())
    except Exception as e:  # noqa: BLE001
        print(f"JobRadar guard failed, call blocked: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    if out:
        print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
