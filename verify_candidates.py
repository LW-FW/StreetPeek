"""
Verify web-researched Idox portal candidates.

For each candidate: GET the monthly list page, confirm the month dropdown
exists, and report the NEWEST month offered — a frozen legacy portal shows
stale months, a live one shows the current month (Jul 26).

Also re-checks the probe-found URLs from data/rediscovered_portals.json
for the newest-month freshness signal.

Output: data/verified_candidates.json
"""

import json
import re
from pathlib import Path

import requests
import urllib3
from bs4 import BeautifulSoup

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# Candidates found by web research (reference, name, base URL without trailing /)
WEB_CANDIDATES = {
    "E60000007": ("Stockton-on-Tees",       "https://www.developmentmanagement.stockton.gov.uk/online-applications"),
    "E60000028": ("Oldham",                  "https://planningpa.oldham.gov.uk/online-applications"),
    "E60000029": ("Rochdale",                "https://publicaccess.rochdale.gov.uk/online-applications"),
    "E60000030": ("Salford (legacy?)",       "https://publicaccess.salford.gov.uk/publicaccess"),
    "E60000037": ("Fylde",                   "https://pa.fylde.gov.uk/online-applications"),
    "E60000051": ("Wirral",                  "https://planning.wirral.gov.uk/online-applications"),
    "E60000054": ("North East Lincolnshire", "https://planninganddevelopment.nelincs.gov.uk/online-applications"),
    "E60000083": ("North East Derbyshire",   "https://planapps-online.ne-derbyshire.gov.uk/online-applications"),
    "E60000084": ("South Derbyshire",        "https://planning.southderbyshire.gov.uk"),
    "E60000087": ("Harborough",              "https://pa2.harborough.gov.uk/online-applications"),
    "E60000089": ("Melton",                  "https://pa.melton.gov.uk/online-applications"),
    "E60000090": ("North West Leicestershire", "https://plans.nwleics.gov.uk/public-access"),
}


def check(base):
    url = f"{base}/search.do?action=monthlyList&searchType=Application"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15, verify=False)
        if r.status_code != 200:
            return {"ok": False, "detail": f"HTTP {r.status_code}"}
        soup = BeautifulSoup(r.text, "html.parser")
        sel = soup.find("select", {"name": "month"})
        if not sel:
            wk = soup.find("select", {"name": "week"})
            if wk:
                opts = [o.get("value", "") for o in wk.find_all("option")]
                return {"ok": True, "detail": f"weekly only, newest: {opts[0] if opts else '?'}"}
            return {"ok": False, "detail": "page 200 but no month/week dropdown"}
        opts = [o.get("value", o.get_text(strip=True)) for o in sel.find_all("option")]
        newest = opts[0] if opts else "?"
        return {"ok": True, "detail": f"{len(opts)} months, newest: {newest}", "newest": newest}
    except requests.exceptions.RequestException as e:
        return {"ok": False, "detail": f"{type(e).__name__}: {str(e)[:120]}"}


def main():
    results = []

    print("── Web-researched candidates ──", flush=True)
    for ref, (name, base) in WEB_CANDIDATES.items():
        res = check(base)
        flag = "+" if res["ok"] else "-"
        print(f"  {flag} {name:<28} {res['detail']:<45} {base}", flush=True)
        results.append({"reference": ref, "name": name, "url": f"{base}/",
                        "source": "web", **res})

    print("\n── Probe-found URLs (freshness check) ──", flush=True)
    probed = json.loads(Path("data/rediscovered_portals.json").read_text())
    for p in probed:
        if not p["found_url"]:
            continue
        base = p["found_url"].rstrip("/")
        res = check(base)
        flag = "+" if res["ok"] else "-"
        print(f"  {flag} {p['name']:<28} {res['detail']:<45} {base}", flush=True)
        results.append({"reference": p["reference"], "name": p["name"],
                        "url": p["found_url"], "source": "probe", **res})

    Path("data/verified_candidates.json").write_text(json.dumps(results, indent=2))
    ok = sum(1 for r in results if r["ok"])
    print(f"\n{ok}/{len(results)} verified OK → data/verified_candidates.json")


if __name__ == "__main__":
    main()
