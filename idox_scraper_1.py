"""
StreetPeek — Idox Planning Portal Scraper v6
=============================================
Uses requests (not mechanize) for form submission — mechanize has a Windows
bug with non-default SelectControl values.

Strategy:
  - First run (--full):   loop through all available months (~5 years)
  - Weekly run (--update): loop through last 8 weeks only

Run modes:
  python idox_scraper.py --test              # 3 councils, last 3 months
  python idox_scraper.py --full              # All 313 councils, full history
  python idox_scraper.py --update            # All 313 councils, last 8 weeks
  python idox_scraper.py --council E60000309 # Single council
  python idox_scraper.py --export            # Export to CSV/JSON for Supabase
  python idox_scraper.py --stats             # Show DB stats

Install: pip install requests beautifulsoup4
"""

import requests
import sqlite3
import json
import time
import logging
import argparse
import re
import csv
from pathlib import Path
from datetime import datetime, timedelta
from urllib.parse import urlparse
from bs4 import BeautifulSoup

DATA_DIR      = Path("data")
DB_PATH       = DATA_DIR / "planning.db"
COUNCILS_JSON = Path("streetpeek/output/councils_final.json")
DELAY         = 3.0    # seconds between councils
PAGE_DELAY    = 1.5    # seconds between pages

logging.basicConfig(level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S")
log = logging.getLogger(__name__)
DATA_DIR.mkdir(exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-GB,en;q=0.9",
}


# ── Database ──────────────────────────────────────────────────────────────────

def init_db(conn):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS planning_applications (
            id               TEXT PRIMARY KEY,
            council_ref      TEXT NOT NULL,
            council_name     TEXT NOT NULL,
            reference        TEXT NOT NULL,
            description      TEXT,
            address          TEXT,
            postcode         TEXT,
            status           TEXT,
            app_type         TEXT,
            date_received    TEXT,
            date_validated   TEXT,
            date_decided     TEXT,
            lat              REAL,
            lng              REAL,
            portal_url       TEXT,
            application_url  TEXT,
            scraped_at       TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_postcode ON planning_applications(postcode);
        CREATE INDEX IF NOT EXISTS idx_council  ON planning_applications(council_ref);
        CREATE INDEX IF NOT EXISTS idx_date     ON planning_applications(date_validated);
        CREATE INDEX IF NOT EXISTS idx_lat_lng  ON planning_applications(lat, lng);

        CREATE TABLE IF NOT EXISTS scrape_log (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            council_ref   TEXT NOT NULL,
            scraped_at    TEXT NOT NULL,
            mode          TEXT,
            records_found INTEGER,
            success       INTEGER,
            error         TEXT
        );
    """)
    conn.commit()

def already_fully_scraped(conn, council_ref):
    return conn.execute(
        "SELECT id FROM scrape_log WHERE council_ref=? AND mode='full' AND success=1 LIMIT 1",
        (council_ref,)
    ).fetchone() is not None

def recently_updated(conn, council_ref, hours=20):
    cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
    return conn.execute(
        "SELECT id FROM scrape_log WHERE council_ref=? AND success=1 AND scraped_at>? LIMIT 1",
        (council_ref, cutoff)
    ).fetchone() is not None


# ── Geocoding ─────────────────────────────────────────────────────────────────

_postcode_cache = {}

def geocode_postcode(postcode):
    if not postcode:
        return None, None
    pc = re.sub(r"\s+", "", postcode.upper())
    if pc in _postcode_cache:
        return _postcode_cache[pc]
    try:
        r = requests.get(f"https://api.postcodes.io/postcodes/{pc}", timeout=5)
        if r.status_code == 200:
            d = r.json()["result"]
            result = (d["latitude"], d["longitude"])
            _postcode_cache[pc] = result
            return result
    except Exception:
        pass
    _postcode_cache[pc] = (None, None)
    return None, None

def extract_postcode(address):
    if not address:
        return ""
    m = re.search(r'\b([A-Z]{1,2}\d{1,2}[A-Z]?\s*\d[A-Z]{2})\b', address.upper())
    return m.group(1) if m else ""


# ── Idox Scraper ──────────────────────────────────────────────────────────────

class IdoxScraper:
    """
    Scrapes Idox portals using requests for form submission.
    Uses the monthly/weekly list pages which work on all Idox versions.
    """

    def __init__(self, portal_url, council_ref, council_name):
        self.portal_url   = portal_url.rstrip("/")
        self.council_ref  = council_ref
        self.council_name = council_name
        self.base         = self._find_base()
        self.search_url   = f"{self.base}/search.do"

    def _find_base(self):
        parsed = urlparse(self.portal_url)
        path   = parsed.path
        if "/online-applications" in path:
            idx = path.index("/online-applications")
            base_path = path[:idx + len("/online-applications")]
        else:
            base_path = path.rstrip("/")
        return f"{parsed.scheme}://{parsed.netloc}{base_path}"

    def _new_session(self):
        """Create a fresh requests session. SSL verification disabled to handle
        councils with invalid/self-signed certificates."""
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        s = requests.Session()
        s.headers.update(HEADERS)
        s.verify = False
        return s

    def _get_options(self, field_name, action="monthlyList"):
        """
        Fetch the list page and return available option values for a select field.
        e.g. field_name='month' returns ['May 26', 'Apr 26', ...]
        """
        s = self._new_session()
        try:
            r = s.get(f"{self.search_url}?action={action}&searchType=Application",
                      timeout=20)
            soup = BeautifulSoup(r.text, "html.parser")
            sel = soup.find("select", {"name": field_name})
            if not sel:
                return []
            return [o.get("value", o.get_text(strip=True))
                    for o in sel.find_all("option")
                    if o.get("value") or o.get_text(strip=True)]
        except Exception as e:
            log.warning(f"  Error getting {field_name} options: {e}")
            return []

    def get_available_months(self):
        return self._get_options("month", "monthlyList")

    def get_available_weeks(self):
        return self._get_options("week", "weeklyList")

    def _scrape_period(self, field_name, field_value, action, results_action):
        """
        Generic method to scrape a monthly or weekly list.
        Creates a fresh session, GETs the list page, extracts CSRF,
        POSTs the form, parses results, handles pagination.
        """
        s = self._new_session()
        all_apps = []

        try:
            # GET the list page to get CSRF token and cookies
            r = s.get(
                f"{self.search_url}?action={action}&searchType=Application",
                timeout=20
            )
            csrf = re.search(r'name="_csrf"[^>]*value="([^"]+)"', r.text)
            csrf_token = csrf.group(1) if csrf else ""

            # Build POST data — include all form fields we can find
            soup = BeautifulSoup(r.text, "html.parser")
            post_data = {"_csrf": csrf_token, "searchType": "Application",
                         "dateType": "DC_Validated"}

            # Add any hidden fields
            for inp in soup.find_all("input", type="hidden"):
                name = inp.get("name")
                if name and name != "_csrf":
                    post_data[name] = inp.get("value", "")

            # Add empty select fields
            for sel in soup.find_all("select"):
                name = sel.get("name")
                if name and name not in post_data:
                    post_data[name] = ""

            # Set our target field
            post_data[field_name] = field_value
            post_data["dateType"] = "DC_Validated"

            origin = f"{urlparse(self.base).scheme}://{urlparse(self.base).netloc}"

            # POST to results page
            r2 = s.post(
                f"{self.base}/{results_action}",
                data=post_data,
                params={"action": "firstPage"},
                headers={"Referer": r.url, "Origin": origin,
                         "Content-Type": "application/x-www-form-urlencoded"},
                timeout=25,
                allow_redirects=True
            )

            if r2.status_code != 200:
                log.warning(f"  POST returned {r2.status_code} for {field_value}")
                return []

            apps = self._parse_results(r2.text)
            all_apps.extend(apps)

            # Pagination
            page = 2
            current_url = r2.url
            html = r2.text
            while True:
                next_url = self._find_next_url(html, current_url)
                if not next_url:
                    break
                time.sleep(PAGE_DELAY)
                r3 = s.get(next_url, timeout=20)
                if r3.status_code != 200:
                    break
                html = r3.text
                current_url = r3.url
                new_apps = self._parse_results(html)
                if not new_apps:
                    break
                all_apps.extend(new_apps)
                log.info(f"    Page {page}: +{len(new_apps)}")
                page += 1

        except Exception as e:
            log.warning(f"  Error scraping {field_value}: {e}")

        return all_apps

    def scrape_month(self, month_value):
        return self._scrape_period(
            "month", month_value,
            action="monthlyList",
            results_action="monthlyListResults.do"
        )

    def scrape_week(self, week_value):
        return self._scrape_period(
            "week", week_value,
            action="weeklyList",
            results_action="weeklyListResults.do"
        )

    def _find_next_url(self, html, current_url):
        soup = BeautifulSoup(html, "html.parser")
        parsed = urlparse(self.base)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        for a in soup.find_all("a"):
            txt = a.get_text(strip=True).lower()
            if txt in ("next", "next page", "›", "»", ">"):
                href = a.get("href", "")
                if href and href != "#":
                    if href.startswith("http"):
                        return href
                    # href is like /online-applications/pagedSearchResults.do?...
                    # just prepend the origin (scheme + host), not the full base
                    return f"{origin}{href}" if href.startswith("/") else f"{origin}/{href}"
        return None

    def _parse_results(self, html):
        soup = BeautifulSoup(html, "html.parser")
        items = soup.find_all("li", class_=re.compile(r"searchresult", re.I))
        return [app for item in items for app in [self._parse_item(item)] if app]

    def _parse_item(self, item):
        link = item.find("a", href=re.compile(r"keyVal=", re.I))
        if not link:
            return None
        m = re.search(r"keyVal=([^&\"]+)", link.get("href", ""))
        if not m:
            return None
        key_val = m.group(1)

        ref_el  = item.find(class_=re.compile(r"caseNo|reference", re.I))
        reference = ref_el.get_text(strip=True) if ref_el else link.get_text(strip=True)

        addr_el = item.find(class_=re.compile(r"\baddress\b", re.I))
        address = addr_el.get_text(strip=True) if addr_el else ""

        desc_el = item.find(class_=re.compile(r"proposal|description", re.I))
        description = desc_el.get_text(strip=True) if desc_el else ""

        status_el = item.find(class_=re.compile(r"\bstatus\b", re.I))
        status = status_el.get_text(strip=True) if status_el else ""

        dates = re.findall(r'(Received|Validated|Decided)\s*:?\s*(\d{1,2}/\d{2}/\d{4})',
                           item.get_text(), re.IGNORECASE)
        date_map = {k.lower(): v for k, v in dates}

        if not reference:
            return None

        postcode = extract_postcode(address)
        lat, lng = None, None
        if postcode:
            lat, lng = geocode_postcode(postcode)
            time.sleep(0.1)

        app_type = ""
        t = re.search(r'/([A-Z]{2,5})$', reference)
        if t:
            app_type = t.group(1)

        return {
            "id":              f"{self.council_ref}_{key_val}",
            "council_ref":     self.council_ref,
            "council_name":    self.council_name,
            "reference":       reference[:100],
            "description":     description[:500],
            "address":         address[:300],
            "postcode":        postcode,
            "status":          status[:100],
            "app_type":        app_type,
            "date_received":   date_map.get("received", ""),
            "date_validated":  date_map.get("validated", ""),
            "date_decided":    date_map.get("decided", ""),
            "lat":             lat,
            "lng":             lng,
            "portal_url":      self.portal_url,
            "application_url": f"{self.base}/applicationDetails.do?activeTab=summary&keyVal={key_val}",
            "scraped_at":      datetime.now().isoformat(),
        }


# ── Storage ───────────────────────────────────────────────────────────────────

def save_applications(conn, apps):
    saved = 0
    for app in apps:
        try:
            conn.execute("""
                INSERT OR REPLACE INTO planning_applications
                (id, council_ref, council_name, reference, description, address,
                 postcode, status, app_type, date_received, date_validated,
                 date_decided, lat, lng, portal_url, application_url, scraped_at)
                VALUES
                (:id, :council_ref, :council_name, :reference, :description, :address,
                 :postcode, :status, :app_type, :date_received, :date_validated,
                 :date_decided, :lat, :lng, :portal_url, :application_url, :scraped_at)
            """, app)
            saved += 1
        except Exception as e:
            log.warning(f"  DB error: {e}")
    conn.commit()
    return saved

def log_scrape(conn, ref, mode, records, success, error=""):
    conn.execute("""
        INSERT INTO scrape_log (council_ref, scraped_at, mode, records_found, success, error)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (ref, datetime.now().isoformat(), mode, records, int(success), error))
    conn.commit()


# ── Council orchestration ─────────────────────────────────────────────────────

def scrape_council(council, conn, mode, max_months=None, max_weeks=None):
    ref  = council["reference"]
    name = council["name"].replace(" LPA", "")
    url  = council["portal_url"]
    log.info(f"Scraping: {name} ({ref})")

    scraper = IdoxScraper(url, ref, name)
    total = 0

    try:
        if mode in ("full", "test_full"):
            months = scraper.get_available_months()
            if not months:
                log.warning(f"  No months — trying weeks")
                weeks = scraper.get_available_weeks()
                if not weeks:
                    log.warning(f"  No weeks either — skipping")
                    log_scrape(conn, ref, mode, 0, False, "No data available")
                    return 0
                if max_weeks:
                    weeks = weeks[:max_weeks]
                log.info(f"  {len(weeks)} weeks")
                for i, week in enumerate(weeks, 1):
                    log.info(f"  Week {i}/{len(weeks)}: {week}")
                    apps  = scraper.scrape_week(week)
                    saved = save_applications(conn, apps)
                    total += saved
                    log.info(f"    {len(apps)} found, {saved} saved")
                    time.sleep(PAGE_DELAY)
            else:
                if max_months:
                    months = months[:max_months]
                log.info(f"  {len(months)} months available")
                for i, month in enumerate(months, 1):
                    log.info(f"  Month {i}/{len(months)}: {month}")
                    apps  = scraper.scrape_month(month)
                    saved = save_applications(conn, apps)
                    total += saved
                    log.info(f"    {len(apps)} found, {saved} saved (total: {total})")
                    time.sleep(PAGE_DELAY)

        else:  # update mode
            weeks = scraper.get_available_weeks()
            if not weeks:
                months = scraper.get_available_months()
                for month in (months[:2] if months else []):
                    apps  = scraper.scrape_month(month)
                    saved = save_applications(conn, apps)
                    total += saved
                    time.sleep(PAGE_DELAY)
            else:
                n = max_weeks or 8
                log.info(f"  {len(weeks[:n])} weeks to scrape")
                for i, week in enumerate(weeks[:n], 1):
                    log.info(f"  Week {i}/{n}: {week}")
                    apps  = scraper.scrape_week(week)
                    saved = save_applications(conn, apps)
                    total += saved
                    log.info(f"    {len(apps)} found, {saved} saved")
                    time.sleep(PAGE_DELAY)

        log_scrape(conn, ref, mode, total, True)
        log.info(f"  ✓ Total: {total}")
        return total

    except Exception as e:
        log.error(f"  ✗ Failed: {e}")
        log_scrape(conn, ref, mode, total, False, str(e))
        return total


# ── Utilities ─────────────────────────────────────────────────────────────────

def load_councils(path):
    with open(path) as f:
        return [c for c in json.load(f) if c["platform"] == "Idox/PublicAccess"]

def print_stats(conn):
    total    = conn.execute("SELECT COUNT(*) FROM planning_applications").fetchone()[0]
    councils = conn.execute("SELECT COUNT(DISTINCT council_ref) FROM planning_applications").fetchone()[0]
    geocoded = conn.execute("SELECT COUNT(*) FROM planning_applications WHERE lat IS NOT NULL").fetchone()[0]
    oldest   = conn.execute("SELECT MIN(date_validated) FROM planning_applications").fetchone()[0]
    newest   = conn.execute("SELECT MAX(date_validated) FROM planning_applications").fetchone()[0]
    print(f"\n{'='*55}\n  DATABASE STATS\n{'='*55}")
    print(f"  Total applications: {total:,}")
    print(f"  Councils covered:   {councils} / 313")
    print(f"  Geocoded:           {geocoded:,} ({geocoded/max(total,1)*100:.0f}%)")
    print(f"  Date range:         {oldest} → {newest}")
    print(f"{'='*55}\n")

def export(conn):
    cursor = conn.execute("SELECT * FROM planning_applications ORDER BY date_validated DESC")
    cols = [d[0] for d in cursor.description]
    rows = cursor.fetchall()
    csv_path  = DATA_DIR / "planning_applications.csv"
    json_path = DATA_DIR / "planning_applications.json"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(cols); w.writerows(rows)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump([dict(zip(cols, r)) for r in rows], f, indent=2)
    log.info(f"Exported {len(rows):,} rows")


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="StreetPeek Idox Scraper")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--test",    action="store_true", help="3 councils, 3 months")
    group.add_argument("--full",    action="store_true", help="All councils, full history (resumable)")
    group.add_argument("--update",  action="store_true", help="All councils, last 8 weeks")
    group.add_argument("--council", metavar="REF",       help="Single council e.g. E60000309")
    group.add_argument("--export",  action="store_true")
    group.add_argument("--stats",   action="store_true")
    parser.add_argument("--months", type=int, default=None)
    parser.add_argument("--weeks",  type=int, default=None)
    args = parser.parse_args()

    conn = sqlite3.connect(DB_PATH)
    init_db(conn)

    if args.stats:  print_stats(conn); conn.close(); return
    if args.export: export(conn); print_stats(conn); conn.close(); return

    if not COUNCILS_JSON.exists():
        log.error(f"Not found: {COUNCILS_JSON}"); conn.close(); return

    councils = load_councils(COUNCILS_JSON)
    log.info(f"Loaded {len(councils)} Idox councils")

    if args.test:
        targets = [c for c in councils
                   if c["reference"] in {"E60000309", "E60000195", "E60000071"}]
        if not targets:
            targets = councils[:3]
        log.info(f"Test: {len(targets)} councils, 3 months each")
        for c in targets:
            scrape_council(c, conn, "test_full", max_months=3)
            time.sleep(DELAY)

    elif args.full:
        log.info(f"Full scrape: {len(councils)} councils — Ctrl+C safe, will resume")
        for i, c in enumerate(councils, 1):
            log.info(f"[{i}/{len(councils)}]")
            if already_fully_scraped(conn, c["reference"]):
                log.info(f"  Already done — skipping")
                continue
            scrape_council(c, conn, "full", max_months=args.months)
            time.sleep(DELAY)

    elif args.update:
        log.info(f"Update: {len(councils)} councils, last {args.weeks or 8} weeks")
        for i, c in enumerate(councils, 1):
            log.info(f"[{i}/{len(councils)}]")
            if recently_updated(conn, c["reference"], hours=20):
                log.info(f"  Updated recently — skipping")
                continue
            scrape_council(c, conn, "update", max_weeks=args.weeks)
            time.sleep(DELAY)

    elif args.council:
        matches = [c for c in councils if c["reference"] == args.council]
        if not matches:
            log.error(f"Not found: {args.council}"); conn.close(); return
        scrape_council(matches[0], conn, "full", max_months=args.months)

    print_stats(conn)
    conn.close()

if __name__ == "__main__":
    main()
