"""Output policy: what a drafted application may contain (A2, A4).

The writer reads the posting, so an injected instruction can put attacker text, links or the
candidate's private details into the draft. The LLM critic checks claims against the CV; it
was never asked to look for injected content. These rules are deterministic and run on the
final text (after the CV link and signature are appended):

- links: only the candidate's own (profile links, CV link, portfolio links);
- emails and phone numbers: only the candidate's own;
- private form answers (salary, ID numbers, birth date, address) never appear;
- every number appears in the CV, the profile or the posting (complements the critic's
  fabrication check);
- no long span copied from the posting (echoed instructions);
- plain text, within a sane length for the channel.

A violating draft gets one revision with the exact violations, then it is rejected.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from jobradar.config import Profile
from jobradar.guard import enabled
from jobradar.guard.recipients import field_of

_URL = re.compile(r"https?://[^\s<>\"')\]]+|www\.[^\s<>\"')\]]+", re.I)
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)*\.[a-z]{2,}", re.I)
_PHONE = re.compile(r"(?:\+|00)\d[\d\s().-]{7,16}\d")
_NUMBER = re.compile(r"\d+(?:[.,]\d+)*")
_MARKUP = re.compile(r"<[a-z/!][^>]*>|\]\(|^#{1,6}\s|\*\*|^```", re.I | re.M)
ECHO_WORDS = 10  # a run of this many words copied from the posting is an echo
WORDS = {"email": (30, 400), "whatsapp": (15, 220), "manual": (50, 500)}


def _digits(s: str) -> str:
    return re.sub(r"\D", "", s)


def _norm_url(u: str) -> str:
    u = re.sub(r"^https?://", "", u.lower().rstrip(".,;:!?")).removeprefix("www.")
    return u.rstrip("/")


def allowed_urls(profile: Profile) -> list[str]:
    c = profile.candidate
    raw = [
        c.cv_link,
        *c.links.values(),
        *_URL.findall(c.domain_portfolio),
        *_URL.findall(profile.outreach.signature),
    ]
    return [_norm_url(u) for u in raw if u]


def _numbers(text: str) -> set[str]:
    return {n.replace(",", "") for n in _NUMBER.findall(text)}


def _words(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower())


def check(text: str, channel: str, profile: Profile, cv: str, row: Mapping[str, Any]) -> list[str]:
    """Violations in a final draft (subject + body). Empty means it may be stored."""
    if not enabled("output"):
        return []
    c = profile.candidate
    posting = field_of(row, "description")
    out: list[str] = []

    allowed = allowed_urls(profile)
    for u in _URL.findall(text):
        n = _norm_url(u)
        if not any(n == a or n.startswith(a + "/") for a in allowed):
            out.append(f"link {u} is not one of the candidate's links")

    own = (c.email or "").lower()
    for e in _EMAIL.findall(text):
        if e.lower().strip(".") != own:
            out.append(f"email address {e} is not the candidate's")
    for p in _PHONE.findall(text):
        if not c.phone or _digits(p) != _digits(c.phone):
            out.append(f"phone number {p.strip()} is not the candidate's")

    for key, value in profile.answers.items():
        v = str(value).strip()
        if len(v) >= 6 and v.lower() in text.lower():
            out.append(f"private answer {key!r} must not be in the message")

    known = _numbers("\n".join([cv, posting, field_of(row, "title"), field_of(row, "company")]))
    sig = profile.outreach.signature
    known |= _numbers(" ".join([c.base, c.phone, c.cv_link, sig, *c.links.values()]))
    for n in sorted(_numbers(_URL.sub(" ", text)) - known):
        out.append(f"number {n} is in neither the CV nor the posting")

    pw, tw = _words(posting), " ".join(_words(text))
    for i in range(len(pw) - ECHO_WORDS + 1):
        span = " ".join(pw[i : i + ECHO_WORDS])
        if span in tw:
            out.append(f"copies the posting word for word: {span!r}")
            break

    if _MARKUP.search(text):
        out.append("use plain text: no HTML or Markdown")
    lo, hi = WORDS.get(channel, (15, 500))
    n = len(text.split())
    if not lo <= n <= hi:
        out.append(f"{n} words; a {channel} message should be {lo}-{hi}")
    return out
