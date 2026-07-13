"""
StreetPeek — Idox Portal URL Re-discovery
==========================================
The failure diagnosis (data/failure_diagnosis.json) showed most scraper
failures are stale portal URLs: hostnames decommissioned (28 DNS failures)
or wrong/moved paths (16 404s). This script tries to find the CURRENT portal
for each affected council by probing common Idox URL patterns.

Also probes the successor councils created by the 2021-2023 mergers
(North/West Northants, Cumberland, Westmorland & Furness, North Yorkshire),
whose recorded URLs are council info pages rather than portals.

A candidate counts as "found" only if the monthly-list page loads AND contains
the month/week dropdown the scraper needs.

Output: data/rediscovered_portals.json
Run:    venv/Scripts/python.exe rediscover_portals.py
"""

import json
import socket
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlparse

import requests
import urllib3
from bs4 import BeautifulSoup

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

DIAG_PATH     = Path("data/failure_diagnosis.json")
COUNCILS_JSON = Path("streetpeek/output/councils_final.json")
OUT_PATH      = Path("data/rediscovered_portals.json")
TIMEOUT       = 8
WORKERS       = 8

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-GB,en;q=0.9",
}

# Councils abolished in local government reorganisations — do NOT re-discover;
# their areas are covered by successor councils already in councils_final.json.
DEFUNCT = {
    "E60000019": "E60000334",  # Allerdale        → Cumberland (2023)
    "E60000022": "E60000334",  # Copeland         → Cumberland (2023)
    "E60000020": "E60000335",  # Barrow-in-Furness → Westmorland & Furness (2023)
    "E60000023": "E60000335",  # Eden             → Westmorland & Furness (2023)
    "E60000024": "E60000335",  # South Lakeland   → Westmorland & Furness (2023)
    "E60000058": "E60000336",  # Hambleton        → North Yorkshire (2023)
    "E60000059": "E60000336",  # Harrogate        → North Yorkshire (2023)
    "E60000061": "E60000336",  # Ryedale          → North Yorkshire (2023)
    "E60000099": "E60000332",  # Corby            → North Northamptonshire (2021)
    "E60000101": "E60000332",  # East Northants   → North Northamptonshire (2021)
    "E60000102": "E60000332",  # Kettering        → North Northamptonshire (2021)
    "E60000100": "E60000333",  # Daventry         → West Northamptonshire (2021)
    "E60000103": "E60000333",  # Northampton      → West Northamptonshire (2021)
}

# Successor councils whose recorded portal_url is an info page — probe these too
SUCCESSORS = ["E60000332", "E60000333", "E60000336", "E60000334", "E60000335"]

SUBDOMAIN_PATTERNS = [
    "publicaccess", "planning", "pa", "public", "planningaccess",
    "planningpublicaccess", "planningregister", "planningonline",
    "planningportal", "idoxpa", "planapp", "development",
    # second wave — patterns seen in the wild after first probe run
    "idoxpublicaccess", "eplanning", "paplanning", "planning2",
    "publicaccess2", "planningapps", "planningsearch", "idox", "portal",
]
PATHS = ["/online-applications", "/publicaccess", ""]


def dns_ok(host):
    try:
        socket.getaddrinfo(host, 443)
        return True
    except socket.gaierror:
        return False


def probe_url(base):
    """Return True if base hosts a working Idox monthly list."""
    url = f"{base}/search.do?action=monthlyList&searchType=Application"
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT,
                         verify=False, allow_redirects=True)
        if r.status_code != 200:
            return False
        soup = BeautifulSoup(r.text, "html.parser")
        return (soup.find("select", {"name": "month"}) is not None
                or soup.find("select", {"name": "week"}) is not None)
    except requests.exceptions.RequestException:
        return False


