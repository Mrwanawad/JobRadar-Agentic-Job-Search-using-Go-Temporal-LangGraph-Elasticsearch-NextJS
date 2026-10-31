# 0002. Go for ingestion, Python for agents, protobuf between them

Status: accepted, 2026-10-25

## Context

Ingestion is I/O bound: ~60 sources, many pages each, bounded concurrency. The agent side
needs LangGraph, pydantic validation, fastembed and the prefilter rules already written and
tested in Python for v0.1.

## Decision

Two Temporal workers on two task queues. Go (`jobradar-ingest`) runs the workflows, fetching
and bookkeeping; Python (`jobradar-agent`) runs prefilter, indexing, matching, scoring and
drafting. All inputs and outputs are protobuf messages from one `radar.proto`, generated for
both languages with `buf`. The Go parsers are tested for parity against the Python parsers on
the same recorded fixtures.

## Consequences

- Each side uses the ecosystem it is best at; Temporal routes activities across languages.
- The contract is typed and versioned in one file; `buf lint` runs in CI.
- Parsers exist twice (Go for the platform, Python for the v0.1 CLI); the parity test keeps them
  in step until the CLI is retired.
