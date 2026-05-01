"""
StreetPeek — Idox Planning Portal Scraper v4 (mechanize)
=========================================================
Uses mechanize to handle form submission properly — same as a real browser.

Strategy:
  - First run:  scrape ALL available data (pass --full, goes back 5+ years)
  - Weekly run: scrape last 30 days only (pass --update)

Run modes:
  python idox_scraper.py --full              # First-time: scrape all history
  python idox_scraper.py --update            # Weekly: last 30 days only
  python idox_scraper.py --council E60000001 # One council (uses current --days setting)
  python idox_scraper.py --test              # 3 councils, last 90 days
  python idox_scraper.py --export            # Export DB to CSV/JSON for Supabase
  python idox_scraper.py --stats             # Show DB stats

Install deps first:
  pip install mechanize beautifulsoup4 requests
"""

import mechanize
import sqlite3
import json
import time
import logging
import argparse
import re
import csv
import http.cookiejar
from pathlib import Path
from datetime import datetime, timedelta
from urllib.parse import urlparse
from bs4 import BeautifulSoup

DATA_DIR      = Path("data")
DB_PATH       = DATA_DIR / "planning.db"
COUNCILS_JSON = Path("streetpeek/output/councils_final.json")
DELAY         = 3.0   # seconds between councils — be polite
PAGE_DELAY    = 1.5   # seconds between pages within a council

