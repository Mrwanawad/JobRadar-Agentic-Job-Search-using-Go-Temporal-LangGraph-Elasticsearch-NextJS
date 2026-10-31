# 0001. Temporal for orchestration

Status: accepted, 2026-10-25

## Context

The v0.1 pipeline was one Python process run by Windows Task Scheduler. A crash mid-run lost
progress, retries were ad hoc, and there was no way to pause a run for a human decision or to
show live progress to a web visitor. The platform needs: dozens of parallel fetches with
per-source retries, LLM calls that can take minutes and hit rate limits, a human approval step
that can last two days, cron-style schedules, and progress visible while a run is open.

## Decision

Model each run as a Temporal workflow (`RadarWorkflow`). Side effects are activities with
explicit timeouts, retry policies and heartbeats. Approvals are signals with a timer; progress
is a query; daily runs and the purge are Temporal Schedules.

## Consequences

- Crash recovery, retries, timers and schedules come from the engine; the workflow code reads
  as the business process.
- Workflow code must stay deterministic; all I/O lives in activities.
- One more stateful service to run (Temporal plus its database).
- Considered: Celery/RQ (no durable timers or signals, retries per task only), Airflow/Prefect
  (batch DAGs, a poor fit for a 48 h human wait and per-visitor runs), a hand-rolled state
  machine in Postgres (all of the above to build and test by hand).
