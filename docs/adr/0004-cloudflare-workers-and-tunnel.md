# 0004. Web on Cloudflare Workers, backend on Oracle free tier behind a Tunnel

Status: accepted, 2026-10-31

## Context

The demo must be public, cost nothing at rest, survive bot traffic, and keep the backend
(Temporal, Postgres, Elasticsearch, ~6 GB RAM) off the open internet. Sign-in should accept
both GitHub and Google accounts.

## Decision

- Next.js 16 on Cloudflare Workers via the OpenNext adapter; D1 for the per-account demo quota;
  Turnstile for bot checks; GitHub and Google OAuth with `arctic`, session as a signed cookie
  (`jose`).
- Backend on an Oracle Cloud free-tier ARM VM, reached only through a Cloudflare Tunnel to the
  gateway, protected by an Access service token plus the gateway bearer token.
- `arctic` + `jose` instead of Auth.js: two providers, no user database, and fewer moving parts
  on the Workers runtime while Auth.js v5 is still in beta.

## Consequences

- No inbound ports open on the VM; TLS and DDoS handling at Cloudflare.
- Next.js Cache Components stay disabled: they hang on the Workers runtime with OpenNext 1.20.
- The Worker relays Server-Sent Events from the gateway; long-lived streams count against
  Worker duration, acceptable for a capped demo.
