# Changelog

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- MCP server (`jobradar-mcp`, stdio): `start_run`, `get_run`, `get_summary`, `search_jobs`,
  `get_outbox`, `approve_draft`, as a thin client over the gateway API.
- `apps/web`: Next.js 16 demo site on Cloudflare Workers (OpenNext). GitHub and Google
  sign-in, Turnstile, one demo run per account (D1), CV text extracted in the browser with
  pdf.js, live run progress over Server-Sent Events, ranked results with drafts.
- Cloudflare Tunnel config for the gateway (`deploy/cloudflare/tunnel.yml`).
- CI `web` job: lint, typecheck and a full Cloudflare Worker build.
- Docs: README v2, architecture, workflows, runbook, security, decision records.

### Changed
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
