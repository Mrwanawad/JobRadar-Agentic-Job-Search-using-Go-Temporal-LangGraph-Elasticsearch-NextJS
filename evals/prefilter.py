"""Prefilter eval: does the free rule pass keep the postings a person would keep?

Deterministic and free, so CI gates on it (tests/test_evals.py). Prints a report:

    uv run python -m evals.prefilter
"""

from __future__ import annotations

from dataclasses import dataclass, field

from evals.common import persona, postings
from jobradar.prefilter import Prefilter


@dataclass
class Report:
    tp: int = 0
    fp: int = 0
    fn: int = 0
    tn: int = 0
    misses: list[str] = field(default_factory=list)  # wanted, but filtered out
    leaks: list[str] = field(default_factory=list)  # unwanted, but kept

    @property
    def precision(self) -> float:
        return self.tp / (self.tp + self.fp) if self.tp + self.fp else 1.0

    @property
    def recall(self) -> float:
        return self.tp / (self.tp + self.fn) if self.tp + self.fn else 1.0


def run() -> Report:
    profile, _ = persona()
    pf = Prefilter(profile)
    rep = Report()
    for j in postings():
        v = pf.check(j["title"], j["location"] or "", j["remote"], j["description"], j["posted_at"])
        want = j["label"]["keep"]
        line = f"{j['title']} | {j['location']} -> {v.reason}"
        if v.keep and want:
            rep.tp += 1
        elif v.keep:
            rep.fp += 1
            rep.leaks.append(line)
        elif want:
            rep.fn += 1
            rep.misses.append(line)
        else:
            rep.tn += 1
    return rep


def main() -> None:
    r = run()
    print(f"prefilter  precision {r.precision:.2f}  recall {r.recall:.2f}")
    print(f"           tp {r.tp}  fp {r.fp}  fn {r.fn}  tn {r.tn}")
    for title, rows in (
        ("missed (wanted, filtered out)", r.misses),
        ("leaked (kept, unwanted)", r.leaks),
    ):
        if rows:
            print(f"\n{title}:")
            for x in rows:
                print("  -", x)


if __name__ == "__main__":
    main()
