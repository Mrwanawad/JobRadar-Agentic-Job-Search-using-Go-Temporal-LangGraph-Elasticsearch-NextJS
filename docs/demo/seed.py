"""Build the synthetic demo home the README GIFs are recorded against.

    uv run python docs/demo/seed.py            # -> docs/demo/build/home

Everything here is made up: the candidate (Sam Rivera, from evals/data/persona.yaml), the
companies and the postings. Point JobRadar at it with JOBRADAR_HOME=docs/demo/build/home.
"""

from __future__ import annotations

import json
import random
import shutil
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import yaml
from pypdf import PdfWriter

REPO = Path(__file__).resolve().parents[2]
HOME = REPO / "docs" / "demo" / "build" / "home"

COMPANIES = [
    "Northwind Analytics", "Acme Robotics", "Lumen Health", "Orbital Freight", "Cedar Payments",
    "Brightline AI", "Nimbus Logistics", "Quill Legal", "Harbor Insurance", "Atlas Mobility",
    "Verde Energy", "Kestrel Security", "Mosaic Learning", "Pinnacle Retail", "Sable Fintech",
    "Tidewater Labs", "Juniper Voice", "Cobalt Maps", "Fennec Travel", "Saffron Foods",
]  # fmt: skip
TITLES = [
    "Senior AI Engineer", "Machine Learning Engineer", "Applied AI Engineer (LLM)",
    "Forward Deployed Engineer", "AI Platform Engineer", "Senior ML Engineer, Search",
    "LLM Engineer, Agents", "AI Engineer - Voice", "Staff Data Scientist", "Backend Engineer",
    "Frontend Engineer", "Product Designer", "Account Executive", "DevOps Engineer",
]  # fmt: skip
PLACES = [
    "Remote (EMEA)", "Remote", "Cairo, Egypt", "Dubai, UAE", "Riyadh, Saudi Arabia",
    "Berlin, Germany (visa support)", "London, UK", "Remote - US", "Doha, Qatar",
]  # fmt: skip
SOURCES = {"greenhouse": 0.32, "ashby": 0.26, "himalayas": 0.16, "lever": 0.1, "wwr": 0.07,
           "workable": 0.05, "remoteok": 0.04}  # fmt: skip
REASONS = [
    "Production RAG and agent work matches the core of the role",
    "FastAPI + LangGraph stack named in the posting",
    "Eval pipelines and CI gates are an explicit ask",
    "Kubernetes model serving on AWS matches their platform",
    "Open to EMEA remote; candidate is in Cairo",
]
FLAGS = ["Asks for 6+ years; CV shows 5", "Arabic preferred, not stated in CV", "On-call rotation"]

# The shortlist the GIFs show, best first: (company, title, location, score, channel, status)
SHORTLIST = [
    ("Brightline AI", "Senior AI Engineer, Agents", "Remote (EMEA)", 9.2, "manual", "sent"),
    ("Lumen Health", "Applied AI Engineer (LLM)", "Dubai, UAE", 8.8, "email", "sent"),
    ("Northwind Analytics", "Forward Deployed Engineer", "Cairo, Egypt", 8.6, "manual", "sent"),
    ("Juniper Voice", "AI Engineer - Voice Agents", "Remote", 8.4, "manual", "sent"),
    ("Cedar Payments", "Machine Learning Engineer", "Riyadh, Saudi Arabia", 8.1, "manual", "sent"),
    ("Tidewater Labs", "LLM Engineer, Evaluation", "Remote (EMEA)", 7.9, "email", "sent"),
    ("Orbital Freight", "AI Platform Engineer", "Berlin, Germany (visa support)", 7.7, "manual",
     "draft"),
    ("Mosaic Learning", "Senior ML Engineer, Search", "Remote", 7.6, "manual", "sent"),
]  # fmt: skip


def iso(d: datetime) -> str:
    return d.isoformat(timespec="seconds")


