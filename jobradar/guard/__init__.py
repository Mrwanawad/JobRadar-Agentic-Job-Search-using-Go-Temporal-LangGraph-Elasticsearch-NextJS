"""Guardrails between untrusted postings and anything that acts (docs/THREAT_MODEL.md).

Deterministic code decides; the LLM only proposes. Each module is one layer of the ablation
table in docs/EVALS.md (Layer 3):

- recipients: who a draft may go to (A3, A7)
- output: what a draft may say (A2, A4)

Every layer is on in production. `disabled()` exists only so the security eval can measure
what each layer adds.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

LAYERS = ("recipients", "output")
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
