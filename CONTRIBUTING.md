# Contributing

Thanks for helping. Small, focused pull requests are easiest to review.

## Setup

```bash
uv sync                                   # Python (lite mode + dev tools)
uv run pytest && uv run ruff check . && uv run ruff format --check .
(cd orchestrator && go test -race ./...)  # only if you touch Go
```

## Good first contributions

- **A new job board**: a parser in `jobradar/sources/` (feeds) or `jobradar/ats/` (ATS boards)
  with a recorded fixture in `tests/fixtures/` and a test in `tests/test_parsers.py`.
  Platform mode has a Go twin in `orchestrator/internal/ingest/`; parity is tested.
- **ATS form notes**: what you learned filling a real form, in
  `plugin/skills/apply/references/ats-forms.md`.
- **Companies**: careers boards worth watching, in `companies.yaml`.
- **Eval labels**: more labeled postings in `evals/data/` make the prefilter gate stronger.

## Rules

- Never commit personal data: `profile.yaml`, CVs, `.env` and `data/` are gitignored; keep it
  that way. Test fixtures must be public postings or synthetic people.
- The agent must not invent facts about the candidate, apply twice, or send anything the user
  has not approved. Changes that weaken those guarantees will not be merged.
- No automation of LinkedIn or other sites whose terms forbid it.
- Conventional commit messages (`feat:`, `fix:`, `docs:` ...).
