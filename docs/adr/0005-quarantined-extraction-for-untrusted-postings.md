# 0005. Quarantined extraction: privileged models read typed facts, not postings

Status: accepted, behind `scoring.extraction` (off by default), 2026-11-27

## Context

The screening and writing models read the CV and the posting in one prompt, and anyone can
write a posting. Sanitisation removes hidden text and the rules detector quarantines postings
that talk to a model, but the detector is a phrase list: on held-out paraphrases it lowers
score-inflation success only from 0.42 to 0.32 (docs/EVALS.md, Layer 3). A defence that
depends on wording loses to an attacker who rewrites.

CaMeL (Debenedetti et al., 2025) separates a quarantined model, which reads untrusted data
and has no tools, from a privileged model that only receives values the quarantined one
produced, in a form that cannot carry instructions. Spotlighting (Hines et al., 2024) marks
untrusted text inside the prompt instead; it lowers success rates but still hands the text
to the model that decides.

## Decision

- A **quarantined extractor** (no tools, never sees the CV or profile) turns the sanitised
  posting into `JobFacts` (`jobradar/guard/extract.py`): enums for seniority, work
  arrangement, regions, visa and languages; integers for years and salary; capped lists of
  skills; a 300-character company summary; application instructions kept for the record.
  Out-of-schema values are coerced, never trusted.
- The **screening model** reads the CV and a rendering of those facts. No free text from the
  extractor reaches it: skills are shown only when they are in a fixed vocabulary
  (`skills.yaml`) or the profile's own skills.
- The **writer** also gets the company summary for the job hook, after the detector has read
  every string the extractor wrote; drafts still pass the output policy.
- Facts are cached on the job row (SQLite `jobs.facts`, Postgres migration `00002`), shared
  by every profile, so the extra call is paid once per posting.
- It ships **off by default** (`scoring.extraction: false`) until a live run shows screening
  accuracy within the Layer 2 gates. The security eval measures it on.

Not chosen: NeMo Guardrails, Guardrails AI and hosted guard APIs. They add a framework or a
service, they are opaque per layer, a hosted API spends free-tier quota per posting, and
none of them turns the posting into data the deciding model cannot be instructed by.

## Consequences

- With the worst-case model, the screening prompt receives none of the payloads on the
  held-out paraphrases even with the detector switched off (payload reach in the screening
  prompt 0.00), and A1 success is 0.00 whatever the wording.
- Tokens per job go down overall: a short facts block replaces up to 6,000 characters of
  posting in both the screening and the writing prompt, more than paying for the extractor's
  own prompt.
- One more LLM call per new posting, a cost on slow free tiers; the cache keeps it to once.
- Screening quality now depends on what the facts keep. Band accuracy and AUC on the clean
  set are unmeasured until a live run; if they drop, the schema grows (a field, not free
  text).
- An extractor that obeys the posting can still lie inside the schema ("visa: yes", "0 years
  required"). That is bounded by the enums and `clamp()`, and listed as a residual risk.
