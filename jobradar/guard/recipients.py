"""Recipient policy: who a drafted application may be sent to (A3, A7).

Contacts come from posting text, which anyone can write. Before this policy, any address that
looked like a hiring inbox became the outbox recipient, and a phone-only posting became a
WhatsApp message with the CV PDF attached. Now:

- email goes out automatically only when its domain belongs to the company: the company
  name, or the host of the posting's own URL (not an ATS or job board host). The attacker
  controls the description, so links inside it are not evidence.
- free-mail and mismatched domains go to `review`: a person approves each one.
- reserved domains (.invalid, .example, .test, .localhost) are blocked.
- WhatsApp always goes to `review`: it carries the CV PDF.
- scam / engagement-bait phrases send the item to `review` with the reason (A7).

The same check runs when drafting (`outreach.route`) and again at send time
(`outreach.sendable`), so an item edited or re-marked in between is checked again.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Literal
from urllib.parse import urlsplit

from jobradar.guard import enabled

Status = Literal["ok", "review", "block"]

FREE_MAIL = {
    "gmail.com", "googlemail.com", "yahoo.com", "ymail.com", "hotmail.com", "outlook.com",
    "live.com", "msn.com", "icloud.com", "me.com", "aol.com", "proton.me", "protonmail.com",
    "gmx.com", "gmx.net", "mail.com", "yandex.com", "yandex.ru", "mail.ru", "zoho.com",
}  # fmt: skip
RESERVED_TLDS = {"invalid", "example", "test", "localhost", "local"}
# Hosts that serve many companies' postings: their domain says nothing about the employer.
SHARED_HOSTS = {
    "greenhouse", "lever", "ashbyhq", "workable", "smartrecruiters", "myworkdayjobs",
    "workday", "recruitee", "bamboohr", "teamtailor", "breezy", "jobvite", "icims",
    "ycombinator", "remoteok", "weworkremotely", "himalayas", "linkedin", "wellfound",
    "indeed", "glassdoor", "wuzzuf", "bayt", "notion", "google", "github",
}  # fmt: skip
_GENERIC_WORDS = {"the", "inc", "llc", "ltd", "co", "corp", "group", "labs", "technologies"}
_SECOND_LEVEL = {"co", "com", "net", "org", "ac", "gov", "edu"}
SCAM = re.compile(
    r"comment\s+[\"'“]?interested|\bdm\s+me\b|\binbox\s+me\b|registration\s+fee|"
    r"training\s+fee|pay\s+(?:a|the)\s+(?:small\s+)?fee|whatsapp\s+only|"
    r"(?:cv|resume)\s+(?:and|with)\s+(?:your\s+)?(?:expected|current)\s+salary",
    re.I,
)


@dataclass
class Verdict:
    status: Status = "ok"
    reasons: list[str] = field(default_factory=list)

    def worse(self, status: Status, reason: str) -> None:
        order = {"ok": 0, "review": 1, "block": 2}
        if order[status] > order[self.status]:
            self.status = status
        self.reasons.append(reason)


def field_of(row: Mapping[str, Any], key: str) -> str:
    """Works for dicts and sqlite3.Row (which has no .get)."""
    try:
        return row[key] or ""
    except (KeyError, IndexError):
        return ""


def registrable(host: str) -> str:
    """The name a company registers: `careers.acme.co.uk` -> `acme`."""
    parts = host.lower().strip(".").split(".")
    if len(parts) >= 3 and parts[-2] in _SECOND_LEVEL and len(parts[-1]) == 2:
        return parts[-3]
    return parts[-2] if len(parts) >= 2 else parts[0]


def company_keys(company: str) -> set[str]:
    words = [w for w in re.findall(r"[a-z0-9]+", company.lower()) if w not in _GENERIC_WORDS]
    keys = {"".join(words)} if words else set()
    if words and len(words[0]) >= 3:
        keys.add(words[0])
    return keys


def posting_hosts(row: Mapping[str, Any]) -> set[str]:
    out = set()
    for key in ("url", "apply_url"):
        host = urlsplit(field_of(row, key)).hostname or ""
        if host and registrable(host) not in SHARED_HOSTS:
            out.add(registrable(host))
    return out


def scam_signals(text: str) -> list[str]:
    return sorted({m.group(0).lower() for m in SCAM.finditer(text or "")})


def check(channel: str, recipient: str, row: Mapping[str, Any]) -> Verdict:
    """Whether `recipient` may receive this job's application over `channel`."""
    v = Verdict()
    if not enabled("recipients") or channel == "manual":
        return v
    if channel == "whatsapp":
        v.worse("review", "WhatsApp sends the CV PDF: approve each message")
    elif channel == "email":
        domain = recipient.rsplit("@", 1)[-1].lower()
        if domain.rsplit(".", 1)[-1] in RESERVED_TLDS:
            v.worse("block", f"reserved domain {domain}")
        elif domain in FREE_MAIL:
            v.worse("review", f"free-mail address ({domain}), not the company's")
        elif registrable(domain) not in company_keys(field_of(row, "company")) | posting_hosts(row):
            v.worse("review", f"{domain} does not match {field_of(row, 'company')!r}")
    for s in scam_signals(field_of(row, "description")):
        v.worse("review", f"scam signal: {s!r}")
    return v
