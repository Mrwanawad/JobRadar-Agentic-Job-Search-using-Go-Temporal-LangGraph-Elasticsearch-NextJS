# Changelog

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- `docs/THREAT_MODEL.md`: the agent's assets, trust boundaries, attacks A1-A10 and their
  OWASP LLM 2025 / OWASP Agentic 2026 / MITRE ATLAS mapping.
- Layer 3 security eval (`evals/security.py`): 510 prompt-injection cases planted in the 52
  labeled postings (English, Modern Standard Arabic, Egyptian Arabic, Franco-Arabic; 9
  concealments; 3 placements), each with its own canary, run through the real ingest,
  screening, recipient and drafting code. A scripted worst-case model makes it deterministic
  and free for CI; `--llm live` uses the provider chain. Row 0 (no defences) is in
  `docs/EVALS.md`.
- Recipient policy (`jobradar/guard/recipients.py`): email goes out automatically only to the
  company's own domain; free-mail, mismatched domains, scam phrases and every WhatsApp
  message (it carries the CV PDF) are held as `review`; reserved domains are blocked.
  Checked when drafting and again in `sendable()`. New `jobradar approve <id>`; outbox
  statuses `review` and `approved`. A3 attack success 0.40 -> 0.00.
- Output policy (`jobradar/guard/output.py`) on every draft, lite and platform: only the
  candidate's own links and contacts, no private form answers, numbers must come from the CV
  or posting, no copied posting text, plain text, sane length; one revision, then rejected.
  A2 attack success 0.75 -> 0.00, no false positives on clean postings.

- Applier guard hook (`plugin/hooks/hooks.json`, `jobradar/guard/hook.py`): a PreToolUse
  hook on Claude in Chrome that allows only the CV as an upload, blocks `file:`/`javascript:`
  and local or private URLs, asks before unknown sites, blocks page JavaScript with network,
  cookie, storage or navigation access, and blocks secrets typed into forms (private answers
  ask first). Fails closed; decisions logged to `data/guard_audit.jsonl`
  (`jobradar guard audit`). Red-team careers pages in `evals/attacks/pages/`.

### Changed
- WhatsApp drafts (and email drafts to a flagged address) are no longer sendable until you
  approve each one with `jobradar approve <id>`.

### Fixed
- Dashboard: requests with a non-local `Host` header get 403 (DNS rebinding could read
  `/api/snapshot` from any website); job links render only for http(s) URLs.
- CI: the buf action no longer tries to comment on pull requests with a read-only token.

## [0.2.0] - 2026-11-20

### Added
- Open for anyone to run as their own job applier agent:
  - `jobradar init`: profile.yaml and .env from a CV and a few questions (titles, skills and
    seniority suggested by the LLM from the CV); dry run for the first week, 5 sends a day.
  - `jobradar doctor`: checks profile, CV text, LLM keys (`--ping` for a live call), sending
    state and blank form answers.
  - `jobradar log` / `jobradar check`: record applications made outside the pipeline and
    look up earlier applications to a company before applying again.
  - Claude Code plugin (`plugin/`, marketplace in `.claude-plugin/`): `apply` (careers-page
    forms through Claude in Chrome, with per-ATS notes), `send-outreach`, `track`.
  - `answers` section in profile.yaml for standing form answers; `docs/GETTING_STARTED.md`,
    `CONTRIBUTING.md`, `scripts/daily.sh` (cron) for macOS/Linux.
  - `JOBRADAR_HOME`: keep profile, CV, database, logs and `.env` outside the repo.
  - README demo GIFs for every stage (setup, find, batch apply, schedule, track), recorded
    from a synthetic demo home (`docs/demo/`), plus issue and pull request templates.
- Evals: 52 hand-labeled real postings for a synthetic persona; prefilter precision/recall
  gate in CI (`tests/test_evals.py`); LLM screening eval (`evals/screening.py`) with band,
  within-one-band and AUC gates, run by the on-demand/weekly `evals` workflow.
