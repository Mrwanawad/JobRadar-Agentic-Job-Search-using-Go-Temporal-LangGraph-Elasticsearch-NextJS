# Runbook

Operating the stack locally (Docker Compose). Production deployment is not done yet; this
page will grow a k3s section when it is.

## Start, stop, reset

```bash
docker compose -f deploy/compose/compose.yaml up -d --build   # start (first boot ~2 min)
docker compose -f deploy/compose/compose.yaml ps              # health
docker compose -f deploy/compose/compose.yaml stop            # free RAM, keep data
docker compose -f deploy/compose/compose.yaml down -v         # DELETES Postgres, Temporal and ES data
```

On first boot `agent-worker` and `orchestrator-worker` may restart a few times with
`dns error` / `no such host` while Temporal and Postgres come up. They recover on their own
(`restart: unless-stopped`).

## Where to look

| Question | Where |
|---|---|
| Is a run progressing? | `curl -H "Authorization: Bearer $GATEWAY_TOKEN" localhost:8080/v1/runs/<workflow-id>` |
| What is a run waiting on? | Temporal UI http://localhost:8233, namespace `jobradar`, the workflow's *Pending Activities* |
| Why did an activity fail? | Same page, activity *Last Failure*; or `docker compose logs agent-worker` / `orchestrator-worker` |
| Full trace of one request | Grafana http://localhost:3000, Explore, Tempo, service `gateway` or `agent-worker` |
| LLM prompts and outputs | Langfuse, when `LANGFUSE_AUTH` is set |

CLI equivalent of the Temporal UI:

```bash
docker compose -f deploy/compose/compose.yaml exec temporal \
  sh -c 'temporal workflow describe -n jobradar -w <workflow-id> --address $(hostname -i):7233'
```

## Common problems

**Scoring is slow or stops with "LLM free quota exhausted; scoring stopped early".**
Free tiers are small (Gemini keys share a per-project daily cap; OpenRouter `:free` allows
50 requests a day and takes 30-50 s per call). The run still completes with whatever was
scored. Add keys (`GEMINI_API_KEY_2`, another provider in `LLM_PROVIDERS`) to `.env` and
`docker compose up -d agent-worker`. Check keys with `uv run python scripts/llm_smoke.py`.

**Every LLM call fails at once with 429.** Gemini free keys share a per-project daily cap;
when both are spent, calls fall through to OpenRouter's free model (50 requests a day,
15-70 s per call). A provider that times out (240 s read timeout) is skipped for that call
rather than retried three times.

**A visitor's run did not start** ("Your profile is saved; submit again to retry"). The
gateway created the profile but could not reach Temporal. The web app keeps the profile; the
next submit starts the run on it.

**`activity Heartbeat timeout` on ScoreJob or DraftApplication.**
The agent worker heartbeats from a side thread during LLM calls. If this appears, the worker
process is stuck or dead: check `docker compose logs agent-worker` and restart it. Temporal
retries the activity.

**A source keeps failing (`context deadline exceeded`).**
One board is slow or down. The run records it in `progress.errors` and continues. Check the
endpoint against [ENDPOINTS.md](ENDPOINTS.md); remove or fix it in `companies.yaml`.

**Second demo start returns 409.** Expected: one run per demo profile, and one demo profile per
owner (`demo_quota`). For local testing use a new `owner` value.

**Drafts: 0 even though jobs scored high.** Either no score reached `MinDraftScore`, or the
critic rejected every revision (`DraftRejected` in the activity failure). A short or
synthetic CV gives the critic nothing to verify claims against; test with a full CV.

**Cold first run is slow (minutes in Indexing).** Only the profile's own candidates are
embedded, on CPU. Later runs reuse the index.

**Docker runs out of disk.** Elasticsearch stops writing below its disk watermark. Free space
or move Docker's disk image to a larger drive (Docker Desktop, Settings, Resources).

## Schedules

```bash
docker compose -f deploy/compose/compose.yaml run --rm orchestrator-worker schedule <personal-profile-id>
```

Creates the daily radar (09:00) and hourly purge schedules; see [WORKFLOWS.md](WORKFLOWS.md#schedules).
The purge schedule is also created automatically when the Go worker starts.

## Web app

Local: [apps/web/README.md](../apps/web/README.md). The worker's own logs:
`npx wrangler tail` in production, the terminal running `wrangler dev` locally.
