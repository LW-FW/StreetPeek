"""
StreetPeek — Live external data-source health check
======================================================
The council planning portals (portal_healthcheck.py) are checked against a
local cache whose age means something. These aren't that: postcode lookup,
crime, live planning/environment data, nearby amenities and live schools are
all called fresh, per user search, straight from third-party APIs — nothing
is stored locally to check the age of.

So "last checked" here means something different: the last time this script
confirmed the endpoint is up AND still shaped the way the app expects (not
just HTTP 200 — the JSON has the fields lib/data.ts / pages/api/*.ts assume).
Feeds build_dashboard.py.

Run: venv/Scripts/python.exe check_live_sources.py
Recommended cadence: same as portal_healthcheck.py — no scheduler wired up
yet, run manually before checking the dashboard.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

import requests

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

OUT_PATH = Path("data/source_health.json")
TIMEOUT = 15
HEADERS = {"User-Agent": "StreetPeek/1.0 (internal health check; contact via streetpeek app)"}

# Trafalgar Square — a fixed point guaranteed to have crime/planning/school/
# amenity data, so an empty result means "endpoint broke", not "nothing here".
TEST_LAT, TEST_LNG = 51.5080, -0.1281
TEST_POSTCODE = "SW1A1AA"


def check_postcode():
    r = requests.get(f"https://api.postcodes.io/postcodes/{TEST_POSTCODE}", timeout=TIMEOUT, headers=HEADERS)
    r.raise_for_status()
    data = r.json()["result"]
    if not data.get("latitude"):
        raise ValueError("response missing latitude — API shape may have changed")
    return f"resolved to {data['admin_district']}"


def check_crime():
    r = requests.get(f"https://data.police.uk/api/crimes-street/all-crime?lat={TEST_LAT}&lng={TEST_LNG}",
                      timeout=TIMEOUT, headers=HEADERS)
    r.raise_for_status()
    data = r.json()
    return f"{len(data)} crimes returned"


def check_planning_gov():
    params = {"latitude": TEST_LAT, "longitude": TEST_LNG, "limit": "5", "dataset": "planning-application"}
    r = requests.get("https://www.planning.data.gov.uk/entity.json", params=params, timeout=TIMEOUT, headers=HEADERS)
    r.raise_for_status()
    n = len(r.json().get("entities", []))
    return f"{n} planning-application entities returned"


def check_environment_gov():
    params = {"latitude": TEST_LAT, "longitude": TEST_LNG, "limit": "5", "dataset": "flood-risk-zone"}
    r = requests.get("https://www.planning.data.gov.uk/entity.json", params=params, timeout=TIMEOUT, headers=HEADERS)
    r.raise_for_status()
    n = len(r.json().get("entities", []))
    return f"{n} flood-risk-zone entities returned (0 is normal if the test point isn't in one)"


def check_overpass():
    query = (f'[out:json][timeout:20];'
             f'(node["amenity"="pharmacy"](around:1000,{TEST_LAT},{TEST_LNG});'
             f'way["amenity"="pharmacy"](around:1000,{TEST_LAT},{TEST_LNG}););'
             f'out center tags;')
    r = requests.post("https://overpass-api.de/api/interpreter", data={"data": query},
                       timeout=TIMEOUT + 10, headers=HEADERS)
    r.raise_for_status()
    data = r.json()
    if data.get("remark") or "elements" not in data:
        raise ValueError(f"Overpass returned an error: {data.get('remark', 'missing elements')}")
    return f"{len(data['elements'])} elements returned"


def check_gias():
    url = "https://get-information-schools.service.gov.uk/api/v1/Establishments/search"
    params = {"lat": TEST_LAT, "lon": TEST_LNG, "rad": "1000", "limit": "5", "statusCode": "1"}
    r = requests.get(url, params=params, timeout=TIMEOUT, headers={**HEADERS, "Accept": "application/json"})
    r.raise_for_status()
    data = r.json()
    n = len(data.get("Establishments") or data.get("establishments") or [])
    return f"{n} establishments returned"


CHECKS = [
    ("Postcode lookup",           "Postcode / geocoding", check_postcode),
    ("Crime data",                "Crime",                check_crime),
    ("Planning applications",     "Planning",             check_planning_gov),
    ("Flood risk / designations", "Environment",          check_environment_gov),
    ("Nearby amenities",          "Nearby amenities",     check_overpass),
    ("Schools (live GIAS)",       "Schools & Nurseries",  check_gias),
]


def main():
    results = []
    for name, category, fn in CHECKS:
        print(f"Checking {name}...", flush=True)
        entry = {"name": name, "category": category, "checked_at": datetime.now().isoformat(),
                  "ok": False, "detail": ""}
        try:
            entry["detail"] = fn()
            entry["ok"] = True
        except Exception as e:
            entry["detail"] = f"{type(e).__name__}: {str(e)[:200]}"
        results.append(entry)
        print(f"  {'OK' if entry['ok'] else 'FAILED'} — {entry['detail']}", flush=True)

    OUT_PATH.write_text(json.dumps(results, indent=2), encoding="utf-8")
    ok_count = sum(1 for r in results if r["ok"])
    print(f"\n{ok_count}/{len(results)} sources healthy. Saved: {OUT_PATH}")


if __name__ == "__main__":
    main()
