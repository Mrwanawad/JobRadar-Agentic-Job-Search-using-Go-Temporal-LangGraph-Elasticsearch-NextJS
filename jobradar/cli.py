"""jobradar CLI: fetch, filter, score, list."""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import typer

from jobradar.config import ROOT, load_profile
from jobradar.db import DB
from jobradar.outreach import draft_applications, sendable
from jobradar.pipeline import fetch_all, prefilter_new, score_candidates

app = typer.Typer(no_args_is_help=True, add_completion=False)


@app.callback()
def main(verbose: bool = typer.Option(False, "--verbose", "-v")) -> None:
    # Windows consoles default to cp1252; job titles carry any Unicode.
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8", errors="replace")
    logging.basicConfig(
        level=logging.INFO if verbose else logging.WARNING, format="%(levelname)s %(message)s"
    )


def _csv(s: str) -> list[str]:
    return [x.strip() for x in s.split(",") if x.strip()]


@app.command()
def init(
    cv: Path = typer.Option(None, help="Your CV as a text PDF (not a scan)"),
    force: bool = typer.Option(False, help="Overwrite an existing profile.yaml"),
) -> None:
    """First-run setup: LLM key, CV, and a profile.yaml built from a few questions."""
    import shutil

    import click
    from pydantic import ValidationError

    from jobradar import onboard
    from jobradar.agent.profiles import DemoForm
    from jobradar.llm import providers_from_env
    from jobradar.score import pdf_text

    target = ROOT / "profile.yaml"
    if target.exists() and not force:
        typer.echo("profile.yaml already exists; edit it, or rerun with --force", err=True)
        raise typer.Exit(1)

    typer.echo("1/3  LLM key (free tiers are enough)")
    if providers_from_env():
        typer.echo("     found keys in .env")
    else:
        provider = typer.prompt(
            "     provider", default="gemini", type=click.Choice(list(onboard.KEY_URLS))
        )
        typer.echo(f"     get a free key: {onboard.KEY_URLS[provider]}")
        key = typer.prompt("     API key", hide_input=True)
        onboard.set_env({f"{provider.upper()}_API_KEY": key.strip(), "LLM_PROVIDERS": provider})

    typer.echo("2/3  CV")
    cv = cv or Path(typer.prompt("     path to your CV PDF"))
    cv = cv.expanduser().resolve()
    if not cv.exists():
        typer.echo(f"     not found: {cv}", err=True)
        raise typer.Exit(1)
    dest = ROOT / "cv" / "cv.pdf"
    dest.parent.mkdir(exist_ok=True)
    if cv != dest:
        shutil.copyfile(cv, dest)
    text = pdf_text(dest)
    if len(text) < 300:
        typer.echo("     the PDF has almost no text (scanned?); export your CV as a text PDF")
        raise typer.Exit(1)
    hint: dict = {}
    try:
        hint = onboard.suggest_from_cv(text)
        typer.echo("     read your CV; suggestions below are defaults, press Enter to keep")
    except Exception as e:  # no key or quota: the user answers without defaults
        typer.echo(f"     could not read the CV with the LLM ({str(e)[:80]}); answer by hand")

    typer.echo("3/3  About you and the jobs you want")
    regions = ", ".join(onboard.region_names())
    while True:
        try:
            form = DemoForm(
                name=typer.prompt("     full name"),
                base=typer.prompt(
                    "     city, country you live in", default=hint.get("base") or None
                ),
                target_titles=_csv(
                    typer.prompt(
                        "     job titles to search, comma separated",
                        default=", ".join(hint.get("target_titles", [])) or None,
                    )
                ),
                seniority=typer.prompt(
                    "     seniority",
                    default=hint.get("seniority") or "mid",
                    type=click.Choice(["junior", "mid", "senior", "lead"]),
                ),
                remote_regions=_csv(
                    typer.prompt(
                        f"     remote regions you can work from ({regions})", default="worldwide"
                    )
                ),
                onsite_locations=_csv(
                    typer.prompt(
                        "     other cities/countries for on-site work, comma separated (or none)",
                        default="none",
                    ).replace("none", "")
                ),
                needs_sponsorship=typer.confirm(
                    "     need visa sponsorship outside your country?", default=True
                ),
                skills=_csv(
                    typer.prompt(
                        "     key skills, comma separated",
                        default=", ".join(hint.get("skills", [])) or None,
                    )
                ),
            )
            break
        except ValidationError as e:
            typer.echo(f"     {e.errors()[0]['loc'][0]}: {e.errors()[0]['msg']}; try again")
    data = onboard.build_profile(
        form,
        email=typer.prompt("     email for applications"),
        phone=typer.prompt("     phone with country code (optional)", default=""),
        cv_link=typer.prompt(
            "     public link to your CV, e.g. Google Drive 'anyone with the link' (optional)",
            default="",
        ),
        links={
            "linkedin": typer.prompt("     LinkedIn URL (optional)", default=""),
            "github": typer.prompt("     GitHub URL (optional)", default=""),
        },
    )
    onboard.write_profile(data, target)
    o = data["outreach"]
    typer.echo(
        f"\nwrote profile.yaml. Nothing is sent before {o['dry_run_until']} (dry run), then max "
        f"{o['daily_cap']}/day.\nNext: `jobradar doctor`, then `jobradar run`."
    )


