"""README GIF 1: set up, find and rank jobs in the terminal.

    python docs/demo/scene_setup.py
    python $DEMO_GIF/compose.py docs/demo/build/setup --out docs/demo/setup.gif

$DEMO_GIF = ~/.claude/skills/demo-gif/scripts (the demo-gif skill).
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.expanduser("~/.claude/skills/demo-gif/scripts"))
from director import Director, run  # noqa: E402

HERE = Path(__file__).resolve().parent
URL = (HERE / "terminal.html").as_uri()


async def scene(d: Director):
    p = d.page
    cmd = p.get_by_label("command").last
    await d.goto(URL, settle=0.6)

    await d.caption("Set up from your CV", step=1)
    await d.move((560, 640))
    await d.type(cmd, "uv run jobradar init --cv ~/Documents/sam-rivera-cv.pdf", cps=22)
    await d.press("Enter")
    await d.fast(p.get_by_text("wrote profile.yaml.").wait_for(timeout=60_000), label="Answering")
    await d.hold(1.4)

    await d.caption("Fetch ~60 boards, score every fit", step=2)
    await d.type(cmd, "uv run jobradar run", cps=18)
    await d.press("Enter")
    await d.fast(p.get_by_text("drafted {").wait_for(timeout=60_000), label="Scoring")
    await d.hold(1.2)

    await d.caption("A shortlist with reasons and red flags", step=3)
    await d.type(cmd, "uv run jobradar top --min 8.5", cps=18)
    await d.press("Enter")
    await p.get_by_text("3 jobs. DB:").wait_for()
    await d.hold(0.6)
    await d.spotlight(p.locator("#best"), pad=6)
    await d.arrow(p.locator("#best"), "Best fit first", side="right")
    await d.hold(2.2)
    await d.clear_arrow()
    await d.clear_spotlight()
    await d.hold(0.5)


run(scene, out=str(HERE / "build" / "setup"), title="JobRadar",
    subtitle="Your CV in, a ranked shortlist out", url_label="Terminal", theme="light")  # fmt: skip
