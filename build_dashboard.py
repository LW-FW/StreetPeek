"""
StreetPeek — Internal data-sources dashboard builder
=======================================================
Pulls together everything that answers "is our data current and correct":

  - Council planning portals   <- streetpeek/output/councils_final.json
                                   + data/planning.db (scrape_log, actual
                                     applications collected)
                                   + data/portal_health.json / latest report
                                     in data/portal_health_reports/
  - Education pipeline          <- data/education_manifest.json (written by
                                   education_scraper.py — absent until that's
                                   been run at least once)
  - Live third-party APIs       <- data/source_health.json (written by
                                   check_live_sources.py)

...and renders it into a single self-contained local HTML file. No server,
no external requests, no build step — just open dashboard.html in a browser.
Never published anywhere; this is a personal ops view, not part of the app.

Run this AFTER running (in whatever order):
    venv/Scripts/python.exe portal_healthcheck.py
    venv/Scripts/python.exe check_live_sources.py
    venv/Scripts/python.exe education_scraper.py   (once it's ever been run)

Then:
    venv/Scripts/python.exe build_dashboard.py
"""

import html
import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

COUNCILS_JSON = Path("streetpeek/output/councils_final.json")
DB_PATH = Path("data/planning.db")
PORTAL_HEALTH = Path("data/portal_health.json")
REPORT_DIR = Path("data/portal_health_reports")
EDU_MANIFEST = Path("data/education_manifest.json")
SOURCE_HEALTH = Path("data/source_health.json")
OUT_PATH = Path("dashboard.html")


def load_json(path, default=None):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def latest_report():
    if not REPORT_DIR.exists():
        return None
    reports = sorted(REPORT_DIR.glob("*.json"))
    return load_json(reports[-1]) if reports else None


def scrape_log_by_council():
    if not DB_PATH.exists():
        return {}, {}
    conn = sqlite3.connect(DB_PATH)
    latest = {}
    for ref, ts, success, records, error in conn.execute(
            "SELECT council_ref, scraped_at, success, records_found, error "
            "FROM scrape_log ORDER BY scraped_at"):
        latest[ref] = {"last_attempt": ts, "success": bool(success),
                        "records_found": records, "error": error}
    ever_ok = {r[0] for r in conn.execute(
        "SELECT DISTINCT council_ref FROM scrape_log WHERE success=1")}
    counts = dict(conn.execute(
        "SELECT council_ref, COUNT(*) FROM planning_applications GROUP BY council_ref"))
    conn.close()
    for ref in latest:
        latest[ref]["ever_succeeded"] = ref in ever_ok
        latest[ref]["applications_collected"] = counts.get(ref, 0)
    return latest


def fmt_ts(ts):
    if not ts:
        return "never"
    try:
        dt = datetime.fromisoformat(ts.split(" [")[0])
        return dt.strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return ts


def esc(s):
    return html.escape(str(s), quote=True)


def build_councils_rows(councils, scrape_log, portal_health, report):
    needs_review_by_ref = {}
    if report:
        for n in report.get("needs_review", []):
            needs_review_by_ref[n["reference"]] = n

    rows = []
    for c in councils:
        ref = c["reference"]
        ph = portal_health.get(ref, {})
        sl = scrape_log.get(ref, {})
        portal_status = ph.get("status", "unknown")
        portal_checked = ph.get("checked_at")
        note = ""
        if portal_status == "broken" and ref in needs_review_by_ref:
            note = needs_review_by_ref[ref].get("candidate_note", "")
        scrape_status = ("success" if sl.get("ever_succeeded") else
                          ("attempted" if sl else "never run"))
        rows.append({
            "reference": ref, "name": c["name"], "portal_url": c["portal_url"],
            "portal_status": portal_status, "portal_checked": portal_checked,
            "scrape_status": scrape_status,
            "scrape_last_attempt": sl.get("last_attempt"),
            "scrape_error": sl.get("error") if not sl.get("success") else "",
            "applications_collected": sl.get("applications_collected", 0),
            "note": note,
        })
    return rows


