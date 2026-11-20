"""README GIF "inside the agent": one job traced through every stage of a run.

    python docs/demo/scene_pipeline.py
    python $DEMO_GIF/compose.py docs/demo/build/pipeline --out docs/demo/pipeline.gif --fps 12 --width 1000

$DEMO_GIF = ~/.claude/skills/demo-gif/scripts (the demo-gif skill).
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.expanduser("~/.claude/skills/demo-gif/scripts"))
from director import Director, run  # noqa: E402

HERE = Path(__file__).resolve().parent
URL = (HERE / "pipeline.html").as_uri()


async def scene(d: Director):
    p = d.page

    async def stage(n: int, read: float) -> None:
        await p.evaluate(f"stage({n})")
        await p.locator(f"#d{n}").wait_for(state="attached", timeout=60_000)
        await d.hold(read)

    await d.goto(URL, settle=0.6)
    await d.move((150, 160))

    await d.caption("Fetch ~11,000 postings from 56 sources", step=1)
    await stage(1, 3.0)

    await d.caption("Free rules drop 92% before any LLM call", step=2)
    await stage(2, 1.0)
    await d.spotlight(p.locator("#keep"), pad=6)
    await d.hold(3.0)
    await d.clear_spotlight()

    await d.caption("Keywords + meaning, fused with RRF", step=3)
    await stage(3, 2.0)
    await d.spotlight(p.locator("#rrf"), pad=6)
    await d.arrow(p.locator("#rrf"), "Best match of 190", side="bottom")
    await d.hold(4.0)
    await d.clear_arrow()
    await d.clear_spotlight()

    await d.caption("Screening agent: bad JSON repaired, score calibrated", step=4)
    await stage(4, 1.0)
    await d.spotlight(p.locator("#screenjson"), pad=6)
    await d.hold(5.5)
    await d.clear_spotlight()

    await d.caption("Critic catches an invented claim, writer removes it", step=5)
    await stage(5, 1.0)
    await d.spotlight(p.locator("#letter"), pad=6)
    await d.arrow(p.locator("#fab"), "Not in the CV: deleted", side="bottom")
    await d.hold(4.5)
    await d.clear_arrow()
    await d.clear_spotlight()
    await d.hold(1.5)

    await d.caption("You approve every application", step=6)
    await stage(6, 3.5)

    await d.caption("Applied, skipped or handed back, and tracked", step=7)
    await stage(7, 2.0)
    await d.spotlight(p.locator("#v7 table"), pad=8)
    await d.hold(6.0)
    await d.clear_spotlight()
    await d.hold(0.8)


run(scene, out=str(HERE / "build" / "pipeline"), title="Inside JobRadar",
    subtitle="One job, traced through fetch, rules, hybrid search and two LangGraph agents",
    url_label="RadarWorkflow")  # fmt: skip
