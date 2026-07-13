"""
StreetPeek — Apply re-discovered portal URLs & platform changes
================================================================
Applies the results of the 2026-07-12 failure diagnosis + re-discovery pass
(data/failure_diagnosis.json, data/rediscovered_portals.json,
data/verified_candidates.json) to streetpeek/output/councils_final.json/.csv.

Three kinds of change:
  1. URL_UPDATES     — still Idox, portal moved (all verified live, newest
                       month = Jul 26, except Rochdale which was 503/maintenance
                       but is the URL the council officially links)
  2. PLATFORM_CHANGES — council left Idox for another system
  3. DEFUNCT          — council abolished in 2021/2023 reorganisations;
                        successor council is already in the file

Backs up both files with a .bak-20260712 suffix before writing.
Run: venv/Scripts/python.exe update_councils.py
"""

import csv
import json
import shutil
from datetime import datetime
from pathlib import Path

JSON_PATH = Path("streetpeek/output/councils_final.json")
CSV_PATH  = Path("streetpeek/output/councils_final.csv")
STAMP     = datetime.now().isoformat(timespec="seconds")

# ── 1. Still Idox — portal URL moved ─────────────────────────────────────────
URL_UPDATES = {
    "E60000007": "https://www.developmentmanagement.stockton.gov.uk/online-applications/",  # Stockton-on-Tees
    "E60000010": "https://idoxpublicaccess.northtyneside.gov.uk/online-applications/",      # North Tyneside
    "E60000025": "https://paplanning.bolton.gov.uk/online-applications/",                   # Bolton
    "E60000028": "https://planningpa.oldham.gov.uk/online-applications/",                   # Oldham
    "E60000029": "https://publicaccess.rochdale.gov.uk/online-applications/",               # Rochdale (503 at check time — maintenance)
    "E60000040": "https://publicaccess.pendle.gov.uk/online-applications/",                 # Pendle
    "E60000044": "https://publicaccess.southribble.gov.uk/online-applications/",            # South Ribble
    "E60000047": "https://planapp.knowsley.gov.uk/online-applications/",                    # Knowsley
    "E60000054": "https://planninganddevelopment.nelincs.gov.uk/online-applications/",      # North East Lincolnshire
    "E60000056": "https://planningaccess.york.gov.uk/online-applications/",                 # York
    "E60000067": "https://planningapps.sheffield.gov.uk/online-applications/",              # Sheffield
    "E60000069": "https://portal.calderdale.gov.uk/online-applications/",                   # Calderdale
    "E60000075": "https://publicaccess.nottinghamcity.gov.uk/online-applications/",         # Nottingham
    "E60000083": "https://planapps-online.ne-derbyshire.gov.uk/online-applications/",       # North East Derbyshire
    "E60000087": "https://pa2.harborough.gov.uk/online-applications/",                      # Harborough
    "E60000089": "https://pa.melton.gov.uk/online-applications/",                           # Melton
    "E60000090": "https://plans.nwleics.gov.uk/public-access/",                             # North West Leicestershire
    "E60000091": "https://pa.oadby-wigston.gov.uk/online-applications/",                    # Oadby and Wigston
    "E60000093": "https://publicaccess.e-lindsey.gov.uk/online-applications/",              # East Lindsey
    "E60000095": "https://planningonline.n-kesteven.gov.uk/online-applications/",           # North Kesteven
    "E60000332": "https://publicaccess.northnorthants.gov.uk/online-applications/",         # North Northamptonshire
    "E60000336": "https://publicaccess.northyorks.gov.uk/online-applications/",             # North Yorkshire
}

