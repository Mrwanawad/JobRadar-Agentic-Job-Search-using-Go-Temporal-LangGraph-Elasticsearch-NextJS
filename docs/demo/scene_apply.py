"""README hero GIF: /jobradar:apply works through a batch of five drafted jobs.

    python docs/demo/scene_apply.py
    python $DEMO_GIF/compose.py docs/demo/build/apply --out docs/demo/apply.gif

$DEMO_GIF = ~/.claude/skills/demo-gif/scripts (the demo-gif skill).
"""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.expanduser("~/.claude/skills/demo-gif/scripts"))
from director import Director, run  # noqa: E402

HERE = Path(__file__).resolve().parent
URL = (HERE / "apply.html").as_uri()
LETTER = (
    "Your agents team ships customer-facing LLM workflows, which is what I have built for three "
    "years: a RAG support assistant at Nilecart that resolves 40% of tickets, with the eval set "
    "and CI gate I designed..."
)


async def scene(d: Director):
    p = d.page
    js = lambda code: p.evaluate(code)  # noqa: E731

    async def say(*lines):
        await js(f"say({json.dumps([list(x) for x in lines])})")

    async def q(i, state, text):
        await js(f"q({i}, {json.dumps(state)}, {json.dumps(text)})")

    await d.goto(URL, settle=0.6)

    # 1. the batch
    await d.caption("One command, a batch of jobs", step=1)
    await d.type(p.get_by_label("Reply to Claude"), "/jobradar:apply 5", cps=12)
    await d.press("Enter")
    await say(
        ("tool", "● uv run jobradar doctor  (all OK)"),
        ("tool", "● uv run jobradar outbox --status draft --channel manual"),
        ("dim", "  5 best drafts queued, highest score first"),
    )
    await d.spotlight(p.locator("#queue"), pad=6)
    await d.hold(3.2)  # read the queue
    await d.clear_spotlight()

    # 2. job 1: check, fill, approve
    await d.caption("Checks it never applied, then fills the form", step=2)
    await q(0, "run", "checking")
    await say(
        ("tool", '● uv run jobradar check "Brightline AI"'), ("dim", "  no earlier applications")
    )
    await d.hold(1.2)
    await js("show('brightline', 'jobs.example.com/brightline-ai/senior-ai-engineer')")
    await q(0, "run", "filling")
    await d.type(p.locator("#b-name"), "Sam Rivera", cps=22)
    await d.type(p.locator("#b-email"), "sam.rivera@example.com", cps=30)
    await d.type(p.locator("#b-phone"), "+20 100 000 0000", cps=30)
    await d.type(p.locator("#b-loc"), "Cairo, Egypt", cps=26)
    await d.click(p.locator("#b-cv"))
    await js("attach('b-cv')")
    await d.click(p.locator("#b-cl"))
    await js(f"fill('b-cl', {json.dumps(LETTER)})")
    await d.hold(1.8)  # read the cover letter
    await d.click(p.locator("#b-yrs"))
    await p.locator("#b-yrs").select_option("5+")
    await d.click(p.locator("#b-vno"))
    await say(
        ("", 'Filled from profile.yaml + CV. Visa: "No" (EMEA remote).'),
        ("acc", "Submit Brightline AI? I will ask before each submit."),
    )
    await d.hold(2.2)

    await d.caption("You approve. Or let it run the batch", step=3)
    await d.type(p.get_by_label("Reply to Claude"), "yes, submit the rest without asking", cps=16)
    await d.press("Enter")
    await d.click(p.locator("#b-submit"))
    await js("thanks('brightline')")
    await q(0, "ok", "submitted")
    await say(("tool", '● uv run jobradar mark 1 sent --ref "Careers form; BRT-4471"'),
              ("dim", "  #1 -> sent · tab closed"))  # fmt: skip
    await d.hold(2.0)

    # 3. job 2: duplicate
    await d.caption("Already applied? Skipped", step=4)
    await js("show('blank', 'about:blank')")
    await q(1, "run", "checking")
    await say(("tool", '● uv run jobradar check "Northwind Analytics"'),
              ("warn", "  #3 sent 2026-11-12 Northwind Analytics - Forward Deployed Engineer"))  # fmt: skip
    await q(1, "skip", "applied 11-12")
    await d.spotlight(p.locator("#q1"), pad=4)
    await d.hold(3.0)
    await d.clear_spotlight()

    # 4. job 3: another ATS, filled without asking
    await d.caption("Any careers form, any ATS", step=5)
    await q(2, "run", "filling")
    await say(
        ("tool", '● uv run jobradar check "Juniper Voice"'), ("dim", "  no earlier applications")
    )
    await js("show('juniper', 'boards.example.com/juniper-voice/jobs/ai-engineer')")
    await d.type(p.locator("#j-first"), "Sam", cps=24)
    await d.type(p.locator("#j-last"), "Rivera", cps=24)
    await d.type(p.locator("#j-email"), "sam.rivera@example.com", cps=34)
    await d.type(p.locator("#j-li"), "github.com/sam-rivera-demo", cps=34)
    await d.click(p.locator("#j-cv"))
    await js("attach('j-cv')")
    await js(f"fill('j-cl', {json.dumps(LETTER)})")
    await d.type(p.locator("#j-notice"), "1 month", cps=24)
    await d.type(p.locator("#j-sal"), "4500", cps=20)
    await d.hold(1.2)
    await d.click(p.locator("#j-submit"))
    await js("thanks('juniper')")
    await q(2, "ok", "submitted")
    await say(("tool", '● uv run jobradar mark 4 sent --ref "Greenhouse form"'))
    await d.hold(1.8)

    # 5. job 4: knockout requirement
    await d.caption("Honest about requirements", step=6)
    await q(3, "run", "reading")
    await js("show('orbital', 'jobs.example.com/orbital-freight/ai-platform')")
    await d.hold(0.8)
    await d.spotlight(p.locator("#knock"), pad=6)
    await say(("warn", "  Requires 8+ years; CV shows 5. Not applying."),
              ("tool", '● uv run jobradar mark 7 skipped --ref "needs 8+ years"'))  # fmt: skip
    await q(3, "skip", "needs 8+ yrs")
    await d.hold(3.0)
    await d.clear_spotlight()

    # 6. job 5: CAPTCHA goes to the user
    await d.caption("CAPTCHA or login? Handed to you", step=7)
    await q(4, "run", "filling")
    await js("show('cedar', 'cedar.example.com/apply/ml-engineer')")
    await d.type(p.locator("#c-name"), "Sam Rivera", cps=26)
    await d.type(p.locator("#c-email"), "sam.rivera@example.com", cps=34)
    await js("attach('c-cv')")
    await d.type(p.locator("#c-sal"), "4500 USD/month", cps=26)
    await d.spotlight(p.locator("#captcha"), pad=8)
    await q(4, "you", "CAPTCHA, tab open")
    await say(("warn", "  reCAPTCHA at submit: over to you. Tab left open."))
    await d.hold(2.6)
    await d.clear_spotlight()

    # 7. report
    await d.caption("A report for every job", step=8)
    await say(
        ("", "Done: 2 submitted · 2 skipped · 1 needs you"),
        ("dim", "All logged in data/jobradar.db; dashboard updated."),
    )
    await d.spotlight(p.locator("#queue"), pad=6)
    await d.hold(4.5)
    await d.clear_spotlight()
    await d.hold(0.5)


run(scene, out=str(HERE / "build" / "apply"), title="JobRadar for Claude Code",
    subtitle="Applies to your shortlist through careers pages, one approved batch at a time",
    url_label="Claude Code + Chrome")  # fmt: skip
