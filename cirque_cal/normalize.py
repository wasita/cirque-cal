"""Turn raw platform titles/tags into comparable fields: apparatus, kind, level."""
from __future__ import annotations

import re

from .models import Session

APPARATUS = {
    "lyra": r"\blyra\b|aerial hoop|\bhoop\b",
    "silks": r"\bsilks?\b|aerial fabric",
    "hammock": r"\bhammock\b|\bsling\b",
    "straps": r"\bstraps?\b",
    "trapeze": r"\btrapeze\b",
    "pole": r"\bpole\b",
    "bungee": r"\bbungee\b",
    "aerial_yoga": r"aerial yoga|aerial mellow",
}

# "open" = unstructured training time. Deliberately does NOT match "Open Level".
DEFAULT_OPEN = r"\bopen\s+(circus|workout|training|practice|gym)\b|\bopen\s+pole\s*/\s*circus\b"

# Ordered: first match wins. Values are on a common scale (0 = intro/101).
DEFAULT_LEVELS = [
    (r"\b101\b|\bintro\b|fundamentals|absolute beginner", 0),
    (r"\blevel\s*(\d(?:\.\d)?)", None),          # "Level 1", "Level 2/3" -> 2
    (r"\b(?:lyra|hoop|silks|hammock|straps|pole|trapeze)\s+(\d(?:\.\d)?)\b", None),  # "Lyra 2"
]


def _match_any(pattern: str, text: str) -> bool:
    return bool(re.search(pattern, text, re.I))


def detect_apparatus(s: Session) -> list[str]:
    text = " ".join([s.title, *s.tags])
    return [name for name, pat in APPARATUS.items() if _match_any(pat, text)]


def detect_level(title: str, rules) -> float | None:
    for pat, value in rules:
        m = re.search(pat, title, re.I)
        if m:
            if value is not None:
                return float(value)
            return float(m.group(1))
    return None


def enrich(sessions: list[Session], studio_cfg: dict) -> list[Session]:
    open_pat = studio_cfg.get("open_pattern", DEFAULT_OPEN)
    custom = [(r["pattern"], r.get("level")) for r in studio_cfg.get("levels", [])]
    rules = custom + DEFAULT_LEVELS
    for s in sessions:
        s.apparatus = detect_apparatus(s)
        s.kind = "open" if _match_any(open_pat, s.title) else "class"
        s.level = None if s.kind == "open" else detect_level(s.title, rules)
    return sessions
