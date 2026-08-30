"""
StreetPeek — Automated portal health check
============================================
Answers "is our council portal list still correct?" on demand, without
waiting to notice via failed scrapes.

Why this exists, and how it differs from the three one-off 2026-07-12
scripts (diagnose_failures.py / rediscover_portals.py / verify_candidates.py):

  - Those scripts only ever look at councils that scrape_log already knows
    have failed. A council that was working and THEN broke — portal moved,
    went behind a login, started 403-blocking bots — is invisible to them
    until the next full scrape run stumbles into it.
  - verify_candidates.py's freshness check (does the portal show the
    CURRENT month, or a frozen legacy mirror?) was a manual one-off against
    a hand-typed list of candidate URLs. This script applies that same
    freshness test automatically to every council, every run.
  - update_councils.py's fixes were hardcoded dicts written by a human
    after reading a diagnosis. This script closes that loop itself: if a
    replacement URL is found AND shows fresh data, it applies the fix to
    councils_final.json directly. Anything it can't confidently resolve
    (no candidate found, or found but stale) still goes into the report for
    a human to research — same manual step, just narrowed to the genuinely
    hard cases.

Every run is diffed against the previous one (data/portal_health.json) so
the summary reads as "3 newly broken, 1 recovered, 2 auto-fixed" rather than
a flat 337-row dump.

Run:      venv/Scripts/python.exe portal_healthcheck.py
Dry run:  venv/Scripts/python.exe portal_healthcheck.py --dry-run
          (probes and reports as normal, but never writes councils_final.*)

Recommended cadence: weekly — see TODO.md. Not yet wired into a scheduler;
run manually until that's set up.
"""

import argparse
import csv
import json
import re
import shutil
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
import urllib3
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

import diagnose_failures as df
import rediscover_portals as rp

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

JSON_PATH    = Path("streetpeek/output/councils_final.json")
CSV_PATH     = Path("streetpeek/output/councils_final.csv")
HISTORY_PATH = Path("data/portal_health.json")
REPORT_DIR   = Path("data/portal_health_reports")
REPORT_DIR.mkdir(parents=True, exist_ok=True)

TIMEOUT       = 15
WORKERS       = 8
FRESH_MONTHS  = 2   # newest month on the portal must be within this many months of today

MONTH_NAMES = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


