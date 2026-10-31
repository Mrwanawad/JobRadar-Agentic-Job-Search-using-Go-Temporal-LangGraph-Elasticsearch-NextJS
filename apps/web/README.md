# apps/web

Public demo site for JobRadar. Next.js 16 on Cloudflare Workers (OpenNext adapter).

```
browser ──► Worker (this app) ──Cloudflare Tunnel──► gateway (Go) ──► Temporal / Postgres
              │  GitHub + Google OAuth (arctic), signed session cookie (jose)
              │  Turnstile bot check, D1: one demo run per account
              └  pdf.js reads the CV in the browser; only text is sent
```

The gateway bearer token lives only in the Worker. Browsers never talk to the gateway.

## Routes

| Route | What it does |
|---|---|
| `/` | Landing page |
| `/demo` | Sign in, fill the profile form, upload CV, start a run |
| `/run` | Live progress (SSE) and ranked jobs with drafts |
| `GET /api/auth/{github,google}` | Start OAuth |
| `GET /api/auth/{provider}/callback` | Finish OAuth, set session |
| `POST /api/demo` | Turnstile check, create demo profile, start workflow, record in D1 |
| `GET /api/runs/{id}/events` | Relay the gateway's SSE stream (owner only) |
| `GET /api/results` | Ranked jobs for the caller's run |

## Local

Needs the compose stack running (`docker compose -f deploy/compose/compose.yaml up -d`).

```
npm install
cp .dev.vars.example .dev.vars        # set SESSION_SECRET (32+ chars) and OAuth apps
npm run db:migrate:local
npm run dev                           # http://localhost:3001 (3000 is Grafana)
npm run preview                       # real Worker build on http://localhost:8787
```

OAuth callback URLs: `http://localhost:3001/api/auth/github/callback` and
`http://localhost:3001/api/auth/google/callback` (swap the host for production).
The Turnstile keys in the examples are Cloudflare's always-pass test keys.

## Deploy

```
npx wrangler d1 create jobradar-web          # put the id in wrangler.jsonc
npm run db:migrate
npx wrangler secret put SESSION_SECRET       # and GATEWAY_URL, GATEWAY_TOKEN, GITHUB_*, GOOGLE_*,
                                             # TURNSTILE_SECRET_KEY, CF_ACCESS_CLIENT_ID/SECRET
npm run deploy
```

Set `APP_URL` and `TURNSTILE_SITE_KEY` in `wrangler.jsonc` `vars`. Tunnel config: `deploy/cloudflare/tunnel.yml`.
