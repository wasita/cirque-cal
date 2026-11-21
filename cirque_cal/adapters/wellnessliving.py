"""WellnessLiving — schedule is behind Imperva/Incapsula bot protection and its
JSON calls are signed per-session, so we drive a real (headless) browser and
capture the JSON the page itself loads while we click through the weeks.

Used by: OM Factory NYC.
"""
from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

from ..models import Session
from ..util import html_to_text

SCHEDULE = "https://app.wellnessliving.com/rs/schedule/{slug}?k_business={business}&k_class_tab={tab}&id_class_tab=1"
NEXT_WEEK = 'button:has(svg[data-icon="angle-right"])'


def _utc(s: str) -> datetime:
    # dt_date is UTC "YYYY-MM-DD HH:MM:SS"
    return datetime.strptime(s, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)


class WellnessLivingAdapter:
    def __init__(self, key: str, cfg: dict):
        self.key = key
        self.cfg = cfg

    def fetch_raw(self, start: datetime, end: datetime) -> dict:
        from playwright.sync_api import sync_playwright

        sessions: list[dict] = []
        staff: dict = {}
        weeks = max(1, math.ceil((end - start).days / 7) + 1)

        def on_response(resp):
            url = resp.url
            try:
                if "/Wl/Schedule/ClassList/ClassList" in url:
                    sessions.extend(resp.json().get("a_session") or [])
                elif "/Wl/Staff/StaffList/StaffList.json" in url:
                    staff.update(resp.json().get("a_staff") or {})
            except Exception:
                pass

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/131.0 Safari/537.36"
                ),
                viewport={"width": 1280, "height": 900},
                timezone_id="America/New_York",
            )
            page.on("response", on_response)
            page.goto(
                SCHEDULE.format(slug=self.cfg["slug"], business=self.cfg["business_id"], tab=self.cfg["class_tab"]),
                wait_until="networkidle",
                timeout=90_000,
            )
            page.wait_for_selector(NEXT_WEEK, timeout=60_000)
            for _ in range(weeks - 1):
                before = len(sessions)
                with page.expect_response(lambda r: "ClassList/ClassList" in r.url, timeout=30_000):
                    page.click(NEXT_WEEK)
                page.wait_for_timeout(1500)
                if len(sessions) == before:
                    page.wait_for_timeout(3000)
            browser.close()
        return {"sessions": sessions, "staff": staff}

    def parse(self, raw: dict) -> list[Session]:
        staff = {
            k: (v.get("text_name_full") or f"{v.get('s_name', '')} {v.get('s_surname', '')}").strip()
            for k, v in (raw.get("staff") or {}).items()
        }
        out: dict[str, Session] = {}
        for s in raw.get("sessions") or []:
            if not s.get("dt_date") or not s.get("s_title"):
                continue
            start = _utc(s["dt_date"])
            # Regular classes have k_class_period; events/workshops may only
            # carry k_class or k_event. Fall back so odd items don't break the run.
            sid = s.get("k_class_period") or s.get("k_event") or s.get("k_class") or abs(hash(s["s_title"]))
            uid = f"wl-{sid}-{start:%Y%m%dT%H%M}@cirque-cal"
            cap, booked = s.get("i_capacity"), s.get("i_book")
            out[uid] = Session(
                uid=uid,
                studio=self.key,
                studio_name=self.cfg["name"],
                title=s["s_title"].strip(),
                start=start,
                end=start + timedelta(minutes=int(s.get("i_duration") or 60)),
                instructors=[staff.get(k, "") for k in s.get("a_staff") or [] if staff.get(k)],
                tags=[t if isinstance(t, str) else str(t) for t in s.get("a_search_tag") or []],
                description=html_to_text(s.get("html_description")),
                url=s.get("url_book") or "",
                address=self.cfg.get("address", ""),
                cancelled=str(s.get("is_cancel")) == "1",
                spots_left=(cap - booked) if isinstance(cap, int) and isinstance(booked, int) else None,
            )
        return list(out.values())

    def fetch(self, start: datetime, end: datetime) -> list[Session]:
        sessions = self.parse(self.fetch_raw(start, end))
        return [s for s in sessions if start <= s.start < end]
