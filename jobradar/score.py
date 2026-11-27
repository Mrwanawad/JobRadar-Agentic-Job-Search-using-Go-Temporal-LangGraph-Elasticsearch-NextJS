"""LLM scoring: CV + one job -> 0-10 fit score with reasons. Second, paid-in-quota pass."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from pypdf import PdfReader

from jobradar.config import DEFAULT_CONSTRAINTS, ROOT, Profile
from jobradar.guard.sanitize import clean_text
from jobradar.llm import LLMClient

MAX_DESC_CHARS = 6000

SYSTEM = """You screen job postings for one candidate. Judge strictly and honestly; a wrong
"yes" costs the candidate an embarrassing application. Reply with JSON only."""

TEMPLATE = """CANDIDATE CV
{cv}

CANDIDATE CONSTRAINTS
{constraints}

JOB
Company: {company}
Title: {title}
Location: {location} (remote flag: {remote})
Salary: {salary}
Posted: {posted_at}
Description:
{description}

Return this JSON:
{{
  "score": <0-10 overall fit; 8+ only if role, seniority and location all fit>,
  "role_fit": <0-10 skills/experience match>,
  "seniority_fit": "under" | "match" | "over",
  "location_fit": "eligible" | "needs_sponsorship" | "ineligible",
  "visa_sponsorship": "yes" | "no" | "unknown",
  "salary_signal": "<short note or 'unknown'>",
  "reasons": ["<max 3 short reasons it fits>"],
  "red_flags": ["<max 3 short concerns>"],
  "pitch_angle": "<one sentence: the strongest CV hook for this job>"
}}"""


def pdf_text(pdf: Path) -> str:
    """Text of a CV PDF, cached next to it as .txt (gitignored)."""
    cache = pdf.with_suffix(".txt")
    if cache.exists() and cache.stat().st_mtime >= pdf.stat().st_mtime:
        return cache.read_text(encoding="utf-8")
    text = "\n".join(p.extract_text() or "" for p in PdfReader(pdf).pages).strip()
    cache.write_text(text, encoding="utf-8")
    return text


def cv_text(profile: Profile) -> str:
    return pdf_text(ROOT / profile.candidate.cv)


def clamp(score: Any, result: dict[str, Any]) -> float:
    try:
        s = max(0.0, min(10.0, float(score)))
    except (TypeError, ValueError):
        return 0.0
    if result.get("location_fit") == "ineligible":
        s = min(s, 3.0)
    if result.get("location_fit") == "needs_sponsorship" and result.get("visa_sponsorship") == "no":
        s = min(s, 3.0)
    return s


def constraints_text(profile: Profile) -> str:
    c = profile.candidate
    return (c.constraints or DEFAULT_CONSTRAINTS).format(base=c.base or "unknown")


def posting_text(job: Mapping[str, Any]) -> str:
    """The description as a person reads it (guard/sanitize.py): the only form any prompt gets."""
    return clean_text(job["description"]).text


def build_prompt(
    profile: Profile, cv: str, job: Mapping[str, Any], facts: Any = None
) -> list[dict[str, str]]:
    """Messages for one screening call. `job` is a SQLite row or a Postgres dict row. With
    `facts` (guard/extract.py JobFacts) the posting text is replaced by structured facts."""
    if facts is not None:
        from jobradar.guard.extract import render

        description = render(facts, profile)
    else:
        description = posting_text(job)[:MAX_DESC_CHARS] or "(no description available)"
    prompt = TEMPLATE.format(
        cv=cv,
        constraints=constraints_text(profile),
        company=clean_text(job["company"]).text,
        title=clean_text(job["title"]).text,
        location=clean_text(job["location"]).text or "unknown",
        remote={1: "yes", 0: "no"}.get(job["remote"], "unknown"),
        salary=clean_text(job["salary"]).text or "not stated",
        posted_at=job["posted_at"] or "unknown",
        description=description,
    )
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}]


def score_job(
    llm: LLMClient, profile: Profile, cv: str, row: Mapping[str, Any], facts: Any = None
) -> tuple[float, dict[str, Any], str]:
    data, res = llm.chat_json(
        build_prompt(profile, cv, row, facts),
        max_tokens=4000,  # some free models reason in the visible reply
    )
    if not isinstance(data, dict):
        raise ValueError(f"expected JSON object, got {type(data).__name__}")
    return clamp(data.get("score"), data), data, f"{res.provider}:{res.model}"
