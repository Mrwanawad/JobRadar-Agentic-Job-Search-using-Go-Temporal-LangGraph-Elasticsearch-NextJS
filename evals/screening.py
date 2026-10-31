"""Screening eval: do the LLM screening agent's scores agree with the hand labels?

Runs the real LangGraph screening graph with the LLM chain from .env, so it spends quota and
is not part of the push CI. The `evals` GitHub workflow runs it on demand and weekly when an
LLM key secret is set.

    uv run --extra platform python -m evals.screening [--limit N]

Exits 1 when a gate fails, 2 when too few postings were scored to judge (quota ran out).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from evals.common import BANDS, band, persona, postings
from jobradar.agent import graphs
from jobradar.llm import LLMClient, LLMError

GATES = {"band_accuracy": 0.6, "within_one_band": 0.9, "auc_high_vs_low": 0.85}
MIN_SCORED = 20
RESULTS = Path(__file__).parent / "results"


def auc(pos: list[float], neg: list[float]) -> float:
    """Probability a random `pos` item outscores a random `neg` item (ties count half)."""
    if not pos or not neg:
        return float("nan")
    wins = sum((p > n) + 0.5 * (p == n) for p in pos for n in neg)
    return wins / (len(pos) * len(neg))


def metrics(rows: list[dict[str, Any]]) -> dict[str, float]:
    scored = [r for r in rows if r["score"] is not None]
    if not scored:
        return {"scored": 0}
    idx = {b: i for i, b in enumerate(BANDS)}
    exact = sum(band(r["score"]) == r["label"] for r in scored)
    near = sum(abs(idx[band(r["score"])] - idx[r["label"]]) <= 1 for r in scored)
    return {
        "scored": len(scored),
        "errors": len(rows) - len(scored),
        "band_accuracy": exact / len(scored),
        "within_one_band": near / len(scored),
        "auc_high_vs_low": auc(
            [r["score"] for r in scored if r["label"] == "high"],
            [r["score"] for r in scored if r["label"] == "low"],
        ),
    }


def run(limit: int | None) -> list[dict[str, Any]]:
    profile, cv = persona()
    llm = LLMClient()
    rows = []
    for j in postings()[:limit]:
        job = {**j, "salary": None}
        row: dict[str, Any] = {"uid": j["uid"], "title": j["title"], "label": j["label"]["band"]}
        t0 = time.monotonic()
        try:
            score, assessment, by = graphs.screen(llm, profile, cv, job)
            row |= {"score": score, "by": by, "location_fit": assessment.get("location_fit")}
        except LLMError as e:
            row |= {"score": None, "error": str(e)[:200]}
            rows.append(row)
            print(f"stopping: {e}", file=sys.stderr)
            break
        except Exception as e:  # noqa: BLE001 - one bad reply must not end the eval
            row |= {"score": None, "error": f"{type(e).__name__}: {e}"[:200]}
        row["seconds"] = round(time.monotonic() - t0, 1)
        rows.append(row)
        print(f"{row.get('score')!s:>5} [{row['label']:>4}] {j['title'][:70]}", file=sys.stderr)
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    rows = run(args.limit)
    m = metrics(rows)
    RESULTS.mkdir(exist_ok=True)
    out = RESULTS / f"screening-{datetime.now(UTC):%Y%m%d-%H%M}.json"
    out.write_text(json.dumps({"metrics": m, "gates": GATES, "rows": rows}, indent=1) + "\n")

    print(json.dumps(m, indent=1))
    print(f"report: {out}")
    if m["scored"] < MIN_SCORED:
        print(f"inconclusive: only {m['scored']} scored (need {MIN_SCORED})")
        return 2
    failed = [k for k, v in GATES.items() if not m[k] >= v]
    for k in failed:
        print(f"GATE FAILED: {k} {m[k]:.2f} < {GATES[k]}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
