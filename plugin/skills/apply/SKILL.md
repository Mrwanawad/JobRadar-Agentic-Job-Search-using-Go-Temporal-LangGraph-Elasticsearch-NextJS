---
name: apply
description: Apply to jobs for the user through company careers pages and ATS forms (Workable, Greenhouse, Lever, Ashby, SmartRecruiters, JazzHR, BambooHR, Teamtailor, Google Forms) with Claude in Chrome, using their JobRadar profile, CV and drafted cover letters, then record each application. Use when the user says "apply", "run an apply cycle", "apply to my shortlist", or gives a job URL to apply to.
---

# Apply cycle

You apply to jobs on the user's behalf, one at a time, from the JobRadar repo folder (the one
with `profile.yaml`). Every fact you type comes from `profile.yaml` or the CV text. You never
invent experience, numbers, titles, employers or answers.

## 0. Preflight (once per cycle)

1. `uv run jobradar doctor`. If anything says FAIL, stop and show it.
2. Read `profile.yaml`: `candidate` (name, email, phone, base, links, `cv` path) and
   `answers` (standing answers for forms). Read the CV text: the `.txt` file next to the CV PDF
   (created by `doctor`).
3. Load the Claude in Chrome tools (one ToolSearch call: tabs_context_mcp, tabs_create_mcp,
   tabs_close_mcp, navigate, read_page, find, form_input, computer, file_upload,
   get_page_text, javascript_tool). Call `tabs_context_mcp` first, then work in new tabs.

## 1. Pick the jobs

- If the user gave URLs, use those.
- Otherwise: `uv run jobradar outbox --status draft --channel manual --full`. Each item is a
  shortlisted job with a drafted cover letter and the apply URL as `to:`. Best scores first.
- Default batch: 5 jobs, unless the user asked for a number.

## 2. For each job

1. **Not applied before:** `uv run jobradar check "<Company>"`. If the same or a very similar
   role was already sent, skip it (`uv run jobradar mark <id> skipped --ref "already applied"`).
2. **Read the posting.** Skip (mark skipped with a short reason) when a hard requirement
   clearly rules the user out: required years far above the CV, location or work permit they
   do not have, a language they do not speak, a degree they do not hold.
3. **Open the form** in a new tab. See `references/ats-forms.md` for each ATS's quirks.
4. **Fill it**:
   - Identity and links from `candidate`; upload the CV PDF from `candidate.cv` with
     `file_upload`.
   - Cover letter / "why us" fields: the drafted body from the outbox item (or write one in the
     same style from the CV and the posting: 120-200 words, no claims beyond the CV).
   - Screening questions: use `answers`. Knockout questions ("5+ years?", "authorised to work
     in X?") get the truthful answer even if it loses the application.
   - A required question with no answer in `profile.yaml` or the CV: ask the user, then
     suggest they add it under `answers` so it is never asked again.
5. **Submit**: show the user a short summary (job, form, any answer you were unsure of) and
   wait for their yes, unless they told you in this session to submit without asking.
6. **Confirm** the success page or "thank you" text. Then record it:
   - outbox item: `uv run jobradar mark <id> sent --ref "<ATS>; <confirmation>" --found-on "<where found>"`
   - job from a URL: `uv run jobradar log "<Company>" "<Title>" --url "<url>" --ref "<ATS>" --found-on "<where found>"`
7. Close every tab you opened for that job.

## 3. Hand back to the user, never work around

Stop on that job, leave its tab open, and tell the user when you hit: a CAPTCHA, a login or
"create account" wall, a payment or ID-document request, a required essay that says "do not
use AI", or anything that asks for a password. Move on to the next job.

## 4. End of cycle

Close the remaining tabs you opened. Report one line per job:
`Company - Title -> submitted | skipped (reason) | needs you (reason, tab left open)`.

Rules that never bend: no fabricated facts, no applying twice to the same role, no sending
anything (email, message) that the user has not approved, never type passwords or payment
details.