@app.command()
def doctor(ping: bool = typer.Option(False, help="Also make one real LLM call")) -> None:
    """Check setup: profile, CV, LLM keys, sending state, blank form answers."""
    from jobradar.onboard import checks

    results = checks(ping=ping)
    for level, name, detail in results:
        typer.echo(f"{level.upper():<5} {name:<15} {detail}")
    if any(level == "fail" for level, _, _ in results):
        raise typer.Exit(1)


@app.command("log")
def log_cmd(
    company: str,
    title: str,
    url: str = typer.Option("", help="Posting or application page"),
    channel: str = typer.Option("manual", help="manual (form) | email | whatsapp | linkedin"),
    recipient: str = typer.Option("", help="Email/number, if sent to a person"),
    ref: str = typer.Option("", help="ATS, confirmation id, salary asked... free text"),
    found_on: str = typer.Option(None, help="Where you found it, e.g. 'LinkedIn post'"),
) -> None:
    """Record an application sent outside the pipeline, so it is counted and never repeated."""
    oid = DB().log_application(company, title, url, channel, recipient, ref, found_on)
    typer.echo(f"#{oid} logged" if oid else "already logged")


@app.command()
def check(company: str) -> None:
    """Show applications already sent or drafted to a company. Run before applying."""
    rows = DB().applications_to(company)
    for r in rows:
        typer.echo(
            f"#{r['id']:<4} {r['status']:<6} {(r['sent_at'] or '')[:10]:<10} "
            f"{r['company']} - {r['title']}  ({r['channel']}: {r['recipient']})"
        )
    typer.echo(f"{len(rows)} earlier applications" if rows else "no earlier applications")


@app.command()
def fetch() -> None:
    """Pull jobs from every board and feed into the DB, then prefilter new ones."""
    db = DB()
    s = fetch_all(db)
    typer.echo(f"fetched {s.fetched}, new {s.new}, failed sources {len(s.failed)}")
    for f in s.failed:
        typer.echo(f"  FAIL {f}")
    typer.echo(f"prefilter: {prefilter_new(db, load_profile())}")


@app.command()
def refilter() -> None:
    """Re-run the prefilter on all unscored jobs, e.g. after editing profile.yaml."""
    db = DB()
    typer.echo(f"reset {db.reset_unscored()} jobs")
    typer.echo(f"prefilter: {prefilter_new(db, load_profile())}")


@app.command()
def score(limit: int = typer.Option(None, help="Max LLM calls (default from profile)")) -> None:
    """LLM-score candidate jobs, best keyword matches first."""
    db, profile = DB(), load_profile()
    s = score_candidates(
        db, profile, limit=limit, on_scored=lambda name, sc: typer.echo(f"  {sc:4.1f}  {name}")
    )
    typer.echo(f"scored {s.scored}")
    for e in s.errors:
        typer.echo(f"  ERR {e}")
    if s.stopped:
        typer.echo(f"stopped early, LLM quota exhausted: {s.stopped}")


