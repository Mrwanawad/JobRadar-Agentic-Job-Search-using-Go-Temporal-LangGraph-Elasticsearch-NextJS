"""README GIFs recorded from terminal.html replays and the live dashboard.

    python docs/demo/scenes.py setup|find|schedule|track
    python $DEMO_GIF/compose.py docs/demo/build/<name> --out docs/demo/<name>.gif --fps 12 --width 1000

$DEMO_GIF = ~/.claude/skills/demo-gif/scripts (the demo-gif skill). `track` also needs the
dashboard on the demo home (see seed.py). The hero GIF is scene_apply.py.

Holds after each output are reading time: about 0.35 s per line plus 1.5 s.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.expanduser("~/.claude/skills/demo-gif/scripts"))
from director import Director, run  # noqa: E402

HERE = Path(__file__).resolve().parent
TERM = (HERE / "terminal.html").as_uri()
DASH = "http://127.0.0.1:8799/"


async def cmd(d: Director, text: str, done: str, read: float, cps: float = 20) -> None:
    """Type a command, wait for its last line (element id `done`), then hold to read."""
    await d.type(d.page.get_by_label("command").last, text, cps=cps)
    await d.press("Enter")
    await d.page.locator(f"#{done}").wait_for(timeout=120_000)
    await d.hold(read)


async def setup(d: Director):
    await d.goto(TERM, settle=0.6)
    await d.move((560, 640))
    await d.caption("Answer a few questions, once", step=1)
    await cmd(d, "uv run jobradar init --cv ~/Documents/sam-rivera-cv.pdf", "wrote", 3.5)
    await d.caption("Doctor checks keys, CV and limits", step=2)
    await cmd(d, "uv run jobradar doctor", "docdone", 2.0)
    await d.spotlight(d.page.locator("#dry"), pad=6)
    await d.arrow(d.page.locator("#dry"),
                  "Nothing sent for a week", side="right")  # fmt: skip
    await d.hold(3.0)
    await d.clear_arrow()
    await d.clear_spotlight()
    await d.hold(0.6)


async def find(d: Director):
    await d.goto(TERM, settle=0.6)
    await d.move((560, 640))
    await d.caption("Fetch ~60 boards, filter for free, LLM-score the rest", step=1)
    await cmd(d, "uv run jobradar run", "drafted", 3.5)
    await d.caption("A shortlist with reasons and red flags", step=2)
    await cmd(d, "uv run jobradar top --min 8.5", "topdone", 1.0)
    await d.spotlight(d.page.locator("#best"), pad=6)
    await d.arrow(d.page.locator("#best"), "Best fit first", side="right")
    await d.hold(4.5)
    await d.clear_arrow()
    await d.clear_spotlight()
    await d.caption("Drafts ready: careers forms and recruiter emails", step=3)
    await cmd(d, "uv run jobradar outbox --status draft", "outdone", 5.0)


async def schedule(d: Director):
    await d.goto(TERM, settle=0.6)
    await d.move((560, 640))
    await d.caption("Dry run first: nothing leaves until you trust it", step=1)
    await cmd(d, "uv run jobradar sendable", "blocked", 2.8)
    await d.caption("Schedule it once: every morning at 09:00", step=2)
    await cmd(d, "powershell -File scripts/install_schedule.ps1 -At 09:00", "installed", 2.2)
    await cmd(d, "crontab -l", "cron", 2.6)
    await d.caption("Next morning: fetched, scored, drafted, sent within the cap", step=3)
    await cmd(d, "cat out/logs/2026-11-28.log", "logdone", 5.5)


async def track(d: Director):
    await d.goto(TERM + "?mode=claude", settle=0.6)
    await d.move((560, 640))
    await d.caption("Got a reply? Tell Claude", step=1)
    await cmd(d, "/jobradar:track Brightline replied: interview Thu 3 Dec 14:00 with Dana (Eng Manager)",
              "trackdone", 4.5, cps=30)  # fmt: skip

    p = d.page
    await d.goto(DASH, settle=1.2)
    await p.locator("#procs tr").nth(1).wait_for()
    await d.caption("Your search on one local dashboard", step=2)
    await d.move(p.locator("#kpis"))
    await d.hold(3.0)
    await d.caption("Interviews and the next step", step=3)
    await d.spotlight(p.locator("#procs tr").nth(1))
    await d.arrow(p.get_by_text("Thu 3 Dec 14:00").first, "Next step", side="left")
    await d.hold(3.5)
    await d.clear_arrow()
    await d.clear_spotlight()
    await d.caption("Which methods and sources work", step=4)
    await d.scroll(330)
    await d.move(p.locator("#bymethod"))
    await d.hold(3.5)
    await d.caption("Every application, scored and logged", step=5)
    await d.scroll(560)
    await d.move(p.locator("#apps"))
    await d.hold(3.5)


TITLES = {
    "setup": ("JobRadar", "Set up from your CV in two minutes"),
    "find": ("JobRadar", "From 11,000 postings to a shortlist and drafts"),
    "schedule": ("JobRadar", "Runs every morning, inside your limits"),
    "track": ("JobRadar", "Replies, interviews and the whole pipeline"),
}

if __name__ == "__main__":
    name = sys.argv[1]
    title, sub = TITLES[name]
    run(globals()[name], out=str(HERE / "build" / name), title=title, subtitle=sub,
        url_label="Claude Code + dashboard" if name == "track" else "Terminal")  # fmt: skip
