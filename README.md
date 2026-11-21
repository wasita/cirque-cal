# cirque-cal

A self-updating calendar of NYC aerial / lyra classes, built from studio booking
sites and published as an `.ics` feed you subscribe to in Google Calendar.

**Feed:** https://wasita.space/cirque-cal/cirque.ics

## How it works

```
GitHub Actions (daily) → adapters scrape each studio → normalize (apparatus, level, open vs class)
  → filter rules (config/feeds.yaml) → site/cirque.ics → GitHub Pages
```

| Studio | Platform | How we read it |
|---|---|---|
| OM Factory | WellnessLiving | Headless Chromium (Playwright) loads the schedule and captures the JSON it fetches — the site is bot-protected and its API calls are signed |
| The Atrium | feather.rsvp | Public JSON API (`api.feather.rsvp/public/organizations/<id>/events`) |

Adapters are per *platform*, so adding another WellnessLiving or Feather studio is
just a new entry in `config/studios.yaml`.

If a studio fails, the build keeps its **last published data** (so classes don't
vanish from your calendar), still deploys the rest, then marks the run failed so
GitHub emails you.

## Changing what's in the calendar

Edit `config/feeds.yaml`. A session is included if it matches **any** rule; a rule
matches if **all** its conditions match:

```yaml
feeds:
  - file: cirque.ics
    name: Cirque
    include:
      - instructors: ["Jacob McKee"]
        apparatus: [lyra]
      - kind: open                 # Open Circus / Open Workout
      # - apparatus: [lyra]        # e.g. every lyra class
      #   level_min: 1
      #   level_max: 2
```

Add more entries under `feeds:` to publish extra calendars you can toggle separately.

Levels are mapped to a common scale (0 = 101/intro, 1, 2, 2.5 = "Level 2/3"…).
Defaults live in `cirque_cal/normalize.py`; per-studio overrides in `studios.yaml`.

## Run locally

```bash
uv sync
uv run playwright install chromium
uv run pytest -q
uv run cirque-cal --out site            # all studios
uv run cirque-cal --only atrium         # one studio
open site/cirque.ics
```

## One-time setup

1. Repo → Settings → Pages → **Source: GitHub Actions**.
2. Actions → *Build calendar feed* → **Run workflow**.
3. Google Calendar (web) → Other calendars → **+** → **From URL** → paste the feed URL.

Google refreshes subscribed calendars on its own schedule (roughly every 8–24h).
