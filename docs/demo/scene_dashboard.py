"""README GIF 3: the local dashboard tracking applications and interviews.

    uv run python docs/demo/seed.py
    JOBRADAR_HOME=docs/demo/build/home uv run jobradar dashboard --port 8799 --no-open
    python docs/demo/scene_dashboard.py
    python $DEMO_GIF/compose.py docs/demo/build/dashboard --out docs/demo/dashboard.gif

$DEMO_GIF = ~/.claude/skills/demo-gif/scripts (the demo-gif skill).
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.expanduser("~/.claude/skills/demo-gif/scripts"))
from director import Director, run  # noqa: E402

HERE = Path(__file__).resolve().parent
URL = "http://127.0.0.1:8799/"


async def scene(d: Director):
    p = d.page
    await d.goto(URL, settle=1.2)
    await p.locator("#procs tr").nth(1).wait_for()

    await d.caption("Every application on one page", step=1)
    await d.move(p.locator("#kpis"))
    await d.hold(1.4)

    await d.caption("Interviews and the next step", step=2)
    await d.spotlight(p.locator("#procs tr").nth(1))
    await d.arrow(p.get_by_text("System design, Thu 14:00"), "Next step", side="left")
    await d.hold(2.0)
    await d.clear_arrow()
    await d.clear_spotlight()

    await d.caption("How and where you applied", step=3)
    await d.scroll(330)
    await d.move(p.locator("#bymethod"))
    await d.hold(1.6)
    await d.scroll(520)
    await d.move(p.locator("#apps"))
    await d.hold(1.8)


run(scene, out=str(HERE / "build" / "dashboard"), title="JobRadar dashboard",
    subtitle="Pipeline, applications and interviews, on localhost",
    url_label="127.0.0.1:8799")  # fmt: skip