STATUS_COLORS = {
    "ok": "#2e7d46", "success": "#2e7d46",
    "stale": "#a06a00", "attempted": "#a06a00",
    "broken": "#b3372c", "never run": "#5a5a5a", "unknown": "#5a5a5a",
}


def status_pill(label):
    color = STATUS_COLORS.get(label, "#5a5a5a")
    return f'<span class="pill" style="--pill-color:{color}">{esc(label)}</span>'


def render_councils_table(rows):
    body_rows = []
    for r in rows:
        body_rows.append(f"""
        <tr data-name="{esc(r['name'].lower())}" data-portal="{esc(r['portal_status'])}" data-scrape="{esc(r['scrape_status'])}">
          <td>{esc(r['name'])}</td>
          <td class="ref">{esc(r['reference'])}</td>
          <td>{status_pill(r['portal_status'])}</td>
          <td class="ts">{esc(fmt_ts(r['portal_checked']))}</td>
          <td>{status_pill(r['scrape_status'])}</td>
          <td class="ts">{esc(fmt_ts(r['scrape_last_attempt']))}</td>
          <td class="num">{r['applications_collected']}</td>
          <td class="note">{esc(r['note'] or r['scrape_error'] or '')}</td>
        </tr>""")
    return "".join(body_rows)


def render_live_sources(source_health):
    if not source_health:
        return '<p class="empty">Never checked — run <code>check_live_sources.py</code>.</p>'
    rows = []
    for s in source_health:
        status = "ok" if s["ok"] else "broken"
        rows.append(f"""
        <tr>
          <td>{esc(s['name'])}</td>
          <td>{esc(s['category'])}</td>
          <td>{status_pill(status)}</td>
          <td class="ts">{esc(fmt_ts(s['checked_at']))}</td>
          <td class="note">{esc(s['detail'])}</td>
        </tr>""")
    return f"""
    <table>
      <thead><tr><th>Source</th><th>Category</th><th>Status</th><th>Last checked</th><th>Detail</th></tr></thead>
      <tbody>{''.join(rows)}</tbody>
    </table>"""


def render_education(manifest):
    if not manifest:
        return '<p class="empty">Pipeline has never been run — no data/schools.json or data/nurseries.json yet. Run <code>education_scraper.py</code>.</p>'
    rows = [
        ("Schools register (GIAS)", manifest["sources"]["gias"]),
        ("Ofsted school ratings", manifest["sources"]["ofstedSchools"]),
        ("Ofsted childcare ratings", manifest["sources"]["ofstedChildcare"]),
        ("Postcode lookup (ONS NSPL)", manifest["sources"]["nspl"]),
    ]
    body = "".join(f"""
        <tr>
          <td>{esc(label)}</td>
          <td class="note" style="max-width:420px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{esc(src)}</td>
        </tr>""" for label, src in rows)
    return f"""
    <p><b>{manifest['schoolsCount']}</b> schools, <b>{manifest['nurseriesCount']}</b> nurseries — last built
       <b>{esc(fmt_ts(manifest['generatedAt']))}</b>. Recommended cadence: {esc(manifest.get('refreshCadence',''))}</p>
    <table>
      <thead><tr><th>Sub-source</th><th>URL / file used</th></tr></thead>
      <tbody>{body}</tbody>
    </table>"""


def main():
    councils = load_json(COUNCILS_JSON, [])
    idox = [c for c in councils if c["platform"] == "Idox/PublicAccess"]
    scrape_log = scrape_log_by_council()
    portal_health = load_json(PORTAL_HEALTH, {})
    report = latest_report()
    source_health = load_json(SOURCE_HEALTH, [])
    edu_manifest = load_json(EDU_MANIFEST, None)

    rows = build_councils_rows(idox, scrape_log, portal_health, report)

    n_portal_ok = sum(1 for r in rows if r["portal_status"] == "ok")
    n_scrape_ok = sum(1 for r in rows if r["scrape_status"] == "success")
    n_live_ok = sum(1 for s in source_health if s["ok"])
    report_time = report["run_at"] if report else None

    html_out = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>StreetPeek — Data Sources</title>
