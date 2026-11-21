"""Build the calendar feed(s).

    uv run cirque-cal                      # scrape + write ./site
    uv run cirque-cal --only atrium        # one studio (debugging)
    uv run cirque-cal --weeks 2
"""
from __future__ import annotations

import argparse
import json
import sys
import traceback
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import yaml

from .adapters import ADAPTERS
from .filters import select
from .ics import build_calendar
from .models import Session
from .normalize import enrich

ROOT = Path(__file__).resolve().parent.parent


def load_previous(base_url: str | None, key: str) -> list[Session] | None:
    """Last successfully published data for a studio (so one broken site
    doesn't wipe its classes from everyone's calendar)."""
    if not base_url:
        return None
    try:
        r = httpx.get(f"{base_url.rstrip('/')}/data/{key}.json", timeout=20, follow_redirects=True)
        r.raise_for_status()
        return [Session.from_json(d) for d in r.json()["sessions"]]
    except Exception:
        return None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=ROOT / "config", type=Path)
    ap.add_argument("--out", default=ROOT / "site", type=Path)
    ap.add_argument("--weeks", type=int, default=None)
    ap.add_argument("--only", action="append", help="studio key(s) to scrape")
    args = ap.parse_args(argv)

    studios = yaml.safe_load((args.config / "studios.yaml").read_text())["studios"]
    feeds_cfg = yaml.safe_load((args.config / "feeds.yaml").read_text())
    weeks = args.weeks or feeds_cfg.get("weeks_ahead", 5)
    base_url = feeds_cfg.get("published_url")

    now = datetime.now(timezone.utc)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
    end = now + timedelta(weeks=weeks)

    out = args.out
    (out / "data").mkdir(parents=True, exist_ok=True)

    all_sessions: list[Session] = []
    status = {"generated_at": now.isoformat(), "studios": {}}
    failures = []

    for key, cfg in studios.items():
        if args.only and key not in args.only:
            continue
        adapter = ADAPTERS[cfg["platform"]](key, cfg)
        try:
            sessions = adapter.fetch(start, end)
            if not sessions:
                raise RuntimeError("0 sessions returned - site layout/API may have changed")
            enrich(sessions, cfg)
            src = "live"
        except Exception as e:
            traceback.print_exc()
            failures.append(f"{key}: {e!r}")
            sessions = load_previous(base_url, key) or []
            src = "previous" if sessions else "none"
        print(f"[{key}] {len(sessions)} sessions ({src})")
        status["studios"][key] = {"count": len(sessions), "source": src}
        (out / "data" / f"{key}.json").write_text(
            json.dumps({"studio": key, "sessions": [s.to_json() for s in sessions]}, indent=1)
        )
        all_sessions += sessions

    for feed in feeds_cfg["feeds"]:
        chosen = select(all_sessions, feed)
        (out / feed["file"]).write_bytes(build_calendar(chosen, feed["name"]))
        status.setdefault("feeds", {})[feed["file"]] = len(chosen)
        print(f"[feed] {feed['file']}: {len(chosen)} events")

    status["failures"] = failures
    (out / "data" / "status.json").write_text(json.dumps(status, indent=1))
    links = "".join(f'<li><a href="{f["file"]}">{f["name"]}</a> ({status["feeds"][f["file"]]} events)</li>' for f in feeds_cfg["feeds"])
    (out / "index.html").write_text(
        f"<!doctype html><meta charset=utf-8><title>cirque-cal</title><h1>cirque-cal</h1>"
        f"<p>Updated {now:%Y-%m-%d %H:%M} UTC</p><ul>{links}</ul>"
        f"<p>Subscribe in Google Calendar: Other calendars → + → From URL.</p>"
    )
    if failures:
        (out / "FAILED").write_text("\n".join(failures) + "\n")
        print("FAILURES:\n  " + "\n  ".join(failures), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
