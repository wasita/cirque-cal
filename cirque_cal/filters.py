"""Feed rules.  A feed includes a session if ANY rule matches; a rule matches
if ALL of its conditions match.  See config/feeds.yaml."""
from __future__ import annotations

import re
from zoneinfo import ZoneInfo

from .models import Session

ET = ZoneInfo("America/New_York")
DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def _norm(name: str) -> str:
    return re.sub(r"\s+", " ", name).strip().lower()


def rule_matches(s: Session, rule: dict) -> bool:
    if "studios" in rule and s.studio not in rule["studios"]:
        return False
    if "kind" in rule and s.kind != rule["kind"]:
        return False
    if "instructors" in rule:
        wanted = {_norm(n) for n in rule["instructors"]}
        if not wanted & {_norm(n) for n in s.instructors}:
            return False
    if "apparatus" in rule and not set(rule["apparatus"]) & set(s.apparatus):
        return False
    if "level_min" in rule and (s.level is None or s.level < rule["level_min"]):
        return False
    if "level_max" in rule and (s.level is None or s.level > rule["level_max"]):
        return False
    if "title" in rule and not re.search(rule["title"], s.title, re.I):
        return False
    if "days" in rule and DAYS[s.start.astimezone(ET).weekday()] not in rule["days"]:
        return False
    return True


def select(sessions: list[Session], feed: dict) -> list[Session]:
    rules = feed.get("include") or []
    excludes = feed.get("exclude") or []
    keep_cancelled = feed.get("include_cancelled", False)
    out = []
    for s in sessions:
        if s.cancelled and not keep_cancelled:
            continue
        if any(rule_matches(s, r) for r in excludes):
            continue
        if any(rule_matches(s, r) for r in rules):
            out.append(s)
    return sorted(out, key=lambda s: s.start)
