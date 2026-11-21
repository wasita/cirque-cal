"""feather.rsvp — public JSON API, no auth or browser needed.

Used by: The Atrium Space.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import httpx

from ..models import Session
from ..util import html_to_text

API = "https://api.feather.rsvp/public/organizations/{org}/events"
EVENT_URL = "https://www.feather.rsvp/events/{id}"


def _dt(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


class FeatherAdapter:
    def __init__(self, key: str, cfg: dict):
        self.key = key
        self.cfg = cfg
        self.org = cfg["org_id"]

    def fetch_raw(self, start: datetime, end: datetime) -> list[dict]:
        """The endpoint returns a page of events starting at `startAt`; walk forward."""
        seen: dict[str, dict] = {}
        cursor = start
        with httpx.Client(timeout=30, headers={"User-Agent": "cirque-cal (personal calendar)"}) as c:
            for _ in range(60):  # hard stop
                r = c.get(API.format(org=self.org), params={"startAt": cursor.strftime("%Y-%m-%dT%H:%M:%S.000Z")})
                r.raise_for_status()
                page = r.json()
                if not page:
                    break
                for e in page:
                    seen[e["id"]] = e
                last = max(_dt(e["start_at"]) for e in page)
                if last >= end:
                    break
                nxt = last + timedelta(minutes=1)
                if nxt <= cursor:
                    break
                cursor = nxt
        return list(seen.values())

    def parse(self, raw: list[dict]) -> list[Session]:
        out = []
        for e in raw:
            if e.get("is_private") or e.get("deleted_at"):
                continue
            out.append(
                Session(
                    uid=f"feather-{e['id']}@cirque-cal",
                    studio=self.key,
                    studio_name=self.cfg["name"],
                    title=e["name"].strip(),
                    start=_dt(e["start_at"]),
                    end=_dt(e["end_at"]),
                    instructors=[i["full_name"].strip() for i in e.get("instructors") or []],
                    tags=[t["name"] for t in e.get("tags") or [] if not t.get("deleted_at")],
                    description=html_to_text(e.get("description")),
                    url=EVENT_URL.format(id=e["id"]),
                    address=self.cfg.get("address", ""),
                    cancelled=bool(e.get("cancelled_at")) or e.get("status") == "cancelled",
                    spots_left=e.get("num_tickets_available"),
                )
            )
        return out

    def fetch(self, start: datetime, end: datetime) -> list[Session]:
        sessions = self.parse(self.fetch_raw(start, end))
        return [s for s in sessions if start <= s.start < end]
