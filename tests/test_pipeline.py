import json
from pathlib import Path

import yaml
from icalendar import Calendar

from cirque_cal.adapters.feather import FeatherAdapter
from cirque_cal.adapters.wellnessliving import WellnessLivingAdapter
from cirque_cal.filters import select
from cirque_cal.ics import build_calendar
from cirque_cal.normalize import enrich

ROOT = Path(__file__).resolve().parent.parent
FX = Path(__file__).parent / "fixtures"
STUDIOS = yaml.safe_load((ROOT / "config/studios.yaml").read_text())["studios"]
FEED = yaml.safe_load((ROOT / "config/feeds.yaml").read_text())["feeds"][0]


def atrium():
    a = FeatherAdapter("atrium", STUDIOS["atrium"])
    return enrich(a.parse(json.loads((FX / "feather_events.json").read_text())), STUDIOS["atrium"])


def om():
    a = WellnessLivingAdapter("om_factory", STUDIOS["om_factory"])
    return enrich(a.parse(json.loads((FX / "wellnessliving.json").read_text())), STUDIOS["om_factory"])


def by_title(sessions, title):
    return [s for s in sessions if s.title == title]


def test_feather_parse_and_normalize():
    s = atrium()
    lyra101 = by_title(s, "Lyra 101")[0]
    assert lyra101.instructors == ["Jacob McKee"]
    assert lyra101.level == 0 and "lyra" in lyra101.apparatus and lyra101.kind == "class"
    assert by_title(s, "Lyra 1")[0].level == 1
    assert by_title(s, "Lyra 2")[0].cancelled
    assert by_title(s, "Open Circus")[0].kind == "open"
    assert by_title(s, "Open Pole / Circus")[0].kind == "open"
    assert by_title(s, "Open Pole")[0].kind == "class"       # pole-only, not circus
    assert by_title(s, "Night Owl Hours")[0].kind == "class"
    assert lyra101.url.endswith("82f1fb5d-e913-4acf-ba02-24c84f4269ed")


def test_wellnessliving_parse_and_normalize():
    s = om()
    lyra = [x for x in s if x.title == "CIRCUS Lyra: Level 1" and not x.cancelled]
    assert len(lyra) == 2                                       # duplicate response deduped
    jacob = [x for x in lyra if x.instructors == ["Jacob McKee"]][0]
    assert jacob.level == 1 and jacob.spots_left == 3
    assert (jacob.end - jacob.start).seconds == 75 * 60
    assert jacob.start.hour == 17                               # UTC
    assert by_title(s, "CIRCUS Open Workout")[0].kind == "open"
    assert by_title(s, "*Handstands: Open Level (Off-Peak)")[0].kind == "class"


def test_cirque_feed_selection():
    chosen = select(atrium() + om(), FEED)
    titles = sorted((x.studio, x.title) for x in chosen)
    assert titles == sorted([
        ("atrium", "Lyra 101"),
        ("atrium", "Lyra 1"),
        ("atrium", "Open Circus"),
        ("atrium", "Open Pole / Circus"),
        ("om_factory", "CIRCUS Lyra: Level 1"),   # Jacob's; cancelled one dropped, Lexy's excluded
        ("om_factory", "CIRCUS Open Workout"),
    ])


def test_ics_roundtrip_and_stable_uids():
    chosen = select(atrium() + om(), FEED)
    cal = Calendar.from_ical(build_calendar(chosen, "Cirque"))
    evs = list(cal.walk("VEVENT"))
    assert len(evs) == len(chosen)
    assert str(cal["X-WR-CALNAME"]) == "Cirque"
    uids = {str(e["UID"]) for e in evs}
    assert "feather-82f1fb5d-e913-4acf-ba02-24c84f4269ed@cirque-cal" in uids   # same as the manual import
    assert all(u.endswith("@cirque-cal") for u in uids)
