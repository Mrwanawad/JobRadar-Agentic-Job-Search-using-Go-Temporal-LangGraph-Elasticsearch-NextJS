"""CI gate on the labeled eval set (evals/). Thresholds sit at the current baseline, so a
rule change that drops relevant jobs or lets irrelevant ones through fails the build."""

import math

from evals import prefilter
from evals.common import band, persona, postings
from evals.screening import auc, metrics

PRECISION_GATE = 0.95
RECALL_GATE = 0.90


def test_dataset_is_labeled_and_balanced():
    rows = postings()
    assert len(rows) >= 50
    assert len({r["uid"] for r in rows}) == len(rows)
    keep = sum(r["label"]["keep"] for r in rows)
    assert 15 <= keep <= len(rows) - 15
    assert {r["label"]["band"] for r in rows} == {"low", "mid", "high"}


def test_persona_is_a_valid_demo_profile():
    profile, cv = persona()
    assert len(cv) > 1000
    assert profile.roles.include


def test_prefilter_quality_gate():
    r = prefilter.run()
    report = "\n".join(["misses:", *r.misses, "leaks:", *r.leaks])
    assert r.precision >= PRECISION_GATE, report
    assert r.recall >= RECALL_GATE, report


def test_band_edges():
    assert [band(s) for s in (0, 3.9, 4, 6.9, 7, 10)] == [
        "low",
        "low",
        "mid",
        "mid",
        "high",
        "high",
    ]


def test_screening_metrics():
    rows = [
        {"score": 8.0, "label": "high"},
        {"score": 5.0, "label": "high"},
        {"score": 2.0, "label": "low"},
        {"score": None, "label": "low"},
    ]
    m = metrics(rows)
    assert m["scored"] == 3 and m["errors"] == 1
    assert m["band_accuracy"] == 2 / 3
    assert m["within_one_band"] == 1.0
    assert m["auc_high_vs_low"] == 1.0
    assert auc([1, 2], [2]) == 0.25  # 1 < 2 loses, 2 == 2 ties: (0 + 0.5) / 2
    assert math.isnan(auc([], [1]))
