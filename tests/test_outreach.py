import json
from datetime import date

import httpx
import respx

from jobradar.config import load_profile
from jobradar.db import DB
from jobradar.llm import LLMClient, Provider
from jobradar.models import Job
from jobradar.outreach import draft_applications, pick_email, sendable

PROFILE = load_profile()
SCORE = {"score": 9, "location_fit": "eligible", "reasons": ["fit"], "pitch_angle": "voice agents"}
BODY = (
    "Your voice agent work is the reason I am writing. I build voice agents and the backend"
    " services behind them, and I would like to bring that to this role. Happy to walk you"
    " through what I have shipped and how I would approach your roadmap. When could we talk?"
)
DRAFT = json.dumps({"subject": "Voice AI Engineer", "body": BODY})


def profile(**outreach):
    p = PROFILE.model_copy(deep=True)
    p.candidate.cv_link = "https://drive.example/cv"
    for k, v in outreach.items():
        setattr(p.outreach, k, v)
    return p


def scored_db(*contacts):
    db = DB(":memory:")
    jobs = [
        Job(
            source="t",
            external_id=str(i),
            company=f"Co{i}",
            title="Voice AI Engineer",
            url=f"https://x/{i}",
            apply_url=f"https://x/{i}/apply",
            emails=emails,
            phones=phones,
        )
        for i, (emails, phones) in enumerate(contacts)
    ]
    db.upsert_jobs(jobs)
    for j in jobs:
        db.set_score(j.uid, 9.0, SCORE, "t:m")
    return db


def llm():
    return LLMClient([Provider("t", "https://llm.test/v1", "k", "m")], http=httpx.Client())


def test_pick_email_skips_non_hiring_addresses():
    assert pick_email(["privacy@co.com", "jane@co.com", "careers@co.com"]) == "careers@co.com"
    assert pick_email(["privacy@co.com", "jane@co.com"]) == "jane@co.com"
    assert pick_email(["noreply@co.com", "accommodations@co.com"]) == ""


@respx.mock
def test_draft_picks_channel_and_appends_cv_link(monkeypatch):
    monkeypatch.setattr("jobradar.outreach.cv_text", lambda p: "CV")
    respx.post("https://llm.test/v1/chat/completions").mock(
        return_value=httpx.Response(200, json={"choices": [{"message": {"content": DRAFT}}]})
    )
    db = scored_db((["jobs@co0.com"], []), ([], ["+201001234567"]), ([], []))
    s = draft_applications(db, profile(), llm=llm())
    assert s.drafted == {"email": 1, "whatsapp": 1, "manual": 1}
    assert s.review == 1  # WhatsApp carries the CV: held for approval
    by = {r["channel"]: r for r in db.outbox()}
    assert by["email"]["recipient"] == "jobs@co0.com" and by["email"]["status"] == "draft"
    assert by["whatsapp"]["status"] == "review" and "CV PDF" in by["whatsapp"]["guard"]
    assert "https://drive.example/cv" in by["email"]["body"]
    assert by["whatsapp"]["recipient"] == "201001234567" and by["whatsapp"]["subject"] == ""
    assert by["manual"]["recipient"].endswith("/apply")
    assert draft_applications(db, profile(), llm=llm()).drafted["email"] == 0  # no re-draft


def add(db, channel, recipient):
    uid = db.to_draft(0)[0]["uid"]
    return db.add_draft(uid, channel, recipient, "s", "b")


def test_sendable_gates():
    db = scored_db(([], []), ([], []), ([], []), ([], []))
    a = add(db, "email", "jobs@co0.com")
    # Co1's posting listing Co0's address: held, so approve it to test the dedupe below
    assert db.approve(add(db, "email", "jobs@co0.com"))
    w = add(db, "whatsapp", "2010")
    add(db, "manual", "https://x/apply")
    today = date(2026, 10, 30)

    assert sendable(db, profile(dry_run_until=today), today).blocked.startswith("dry run")
    s = sendable(db, profile(dry_run_until=None), today)
    assert {i["recipient"] for i in s.items} == {"jobs@co0.com"}  # one per recipient, no manual
    # WhatsApp attaches the CV PDF: held until a person approves that one item
    assert next(r for r in db.outbox() if r["id"] == w)["status"] == "review"
    assert db.approve(w)
    no_link = profile(dry_run_until=None)
    no_link.candidate.cv_link = ""
    assert [i["channel"] for i in sendable(db, no_link, today).items] == ["whatsapp"]

    db.mark(a, "sent", "msg1")
    s = sendable(db, profile(dry_run_until=None), today)
    assert [i["recipient"] for i in s.items] == ["2010"]  # duplicate recipient skipped
    assert [r["status"] for r in db.outbox(channel="email")].count("skipped") == 1
    assert sendable(db, profile(dry_run_until=None, daily_cap=1)).blocked.startswith("daily cap")


def test_sendable_rechecks_recipients_at_send_time():
    db = scored_db(([], []), ([], []), ([], []))
    bad = add(db, "email", "hiring@attacker.invalid")
    other = add(db, "email", "jobs@gmail.com")
    ok = add(db, "email", "jobs@co2.com")
    s = sendable(db, profile(dry_run_until=None), date(2026, 10, 30))
    assert [i["id"] for i in s.items] == [ok]
    rows = {r["id"]: r for r in db.outbox()}
    assert rows[bad]["status"] == "skipped" and "reserved domain" in rows[bad]["ref"]
    assert rows[other]["status"] == "review" and "free-mail" in rows[other]["guard"]
    db.mark(other, "draft")  # re-marking by hand does not get around the check
    sendable(db, profile(dry_run_until=None), date(2026, 10, 30))
    assert next(r for r in db.outbox() if r["id"] == other)["status"] == "review"