def main() -> None:
    from jobradar.agent.profiles import DemoForm
    from jobradar.onboard import build_profile

    rnd = random.Random(7)
    if HOME.exists():
        shutil.rmtree(HOME)
    (HOME / "cv").mkdir(parents=True)
    persona = yaml.safe_load((REPO / "evals" / "data" / "persona.yaml").read_text("utf-8"))

    # CV: a placeholder PDF plus the text cache JobRadar reads (newer than the PDF).
    w = PdfWriter()
    w.add_blank_page(595, 842)
    with open(HOME / "cv" / "cv.pdf", "wb") as f:
        w.write(f)
    (HOME / "cv" / "cv.txt").write_text(persona["cv"], encoding="utf-8")

    profile = build_profile(
        DemoForm(**persona["form"]),
        email="sam.rivera@example.com",
        phone="+20 100 000 0000",
        cv_link="https://example.com/sam-rivera-cv.pdf",
        links={"github": "https://github.com/sam-rivera-demo"},
        today=date.today() - timedelta(days=10),  # dry-run week already over
    )
    profile["answers"].update(
        work_authorisation="Egypt; needs sponsorship elsewhere",
        willing_to_relocate="yes",
        notice_period="1 month",
        years_of_experience="5",
        salary={"current": "", "expected": "4,500", "currency": "USD/month"},
        pronouns="prefer not to say",
    )
    (HOME / "profile.yaml").write_text(yaml.safe_dump(profile, sort_keys=False), "utf-8")
    (HOME / ".env").write_text("LLM_PROVIDERS=gemini\nGEMINI_API_KEY=demo-key\n", "utf-8")

    from jobradar.db import DB, fingerprint  # imported after JOBRADAR_HOME is set

    db = DB(HOME / "data" / "jobradar.db")
    now = datetime.now(UTC)
    rows = []
    for i in range(2380):
        src = rnd.choices(list(SOURCES), weights=list(SOURCES.values()))[0]
        company, title = rnd.choice(COMPANIES), rnd.choice(TITLES)
        status = rnd.choices(["filtered", "duplicate", "candidate"], weights=[88, 7, 5])[0]
        rows.append((f"demo{i:05d}", src, company, title, rnd.choice(PLACES), status, None, None))
    for i in range(46):  # scored, below the shortlist
        rows.append((f"low{i:03d}", rnd.choice(list(SOURCES)), rnd.choice(COMPANIES),
                     rnd.choice(TITLES[:9]), rnd.choice(PLACES), "scored",
                     round(rnd.uniform(2.5, 7.4), 1), None))  # fmt: skip
    for i, (company, title, place, score, ch, st) in enumerate(SHORTLIST):
        rows.append((f"top{i:02d}", ["ashby", "greenhouse", "lever", "workable"][i % 4], company,
                     title, place, "scored", score, (ch, st)))  # fmt: skip

    for uid, src, company, title, place, status, score, out in rows:
        seen = now - timedelta(hours=rnd.randint(1, 240))
        slug = company.lower().replace(" ", "-")
        res = {
            "score": score,
            "location_fit": "eligible" if "Berlin" not in place else "needs_sponsorship",
            "reasons": rnd.sample(REASONS, 3),
            "red_flags": rnd.sample(FLAGS, 1),
            "pitch_angle": "Shipped a RAG support assistant that resolves 40% of tickets",
        }
        db.conn.execute(
            "INSERT INTO jobs (uid, fingerprint, source, company, title, location, remote, url, "
            "description, posted_at, first_seen, status, kw_score, llm_score, llm_json, "
            "scored_by, scored_at, emails, phones, tags) VALUES "
            "(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'[]','[]','[]')",
            (uid, fingerprint(company, title), src, company, title, place,
             int("Remote" in place), f"https://jobs.example.com/{slug}/{uid}", "", iso(seen),
             iso(seen), status, rnd.randint(1, 12), score,
             json.dumps(res) if score else None, "gemini:gemini-flash" if score else None,
             iso(seen) if score else None),
        )  # fmt: skip
        if out:
            ch, st = out
            rec = (
                f"careers@{slug}.example.com"
                if ch == "email"
                else f"https://jobs.example.com/{slug}/{uid}"
            )
            ats = ["Workable form", "Greenhouse form", "Ashby form", "Lever form"][len(uid) % 4]
            sent = iso(now - timedelta(days=rnd.randint(0, 9), hours=rnd.randint(1, 8)))
            db.conn.execute(
                "INSERT INTO outbox (uid, channel, recipient, subject, body, status, created_at, "
                "sent_at, ref) VALUES (?,?,?,?,?,?,?,?,?)",
                (uid, ch, rec, title if ch == "email" else "", "Hi team, ...", st, sent,
                 sent if st == "sent" else None, "ok" if ch == "email" else ats),
            )  # fmt: skip
    db.conn.commit()

    oid = {r["title"]: r["id"] for r in db.conn.execute(
        "SELECT o.id, j.title FROM outbox o JOIN jobs j USING(uid)")}  # fmt: skip
    db.upsert_process("Brightline AI", "Senior AI Engineer, Agents", stage="Technical 1 booked",
                      found_by="pipeline", method="Careers form", found_on="Ashby board",
                      outbox_id=oid["Senior AI Engineer, Agents"], contacts="Dana (Eng Manager)",
                      next_step="Thu 3 Dec 14:00")  # fmt: skip
    db.upsert_process("Northwind Analytics", "Forward Deployed Engineer",
                      stage="Technical 2 booked", found_by="pipeline", method="Ashby form",
                      found_on="Ashby board",
                      outbox_id=oid["Forward Deployed Engineer"], contacts="Dana K. (Talent)",
                      next_step="System design, Thu 14:00")  # fmt: skip
    db.upsert_process("Lumen Health", "Applied AI Engineer (LLM)", stage="HR screen done",
                      found_by="pipeline", method="Cold email", found_on="Greenhouse board",
                      outbox_id=oid["Applied AI Engineer (LLM)"],
                      next_step="Take-home due Monday")  # fmt: skip
    db.upsert_process(
        "Fennec Travel",
        "AI Engineer",
        stage="Offer received",
        found_by="you",
        method="Referral",
        found_on="LinkedIn post",
        next_step="Decide by Friday",
    )

    logs = HOME / "out" / "logs"
    logs.mkdir(parents=True)
    for d in range(6):
        day = date.today() - timedelta(days=d)
        (logs / f"{day}.log").write_text(
            f"\n=== run 09:0{d} ===\nfetched {11400 - d * 37}, new {300 + d * 11}, "
            f"failed sources 0\nscored {40 + d}\ndrafted {{'email': 1, 'whatsapp': 0, "
            f"'manual': {3 + d % 2}}}\n=== send 09:2{d} ===\n#{20 + d} email -> sent\n",
            encoding="utf-8",
        )
    print(f"demo home: {HOME}")


if __name__ == "__main__":
    import os

    os.environ["JOBRADAR_HOME"] = str(HOME)
    main()