@app.command()
def run(limit: int = typer.Option(None, help="Max LLM calls (default from profile)")) -> None:
    """fetch + score + draft applications."""
    fetch()
    score(limit)
    draft(limit=None)
    top(min_score=None, n=25, xlsx=None)


@app.command()
def draft(limit: int = typer.Option(None, help="Max drafts (default from profile)")) -> None:
    """Draft an application (email, WhatsApp or form cover letter) per shortlisted job."""
    s = draft_applications(DB(), load_profile(), limit=limit)
    typer.echo(f"drafted {s.drafted}")
    for e in s.errors:
        typer.echo(f"  ERR {e}")
    if s.stopped:
        typer.echo(f"stopped early, LLM quota exhausted: {s.stopped}")


@app.command()
def outbox(
    status: str = typer.Option(None, help="draft | sent | failed | skipped"),
    channel: str = typer.Option(None, help="email | whatsapp | manual"),
    full: bool = typer.Option(False, help="Print message bodies"),
) -> None:
    """List drafted applications. `manual` ones are yours to paste into the apply form."""
    rows = DB().outbox(status, channel)
    for r in rows:
        typer.echo(
            f"#{r['id']:<4} {r['status']:<8} {r['channel']:<8} {r['llm_score']:4.1f}  "
            f"{r['company']} - {r['title']}\n      to: {r['recipient']}"
        )
        if full:
            if r["subject"]:
                typer.echo(f"      subject: {r['subject']}")
            typer.echo("      " + r["body"].replace("\n", "\n      ") + "\n")
    typer.echo(f"{len(rows)} items")


@app.command("sendable")
def sendable_cmd() -> None:
    """JSON of drafts allowed out now (dry run, daily cap, dedupe applied). Used by the sender."""
    s = sendable(DB(), load_profile())
    typer.echo(json.dumps({"blocked": s.blocked, "items": s.items}, ensure_ascii=False, indent=1))


@app.command()
def process(
    company: str,
    title: str,
    stage: str = typer.Option(None, help="e.g. 'HR interview done', 'Technical 2 scheduled'"),
    found_by: str = typer.Option(None, help="pipeline | agent | you"),
    found_on: str = typer.Option(None, help="Where the posting was found, e.g. 'LinkedIn post'"),
    method: str = typer.Option(None, help="e.g. Workable form, Cold email, LinkedIn Easy Apply"),
    outbox_id: int = typer.Option(None, help="Outbox row of the application, if the agent sent it"),
    applied_at: str = typer.Option(None, help="YYYY-MM-DD"),
    contacts: str = typer.Option(None),
    next_step: str = typer.Option(None),
    notes: str = typer.Option(None),
    closed: bool = typer.Option(None, "--closed/--active", help="Rejected / withdrawn / done"),
) -> None:
    """Track an application that is moving (interviews). Shown on the dashboard."""
    db = DB()
    exists = db.conn.execute(
        "SELECT 1 FROM processes WHERE company=? AND title=?", (company, title)
    ).fetchone()
    if not exists and not (stage and found_by and method):
        typer.echo("new process needs --stage, --found-by and --method", err=True)
        raise typer.Exit(1)
    if found_by and found_by not in {"pipeline", "agent", "you"}:
        typer.echo("--found-by must be pipeline | agent | you", err=True)
        raise typer.Exit(1)
    pid = db.upsert_process(
        company,
        title,
        stage=stage,
        found_by=found_by,
        found_on=found_on,
        method=method,
        outbox_id=outbox_id,
        applied_at=applied_at,
        contacts=contacts,
        next_step=next_step,
        notes=notes,
        active=None if closed is None else int(not closed),
    )
    typer.echo(f"process #{pid} saved")


@app.command()
def dashboard(
    port: int = typer.Option(0, help="0 = random free port"),
    open_browser: bool = typer.Option(True, "--open/--no-open"),
) -> None:
    """Serve a read-only dashboard of the agent's work on localhost."""
    import webbrowser

    from jobradar.dashboard import serve

    server = serve(port)
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    typer.echo(f"JobRadar dashboard: {url}  (Ctrl+C to stop)")
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


