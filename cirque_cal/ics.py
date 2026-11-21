from __future__ import annotations

from datetime import datetime, timedelta, timezone

from icalendar import Calendar, Event

from .models import Session


def _summary(s: Session) -> str:
    who = f" · {', '.join(s.instructors)}" if s.instructors and s.kind != "open" else ""
    return f"{s.title}{who} @ {s.studio_name}"


def build_calendar(sessions: list[Session], name: str) -> bytes:
    cal = Calendar()
    cal.add("prodid", "-//cirque-cal//EN")
    cal.add("version", "2.0")
    cal.add("calscale", "GREGORIAN")
    cal.add("x-wr-calname", name)
    cal.add("x-wr-timezone", "America/New_York")
    # Hint to clients that support it (Google mostly ignores this).
    cal.add("refresh-interval", timedelta(hours=6), parameters={"VALUE": "DURATION"})
    cal.add("x-published-ttl", "PT6H")
    stamp = datetime.now(timezone.utc)
    for s in sessions:
        ev = Event()
        ev.add("uid", s.uid)
        ev.add("dtstamp", stamp)
        ev.add("dtstart", s.start)
        ev.add("dtend", s.end)
        ev.add("summary", _summary(s))
        if s.address:
            ev.add("location", s.address)
        lines = []
        if s.instructors:
            lines.append("Instructor: " + ", ".join(s.instructors))
        lines.append(f"Studio: {s.studio_name}")
        if s.spots_left is not None:
            lines.append(f"Spots left (at last check): {s.spots_left}")
        if s.url:
            lines.append(f"Book: {s.url}")
        if s.description:
            lines += ["", s.description]
        ev.add("description", "\n".join(lines))
        if s.url:
            ev.add("url", s.url)
        cal.add_component(ev)
    return cal.to_ical()
