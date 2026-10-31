# Evals

How we know the matching is any good, and how CI stops it getting worse.

## The labeled set

`evals/data/`:

| File | What |
|---|---|
| `persona.yaml` | A synthetic candidate (Cairo-based senior AI engineer, open to remote and Gulf on-site, needs visa sponsorship): the web demo form plus a CV. Not a real person. |
| `labels.csv` | 52 hand labels: `keep` (should the free prefilter keep it?) and `band` (low < 4 ≤ mid < 7 ≤ high, the score a careful recruiter would give this candidate). |
| `postings.jsonl` | The 52 real postings those labels refer to, pulled from the platform's database by `evals/build_dataset.py`. |

The set is built to be hard in the ways that matter: AI titles in the wrong function (sales,
product, design), right roles in the wrong place (US-only remote, US on-site without
sponsorship), right place but wrong level (interns, new grads), adjacent roles (backend
without AI), and good fits whose titles do not literally say "AI Engineer" (forward deployed,
"AI Harness Engineer", "Research Engineer, Machine Learning").

Labels judge role and location only; posting age is ignored so results do not drift with
time.

## Layer 1: prefilter (every push)

`uv run python -m evals.prefilter` runs the free rule pass for the persona over the set and
reports precision, recall, and every miss and leak. `tests/test_evals.py` gates CI on it:

| Metric | Gate | Current |
|---|---|---|
| Precision (kept postings that should be kept) | ≥ 0.95 | 1.00 |
| Recall (wanted postings that are kept) | ≥ 0.90 | 0.95 |

The first run of this eval found the demo title rule matched target titles only as exact
phrases: recall was **0.52**. Titles now match when all words of a target title appear in
any order, with engineer/developer and ML/machine learning treated as equivalent
(`jobradar/agent/profiles.py::_title_rx`). Recall went to 0.95 with no loss of precision.
The remaining miss ("Senior Deployment Engineer with LLM and GPU Infrastructure") is a title
the persona's target list does not cover.

## Layer 2: LLM screening (on demand, weekly)

`uv run --extra platform python -m evals.screening [--limit N]` runs the real LangGraph
screening agent with the configured LLM chain on each posting and compares scores with the
labels:

| Metric | Gate |
|---|---|
| Band accuracy (score falls in the labeled band) | ≥ 0.60 |
| Within one band | ≥ 0.90 |
| AUC, high-labeled vs low-labeled postings | ≥ 0.85 |

It needs at least 20 scored postings to judge; fewer (quota ran out) exits 2,
"inconclusive". Each run writes `evals/results/screening-<timestamp>.json` with every score.

The `evals` GitHub workflow runs it on demand and every Monday when the repo has an
`GEMINI_API_KEY_1` or `OPENROUTER_API_KEY` secret, and uploads the report as an artifact. It
is not part of push CI because it spends LLM quota and free-tier calls can take minutes
each.

**Status:** no full baseline yet. A first local run scored the first posting correctly
(8.0, labeled high) but the free tier then took over nine minutes per call. A full run needs
either a paid key or the scheduled workflow with repo secrets.

## Changing labels

Edit `labels.csv` (and `persona.yaml` if needed), then rebuild the postings from a running
stack:

```bash
DATABASE_URL=postgres://jobradar:jobradar@localhost:5432/jobradar \
  uv run --extra platform python -m evals.build_dataset
```

Raise a gate only when the measured baseline has moved up; never lower one to make a change
pass.
