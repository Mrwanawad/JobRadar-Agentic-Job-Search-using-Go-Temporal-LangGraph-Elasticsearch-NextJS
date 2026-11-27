"""profile.yaml and companies.yaml, loaded once and validated."""

from __future__ import annotations

import os
import re
from datetime import date
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field

PACKAGE_ROOT = Path(__file__).resolve().parent.parent
# Where profile.yaml, cv/, data/, out/ and .env live: the repo, unless JOBRADAR_HOME says else.
ROOT = Path(os.getenv("JOBRADAR_HOME") or PACKAGE_ROOT).resolve()


class Candidate(BaseModel):
    name: str
    email: str
    phone: str = ""
    base: str = ""
    cv: str
    # Public link to the CV (e.g. Google Drive "anyone with the link"). Emails carry the link,
    # since the Gmail connector needs attachments inlined as base64.
    cv_link: str = ""
    links: dict[str, str] = Field(default_factory=dict)  # linkedin, github, portfolio, ...
    # Eligibility and target, as told to the screening LLM. Empty = DEFAULT_CONSTRAINTS.
    constraints: str = ""
    # Public projects grouped by business domain (e.g. "real estate", "telecom"). Cover letters
    # and "why you" answers name the ones that match the employer's domain.
    domain_portfolio: str = ""


DEFAULT_CONSTRAINTS = """\
- Based in {base}. Work authorisation only where the CV states it; anywhere else needs
  visa sponsorship.
- Acceptable: remote roles open to the candidate's region or worldwide; on-site where they
  live or are authorised; elsewhere only with visa sponsorship."""


class Roles(BaseModel):
    include: list[str]
    conditional: list[str] = Field(default_factory=list)
    conditional_requires: str = r"\b(senior|lead|staff|principal)\b"
    exclude: list[str] = Field(default_factory=list)


class Locations(BaseModel):
    remote_allowed: str
    onsite_allowed: str
    sponsor_hint: str


class Scoring(BaseModel):
    max_age_days: int = 30
    max_llm_per_run: int = 60
    shortlist_min: int = 7


class Outreach(BaseModel):
    min_score: float = 7.5
    daily_cap: int = 10  # email + WhatsApp sends per local day
    # Until this date (inclusive) nothing is sendable: drafts only, for review.
    dry_run_until: date | None = None
    tone: str = "warm, direct, confident, no clichés; 120-180 words"
    signature: str = ""
    max_drafts_per_run: int = 15

    def dry_run(self, today: date | None = None) -> bool:
        return self.dry_run_until is not None and (today or date.today()) <= self.dry_run_until


class GuardSettings(BaseModel):
    """What each user may loosen in the applier guard (jobradar/guard/hook.py). The hard
    rules are fixed: no file:, javascript: or local addresses, no secrets typed into pages,
    no network or cookie access from page JavaScript, no uploads outside the allow list."""

    enabled: bool = True
    # Extra sites the applier may open without asking (suffix match: "acme.com" covers
    # "careers.acme.com"). Job boards, ATS hosts and companies in your job list pass already.
    allow_hosts: list[str] = Field(default_factory=list)
    # Any other site: "ask" (a prompt with the reason) or "allow".
    unknown_sites: Literal["ask", "allow"] = "ask"
    # Files or folders besides the CV that may be uploaded (portfolio PDF, certificates...).
    # Relative paths are inside the JobRadar home.
    allow_uploads: list[str] = Field(default_factory=list)
    # `answers` keys to confirm before typing (a key covers its sub-keys: "salary" covers
    # "salary.egypt.current"). Unset = salary, ID and passport numbers, birth date, address,
    # bank details. [] = never ask.
    ask_before_typing: list[str] | None = None


class Profile(BaseModel):
    candidate: Candidate
    roles: Roles
    locations: Locations
    skills: list[str] = Field(default_factory=list)
    scoring: Scoring = Scoring()
    outreach: Outreach = Outreach()
    # Standing answers for application forms (salary, notice period, relocation, work
    # authorisation...). Read by the Claude Code plugin when it fills forms, not by the pipeline.
    answers: dict[str, Any] = Field(default_factory=dict)
    guard: GuardSettings = GuardSettings()

    def rx(self, pattern: str) -> re.Pattern[str]:
        return re.compile(pattern, re.I)


def load_profile(path: Path | None = None) -> Profile:
    # profile.yaml holds personal data and is gitignored; a fresh clone runs on the example.
    p = path or next(
        (f for f in (ROOT / "profile.yaml", PACKAGE_ROOT / "profile.example.yaml") if f.exists()),
        ROOT / "profile.yaml",
    )
    return Profile.model_validate(yaml.safe_load(p.read_text(encoding="utf-8")))


def load_companies(path: Path | None = None) -> list[tuple[str, str, str]]:
    """[(ats, slug, display name)]"""
    p = path or next(
        (f for f in (ROOT / "companies.yaml", PACKAGE_ROOT / "companies.yaml") if f.exists()),
        ROOT / "companies.yaml",
    )
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    return [
        (ats, slug, name) for ats, boards in data.items() for slug, name in (boards or {}).items()
    ]
