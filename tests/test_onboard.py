from datetime import date

import yaml
from typer.testing import CliRunner

from jobradar import cli, onboard
from jobradar.agent.profiles import DemoForm
from jobradar.config import Profile
from jobradar.db import DB
from jobradar.prefilter import Prefilter

FORM = DemoForm(
    name="Sara Ali",
    base="Lagos, Nigeria",
    target_titles=["Data Analyst", "BI Developer"],
    seniority="junior",
    remote_regions=["worldwide", "emea"],
    onsite_locations=["Accra"],
    needs_sponsorship=True,
    skills=["sql", "power bi"],
)


def test_build_profile_is_valid_and_safe_by_default():
    data = onboard.build_profile(
        FORM, email="sara@example.com", phone="+2348000000000", today=date(2026, 1, 1)
    )
    p = Profile.model_validate(data)
    assert p.candidate.email == "sara@example.com"
    assert p.outreach.dry_run(date(2026, 1, 8)) and not p.outreach.dry_run(date(2026, 1, 9))
    assert p.outreach.daily_cap == 5
    assert p.answers["needs_visa_sponsorship"] == "yes"
    assert "Lagos" in p.candidate.constraints

    pf = Prefilter(p)
    assert pf.title_ok("Junior Data Analyst")[0]
    assert not pf.title_ok("Senior Data Analyst")[0]  # junior search excludes senior
    assert pf.location_ok("Accra, Ghana", False, "")[0]
    assert not pf.location_ok("Remote - US", True, "")[0]


def test_write_profile_round_trips(tmp_path):
    path = onboard.write_profile(onboard.build_profile(FORM, email="a@b.co"), tmp_path / "p.yaml")
    assert path.read_text(encoding="utf-8").startswith("# Your JobRadar profile")
    Profile.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


def test_set_env_keeps_other_lines(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    (tmp_path / ".env.example").write_text("# comment\nLLM_PROVIDERS=gemini\n# GROQ_API_KEY=\n")
    monkeypatch.setenv("GROQ_API_KEY", "")
    onboard.set_env({"GROQ_API_KEY": "k1", "LLM_PROVIDERS": "groq"}, env, tmp_path / ".env.example")
    assert env.read_text().splitlines() == ["# comment", "LLM_PROVIDERS=groq", "GROQ_API_KEY=k1"]


def test_checks_without_profile(tmp_path):
    assert onboard.checks(tmp_path)[0][0] == "fail"


def test_log_and_check(tmp_path):
    db = DB(tmp_path / "t.db")
    first = db.log_application("Acme AI", "ML Engineer", "https://acme.ai/jobs/1", ref="Workable")
    assert first and not db.log_application("Acme AI", "ML Engineer", "https://acme.ai/jobs/1")
    hits = db.applications_to("acme ai, inc.")
    assert [h["title"] for h in hits] == ["ML Engineer"] and hits[0]["status"] == "sent"
    assert db.applications_to("Other Co") == []


def test_init_wizard(tmp_path, monkeypatch):
    cv = tmp_path / "my cv.pdf"
    cv.write_bytes(b"%PDF")
    monkeypatch.setattr(cli, "ROOT", tmp_path)
    monkeypatch.setattr("jobradar.llm.providers_from_env", lambda: ["key"])
    monkeypatch.setattr("jobradar.score.pdf_text", lambda p: "x" * 500)
    monkeypatch.setattr(
        onboard,
        "suggest_from_cv",
        lambda text: {"target_titles": ["Data Analyst"], "skills": ["sql"], "seniority": "mid"},
    )
    answers = [
        "Sara Ali", "Lagos, Nigeria", "", "", "worldwide", "", "y", "",
        "sara@example.com", "", "", "", "",
    ]  # fmt: skip
    res = CliRunner().invoke(cli.app, ["init", "--cv", str(cv)], input="\n".join(answers) + "\n")
    assert res.exit_code == 0, res.output
    p = Profile.model_validate(yaml.safe_load((tmp_path / "profile.yaml").read_text("utf-8")))
    assert (tmp_path / "cv" / "cv.pdf").exists() and p.candidate.cv == "cv/cv.pdf"
    assert p.skills == ["sql"] and p.candidate.name == "Sara Ali"
    assert CliRunner().invoke(cli.app, ["init", "--cv", str(cv)]).exit_code == 1  # no overwrite
