"""Shared loaders for the eval set: the synthetic persona and the labeled postings."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from jobradar.agent.profiles import DemoForm, demo_profile
from jobradar.config import Profile

DATA = Path(__file__).parent / "data"
BANDS = ("low", "mid", "high")


def band(score: float) -> str:
    """Score band the labels use: low < 4 <= mid < 7 <= high."""
    return "high" if score >= 7 else "mid" if score >= 4 else "low"


def persona() -> tuple[Profile, str]:
    raw = yaml.safe_load((DATA / "persona.yaml").read_text(encoding="utf-8"))
    profile = demo_profile(DemoForm.model_validate(raw["form"]))
    # Labels judge role and location only; posting age would make the eval drift with time.
    profile.scoring.max_age_days = 100_000
    return profile, raw["cv"]


def postings() -> list[dict[str, Any]]:
    lines = (DATA / "postings.jsonl").read_text(encoding="utf-8").splitlines()
    return [json.loads(x) for x in lines if x.strip()]
