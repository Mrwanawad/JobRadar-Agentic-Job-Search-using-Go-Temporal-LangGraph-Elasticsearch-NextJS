"""Input sanitisation (A1, A2, A5): what a model reads of a posting is what a person sees.

Postings come from strangers. Before this layer, text hidden with CSS, HTML comments,
zero-width or Unicode tag characters, direction overrides and base64 all reached the
screening and writing prompts (docs/EVALS.md, Layer 3, row 0). Two steps:

1. `strip_hidden_html` runs inside `html_to_text`, the only place markup is still there.
   Comments and elements hidden by attribute or inline style are cut out and replaced by an
   invisible marker (U+E000 kind U+E001), so the fact that something was hidden survives as
   a signal. The Go ingest worker has a line-for-line port (orchestrator/internal/ingest,
   `StripHidden`) tested on the same cases (tests/fixtures/golden/hidden_html.json), so
   lite and platform mode store the same text.
2. `clean_text` runs where text enters a prompt: it turns markers into findings and removes
   invisible and direction-override characters, decodes Unicode tag text only to report it,
   normalises with NFKC and replaces base64 blobs that decode to text. It never raises.

A tag scanner with regular expressions, not a DOM parser: it only has to find hidden
elements, it must behave the same in Python and Go, and it has no dependencies.
"""

from __future__ import annotations

import base64
import binascii
import re
import unicodedata
from dataclasses import dataclass, field

from jobradar.guard import enabled

MARK_OPEN, MARK_CLOSE = "\ue000", "\ue001"
_MARK = re.compile("\ue000([a-z-]+)\ue001")

_COMMENT = re.compile(r"<!--[\s\S]*?-->")
_TAG = re.compile(r"<(/?)([a-zA-Z][a-zA-Z0-9]*)\b([^>]*)>")
_VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source",
         "track", "wbr"}  # fmt: skip
# (kind, pattern on the lowercased attributes of a start tag)
_HIDDEN = [
    ("display-none", re.compile(r"display\s*:\s*none")),
    ("invisible", re.compile(r"visibility\s*:\s*hidden|opacity\s*:\s*0(?:\.0+)?(?:[;\s\"']|$)")),
    ("tiny-font", re.compile(r"font-size\s*:\s*(?:0|1px|0?\.\d+[a-z%]*)(?:[;\s\"']|$)")),
    ("white-text", re.compile(
        r"(?:^|[;\s\"'])color\s*:\s*(?:#fff\b|#ffffff\b|white\b|rgb\(\s*255\s*,\s*255\s*,\s*255\s*\))"
    )),
    ("offscreen", re.compile(r"(?:left|top|text-indent)\s*:\s*-\d{3,}")),
    ("aria-hidden", re.compile(r"aria-hidden\s*=\s*[\"']?true")),
    ("hidden-attr", re.compile(r"(?:^|\s)hidden(?:\s|=|$)")),
]  # fmt: skip

_INVISIBLE = re.compile("[\u00ad\u180e\u200b-\u200d\u2060-\u2064\ufeff]")
_BIDI = re.compile("[\u202a-\u202e\u2066-\u2069]")
_TAGS = re.compile("[\U000e0000-\U000e007f]+")
_B64 = re.compile(r"(?<![A-Za-z0-9+/])[A-Za-z0-9+/]{40,}={0,2}(?![A-Za-z0-9+/=])")


def mark(kind: str) -> str:
    return f"{MARK_OPEN}{kind}{MARK_CLOSE}"


def _has_text(fragment: str) -> bool:
    return bool(_TAG.sub("", fragment).strip())


def hidden_kind(attrs: str) -> str:
    a = attrs.lower()
    return next((kind for kind, rx in _HIDDEN if rx.search(a)), "")


def strip_hidden_html(s: str) -> str:
    """Cut comments and hidden elements out of HTML, leaving a marker where text was."""
    if not enabled("sanitize") or "<" not in s:
        return s
    s = _COMMENT.sub(lambda m: mark("comment") if m.group().strip("<!-> \n\t") else "", s)
    out, pos = [], 0
    while True:
        m = _TAG.search(s, pos)
        if m is None:
            out.append(s[pos:])
            return "".join(out)
        closing, name, attrs = m.group(1), m.group(2).lower(), m.group(3)
        kind = "" if closing else hidden_kind(attrs)
        if not kind:
            out.append(s[pos : m.end()])
            pos = m.end()
            continue
        out.append(s[pos : m.start()])
        if name in _VOID or attrs.rstrip().endswith("/"):
            pos = m.end()
            continue
        end = _matching_end(s, name, m.end())
        if _has_text(s[m.end() : end]):
            out.append(mark(kind))
        pos = end


def _matching_end(s: str, name: str, start: int) -> int:
    """Index just past the end tag closing the element opened before `start` (or len(s))."""
    depth = 1
    for t in _TAG.finditer(s, start):
        if t.group(2).lower() != name:
            continue
        if t.group(1):
            depth -= 1
            if depth == 0:
                return t.end()
        elif not t.group(3).rstrip().endswith("/"):
            depth += 1
    return len(s)


@dataclass
class Sanitized:
    text: str
    findings: list[str] = field(default_factory=list)


def _decode_b64(blob: str) -> str | None:
    try:
        text = base64.b64decode(blob, validate=True).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError, ValueError):
        return None
    printable = sum(c.isprintable() or c.isspace() for c in text)
    return text if text and printable / len(text) > 0.9 else None


def clean_text(text: str | None) -> Sanitized:
    """Text as a person would read it, plus what was hidden in it."""
    text = text or ""
    if not enabled("sanitize"):
        return Sanitized(text)
    findings: list[str] = []
    kinds = _MARK.findall(text)
    if kinds:
        findings.append("hidden HTML: " + ", ".join(sorted(set(kinds))))
    text = _MARK.sub(" ", text)

    tags = _TAGS.findall(text)
    if tags:
        decoded = "".join(chr(ord(c) - 0xE0000) for c in "".join(tags))
        findings.append(f"invisible Unicode tag text: {decoded[:60]!r}")
        text = _TAGS.sub("", text)
    n = len(_INVISIBLE.findall(text))
    if n >= 3:
        findings.append(f"{n} zero-width characters")
    text = _INVISIBLE.sub("", text)
    if _BIDI.search(text):
        findings.append("direction-override characters")
        text = _BIDI.sub("", text)
    text = unicodedata.normalize("NFKC", text)

    def b64(m: re.Match[str]) -> str:
        decoded = _decode_b64(m.group())
        if decoded is None:
            return m.group()
        findings.append(f"base64 text: {decoded[:60]!r}")
        return "[encoded text removed]"

    text = _B64.sub(b64, text)
    return Sanitized(text, findings)
