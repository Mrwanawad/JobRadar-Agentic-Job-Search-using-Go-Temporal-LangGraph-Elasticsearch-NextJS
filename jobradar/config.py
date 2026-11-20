"""profile.yaml and companies.yaml, loaded once and validated."""

from __future__ import annotations

import os
import re
from datetime import date
from pathlib import Path
from typing import Any

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