<style>
  :root {{
    --bg: #14161a; --panel: #1c1f24; --border: #2c3038; --text: #e6e8eb;
    --text-dim: #9099a3; --mono: 'Consolas','SFMono-Regular',monospace;
  }}
  * {{ box-sizing: border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--text); font-family:-apple-system,Segoe UI,Arial,sans-serif; }}
  header {{ padding:28px 32px 18px; border-bottom:1px solid var(--border); }}
  header h1 {{ margin:0 0 4px; font-size:22px; font-weight:600; }}
  header p {{ margin:0; color:var(--text-dim); font-size:13px; }}
  .badge-private {{ display:inline-block; background:#3a2a10; color:#e0a94a; border:1px solid #5a3f18;
    border-radius:4px; padding:2px 8px; font-size:11px; margin-left:10px; vertical-align:2px; }}
  main {{ padding:24px 32px 60px; max-width:1400px; margin:0 auto; }}
  .cards {{ display:flex; gap:16px; margin-bottom:32px; flex-wrap:wrap; }}
  .card {{ background:var(--panel); border:1px solid var(--border); border-radius:8px; padding:16px 20px; min-width:180px; }}
  .card .num {{ font-size:26px; font-weight:600; }}
  .card .label {{ color:var(--text-dim); font-size:12px; margin-top:4px; }}
  section {{ margin-bottom:40px; }}
  section h2 {{ font-size:16px; margin:0 0 4px; }}
  section .sub {{ color:var(--text-dim); font-size:12px; margin-bottom:14px; }}
  table {{ width:100%; border-collapse:collapse; background:var(--panel); border:1px solid var(--border); border-radius:8px; overflow:hidden; font-size:13px; }}
  th {{ text-align:left; padding:10px 12px; background:#22262c; color:var(--text-dim); font-weight:500; font-size:11px; text-transform:uppercase; letter-spacing:.03em; cursor:pointer; user-select:none; }}
  th:hover {{ color:var(--text); }}
  td {{ padding:8px 12px; border-top:1px solid var(--border); vertical-align:top; }}
  td.ref, td.ts {{ font-family:var(--mono); color:var(--text-dim); white-space:nowrap; font-size:12px; }}
  td.num {{ font-family:var(--mono); text-align:right; }}
  td.note {{ color:var(--text-dim); font-size:12px; max-width:380px; }}
  .pill {{ display:inline-block; padding:2px 9px; border-radius:999px; font-size:11px; font-weight:600;
    color:var(--pill-color); background:color-mix(in srgb, var(--pill-color) 18%, transparent);
    border:1px solid color-mix(in srgb, var(--pill-color) 45%, transparent); }}
  .controls {{ display:flex; gap:10px; margin-bottom:12px; }}
  input[type=text] {{ background:var(--panel); border:1px solid var(--border); color:var(--text);
    padding:7px 12px; border-radius:6px; font-size:13px; width:260px; }}
  select {{ background:var(--panel); border:1px solid var(--border); color:var(--text); padding:7px 10px; border-radius:6px; font-size:13px; }}
  .empty {{ color:var(--text-dim); font-size:13px; }}
  code {{ background:#22262c; padding:1px 5px; border-radius:3px; font-size:12px; }}
  .scroll {{ max-height:640px; overflow:auto; border-radius:8px; }}
  .scroll table {{ border-radius:0; }}
  .scroll thead th {{ position:sticky; top:0; z-index:1; }}
  footer {{ padding:20px 32px; color:var(--text-dim); font-size:11px; border-top:1px solid var(--border); }}
</style>
</head>
<body>
<header>
  <h1>StreetPeek Data Sources<span class="badge-private">private — local file only</span></h1>
  <p>Generated {esc(fmt_ts(datetime.now().isoformat()))} · re-run <code>build_dashboard.py</code> after any health check to refresh</p>
</header>
<main>

  <div class="cards">
    <div class="card"><div class="num">{n_portal_ok}/{len(rows)}</div><div class="label">council portals reachable &amp; fresh</div></div>
    <div class="card"><div class="num">{n_scrape_ok}/{len(rows)}</div><div class="label">councils with data ever collected</div></div>
    <div class="card"><div class="num">{n_live_ok}/{len(source_health) or '?'}</div><div class="label">live API sources healthy</div></div>
    <div class="card"><div class="num">{esc(fmt_ts(report_time)) if report_time else 'never'}</div><div class="label">last portal health check</div></div>
  </div>

  <section>
    <h2>Council planning portals</h2>
    <p class="sub">Portal status = is the URL itself reachable and showing fresh (current-month) data right now. Scrape status = have we ever actually pulled application data from it into planning.db.</p>
    <div class="controls">
      <input type="text" id="search" placeholder="Filter by council name...">
      <select id="portalFilter">
        <option value="">All portal statuses</option>
        <option value="ok">OK</option>
        <option value="stale">Stale</option>
        <option value="broken">Broken</option>
        <option value="unknown">Unknown</option>
      </select>
      <select id="scrapeFilter">
        <option value="">All scrape statuses</option>
        <option value="success">Success</option>
        <option value="attempted">Attempted, never succeeded</option>
        <option value="never run">Never run</option>
      </select>
    </div>
    <div class="scroll">
    <table id="councilsTable">
      <thead><tr>
        <th data-sort="text">Council</th>
        <th data-sort="text">Ref</th>
        <th data-sort="text">Portal status</th>
        <th data-sort="text">Portal last checked</th>
        <th data-sort="text">Scrape status</th>
        <th data-sort="text">Scrape last attempt</th>
        <th data-sort="num">Applications</th>
        <th>Note</th>
      </tr></thead>
      <tbody>{render_councils_table(rows)}</tbody>
    </table>
    </div>
  </section>

  <section>
    <h2>Live external APIs</h2>
    <p class="sub">Called fresh per user search — nothing cached, so "last checked" is the last time this was confirmed still working. Run <code>check_live_sources.py</code> to refresh.</p>
    {render_live_sources(source_health)}
  </section>

  <section>
    <h2>Schools &amp; nurseries pipeline</h2>
    <p class="sub">Local dataset built from GIAS + Ofsted + ONS NSPL. The live app currently calls GIAS directly instead (see live APIs above) — this section tracks the not-yet-wired-up local pipeline.</p>
    {render_education(edu_manifest)}
  </section>

</main>
<footer>Generated locally by build_dashboard.py — reads streetpeek/output/councils_final.json, data/planning.db, data/portal_health.json, data/portal_health_reports/, data/source_health.json, data/education_manifest.json. Nothing on this page is fetched live or sent anywhere.</footer>

<script>
  const search = document.getElementById('search');
  const portalFilter = document.getElementById('portalFilter');
  const scrapeFilter = document.getElementById('scrapeFilter');
  const rows = Array.from(document.querySelectorAll('#councilsTable tbody tr'));

  function applyFilters() {{
    const q = search.value.toLowerCase();
    const pf = portalFilter.value;
    const sf = scrapeFilter.value;
    rows.forEach(r => {{
      const matches = r.dataset.name.includes(q)
        && (!pf || r.dataset.portal === pf)
        && (!sf || r.dataset.scrape === sf);
      r.style.display = matches ? '' : 'none';
    }});
  }}
  search.addEventListener('input', applyFilters);
  portalFilter.addEventListener('change', applyFilters);
  scrapeFilter.addEventListener('change', applyFilters);

  document.querySelectorAll('#councilsTable th[data-sort]').forEach((th, idx) => {{
    let asc = true;
    th.addEventListener('click', () => {{
      const type = th.dataset.sort;
      const tbody = document.querySelector('#councilsTable tbody');
      const sorted = rows.slice().sort((a, b) => {{
        const av = a.children[idx].innerText.trim();
        const bv = b.children[idx].innerText.trim();
        const cmp = type === 'num' ? (parseFloat(av)||0) - (parseFloat(bv)||0) : av.localeCompare(bv);
        return asc ? cmp : -cmp;
      }});
      asc = !asc;
      sorted.forEach(r => tbody.appendChild(r));
    }});
  }});
</script>
</body>
</html>"""

    OUT_PATH.write_text(html_out, encoding="utf-8")
    print(f"Wrote {OUT_PATH} ({len(rows)} councils, {len(source_health)} live sources)")


if __name__ == "__main__":
    main()
