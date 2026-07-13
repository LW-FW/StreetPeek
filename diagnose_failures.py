"""
StreetPeek — Diagnose Idox scraper failures
============================================
For every council that failed with "No data available", probe the portal and
record exactly WHY it failed:
  - SSL certificate errors (retry with verify=False and note if that fixes it)
  - Connection errors / DNS failures / timeouts
  - HTTP error statuses (403 bot-block, 404, 500...)
  - Redirects away from the portal (council merged, portal moved)
  - Page loads but has no month/week dropdown (not actually an Idox portal,
    or monthly list disabled)

Output: printed categorised summary + data/failure_diagnosis.json

Run: python diagnose_failures.py
"""

import json
import re
import sqlite3
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import requests
import urllib3
from bs4 import BeautifulSoup

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

DB_PATH       = Path("data/planning.db")
COUNCILS_JSON = Path("streetpeek/output/councils_final.json")
OUT_PATH      = Path("data/failure_diagnosis.json")
TIMEOUT       = 15
DELAY         = 1.0

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-GB,en;q=0.9",
}


def find_base(portal_url):
    """Same logic as IdoxScraper._find_base."""
    parsed = urlparse(portal_url.rstrip("/"))
    path = parsed.path
    if "/online-applications" in path:
        idx = path.index("/online-applications")
        base_path = path[:idx + len("/online-applications")]
    else:
        base_path = path.rstrip("/")
    return f"{parsed.scheme}://{parsed.netloc}{base_path}"


def get_failing_councils():
    conn = sqlite3.connect(DB_PATH)
    ok = {r[0] for r in conn.execute(
        "SELECT DISTINCT council_ref FROM scrape_log WHERE success=1")}
    failed = {r[0] for r in conn.execute(
        "SELECT DISTINCT council_ref FROM scrape_log WHERE success=0")} - ok
    conn.close()

    councils = json.load(open(COUNCILS_JSON))
    idox = {c["reference"]: c for c in councils
            if c["platform"] == "Idox/PublicAccess"}
    return [idox[ref] for ref in sorted(failed) if ref in idox]


def probe_council(council):
    """Probe one council's monthly list page. Returns a diagnosis dict."""
    base = find_base(council["portal_url"])
    url = f"{base}/search.do?action=monthlyList&searchType=Application"

    result = {
        "reference":  council["reference"],
        "name":       council["name"].replace(" LPA", ""),
        "portal_url": council["portal_url"],
        "probe_url":  url,
        "category":   None,     # filled below
        "detail":     "",
        "ssl_bypass_needed": False,
        "final_url":  None,
        "http_status": None,
        "has_month_select": False,
        "has_week_select":  False,
        "page_title": None,
    }

    s = requests.Session()
    s.headers.update(HEADERS)

    # Attempt 1: normal request. Attempt 2 (on SSL error only): verify=False.
    r = None
    for verify in (True, False):
        try:
            r = s.get(url, timeout=TIMEOUT, verify=verify)
            result["ssl_bypass_needed"] = not verify
            break
        except requests.exceptions.SSLError as e:
            if not verify:  # failed even with verify=False
                result["category"] = "ssl_error"
                result["detail"] = str(e)[:200]
                return result
            continue  # retry without verification
        except requests.exceptions.ConnectTimeout:
            result["category"] = "timeout"
            result["detail"] = f"Connect timeout after {TIMEOUT}s"
            return result
        except requests.exceptions.ReadTimeout:
            result["category"] = "timeout"
            result["detail"] = f"Read timeout after {TIMEOUT}s"
            return result
        except requests.exceptions.ConnectionError as e:
            msg = str(e)
            if "NameResolutionError" in msg or "getaddrinfo" in msg:
                result["category"] = "dns_failure"
            else:
                result["category"] = "connection_refused"
            result["detail"] = msg[:200]
            return result
        except requests.exceptions.RequestException as e:
            result["category"] = "other_error"
            result["detail"] = f"{type(e).__name__}: {str(e)[:200]}"
            return result

    result["http_status"] = r.status_code
    result["final_url"] = r.url

    if r.status_code != 200:
        result["category"] = f"http_{r.status_code}"
        result["detail"] = f"HTTP {r.status_code} at {r.url}"
        return result

    soup = BeautifulSoup(r.text, "html.parser")
    title = soup.find("title")
    result["page_title"] = title.get_text(strip=True)[:100] if title else ""
    result["has_month_select"] = soup.find("select", {"name": "month"}) is not None
    result["has_week_select"]  = soup.find("select", {"name": "week"}) is not None

    probe_host = urlparse(url).netloc
    final_host = urlparse(r.url).netloc

    if result["has_month_select"] or result["has_week_select"]:
        # The dropdown IS there — original failure was transient or SSL
        result["category"] = "works_now"
        bits = []
        if result["ssl_bypass_needed"]:
            bits.append("needed verify=False")
        if not result["has_month_select"]:
            bits.append("weekly list only")
        result["detail"] = "; ".join(bits) or "month dropdown present"
        return result

    if final_host != probe_host:
        result["category"] = "redirected_away"
        result["detail"] = f"Redirected to {r.url[:150]}"
        return result

    # Page loaded on the right host but no dropdown — inspect what it is
    text = r.text.lower()
    if "idox" in text or "online-applications" in text or "publicaccess" in text:
        result["category"] = "idox_no_dropdown"
        result["detail"] = ("Idox portal but no month/week select — monthly "
                            "list may be disabled or behind a different action")
    elif any(w in text for w in ("captcha", "cloudflare", "access denied",
                                 "request unsuccessful", "incapsula")):
        result["category"] = "bot_blocked"
        result["detail"] = "Bot protection page served"
    else:
        result["category"] = "not_idox_page"
        result["detail"] = f"Page title: {result['page_title']!r}"
    return result


def main():
    councils = get_failing_councils()
    print(f"Probing {len(councils)} failing councils "
          f"(timeout {TIMEOUT}s each)...\n", flush=True)

    results = []
    for i, c in enumerate(councils, 1):
        res = probe_council(c)
        results.append(res)
        flag = "+" if res["category"] == "works_now" else "-"
        print(f"[{i:2}/{len(councils)}] {flag} {res['name']:<28} "
              f"{res['category']:<18} {res['detail'][:80]}", flush=True)
        time.sleep(DELAY)

    OUT_PATH.write_text(json.dumps(results, indent=2))

    # ── Summary ──
    from collections import Counter
    cats = Counter(r["category"] for r in results)
    print(f"\n{'='*60}\n  DIAGNOSIS SUMMARY  ({len(results)} councils)\n{'='*60}")
    for cat, n in cats.most_common():
        print(f"  {cat:<20} {n}")
        for r in results:
            if r["category"] == cat:
                print(f"      {r['name']}")
    ssl_fixable = [r for r in results if r["ssl_bypass_needed"]
                   and r["category"] == "works_now"]
    if ssl_fixable:
        print(f"\n  {len(ssl_fixable)} councils just need verify=False")
    print(f"\nFull details: {OUT_PATH}")


if __name__ == "__main__":
    main()
