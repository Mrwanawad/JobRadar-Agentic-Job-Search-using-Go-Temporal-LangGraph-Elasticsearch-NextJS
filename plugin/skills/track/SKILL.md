---
name: track
description: Record replies, interviews, rejections and offers for the user's job applications in JobRadar, and report where every process stands. Use when the user says "I got an interview", "they replied", "rejected", "update my applications", "where do my applications stand", or pastes a recruiter email.
---

# Track applications

Run from the JobRadar repo folder. Moving applications live in the `processes` table and show
on the dashboard (`uv run jobradar dashboard`).

## Record an update

1. Find the application: `uv run jobradar check "<Company>"` (gives the outbox id).
2. Save it:

   ```bash
   uv run jobradar process "<Company>" "<Title>" \
     --stage "<e.g. HR screen done, Technical 1 on 2026-12-03 14:00>" \
     --found-by pipeline|agent|you --method "<e.g. Workable form, Cold email>" \
     --outbox-id <id> --contacts "<recruiter name, email>" --next-step "<what and when>"
   ```

   `--stage`, `--found-by` and `--method` are required the first time only; later updates need
   just the fields that changed. Rejected, withdrawn or finished: add `--closed`.
3. If the user pasted an email or message, take the stage, date/time, people and next step from
   it. Do not reply to the recruiter unless the user asks; if they do, show the exact text
   first.

## Report

Open the dashboard snapshot (`uv run python -c "from jobradar.dashboard import snapshot; import json; print(json.dumps(snapshot(), indent=1, default=str))"`)
and list active processes: company, title, stage, next step. Flag any next step that is
today or overdue.