def candidates_for(council):
    """Generate candidate portal base URLs, most-likely first."""
    website = council.get("website", "")
    domain = urlparse(website).netloc.replace("www.", "") if website else ""
    slug = domain.split(".")[0] if domain else ""
    old = council["portal_url"].rstrip("/")
    old_parsed = urlparse(old)
    old_origin = f"{old_parsed.scheme}://{old_parsed.netloc}"

    bases = []
    # 1. The recorded URL itself, and its origin with standard paths
    #    (fixes wrong-path 404s where the host is still alive)
    if "/online-applications" in old_parsed.path:
        idx = old_parsed.path.index("/online-applications")
        bases.append(f"{old_origin}{old_parsed.path[:idx + len('/online-applications')]}")
    else:
        bases.append(old)
    for p in PATHS:
        bases.append(f"{old_origin}{p}")

    # 2. Common subdomain patterns on the council's own domain
    if domain:
        for sub in SUBDOMAIN_PATTERNS:
            for p in PATHS[:2]:  # /online-applications and /publicaccess
                bases.append(f"https://{sub}.{domain}{p}")

    # 3. Idox cloud hosting (e.g. sandwell.idoxcloud.com)
    if slug:
        bases.append(f"https://{slug}.idoxcloud.com/online-applications")
        bases.append(f"https://{slug}publicaccess.idoxcloud.com/online-applications")

    # De-dup preserving order
    seen, out = set(), []
    for b in bases:
        if b not in seen:
            seen.add(b)
            out.append(b)
    return out


def rediscover(council):
    tried = 0
    checked_hosts = {}
    for base in candidates_for(council):
        host = urlparse(base).netloc
        if host not in checked_hosts:
            checked_hosts[host] = dns_ok(host)
        if not checked_hosts[host]:
            continue
        tried += 1
        if probe_url(base):
            return {
                "reference": council["reference"],
                "name": council["name"].replace(" LPA", ""),
                "old_url": council["portal_url"],
                "found_url": f"{base}/",
                "probed": tried,
            }
        time.sleep(0.3)
    return {
        "reference": council["reference"],
        "name": council["name"].replace(" LPA", ""),
        "old_url": council["portal_url"],
        "found_url": None,
        "probed": tried,
    }


def main():
    diag = json.load(open(DIAG_PATH))
    councils = json.load(open(COUNCILS_JSON))
    by_ref = {c["reference"]: c for c in councils}

    # Skip councils already found in a previous run
    previous = {}
    if OUT_PATH.exists():
        previous = {r["reference"]: r for r in json.loads(OUT_PATH.read_text())}
    already_found = {ref for ref, r in previous.items() if r["found_url"]}

    # Targets: failing councils that still exist and didn't come back on retry
    targets = []
    for d in diag:
        ref = d["reference"]
        if d["category"] == "works_now" or ref in DEFUNCT or ref in already_found:
            continue
        targets.append(by_ref[ref])
    # Plus the successor councils (their URLs are info pages, not portals)
    for ref in SUCCESSORS:
        if ref in by_ref and ref not in already_found and by_ref[ref] not in targets:
            targets.append(by_ref[ref])

    print(f"Re-discovering portals for {len(targets)} councils "
          f"({WORKERS} parallel)...\n", flush=True)

    results = []
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futures = {ex.submit(rediscover, c): c for c in targets}
        for i, fut in enumerate(as_completed(futures), 1):
            res = fut.result()
            results.append(res)
            flag = "+" if res["found_url"] else "-"
            print(f"[{i:2}/{len(targets)}] {flag} {res['name']:<28} "
                  f"{res['found_url'] or 'NOT FOUND':<70} "
                  f"({res['probed']} probed)", flush=True)

    # Merge with previous run's finds
    merged = {r["reference"]: r for r in previous.values() if r["found_url"]}
    for r in results:
        merged[r["reference"]] = r
    results = sorted(merged.values(), key=lambda r: r["reference"])
    OUT_PATH.write_text(json.dumps(results, indent=2))

    found = [r for r in results if r["found_url"]]
    missing = [r for r in results if not r["found_url"]]
    print(f"\n{'='*60}")
    print(f"  Found:     {len(found)}/{len(results)}")
    print(f"  Not found: {len(missing)} — need manual/web research:")
    for r in missing:
        print(f"      {r['reference']}  {r['name']}")
    print(f"{'='*60}\nSaved: {OUT_PATH}")


if __name__ == "__main__":
    main()
