# 0003. Hybrid search with client-side Reciprocal Rank Fusion and local embeddings

Status: accepted, 2026-10-25

## Context

Keyword search alone misses postings that describe the same work in other words; vector search
alone over-ranks vaguely similar roles and ignores exact skills. Elasticsearch's built-in RRF
retriever depends on license tier. Embedding a visitor's CV with a hosted API would send
personal data to another party and spend quota.

## Decision

Run two retrievers per profile, BM25 over title/company/location/description and kNN over a
384-d `bge-small-en-v1.5` vector, and fuse them in Python with RRF (k = 60). Embeddings are
computed with fastembed (ONNX, CPU) inside the agent worker.

## Consequences

- Works on any Elasticsearch license; fusion is explicit and unit-tested.
- No embedding API cost or quota; the CV never leaves the platform for embedding.
- Two round trips per match instead of one; negligible at top-k 25-40.
- CPU embedding makes a cold first run slow; only the profile's own candidates are embedded.