MONTH_NAME_RE = re.compile(
    r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+(\d{2,4})\b", re.IGNORECASE)
SLASH_DATE_RE = re.compile(r"\b(\d{1,2})[/-](\d{2,4})\b")
BARE_YEAR_RE = re.compile(r"\b(20\d{2})\b")


def _expand_year(y):
    return int(y) if len(y) == 4 else 2000 + int(y)


def parse_month_option(text):
    """Best-effort (year, month) out of an Idox month-dropdown option's text/value.
    Idox renders these as e.g. "Aug 26" (2-digit year) as often as "Aug 2026" or
    numeric "08/2026" — all three show up across different council installs.
    month may be None if only a year could be found."""
    if not text:
        return None
    m = MONTH_NAME_RE.search(text)
    if m:
        return (_expand_year(m.group(2)), MONTH_NAMES[m.group(1).lower()])
    m = SLASH_DATE_RE.search(text)
    if m and 1 <= int(m.group(1)) <= 12:
        return (_expand_year(m.group(2)), int(m.group(1)))
    m = BARE_YEAR_RE.search(text)
    if m:
        return (int(m.group(1)), None)
    return None


def is_fresh(parsed, max_age_months=FRESH_MONTHS):
    if not parsed:
        return False  # can't confirm -> not safe to treat as fresh
    year, month = parsed
    now = datetime.now()
    if month is None:
        return year >= now.year  # weak fallback: at least this calendar year
    age = (now.year - year) * 12 + (now.month - month)
    return -1 <= age <= max_age_months  # small tolerance for portals dated slightly ahead


def probe(base):
    """Probe an Idox base URL's monthly list page. Mirrors diagnose_failures.py's
    probe_council but always also extracts freshness, for both existing portals
    and rediscovery candidates."""
    url = f"{base}/search.do?action=monthlyList&searchType=Application"
    result = {"ok": False, "has_dropdown": False, "weekly_only": False,
              "newest_text": None, "newest_parsed": None, "fresh": False,
              "status": None, "error": None}
    try:
        r = requests.get(url, headers=rp.HEADERS, timeout=TIMEOUT, verify=False)
    except requests.exceptions.RequestException as e:
        result["error"] = f"{type(e).__name__}: {str(e)[:180]}"
        return result

    result["status"] = r.status_code
    if r.status_code != 200:
        result["error"] = f"HTTP {r.status_code}"
        return result

    soup = BeautifulSoup(r.text, "html.parser")
    month_sel = soup.find("select", {"name": "month"})
    week_sel = soup.find("select", {"name": "week"})

    if month_sel is not None:
        opts = [o.get("value", "") or o.get_text(strip=True) for o in month_sel.find_all("option")]
        newest = opts[0] if opts else None
        parsed = parse_month_option(newest)
        result.update(ok=True, has_dropdown=True, newest_text=newest,
                       newest_parsed=parsed, fresh=is_fresh(parsed))
        return result

    if week_sel is not None:
        opts = [o.get("value", "") or o.get_text(strip=True) for o in week_sel.find_all("option")]
        newest = opts[0] if opts else None
        parsed = parse_month_option(newest)
        result.update(ok=True, has_dropdown=True, weekly_only=True, newest_text=newest,
                       newest_parsed=parsed, fresh=is_fresh(parsed))
        return result

    result["error"] = "page 200 but no month/week dropdown"
    return result


def check_council(council):
    # A single failed attempt under an 8-way concurrent sweep is as likely to be
    # a transient blip (one retry later, it's fine) as a real outage — seen in
    # practice (Cornwall LPA failed under load, passed instantly on retry).
    # One retry after a short pause turns that noise into a real signal.
    base = df.find_base(council["portal_url"])
    res = probe(base)
    if not res["ok"]:
        time.sleep(2)
        res = probe(base)
    res["reference"] = council["reference"]
    res["name"] = council["name"]
    return res


PLANNING_HREF_HINTS = [
    "planning-application", "planningapplication", "planning-register",
    "public-access", "publicaccess", "online-application", "onlineapplication",
    "planningexplorer", "planning-explorer", "idox", "arcus", "planning-search",
    "search-planning", "view-planning", "track-planning", "planning-portal",
    "/planning",
]
PLANNING_TEXT_HINTS = [
    "planning application", "planning applications", "planning register",
    "search planning", "view planning", "track a planning application",
    "online planning", "planning portal", "comment on a planning application",
]

# Not exhaustive — just enough to turn "not found" into "here's the URL and
# roughly what it's running," which is most of what manual research does anyway.
PLATFORM_SIGNATURES = [
    ("planningexplorer", "Northgate / Planning Explorer"),
    ("northgate", "Northgate / Planning Explorer"),
    ("arcus", "Arcus"),
    ("agileapplications", "Agile Applications"),
    ("idoxcloud", "Idox Cloud"),
    ("ocella", "OcellaWeb"),
    ("force.com", "Salesforce Community"),
    ("civica", "Civica"),
]

MAX_CRAWL_PAGES = 10
MAX_CRAWL_DEPTH = 3


def guess_platform(url, html=""):
    hay = (url + " " + html).lower()
    for sig, label in PLATFORM_SIGNATURES:
        if sig in hay:
            return label
    return None


def find_planning_links(base_url, html):
    soup = BeautifulSoup(html, "html.parser")
    candidates = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(strip=True).lower()
        href_low = href.lower()
        if any(h in href_low for h in PLANNING_HREF_HINTS) or any(t in text for t in PLANNING_TEXT_HINTS):
            candidates.append(urljoin(base_url, href))
    seen, out = set(), []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out[:5]


def crawl_rediscover(council):
    """Fallback for when pattern-guessing (candidates_for) finds nothing: fetch
    the council's own homepage and follow links that look like they lead to
    planning applications, the way a human researching this by hand would —
    up to MAX_CRAWL_DEPTH hops deep (many councils bury the actual register
    behind a "Planning" landing page, itself linking to the real tool).
    Can recover genuine Idox instances the pattern guesser's subdomain list
    didn't happen to cover, and — for councils that have moved to a different
    platform entirely — surfaces the actual current URL and a rough platform
    guess instead of a bare 'not found'."""
    website = council.get("website", "")
    if not website:
        return {"found_url": None, "fresh": False, "platform_lead": None}
    try:
        r = requests.get(website, headers=rp.HEADERS, timeout=8, verify=False)
        if r.status_code != 200:
            return {"found_url": None, "fresh": False, "platform_lead": None}
    except requests.exceptions.RequestException:
        return {"found_url": None, "fresh": False, "platform_lead": None}

    visited = {r.url}
    queue = [(u, 1) for u in find_planning_links(r.url, r.text)]
    first_lead = queue[0][0] if queue else None
    fetched = 0

    while queue and fetched < MAX_CRAWL_PAGES:
        link, depth = queue.pop(0)
        if link in visited:
            continue
        visited.add(link)
        try:
            lr = requests.get(link, headers=rp.HEADERS, timeout=8, verify=False)
        except requests.exceptions.RequestException:
            continue
        fetched += 1
        if lr.status_code != 200:
            continue

        if "/online-applications" in lr.url or "/publicaccess" in lr.url:
            base = df.find_base(lr.url)
            res = probe(base)
            if res["ok"]:
                return {"found_url": f"{base}/", "fresh": res["fresh"], "platform_lead": None}

        soup2 = BeautifulSoup(lr.text, "html.parser")
        if soup2.find("select", {"name": "month"}) or soup2.find("select", {"name": "week"}):
            base = df.find_base(lr.url)
            res = probe(base)
            if res["ok"]:
                return {"found_url": f"{base}/", "fresh": res["fresh"], "platform_lead": None}

        platform = guess_platform(lr.url, lr.text)
        if platform:
            return {"found_url": None, "fresh": False,
                    "platform_lead": {"url": lr.url, "platform": platform}}

        if depth < MAX_CRAWL_DEPTH:
            for nxt in find_planning_links(lr.url, lr.text):
                if nxt not in visited:
                    queue.append((nxt, depth + 1))

    if first_lead:
        return {"found_url": None, "fresh": False,
                "platform_lead": {"url": first_lead, "platform": "unknown — needs a look"}}
    return {"found_url": None, "fresh": False, "platform_lead": None}


def attempt_rediscover(council):
    """Try every Idox-pattern candidate for this council; return the first one
    that's reachable AND fresh. If none of those pan out, fall back to crawling
    the council's own website (crawl_rediscover) rather than giving up."""
    best_stale = None
    for base in rp.candidates_for(council):
        host = base.split("//", 1)[-1].split("/", 1)[0]
        if not rp.dns_ok(host):
            continue
        res = probe(base)
        time.sleep(0.3)
        if res["ok"] and res["fresh"]:
            return {"found_url": f"{base}/", "fresh": True, "detail": res, "platform_lead": None}
        if res["ok"] and best_stale is None:
            best_stale = {"found_url": f"{base}/", "fresh": False, "detail": res, "platform_lead": None}
    if best_stale:
        return best_stale
    result = crawl_rediscover(council)
    result.setdefault("detail", None)
    return result


def load_councils():
    return json.loads(JSON_PATH.read_text(encoding="utf-8"))


def backup(path):
    if not path.exists():
        return
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    shutil.copy2(path, path.with_suffix(path.suffix + f".bak-{stamp}"))


def apply_fix(councils, reference, new_url):
    for c in councils:
        if c["reference"] == reference:
            c["portal_url"] = new_url
            c["scanned_at"] = datetime.now().isoformat()
            return


def write_councils(councils, dry_run):
    if dry_run:
        return
    backup(JSON_PATH)
    backup(CSV_PATH)
    JSON_PATH.write_text(json.dumps(councils, indent=2), encoding="utf-8")
    fieldnames = ["reference", "name", "website", "portal_url", "platform", "scanned_at"]
    with CSV_PATH.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for c in councils:
            w.writerow({k: c.get(k, "") for k in fieldnames})


def main():
    parser = argparse.ArgumentParser(description="StreetPeek portal health check")
    parser.add_argument("--dry-run", action="store_true",
                         help="Probe and report only; never write councils_final.*")
    args = parser.parse_args()

    councils = load_councils()
    idox = [c for c in councils if c["platform"] == "Idox/PublicAccess"
            and c["reference"] not in rp.DEFUNCT]
    print(f"Checking {len(idox)} Idox councils ({WORKERS} parallel, "
          f"{TIMEOUT}s timeout each)...\n", flush=True)

    results = {}
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futures = {ex.submit(check_council, c): c for c in idox}
        done = 0
        for fut in as_completed(futures):
            res = fut.result()
            done += 1
            results[res["reference"]] = res
            if res["ok"] and res["fresh"]:
                flag, note = "OK", res["newest_text"]
            elif res["ok"]:
                flag, note = "STALE", f"newest: {res['newest_text']}"
            else:
                flag, note = "BROKEN", res["error"]
            print(f"[{done:3}/{len(idox)}] {flag:<6} {res['name']:<30} {note}", flush=True)

    previous = {}
    if HISTORY_PATH.exists():
        previous = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))

    def status_of(r):
        if r["ok"] and r["fresh"]:
            return "ok"
        if r["ok"]:
            return "stale"
        return "broken"

    # Host -> owning council, from URLs as they stood BEFORE any fix in this run.
    # A rediscovered candidate that lands on a host another council already owns
    # is far more likely to be bad "website" metadata (see portal_healthcheck's
    # docstring / TODO.md — this bit us for 3 National Park entries whose
    # website field had been mis-recorded as their host authority's site) than
    # a genuine shared Idox instance. Treat any such match as needing a human
    # to confirm, never auto-apply it.
    host_owner = {}
    for c in idox:
        host_owner.setdefault(urlparse(c["portal_url"]).netloc, []).append(c["reference"])

    councils_by_ref = {c["reference"]: c for c in idox}
    broken_or_stale = [ref for ref, res in results.items() if status_of(res) in ("broken", "stale")]

    # Rediscovery (pattern-guessing, then a website crawl fallback) is the slow
    # part — parallelise it the same way as the initial sweep, rather than
    # doing it one council at a time.
    print(f"\nRediscovering {len(broken_or_stale)} broken/stale councils "
          f"({WORKERS} parallel)...\n", flush=True)
    fixes = {}
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futures = {ex.submit(attempt_rediscover, councils_by_ref[ref]): ref for ref in broken_or_stale}
        done = 0
        for fut in as_completed(futures):
            ref = futures[fut]
            fixes[ref] = fut.result()
            done += 1
            fix = fixes[ref]
            shown = fix.get("found_url") or (fix.get("platform_lead") or {}).get("url") or "nothing found"
            print(f"[rediscover {done:3}/{len(broken_or_stale)}] {councils_by_ref[ref]['name']:<30} {shown}", flush=True)

    newly_broken, newly_stale, recovered, auto_fixed, needs_review = [], [], [], [], []

    for ref, res in results.items():
        cur_status = status_of(res)
        prev_status = previous.get(ref, {}).get("status")

        if cur_status in ("broken", "stale"):
            council = councils_by_ref[ref]
            fix = fixes[ref]
            candidate_host = urlparse(fix["found_url"]).netloc if fix["found_url"] else None
            other_owners = [r for r in host_owner.get(candidate_host, []) if r != ref] if candidate_host else []

            if fix["found_url"] and fix["fresh"] and not other_owners:
                old_url = council["portal_url"]
                apply_fix(councils, ref, fix["found_url"])
                auto_fixed.append({"reference": ref, "name": res["name"],
                                    "old_url": old_url, "new_url": fix["found_url"]})
                cur_status = "ok"  # reflects the state after the fix for history purposes
            elif fix["found_url"] and fix["fresh"] and other_owners:
                needs_review.append({
                    "reference": ref, "name": res["name"], "status": cur_status,
                    "current_url": council["portal_url"], "detail": res["error"] or res["newest_text"],
                    "best_candidate": fix["found_url"],
                    "candidate_note": f"NOT auto-applied — candidate host is already used by {other_owners}; "
                                       "confirm this isn't a shared-website data error before applying by hand",
                })
            else:
                lead = fix.get("platform_lead")
                if lead:
                    note = f"found via site crawl: {lead['url']}  (looks like {lead['platform']})"
                elif fix["found_url"]:
                    note = "found but not fresh"
                else:
                    note = "no working candidate found"
                needs_review.append({
                    "reference": ref, "name": res["name"], "status": cur_status,
                    "current_url": council["portal_url"], "detail": res["error"] or res["newest_text"],
                    "best_candidate": fix["found_url"], "platform_lead": lead,
                    "candidate_note": note,
                })

        if prev_status in ("ok",) and cur_status == "broken":
            newly_broken.append(res["name"])
        elif prev_status in ("ok",) and cur_status == "stale":
            newly_stale.append(res["name"])
        elif prev_status in ("broken", "stale") and cur_status == "ok" and ref not in [f["reference"] for f in auto_fixed]:
            recovered.append(res["name"])

    write_councils(councils, args.dry_run)

    if not args.dry_run:
        new_history = {ref: {"status": status_of(res), "checked_at": datetime.now().isoformat()}
                       for ref, res in results.items()}
        for f in auto_fixed:
            new_history[f["reference"]]["status"] = "ok"
        HISTORY_PATH.write_text(json.dumps(new_history, indent=2), encoding="utf-8")

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    report = {
        "run_at": datetime.now().isoformat(),
        "dry_run": args.dry_run,
        "checked": len(idox),
        "summary": dict(Counter(status_of(r) for r in results.values())),
        "newly_broken": newly_broken,
        "newly_stale": newly_stale,
        "recovered": recovered,
        "auto_fixed": auto_fixed,
        "needs_review": needs_review,
    }
    report_path = REPORT_DIR / f"{stamp}.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"\n{'='*60}\n  PORTAL HEALTH SUMMARY\n{'='*60}")
    counts = Counter(status_of(r) for r in results.values())
    print(f"  OK: {counts['ok']}   Stale: {counts['stale']}   Broken: {counts['broken']}")
    print(f"  Newly broken:  {len(newly_broken)}  {newly_broken}")
    print(f"  Newly stale:   {len(newly_stale)}  {newly_stale}")
    print(f"  Recovered:     {len(recovered)}  {recovered}")
    print(f"  Auto-fixed:    {len(auto_fixed)}")
    for f in auto_fixed:
        print(f"      {f['name']}: {f['old_url']} -> {f['new_url']}")
    print(f"  Needs manual review: {len(needs_review)}")
    for n in needs_review:
        print(f"      {n['reference']}  {n['name']:<28} {n['status']:<7} {n['candidate_note']}")
    if args.dry_run:
        print("\n  DRY RUN — councils_final.json/csv were not modified.")
    print(f"\nFull report: {report_path}")


if __name__ == "__main__":
    main()
