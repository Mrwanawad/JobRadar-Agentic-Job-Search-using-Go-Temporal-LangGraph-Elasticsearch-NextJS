# Getting started: JobRadar as your own job applier agent

JobRadar runs on your laptop. It finds jobs that fit your CV, explains each fit, drafts cover
letters and emails, and then Claude Code applies through careers-page forms with you watching.
Nothing goes out until you approve it.

Lite mode is all you need: Python, SQLite and a free LLM key. No Docker, no servers. The Docker
platform (Temporal, Elasticsearch, Go workers) is for running it as a multi-user service; see
the main [README](../README.md).

Cost: free. Gemini's free tier covers about 60 scored jobs a day; Claude Code needs a Claude plan.

## 1. Install (5 minutes)

You need `git` and [uv](https://docs.astral.sh/uv/getting-started/installation/)
(it installs the right Python for you).

```bash
git clone https://github.com/Mrwanawad/JobRadar-Agentic-Job-Search-using-Go-Temporal-LangGraph-Elasticsearch-NextJS.git jobradar
cd jobradar
uv sync
```

## 2. Set up your profile

Get a free LLM key first: Gemini at <https://aistudio.google.com/apikey> (or OpenRouter, Groq).
Have your CV as a **text PDF** (exported from Word/Docs, not scanned).

```bash
uv run jobradar init --cv ~/Documents/my-cv.pdf
uv run jobradar doctor
```

`init` reads your CV, suggests titles and skills, asks a few questions and writes
`profile.yaml` and `.env`. Both stay on your machine: they are gitignored.

Open `profile.yaml` once and fill in `answers`: notice period, salary, relocation, work
authorisation. Those are what the agent types into application forms. Anything left blank,
it asks you.

## 3. Find and rank jobs

```bash
uv run jobradar run          # fetch ~60 boards, filter, LLM-score, draft applications
uv run jobradar top          # the shortlist, best first, with reasons and red flags
uv run jobradar dashboard    # the same in your browser
```

Fetching is free. Scoring uses your LLM quota: `scoring.max_llm_per_run` in `profile.yaml`
caps it, and a run that hits the quota stops cleanly and continues next time.

Add companies you care about to `companies.yaml` (Greenhouse, Lever, Ashby, Workable and
SmartRecruiters boards: the slug is in their careers-page URL).

## 4. Apply with Claude Code

Install Claude Code and the Claude in Chrome browser extension, open Claude Code in the repo
folder, and run:

```text
/plugin install jobradar --marketplace Mrwanawad/JobRadar-Agentic-Job-Search-using-Go-Temporal-LangGraph-Elasticsearch-NextJS
```

| Say | What happens |
|---|---|
| `/jobradar:apply` | Takes your top drafted jobs, checks you have not applied already, fills each form in Chrome with your profile, CV and cover letter, shows you a summary, submits on your yes, records it |
| `/jobradar:apply https://...` | Same, for a job you found yourself |
| `/jobradar:send-outreach` | Sends approved application emails (needs a Gmail MCP server) |
| `/jobradar:track` | Records replies and interviews; "where do my applications stand?" |

The agent stops and hands the tab to you on CAPTCHAs, logins, account creation and
"do not use AI" essays. It never types passwords. The plugin's guard hook checks every
upload, page, script and typed value before Chrome acts: a blocked call stops that job with
the reason, an unusual site or a private answer (salary, ID) asks you first.
`uv run jobradar guard audit` lists what it blocked.

## 5. Sending emails (optional)

Some postings list a recruiter email instead of a form. Those become email drafts.

1. Review them: `uv run jobradar outbox --full`. Items the guard held show `review` and the
   reason (WhatsApp always, since it sends your CV; addresses not on the company's domain;
   scam phrases). Approve one with `uv run jobradar approve <id>`; nothing else approves them.
2. In `profile.yaml`: set `candidate.cv_link` (a public link to your CV), and move
   `outreach.dry_run_until` to a past date when you are happy with the drafts.
3. `/jobradar:send-outreach` sends at most `outreach.daily_cap` a day, one per recipient.

## 6. Run it every day (optional)

- Windows: `powershell -File scripts/install_schedule.ps1` (Task Scheduler).
- macOS / Linux: `crontab -e` and add `0 9 * * * /path/to/jobradar/scripts/daily.sh`.

## Log what you apply to yourself

So the counts are right and the agent never applies twice:

```bash
uv run jobradar log "Acme" "ML Engineer" --url https://... --ref "Applied on LinkedIn"
uv run jobradar check "Acme"
uv run jobradar process "Acme" "ML Engineer" --stage "HR call booked" --found-by you --method "LinkedIn Easy Apply"
```

## Good to know

- **Be honest in forms.** The agent answers knockout questions truthfully and never claims
  skills that are not in your CV. A wrong "yes" wastes everyone's time.
- **Volume.** Five good applications a day beat fifty sprayed ones. Careers-page forms and
  emails to a named recruiter get far more replies than one-click applies.
- **LinkedIn** is not automated: LinkedIn's terms forbid it and accounts get restricted.
  Apply there yourself and `jobradar log` it.
- **Privacy.** Your CV text goes to the LLM provider you pick; read its data terms (free tiers
  often allow training on prompts). Your profile, CV file and database stay on your machine.

## Troubleshooting

| Problem | Fix |
|---|---|
| `doctor`: CV has almost no text | Export the CV again as a PDF from Word/Google Docs |
| `stopped early, LLM quota exhausted` | Free daily quota used up; it resumes tomorrow. Add a second provider key in `.env` |
| Shortlist is empty | Too strict: widen `roles.include`, `locations` in `profile.yaml`, then `jobradar refilter` |
| Shortlist is full of wrong roles | Add words to `roles.exclude`, then `jobradar refilter` |