- MCP server (`jobradar-mcp`, stdio): `start_run`, `get_run`, `get_summary`, `search_jobs`,
  `get_outbox`, `approve_draft`, as a thin client over the gateway API.
- `apps/web`: Next.js 16 demo site on Cloudflare Workers (OpenNext). GitHub and Google
  sign-in, Turnstile, one demo run per account (D1), CV text extracted in the browser with
  pdf.js, live run progress over Server-Sent Events, ranked results with drafts.
- Cloudflare Tunnel config for the gateway (`deploy/cloudflare/tunnel.yml`).
- CI `web` job: lint, typecheck and a full Cloudflare Worker build.
- Docs: README v2, architecture, workflows, runbook, security, decision records.

### Changed
- The screening prompt's default candidate constraints are generic instead of the author's
  (Egypt/Gulf); set your own in `candidate.constraints`.

### Fixed
- Drafting produced no drafts: the writer restated the job's requirements as facts about the
  candidate ("I use AI coding tools daily"), and each revision swapped in a new unsupported
  claim, so the critic rejected every version. The writer is now told the job's asks are not
  facts, and revisions delete flagged claims instead of rewording them. Traced live: the loop
  now converges to a draft with no unsupported claims.
- Demo data purge: the Go worker now creates the hourly purge schedule on startup; before,
  it existed only after `jobradar schedule` was run, so demo CVs were not deleted.
- LLM calls: a provider read timeout moves to the next provider instead of three more
  attempts on the same one (a slow free model turned one scoring call into 6-9 minutes);
  read timeout raised to 240 s for slow reasoning models.
- A failed workflow start no longer burns a visitor's demo: the profile is kept and the next
  submit retries the start. The gateway marks failed starts, so runs no longer show as
  running forever.
- Run errors show the activity's own error (`DraftRejected: ...`) instead of the innermost
  library exception (`ValueError`).
- Fetch cache hits report the cached job count instead of 0.
- Agent image: embedding model download moved above the source copy, so code changes no
  longer re-download 130 MB.
- `npm run preview` serves with the matching `APP_URL`.

### Changed
- Localhost-only test sign-in for the web app (`DEV_LOGIN=1`).
- Demo title matching: all words of a target title in any order, engineer/developer and
  ML/machine learning equivalent. Prefilter recall on the eval set 0.52 -> 0.95, precision 1.00.
- Repository renamed to `JobRadar-Agentic-Job-Search-using-Go-Temporal-LangGraph-Elasticsearch-NextJS`.
- Web dev server runs on port 3001 (Grafana uses 3000).

## Platform backend - 2026-10-26

### Added
- Go orchestrator: `RadarWorkflow` (fetch, prefilter, index, match, score, draft, approvals),
  `PurgeWorkflow`, Temporal Schedules, 9 job-board parsers with parity tests against Python,
  HTTP gateway with demo quota and SSE progress, Postgres migrations.
- Python agent worker: LangGraph screening (repair loop) and writing (critic/revise loop)
  graphs, Elasticsearch hybrid search with client-side RRF and local fastembed embeddings,
  Temporal activities.
- OpenTelemetry across services to Grafana LGTM, agent spans to Langfuse.
- Docker Compose stack.

### Fixed
- A second start of the same demo run now returns 409 instead of 202.
- Indexing embeds only the profile's candidates (a cold run took ~23 min embedding every job).
- Slow LLM calls heartbeat from a side thread (fixed "activity Heartbeat timeout").

## [0.1.0] - 2026-10-25

### Added
- Single-machine CLI: fetch ~47 company boards and 4 aggregators, rule prefilter, LLM
  scoring, application drafting, capped sending with a dry-run period.
- Free-tier LLM client with multi-key, multi-provider fallback.
- Gitleaks scan of the full history in CI.
