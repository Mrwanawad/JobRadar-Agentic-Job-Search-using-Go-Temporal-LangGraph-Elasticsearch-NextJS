"""Injection detector (A1, A2, A5): does this posting or page talk to a model?

A real posting talks to people about a job. An injected one talks to the AI reading it
("note to AI screeners", "ignore previous instructions", "اديله 10 من 10", "ensa el
ta3limat"). Rules live in rules.yaml, in English, Modern Standard Arabic, Egyptian Arabic
and Franco-Arabic, and run on normalised text so spelling variants meet one pattern. What
the sanitiser removed (hidden HTML, tag characters, overrides, base64) counts too: a posting
that hides text is already suspicious.

Verdicts, and what the pipeline does with them (Python decides, fail soft on scoring):
- clean: scored as usual.
- suspicious (>= 2 points): quarantined; never sent to the screening or writing model, never
  drafted, hidden from `jobradar top` with a count; `jobradar guard quarantined` lists why.
- malicious (>= 4 points): the same; reported apart.

Deterministic and dependency-free, so lite mode has it. A classifier tier (Llama Prompt
Guard 2) can sit behind the same `detect()` later, if the ablation shows it adds anything.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path
from typing import Any, Literal

import yaml

from jobradar.guard import enabled
from jobradar.guard.sanitize import clean_text

Label = Literal["clean", "suspicious", "malicious"]
SUSPICIOUS, MALICIOUS = 2, 4
WEIGHT = {"strong": 2, "weak": 1}

_AR_DIACRITICS = re.compile("[\u0610-\u061a\u064b-\u065f\u0670\u06d6-\u06ed\u0640]")
_AR_FOLD = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ى": "ي", "ة": "ه",
                          "ؤ": "و", "ئ": "ي"})  # fmt: skip
_FRANCO_WORD = re.compile(r"\b(?=[a-z0-9]*[a-z])(?=[a-z0-9]*[2357])[a-z0-9]+\b")
_FRANCO = {"2": "a", "3": "a", "5": "kh", "7": "h"}


@dataclass
class Verdict:
    label: Label = "clean"
    points: int = 0
    hits: list[str] = field(default_factory=list)

    @property
    def flagged(self) -> bool:
        return self.label != "clean"

    def reason(self) -> str:
        return f"{self.label}: " + ", ".join(self.hits)


def normalise(text: str) -> str:
    t = unicodedata.normalize("NFKC", text).lower()
    t = _AR_DIACRITICS.sub("", t).translate(_AR_FOLD)
    t = _FRANCO_WORD.sub(lambda m: "".join(_FRANCO.get(c, c) for c in m.group()), t)
    return re.sub(r"[ \t ]+", " ", t)


@cache
def rules() -> list[tuple[str, int, re.Pattern[str]]]:
    raw = yaml.safe_load(Path(__file__).with_name("rules.yaml").read_text(encoding="utf-8"))
    out = []
    for severity, group in raw.items():
        for name, pattern in group.items():
            out.append((name, WEIGHT[severity], re.compile(pattern.strip(), re.S | re.M)))
    return out


def detect(text: str, findings: list[str] | None = None) -> Verdict:
    """Verdict on already sanitised text plus the sanitiser's findings."""
    v = Verdict()
    if not enabled("detect"):
        return v
    norm = normalise(text)
    if any(f.startswith("direction-override") for f in findings or []):
        # Text behind a right-to-left override is stored backwards; read it both ways.
        norm += "\n" + norm[::-1]
    for name, weight, rx in rules():
        if rx.search(norm):
            v.points += weight
            v.hits.append(name)
    for f in findings or []:
        v.points += 1
        v.hits.append(f.split(":", 1)[0])
    v.label = (
        "malicious"
        if v.points >= MALICIOUS
        else "suspicious"
        if v.points >= SUSPICIOUS
        else "clean"
    )
    return v


def check_posting(job: Any) -> Verdict:
    """Sanitise and inspect every free-text field of a posting (dict or sqlite3.Row)."""
    parts, findings = [], []
    for key in ("title", "company", "location", "description"):
        try:
            s = clean_text(job[key])
        except (KeyError, IndexError):
            continue
        parts.append(s.text)
        findings += s.findings
    return detect("\n".join(parts), findings)


def check_page(text: str) -> Verdict:
    """A careers page's text (from Claude in Chrome's get_page_text) before filling it."""
    s = clean_text(text)
    return detect(s.text, s.findings)