logging.basicConfig(level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S")
log = logging.getLogger(__name__)
DATA_DIR.mkdir(exist_ok=True)


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
            council_ref   TEXT NOT NULL,
            scraped_at    TEXT NOT NULL,
            mode          TEXT,
            records_found INTEGER,
            success       INTEGER,
            error         TEXT,
            PRIMARY KEY (council_ref, scraped_at)
        );
    """)
    conn.commit()

def was_recently_scraped(conn, council_ref: str, within_hours: int = 20) -> bool:
    """Check if this council was successfully scraped within the last N hours."""
    cutoff = (datetime.now() - timedelta(hours=within_hours)).isoformat()
    row = conn.execute("""
        SELECT scraped_at FROM scrape_log
        WHERE council_ref = ? AND success = 1 AND scraped_at > ?
        ORDER BY scraped_at DESC LIMIT 1
    """, (council_ref, cutoff)).fetchone()
    return row is not None


# ── Geocoding ─────────────────────────────────────────────────────────────────

_postcode_cache = {}

def geocode_postcode(postcode: str):
    import requests
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

def extract_postcode(address: str) -> str:
    if not address:
        return ""
    m = re.search(r'\b([A-Z]{1,2}\d{1,2}[A-Z]?\s*\d[A-Z]{2})\b', address.upper())
    return m.group(1) if m else ""


# ── Mechanize browser factory ─────────────────────────────────────────────────

def make_browser() -> mechanize.Browser:
    """Create a mechanize browser configured to behave like a real browser."""
    br = mechanize.Browser()
    cj = http.cookiejar.LWPCookieJar()
    br.set_cookiejar(cj)

    br.set_handle_equiv(True)
    br.set_handle_redirect(True)
    br.set_handle_referer(True)
    br.set_handle_robots(False)   # ignore robots.txt
    br.set_handle_refresh(mechanize._http.HTTPRefreshProcessor(), max_time=1)

    br.addheaders = [
        ("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/124.0.0.0 Safari/537.36"),
        ("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"),
        ("Accept-Language", "en-GB,en;q=0.9"),
    ]
    return br


# ── Idox scraper ──────────────────────────────────────────────────────────────

class IdoxScraper:
    """
    Scrapes an Idox PublicAccess portal using mechanize for proper
    form submission. Handles pagination to get all results.
    """

    def __init__(self, portal_url: str, council_ref: str, council_name: str):
        self.portal_url  = portal_url.rstrip("/")
        self.council_ref = council_ref
        self.council_name = council_name
        self.base        = self._find_base()
        self.search_url  = f"{self.base}/search.do"

    def _find_base(self) -> str:
        parsed = urlparse(self.portal_url)
        path = parsed.path
        if "/online-applications" in path:
            idx = path.index("/online-applications")
            base_path = path[:idx + len("/online-applications")]
        else:
            base_path = path.rstrip("/")
        return f"{parsed.scheme}://{parsed.netloc}{base_path}"

    def scrape(self, date_from: str, date_to: str) -> list[dict]:
        """
        Scrape all applications validated between date_from and date_to.
        Dates in DD/MM/YYYY format.
        Returns list of application dicts.
        """
        br = make_browser()
        all_apps = []

        try:
            # Step 1: open the advanced search page
            log.info(f"  Opening search page...")
            br.open(f"{self.search_url}?action=advanced", timeout=20)

            # Step 2: select the form and fill it in
            br.select_form(nr=0)  # first form on page

            # Fill in date fields
            br["date(applicationValidatedStart)"] = date_from
            br["date(applicationValidatedEnd)"]   = date_to

            # Leave everything else blank (search all application types)
            # Clear any pre-filled fields
            try: br["searchCriteria.reference"] = ""
            except: pass
            try: br["searchCriteria.description"] = ""
            except: pass
            try: br["searchCriteria.address"] = ""
            except: pass
            try: br["searchCriteria.applicantName"] = ""
            except: pass

            log.info(f"  Submitting search ({date_from} → {date_to})...")

            # Step 3: submit the form (click Search, not Reset)
            response = br.submit()
            html = response.read().decode("utf-8", errors="replace")

            # Check if we got results
            if "searchresult" not in html.lower():
                log.info(f"  No results found")
                return []

            # Parse first page
            page_apps = self._parse_page(html)
            all_apps.extend(page_apps)
            log.info(f"  Page 1: {len(page_apps)} applications")

            # Step 4: handle pagination
            page_num = 2
            while True:
                next_link = self._find_next_link(html)
                if not next_link:
                    break
                time.sleep(PAGE_DELAY)
                try:
                    next_url = next_link if next_link.startswith("http") else \
                               f"{self.base}/{next_link.lstrip('/')}"
                    resp = br.open(next_url, timeout=20)
                    html = resp.read().decode("utf-8", errors="replace")
                    page_apps = self._parse_page(html)
                    if not page_apps:
                        break
                    all_apps.extend(page_apps)
                    log.info(f"  Page {page_num}: {len(page_apps)} applications")
                    page_num += 1
                except Exception as e:
                    log.warning(f"  Pagination error: {e}")
                    break

        except mechanize.FormNotFoundError:
            log.warning(f"  Form not found on search page")
        except Exception as e:
            log.warning(f"  Scrape error: {e}")

        return all_apps

    def _find_next_link(self, html: str) -> str | None:
        """Find the 'Next' pagination link in Idox results."""
        soup = BeautifulSoup(html, "html.parser")
        # Idox pagination: <a class="next">Next</a> or similar
        for link in soup.find_all("a"):
            text = link.get_text(strip=True).lower()
            if text in ("next", "next page", "›", "»"):
                href = link.get("href", "")
                if href and href != "#":
                    return href
        # Also try: <a href="...&page=2">
        next_match = re.search(
            r'<a[^>]+href="([^"]*searchResults[^"]*)"[^>]*>\s*(?:Next|next)\s*</a>',
            html, re.IGNORECASE
        )
        return next_match.group(1) if next_match else None

    def _parse_page(self, html: str) -> list[dict]:
        """Parse all applications from a results page."""
        soup = BeautifulSoup(html, "html.parser")
        apps = []

        # Idox results: <li class="searchresult">
        results = soup.find_all("li", class_=re.compile(r"searchresult", re.I))

        for item in results:
            app = self._parse_item(item)
            if app:
                apps.append(app)

        return apps

    def _parse_item(self, item) -> dict | None:
        """Parse a single search result <li> element."""
        # Get the application link — contains keyVal
        link = item.find("a", href=re.compile(r"keyVal=", re.I))
        if not link:
            return None

        href    = link.get("href", "")
        key_match = re.search(r"keyVal=([^&\"]+)", href)
        if not key_match:
            return None
        key_val = key_match.group(1)

        application_url = f"{self.base}/applicationDetails.do?activeTab=summary&keyVal={key_val}"

        # Reference number — usually the link text or a span.caseNo
        ref_span = item.find(class_=re.compile(r"caseNo|reference", re.I))
        reference = ref_span.get_text(strip=True) if ref_span else link.get_text(strip=True)

        # Address
        addr_el = item.find(class_=re.compile(r"address", re.I))
        address = addr_el.get_text(strip=True) if addr_el else ""

        # Description / proposal
        desc_el = item.find(class_=re.compile(r"proposal|description", re.I))
        description = desc_el.get_text(strip=True) if desc_el else ""

        # Status
        status_el = item.find(class_=re.compile(r"status", re.I))
        status = status_el.get_text(strip=True) if status_el else ""

        # Dates — look for "Received: DD/MM/YYYY" style text
        item_text = item.get_text()
        dates = re.findall(
            r'(Received|Validated|Decided)\s*:?\s*(\d{1,2}/\d{2}/\d{4})',
            item_text, re.IGNORECASE
        )
        date_map = {k.lower(): v for k, v in dates}

        if not reference:
            return None

        # Postcode + geocode
        postcode = extract_postcode(address)
        lat, lng = None, None
        if postcode:
            lat, lng = geocode_postcode(postcode)
            time.sleep(0.1)

        # App type from reference suffix (e.g. /FUL, /HOU, /LBC)
        app_type = ""
        m = re.search(r'/([A-Z]{2,5})$', reference)
        if m:
            app_type = m.group(1)

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
            "application_url": application_url,
            "scraped_at":      datetime.now().isoformat(),
        }


# ── Date range chunking ───────────────────────────────────────────────────────

def date_chunks(days_back: int, chunk_days: int = 180) -> list[tuple[str, str]]:
    """
    Split a date range into chunks to avoid Idox result limits.
    Idox caps results at ~1000 per search, so we chunk into 6-month windows.
    Returns list of (date_from, date_to) tuples in DD/MM/YYYY format.
    """
    chunks = []
    end   = datetime.now()
    start = end - timedelta(days=days_back)
    current = start
    while current < end:
        chunk_end = min(current + timedelta(days=chunk_days), end)
        chunks.append((
            current.strftime("%d/%m/%Y"),
            chunk_end.strftime("%d/%m/%Y")
        ))
        current = chunk_end + timedelta(days=1)
    return chunks


# ── Storage ───────────────────────────────────────────────────────────────────

def save_applications(conn, apps: list[dict]) -> int:
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
        INSERT OR REPLACE INTO scrape_log
        (council_ref, scraped_at, mode, records_found, success, error)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (ref, datetime.now().isoformat(), mode, records, int(success), error))
    conn.commit()


# ── Council scrape orchestration ──────────────────────────────────────────────

def scrape_council(council: dict, conn, days_back: int, mode: str) -> int:
    ref  = council["reference"]
    name = council["name"].replace(" LPA", "")
    url  = council["portal_url"]

    log.info(f"Scraping: {name} ({ref})")
    log.info(f"  Portal: {url}")
    log.info(f"  Mode: {mode} | Days back: {days_back}")

    scraper = IdoxScraper(url, ref, name)
    total_saved = 0

    # Chunk large date ranges to avoid Idox's result cap
    chunks = date_chunks(days_back, chunk_days=180)
    log.info(f"  Date chunks: {len(chunks)}")

    try:
        for i, (date_from, date_to) in enumerate(chunks, 1):
            log.info(f"  Chunk {i}/{len(chunks)}: {date_from} → {date_to}")
            apps = scraper.scrape(date_from, date_to)
            saved = save_applications(conn, apps)
            total_saved += saved
            log.info(f"  Chunk {i}: {len(apps)} found, {saved} saved")
            if i < len(chunks):
                time.sleep(DELAY)

        log_scrape(conn, ref, mode, total_saved, True)
        log.info(f"  ✓ Total saved: {total_saved}")
        return total_saved

    except Exception as e:
        log.error(f"  ✗ Failed: {e}")
        log_scrape(conn, ref, mode, total_saved, False, str(e))
        return total_saved


# ── Utilities ─────────────────────────────────────────────────────────────────

def load_councils(path: Path) -> list[dict]:
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
    log.info(f"Exported {len(rows):,} rows to {csv_path} and {json_path}")


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="StreetPeek Idox Scraper")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--full",    action="store_true",
                       help="First-time full history scrape (5 years)")
    group.add_argument("--update",  action="store_true",
                       help="Weekly update — last 30 days only")
    group.add_argument("--test",    action="store_true",
                       help="Test 3 councils, last 90 days")
    group.add_argument("--council", metavar="REF",
                       help="Single council by reference e.g. E60000309")
    group.add_argument("--export",  action="store_true",
                       help="Export DB to CSV and JSON")
    group.add_argument("--stats",   action="store_true",
                       help="Show database stats")
    parser.add_argument("--days", type=int, default=None,
                        help="Override days back (default: 1825 for --full, 30 for --update)")
    args = parser.parse_args()

    conn = sqlite3.connect(DB_PATH)
    init_db(conn)

    if args.stats:
        print_stats(conn)
        conn.close()
        return

    if args.export:
        export(conn)
        print_stats(conn)
        conn.close()
        return

    if not COUNCILS_JSON.exists():
        log.error(f"Councils file not found: {COUNCILS_JSON}")
        conn.close()
        return

    councils = load_councils(COUNCILS_JSON)
    log.info(f"Loaded {len(councils)} Idox councils")

    if args.test:
        days_back = args.days or 90
        mode = "test"
        test_refs = {"E60000309", "E60000195", "E60000071"}  # Cotswold, Lambeth, Leeds
        targets = [c for c in councils if c["reference"] in test_refs] or councils[:3]
        log.info(f"Test mode: {len(targets)} councils, {days_back} days back")
        for c in targets:
            scrape_council(c, conn, days_back, mode)
            time.sleep(DELAY)

    elif args.update:
        days_back = args.days or 30
        mode = "update"
        log.info(f"Update mode: {len(councils)} councils, last {days_back} days")
        log.info(f"Estimated time: {len(councils) * DELAY / 60:.0f}+ minutes")
        for i, c in enumerate(councils, 1):
            log.info(f"[{i}/{len(councils)}]")
            # Skip if scraped very recently (within 20 hours) to allow re-runs
            if was_recently_scraped(conn, c["reference"], within_hours=20):
                log.info(f"  Skipping — scraped recently")
                continue
            scrape_council(c, conn, days_back, mode)
            time.sleep(DELAY)

    elif args.full:
        days_back = args.days or 1825  # 5 years
        mode = "full"
        log.info(f"Full scrape: {len(councils)} councils, {days_back} days back ({days_back//365} years)")
        log.info(f"This will take many hours — safe to Ctrl+C and resume")
        for i, c in enumerate(councils, 1):
            log.info(f"[{i}/{len(councils)}]")
            # Skip councils already fully scraped
            already = conn.execute(
                "SELECT COUNT(*) FROM scrape_log WHERE council_ref=? AND mode='full' AND success=1",
                (c["reference"],)
            ).fetchone()[0]
            if already:
                log.info(f"  Skipping — full scrape already done")
                continue
            scrape_council(c, conn, days_back, mode)
            time.sleep(DELAY)

    elif args.council:
        days_back = args.days or 90
        matches = [c for c in councils if c["reference"] == args.council]
        if not matches:
            log.error(f"Council {args.council} not found or not Idox")
            conn.close()
            return
        scrape_council(matches[0], conn, days_back, "manual")

    print_stats(conn)
    conn.close()


if __name__ == "__main__":
    main()
