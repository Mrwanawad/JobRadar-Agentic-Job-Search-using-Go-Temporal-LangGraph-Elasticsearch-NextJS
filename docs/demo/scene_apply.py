"""README GIF 2: /jobradar:apply fills a careers-page form, the user approves, it is logged.

    python docs/demo/scene_apply.py
    python $DEMO_GIF/compose.py docs/demo/build/apply --out docs/demo/apply.gif

$DEMO_GIF = ~/.claude/skills/demo-gif/scripts (the demo-gif skill).
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.expanduser("~/.claude/skills/demo-gif/scripts"))
from director import Director, run  # noqa: E402

HERE = Path(__file__).resolve().parent
URL = (HERE / "apply.html").as_uri()


async def scene(d: Director):
    p = d.page
    say = lambda key: p.evaluate(f"say('{key}')")  # noqa: E731
    await d.goto(URL, settle=0.6)

    await d.caption("Best draft first, never twice", step=1)
    await say("start")
    await d.hold(0.6)

    await d.caption("Fills the form from your profile", step=2)
    await say("fill")
    await d.type(p.locator("#name"), "Sam Rivera", cps=24)
    await d.type(p.locator("#email"), "sam.rivera@example.com", cps=30)
    await d.type(p.locator("#phone"), "+20 100 000 0000", cps=30)
    await d.type(p.locator("#loc"), "Cairo, Egypt", cps=26)
    await d.click(p.locator("#cv"))
    await p.evaluate("attachCV()")
    await d.click(p.locator("#cl"))
    await d.fast(p.evaluate("coverLetter()"), label="Cover letter")
    await d.hold(0.5)
    await d.click(p.locator("#yrs"))
    await p.locator("#yrs").select_option("5+")
    await d.click(p.locator("#vno"))
    await say("ready")

    await d.caption("You approve, it submits", step=3)
    await d.type(p.get_by_label("Reply to Claude"), "yes", cps=8)
    await d.press("Enter")
    await d.click(p.locator("#submit"))
    await d.hold(0.4)

    await d.caption("Logged, so it never applies twice", step=4)
    await say("sent")
    await d.arrow(p.locator("#logged"), "Recorded in your DB", side="right")
    await d.hold(2.2)
    await d.clear_arrow()
    await d.hold(0.4)


run(scene, out=str(HERE / "build" / "apply"), title="JobRadar for Claude Code",
    subtitle="Applies through careers pages. You approve every submit.",
    url_label="jobs.example.com/brightline-ai")  # fmt: skip