# ── 2. Left Idox — platform changed ──────────────────────────────────────────
# reference: (new portal_url, new platform)
PLATFORM_CHANGES = {
    "E60000003": ("https://planning.hartlepool.gov.uk/portal/servlets/ApplicationSearchServlet", "Unknown/Custom"),          # Hartlepool
    "E60000004": ("https://planning.agileapplications.co.uk/middlesbrough", "iApply/Agile"),                                 # Middlesbrough
    "E60000006": ("https://planning.redcar-cleveland.gov.uk/", "Unknown/Custom"),                                            # Redcar and Cleveland
    "E60000009": ("https://www.newcastle.gov.uk/services/planning-building-and-development/search-view-and-comment-planning-applications", "Unknown/Custom"),  # Newcastle (map-based system)
    "E60000011": ("https://planning.southtyneside.info/Northgate/PlanningExplorer/ApplicationSearch.aspx", "Northgate/MasterGov"),  # South Tyneside
    "E60000013": ("https://planning.blackburn.gov.uk/Northgate/PlanningExplorer/ApplicationSearch.aspx", "Northgate/MasterGov"),    # Blackburn with Darwen
    "E60000018": ("https://online.warrington.gov.uk/planning/", "Unknown/Custom"),                                           # Warrington
    "E60000030": ("https://salfordcitycouncil.my.site.com/pr/s/", "Arcus/Salesforce"),                                       # Salford (legacy Idox 502s)
    "E60000038": ("https://planning.hyndburnbc.gov.uk/Northgate/ES/Presentation/Planning/OnlinePlanning/OnlinePlanningSearch", "Northgate/MasterGov"),  # Hyndburn
    "E60000041": ("https://selfservice.preston.gov.uk/service/planning/ApplicationSearch.aspx", "Unknown/Custom"),           # Preston
    "E60000042": ("https://webportal.ribblevalley.gov.uk/", "Unknown/Custom"),                                               # Ribble Valley
    "E60000048": ("https://liverpool.gov.uk/planning-and-building-control/search-and-track-planning-applications/", "Unknown/Custom"),  # Liverpool (LAR system)
    "E60000064": ("https://planningexplorer.barnsley.gov.uk/", "Unknown/Custom"),                                            # Barnsley
    "E60000066": ("https://planning.rotherham.gov.uk/", "Unknown/Custom"),                                                   # Rotherham (FastWeb)
    "E60000070": ("https://www.kirklees.gov.uk/beta/planning-applications/search-for-planning-applications/default.aspx", "Unknown/Custom"),  # Kirklees
    "E60000074": ("https://planning.leicester.gov.uk/", "Unknown/Custom"),                                                   # Leicester
    "E60000077": ("https://www.ambervalley.gov.uk/planning/development-management/view-a-planning-application/", "Unknown/Custom"),  # Amber Valley
    "E60000081": ("https://myservice.erewash.gov.uk/Planning/lg/plansearch.page", "Unknown/Custom"),                         # Erewash
    "E60000082": ("https://planning.highpeak.gov.uk/portal/servlets/ApplicationSearchServlet", "Unknown/Custom"),            # High Peak
    "E60000084": ("https://planning.southderbyshire.gov.uk/", "Unknown/Custom"),                                             # South Derbyshire
    "E60000096": ("https://planning.sholland.gov.uk/OcellaWeb/planningSearch", "Civica/OcellaWeb"),                          # South Holland
    "E60000098": ("https://www.west-lindsey.gov.uk/planning-building-control/planning/view-search-planning-applications", "Unknown/Custom"),  # West Lindsey
    "E60000333": ("https://wnc.planning-register.co.uk/", "Unknown/Custom"),                                                 # West Northamptonshire (Planning Register)
    "E60000334": ("https://cumberlandcouncil.my.site.com/pr/s/", "Arcus/Salesforce"),                                        # Cumberland
    "E60000335": ("https://planningregister.westmorlandandfurness.gov.uk/", "Unknown/Custom"),                               # Westmorland and Furness (Planning Register)
}

# ── 3. Abolished councils → successor already in file ────────────────────────
DEFUNCT = {
    "E60000019": "E60000334",  # Allerdale        → Cumberland
    "E60000022": "E60000334",  # Copeland         → Cumberland
    "E60000020": "E60000335",  # Barrow-in-Furness → Westmorland & Furness
    "E60000023": "E60000335",  # Eden             → Westmorland & Furness
    "E60000024": "E60000335",  # South Lakeland   → Westmorland & Furness
    "E60000058": "E60000336",  # Hambleton        → North Yorkshire
    "E60000059": "E60000336",  # Harrogate        → North Yorkshire
    "E60000061": "E60000336",  # Ryedale          → North Yorkshire
    "E60000099": "E60000332",  # Corby            → North Northamptonshire
    "E60000101": "E60000332",  # East Northants   → North Northamptonshire
    "E60000102": "E60000332",  # Kettering        → North Northamptonshire
    "E60000100": "E60000333",  # Daventry         → West Northamptonshire
    "E60000103": "E60000333",  # Northampton      → West Northamptonshire
}

# Still Idox but portal currently unreachable from this network — flagged only
UNRESOLVED = {
    "E60000037": "Fylde — portal host not found (www3.fylde.gov.uk dead, pa.fylde.gov.uk 404)",
    "E60000051": "Wirral — planning.wirral.gov.uk correct per council site but times out",
    "E60000092": "Boston — no current portal URL found (shares PSPS services with E. Lindsey / S. Holland)",
}


def main():
    rows = json.loads(JSON_PATH.read_text())

    # Backups
    for p in (JSON_PATH, CSV_PATH):
        bak = p.with_suffix(p.suffix + ".bak-20260712")
        if not bak.exists():
            shutil.copy2(p, bak)
            print(f"Backup: {bak}")

    n_url = n_plat = n_def = n_flag = 0
    by_ref = {r["reference"]: r for r in rows}

    for ref, url in URL_UPDATES.items():
        r = by_ref[ref]
        r["portal_url"] = url
        r["platform"] = "Idox/PublicAccess"
        r["scanned_at"] = f"{STAMP} [rediscovered]"
        n_url += 1

    for ref, (url, platform) in PLATFORM_CHANGES.items():
        r = by_ref[ref]
        r["portal_url"] = url
        r["platform"] = platform
        r["scanned_at"] = f"{STAMP} [platform-changed]"
        n_plat += 1

    for ref, successor in DEFUNCT.items():
        r = by_ref[ref]
        succ_name = by_ref[successor]["name"].replace(" LPA", "")
        r["platform"] = "Defunct/Merged"
        r["scanned_at"] = f"{STAMP} [merged into {succ_name} ({successor})]"
        n_def += 1

    for ref, note in UNRESOLVED.items():
        r = by_ref[ref]
        r["scanned_at"] = f"{STAMP} [unresolved: {note}]"
        n_flag += 1

    JSON_PATH.write_text(json.dumps(rows, indent=2))
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)

    print(f"URL updates:      {n_url}")
    print(f"Platform changes: {n_plat}")
    print(f"Marked defunct:   {n_def}")
    print(f"Flagged unresolved: {n_flag}")

    from collections import Counter
    counts = Counter(r["platform"] for r in rows)
    print("\nPlatform breakdown now:")
    for p, n in counts.most_common():
        print(f"  {p:<22} {n}")


if __name__ == "__main__":
    main()