@app.command()
def mark(
    outbox_id: int,
    status: str = typer.Argument(..., help="sent | failed | skipped | draft"),
    ref: str = typer.Option("", help="Message id or error text"),
    found_on: str = typer.Option(None, help="Where the posting was found, e.g. 'LinkedIn post'"),
) -> None:
    """Record what happened to an outbox item."""
    if status not in {"sent", "failed", "skipped", "draft"}:
        raise typer.BadParameter("status must be sent, failed, skipped or draft")
    if not DB().mark(outbox_id, status, ref, found_on):
        raise typer.Exit(f"no outbox item #{outbox_id}")
    typer.echo(f"#{outbox_id} -> {status}")


@app.command()
def top(
    min_score: float = typer.Option(None, "--min", help="Default: profile shortlist_min"),
    n: int = 25,
    xlsx: Path = typer.Option(None, help="Also write the shortlist to this .xlsx file"),
) -> None:
    """Show the shortlist."""
    db, profile = DB(), load_profile()
    rows = db.shortlist(profile.scoring.shortlist_min if min_score is None else min_score, n)
    for r in rows:
        res = json.loads(r["llm_json"])
        contact = ", ".join(json.loads(r["emails"]) + json.loads(r["phones"])) or "-"
        typer.echo(
            f"{r['llm_score']:4.1f}  {r['company']} - {r['title']}\n"
            f"      {r['location'] or '?'} | {res.get('location_fit')} | contact: {contact}\n"
            f"      {r['url']}\n"
            f"      + {'; '.join(res.get('reasons', []))}\n"
            f"      - {'; '.join(res.get('red_flags', []))}"
        )
    typer.echo(f"{len(rows)} jobs. DB: {db.counts()}")
    if xlsx:
        _write_xlsx(db, rows, xlsx)
        typer.echo(f"wrote {xlsx}")


def _write_xlsx(db: DB, rows: list, path: Path) -> None:
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "shortlist"
    cols = [
        "score",
        "company",
        "title",
        "location",
        "location_fit",
        "salary",
        "url",
        "reasons",
        "red_flags",
        "pitch_angle",
        "emails",
        "phones",
        "posted_at",
        "source",
        "apply_via",
        "outreach_status",
        "application_text",
    ]
    ws.append(cols)
    for r in rows:
        res = json.loads(r["llm_json"])
        d = db.draft_for(r["uid"])
        ws.append(
            [
                r["llm_score"],
                r["company"],
                r["title"],
                r["location"],
                res.get("location_fit"),
                r["salary"],
                r["url"],
                "; ".join(res.get("reasons", [])),
                "; ".join(res.get("red_flags", [])),
                res.get("pitch_angle", ""),
                ", ".join(json.loads(r["emails"])),
                ", ".join(json.loads(r["phones"])),
                r["posted_at"],
                r["source"],
                d and f"{d['channel']}: {d['recipient']}",
                d and d["status"],
                d and d["body"],
            ]
        )
    path = path if path.is_absolute() else ROOT / path
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)


# ---- platform mode (needs the `platform` extra and the docker compose stack) ----------------


@app.command()
def worker() -> None:
    """Run the Temporal agent worker (task queue jobradar-agent)."""
    from jobradar.agent.worker import main as run_worker

    run_worker()


@app.command("publish-profile")
def publish_profile(
    profile_id: str = typer.Option("owner", help="Id the daily schedule runs for"),
    dsn: str = typer.Option(
        "postgresql://jobradar:jobradar@localhost:5432/jobradar", envvar="DATABASE_URL"
    ),
) -> None:
    """Copy profile.yaml + CV text into Postgres as the personal platform profile."""
    from psycopg import connect
    from psycopg.types.json import Jsonb

    from jobradar.score import cv_text

    prof = load_profile()
    with connect(dsn) as c:
        c.execute(
            """INSERT INTO profiles (id, kind, owner, profile, cv_text)
               VALUES (%s, 'personal', %s, %s, %s)
               ON CONFLICT (id) DO UPDATE SET profile = EXCLUDED.profile,
                                              cv_text = EXCLUDED.cv_text""",
            (profile_id, prof.candidate.email, Jsonb(prof.model_dump(mode="json")), cv_text(prof)),
        )
    typer.echo(f"profile {profile_id!r} published; schedule it: jobradar schedule {profile_id}")


if __name__ == "__main__":
    app()
