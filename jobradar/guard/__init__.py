"""Guardrails between untrusted postings and anything that acts (docs/THREAT_MODEL.md).

Deterministic code decides; the LLM only proposes. Each module is one layer of the ablation
table in docs/EVALS.md (Layer 3):

- sanitize: what a model reads of a posting is what a person sees (A1, A2, A5)
- detect: postings that talk to a model are quarantined (A1, A2, A5)
- extract: privileged models read typed facts, not the posting (A1, A2, A4)
- recipients: who a draft may go to (A3, A7)
- output: what a draft may say (A2, A4)

Every layer is on in production. `disabled()` exists only so the security eval can measure
what each layer adds.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from typing import Any

LAYERS = ("sanitize", "detect", "extract", "recipients", "output")
_off: set[str] = set()


def enabled(layer: str) -> bool:
    return layer not in _off


@contextmanager
def disabled(*layers: str) -> Iterator[None]:
    unknown = set(layers) - set(LAYERS)
    if unknown:
        raise ValueError(f"unknown guard layers: {sorted(unknown)}")
    before = set(_off)
    _off.update(layers)
    try:
        yield
    finally:
        _off.clear()
        _off.update(before)


def flatten(answers: Mapping[str, Any], prefix: str = "") -> dict[str, str]:
    """`{"salary": {"egypt": {"current": "X"}}}` -> `{"salary.egypt.current": "X"}`.
    Standing answers are often nested, and every value must be checked, not the dict."""
    out: dict[str, str] = {}
    for k, v in answers.items():
        key = f"{prefix}{k}"
        if isinstance(v, Mapping):
            out |= flatten(v, key + ".")
        elif isinstance(v, list):
            out |= {f"{key}.{i}": str(x) for i, x in enumerate(v)}
        elif v is not None:
            out[key] = str(v)
    return out
