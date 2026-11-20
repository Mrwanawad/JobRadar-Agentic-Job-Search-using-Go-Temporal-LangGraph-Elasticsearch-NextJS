"""First-run setup for a new user: `jobradar init` writes profile.yaml and .env, `jobradar
doctor` checks that everything the pipeline and the Claude Code plugin need is in place.

The profile is built with the same code as the website's demo form (agent/profiles.py), so a
handful of plain answers (titles, seniority, regions) becomes the regex rules the prefilter uses.
"""

from __future__ import annotations

import os
import re
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import yaml

from jobradar.agent.profiles import REGIONS, DemoForm, demo_profile
from jobradar.config import ROOT, load_companies, load_profile
from jobradar.llm import LLMClient, providers_from_env

# Where to get a free key, per provider `jobradar init` offers.
KEY_URLS = {
    "gemini": "https://aistudio.google.com/apikey",
    "openrouter": "https://openrouter.ai/keys",
    "groq": "https://console.groq.com/keys",
}

# Asked by most application forms; the plugin fills forms from these. Empty = ask the user.
ANSWER_TEMPLATE: dict[str, Any] = {
    "work_authorisation": "",
    "needs_visa_sponsorship": "",
    "willing_to_relocate": "",
    "notice_period": "",
    "years_of_experience": "",
    "salary": {"current": "", "expected": "", "currency": ""},
    "how_did_you_hear": "Company careers page",
    "pronouns": "",
}

SUGGEST_PROMPT = """From this CV, suggest a job search. Reply with JSON only:
{{"target_titles": ["<2-5 job titles this person should apply for>"],
  "seniority": "junior" | "mid" | "senior" | "lead",
  "skills": ["<8-15 short lowercase skill keywords from the CV>"],
  "base": "<city, country the CV says they live in, or empty>"}}

CV:
{cv}"""


def suggest_from_cv(cv: str, llm: LLMClient | None = None) -> dict[str, Any]:
    """Titles, seniority, skills and base read from the CV. {} if no LLM is reachable."""
    if not cv.strip():
        return {}
    llm = llm or LLMClient()
    data, _ = llm.chat_json(
        [{"role": "user", "content": SUGGEST_PROMPT.format(cv=cv[:12000])}], max_tokens=2000
    )
    return data if isinstance(data, dict) else {}


def build_profile(
    form: DemoForm,
    *,
    email: str,
    phone: str = "",
    cv: str = "cv/cv.pdf",
    cv_link: str = "",
    links: dict[str, str] | None = None,
    today: date | None = None,
) -> dict[str, Any]:
    """profile.yaml contents. Sending stays off (dry run) for a week so the user reviews drafts
    before anything goes out."""
    p = demo_profile(form)
    p.candidate.email, p.candidate.phone, p.candidate.cv = email, phone, cv
    p.candidate.cv_link = cv_link
    p.candidate.links = {k: v for k, v in (links or {}).items() if v}
    p.outreach.signature = "\n".join(x for x in (form.name, phone) if x)
    p.outreach.daily_cap = 5
    p.outreach.dry_run_until = (today or date.today()) + timedelta(days=7)
    p.answers = {
        **ANSWER_TEMPLATE,
        "needs_visa_sponsorship": "yes" if form.needs_sponsorship else "no",
    }
    return p.model_dump(mode="json")


HEADER = """\
# Your JobRadar profile (gitignored: never commit it). Written by `jobradar init`.
# Edit freely; patterns are case-insensitive regexes. After editing roles or locations run
# `jobradar refilter`. `answers` is what the Claude Code plugin types into application forms.
"""


def write_profile(data: dict[str, Any], path: Path = ROOT / "profile.yaml") -> Path:
    path.write_text(
        HEADER + yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=100),
        encoding="utf-8",
    )
    return path


def set_env(values: dict[str, str], path: Path = ROOT / ".env") -> Path:
    """Set keys in .env, keeping every other line. Starts from .env.example on first run."""
    if not path.exists():
        example = path.with_name(".env.example")
        path.write_text(
            example.read_text(encoding="utf-8") if example.exists() else "", encoding="utf-8"
        )
    lines = path.read_text(encoding="utf-8").splitlines()
    for key, value in values.items():
        rx = re.compile(rf"^#?\s*{re.escape(key)}=")
        line = f"{key}={value}"
        idx = next((i for i, x in enumerate(lines) if rx.match(x)), None)
        if idx is None:
            lines.append(line)
        else:
            lines[idx] = line
        os.environ[key] = value
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def region_names() -> list[str]:
    return list(REGIONS)


# ---- doctor ---------------------------------------------------------------------------------


def checks(root: Path = ROOT, ping: bool = False) -> list[tuple[str, str, str]]:
    """[(level, name, detail)], level = ok | warn | fail. fail = the pipeline cannot run."""
    out: list[tuple[str, str, str]] = []
    add = lambda lvl, name, detail="": out.append((lvl, name, detail))  # noqa: E731

    prof_path = root / "profile.yaml"
    if not prof_path.exists():
        add("fail", "profile.yaml", "missing: run `jobradar init`")
        return out
    try:
        prof = load_profile(prof_path)
    except Exception as e:  # yaml or validation error, shown as-is
        add("fail", "profile.yaml", f"invalid: {str(e)[:200]}")
        return out
    add("ok", "profile.yaml", prof.candidate.name)

    cv = root / prof.candidate.cv
    if not prof.candidate.cv or not cv.exists():
        add("fail", "CV", f"not found: {cv}")
    else:
        from jobradar.score import pdf_text

        try:
            n = len(pdf_text(cv))
        except Exception as e:
            add("fail", "CV", f"cannot read PDF: {e}")
        else:
            if n < 300:
                add("fail", "CV", f"only {n} characters of text: scanned PDF? export a text PDF")
            else:
                add("ok", "CV", f"{cv.name}, {n} characters")

    providers = providers_from_env()
    if not providers:
        add("fail", "LLM keys", "none in .env: get a free key at " + KEY_URLS["gemini"])
    else:
        add("ok", "LLM keys", ", ".join(p.name for p in providers))
        if ping:
            try:
                res = LLMClient(providers).chat(
                    [{"role": "user", "content": "Reply with the word ok."}], max_tokens=200
                )
                add("ok", "LLM ping", f"{res.provider}:{res.model}")
            except Exception as e:
                add("fail", "LLM ping", str(e)[:200])

    n = len(load_companies())
    add("ok" if n else "warn", "companies.yaml", f"{n} company boards (plus public job feeds)")

    o = prof.outreach
    if o.dry_run():
        add("warn", "sending", f"dry run until {o.dry_run_until}: drafts only")
    else:
        add("ok", "sending", f"live, max {o.daily_cap}/day")
    if not prof.candidate.cv_link:
        add("warn", "cv_link", "empty: email applications stay unsent until you add one")
    blanks = [k for k, v in prof.answers.items() if v in ("", None)]
    if blanks:
        add("warn", "answers", "blank (the plugin will ask you): " + ", ".join(blanks))
    return out
