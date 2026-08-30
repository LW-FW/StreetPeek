"""
StreetPeek — Schools & Nurseries data pipeline
================================================
Builds data/schools.json and data/nurseries.json from official UK government
sources (England only, for now — Wales/Scotland/NI use separate registers
with different formats and aren't wired up yet):

  - GIAS (Get Information About Schools, DfE)      — school register
  - Ofsted "state-funded schools" management info  — school inspection ratings
  - Ofsted "childcare providers" management info   — nursery register + ratings
  - ONS NSPL (National Statistics Postcode Lookup)  — postcode -> lat/lng

All three source URLs below point at a specific dated release and WILL go
stale — GIAS regenerates nightly (URL is date-stamped, this script always
requests today's), but the two Ofsted CSVs and the NSPL zip are versioned,
one-off asset URLs that change every time DfE/Ofsted/ONS publish a new
edition. Re-running this script monthly (matching Ofsted's own publication
cadence) means checking https://www.gov.uk/government/statistical-data-sets/
monthly-management-information-ofsteds-school-inspections-outcomes and
.../childcare-providers-and-inspections-management-information for the
current CSV link, and updating OFSTED_SCHOOLS_URL / OFSTED_CHILDCARE_URL
below. NSPL is published quarterly (Feb/May/Aug/Nov) from
https://geoportal.statistics.gov.uk — update NSPL_ITEM_ID when it moves.

Nurseries are deliberately scoped to "Childcare on non-domestic premises"
only (i.e. nursery/preschool settings). Childminders and home childcarers
are excluded — Ofsted redacts their addresses entirely (no postcode, since
they operate from private homes), so there is nothing to plot.

Ofsted rating systems: schools and nurseries are NOT on the same grading
system. Nurseries are still on Ofsted's old single "Overall Effectiveness"
1-4 scale (Outstanding/Good/Requires improvement/Inadequate). Schools are
mid-migration to Ofsted's new "report card" framework, which grades several
categories separately instead of one headline word — but as of this data,
most schools (~60%) still only have a rating from their last inspection
under the OLD single-grade system, and only ~9% have been inspected under
the new one. `rating.framework` on each school record tells you which case
applies: 'report-card' | 'legacy' | 'ungraded-only' | 'none'.

Run: ./venv/Scripts/python.exe education_scraper.py
"""

import sys

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import argparse
import csv
import io
import json
import logging
import zipfile
from collections import Counter
from datetime import datetime, date
from pathlib import Path

import requests

logging.basicConfig(level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S")
log = logging.getLogger(__name__)

DATA_DIR = Path("data")
RAW_DIR = DATA_DIR / "raw"
DATA_DIR.mkdir(exist_ok=True)
RAW_DIR.mkdir(parents=True, exist_ok=True)

OUT_SCHOOLS = DATA_DIR / "schools.json"
OUT_NURSERIES = DATA_DIR / "nurseries.json"
OUT_MANIFEST = DATA_DIR / "education_manifest.json"

GIAS_URL_TEMPLATE = "https://ea-edubase-api-prod.azurewebsites.net/edubase/downloads/public/edubasealldata{date}.csv"

# These two change every time Ofsted publish a new edition — see module
# docstring for where to find the current link.
OFSTED_SCHOOLS_URL = "https://assets.publishing.service.gov.uk/media/6a54efeba6586e258d371d9c/Management_information_-_state-funded_schools_-_latest_inspections_as_at_30_June_2026.csv"
OFSTED_CHILDCARE_URL = "https://assets.publishing.service.gov.uk/media/6973934c67ae94b3280137b4/Management_information_-_childcare_providers_and_inspections_-_most_recent_inspections_data_as_at_31_December_2025.csv"

# ONS Open Geography Portal item id for the current NSPL release — changes
# quarterly, see module docstring.
NSPL_ITEM_ID = "077631e063eb4e1ab43575d01381ec33"
NSPL_URL = f"https://www.arcgis.com/sharing/rest/content/items/{NSPL_ITEM_ID}/data"

HEADERS = {
    "User-Agent": "StreetPeek/1.0 (property research tool; contact via streetpeek app)",
}

REPORT_CARD_CATEGORIES = {
    "safeguardingStandards": "Safeguarding standards",
    "inclusion": "Inclusion",
    "curriculumAndTeaching": "Curriculum and teaching",
    "achievement": "Achievement",
    "attendanceAndBehaviour": "Attendance and behaviour",
    "personalDevelopment": "Personal development and wellbeing",
    "earlyYears": "Early years (where applicable)",
    "post16": "Post-16 provision (where applicable)",
    "leadershipAndGovernance": "Leadership and governance",
}

EXCLUDED_ESTABLISHMENT_GROUPS = {
    "Universities", "Higher education institutions", "Further education",
    "Welsh schools", "Children's centres", "Online provision", "Miscellaneous",
}


def download(url: str, dest: Path, force: bool = False) -> Path:
    if dest.exists() and not force:
        log.info(f"Using cached {dest} ({dest.stat().st_size / 1_048_576:.1f} MB)")
        return dest
    log.info(f"Downloading {url}")
    with requests.get(url, headers=HEADERS, stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 20):
                f.write(chunk)
    log.info(f"Saved {dest} ({dest.stat().st_size / 1_048_576:.1f} MB)")
    return dest


def download_gias(force: bool = False) -> Path:
    # The GIAS extract is regenerated nightly under today's date; if today's
    # isn't up yet, fall back a few days.
    for days_back in range(4):
        d = date.today()
        stamp = (d.toordinal() - days_back)
        d2 = date.fromordinal(stamp)
        url = GIAS_URL_TEMPLATE.format(date=d2.strftime("%Y%m%d"))
        dest = RAW_DIR / f"gias_{d2.strftime('%Y%m%d')}.csv"
        if dest.exists() and not force:
            log.info(f"Using cached {dest}")
            return dest
        # This endpoint 500s on HEAD requests even when the file exists, so
        # the existence check has to be a real GET.
        try:
            return download(url, dest, force=force)
        except requests.RequestException:
            pass
        log.warning(f"GIAS extract not available for {d2}, trying earlier date")
    raise RuntimeError("Could not find a recent GIAS extract")


def clean(v):
    if v is None:
        return ""
    v = v.strip()
    return "" if v in ("NULL", "") else v


def normalize_postcode(pc: str) -> str:
    pc = clean(pc).upper().replace(" ", "")
    if len(pc) < 5:
        return pc
    return f"{pc[:-3]} {pc[-3:]}"


def load_gias(path: Path):
    rows = []
    type_group_counts = Counter()
    with open(path, encoding="utf-8-sig", errors="replace", newline="") as f:
        for row in csv.DictReader(f):
            type_group_counts[clean(row.get("EstablishmentTypeGroup (name)"))] += 1
            if clean(row.get("EstablishmentStatus (name)")) != "Open":
                continue
            # This field is blank for the ~48k England schools (the register's
            # main content) and only populated for a handful of British-
            # curriculum overseas schools DfE also tracks here, plus a
            # "United Kingdom" catch-all — so "not overseas" is blank/UK, not
            # literally "England".
            country = clean(row.get("Country (name)"))
            if country not in ("", "United Kingdom"):
                continue
            if clean(row.get("PhaseOfEducation (name)")) in ("", "Not applicable"):
                continue
            if clean(row.get("EstablishmentTypeGroup (name)")) in EXCLUDED_ESTABLISHMENT_GROUPS:
                continue
            rows.append(row)
    log.info(f"GIAS: {len(rows)} open England schools kept (by establishment type group, all rows): {type_group_counts.most_common()}")
    return rows


def load_ofsted_school_ratings(path: Path):
    ratings = {}
    with open(path, encoding="utf-8-sig", errors="replace", newline="") as f:
        for row in csv.DictReader(f):
            urn = clean(row.get("URN"))
            if not urn:
                continue
            # Report-card categories are graded on a 5-word scale (Exceptional
            # / Strong standard / Expected standard / Needs attention /
            # Urgent improvement), except Safeguarding which is a Met / Not
            # met binary — none of these are numeric like the legacy grade.
            # "Not applicable" (early years / post-16, when the school has
            # neither) is dropped rather than stored as a grade.
            categories = {}
            for key, col in REPORT_CARD_CATEGORIES.items():
                v = clean(row.get(col))
                if v and v != "Not applicable":
                    categories[key] = v

            dates = [clean(row.get("Inspection start date")),
                     clean(row.get("Inspection start date of latest OEIF graded inspection")),
                     clean(row.get("Date of latest ungraded inspection"))]
            dates = [d for d in dates if d]

            if categories:
                ratings[urn] = {
                    "framework": "report-card",
                    "categories": categories,
                    "inspectionDate": clean(row.get("Inspection start date")) or None,
                    "lastInspectionDate": max(dates) if dates else None,
                }
                continue

            oeif = clean(row.get("Latest OEIF overall effectiveness"))
            if oeif.isdigit():
                ratings[urn] = {
                    "framework": "legacy",
                    "legacyGrade": int(oeif),
                    "inspectionDate": clean(row.get("Inspection start date of latest OEIF graded inspection")) or None,
                    "lastInspectionDate": max(dates) if dates else None,
                }
                continue

            ungraded = clean(row.get("Date of latest ungraded inspection"))
            if ungraded:
                # An "ungraded" (Section 8) monitoring visit doesn't erase the
                # school's previous full-inspection grade — Ofsted's own
                # published rating for the school stays whatever it was,
                # and the visit either reaffirms it or flags a concern. The
                # visit's outcome text says so explicitly ("School remains
                # Good", "School remains Outstanding") for the ~97% of cases
                # where the wording is unambiguous; treating all of these as
                # "not graded" (as this pipeline used to) was wrong — the
                # school genuinely has a current, real grade.
                outcome = clean(row.get("Ungraded inspection overall outcome"))
                reaffirmed_grade = None
                if "remains Outstanding" in outcome:
                    reaffirmed_grade = 1
                elif "remains Good" in outcome:
                    reaffirmed_grade = 2
                if reaffirmed_grade:
                    ratings[urn] = {
                        "framework": "legacy",
                        "legacyGrade": reaffirmed_grade,
                        "inspectionDate": ungraded,
                        "lastInspectionDate": max(dates) if dates else None,
                        "confirmedByMonitoringVisit": True,
                    }
                else:
                    # Outcome text like "Standards maintained" doesn't state
                    # which grade is being maintained, so there's nothing
                    # safe to infer — surface the raw text rather than guess.
                    ratings[urn] = {
                        "framework": "ungraded-only",
                        "inspectionDate": ungraded,
                        "lastInspectionDate": max(dates) if dates else None,
                        "ungradedOutcome": outcome or None,
                    }
                continue

            ratings[urn] = {"framework": "none", "inspectionDate": None, "lastInspectionDate": None}
    fw_counts = Counter(r["framework"] for r in ratings.values())
    log.info(f"Ofsted schools: {len(ratings)} URNs rated, by framework: {dict(fw_counts)}")
    return ratings


def load_ofsted_childcare(path: Path):
    rows = []
    subtype_counts = Counter()
    with open(path, encoding="utf-8-sig", errors="replace", newline="") as f:
        lines = f.readlines()
    # First 2 lines are a title + a note, not the header — same layout as
    # every Ofsted "management information" spreadsheet export.
    reader = csv.DictReader(io.StringIO("".join(lines[2:])))
    for row in reader:
        subtype_counts[clean(row.get("Provider Type"))] += 1
        if clean(row.get("Provider Type")) != "Childcare on non-domestic premises":
            continue
        # "Out-of-school day care" is breakfast/after-school/holiday clubs
        # for school-age kids — a different thing from early-years nursery
        # provision, so it's excluded from what this pipeline calls a
        # "nursery".
        if clean(row.get("Provider Subtype")) not in ("Full day care", "Sessional day care"):
            continue
        if clean(row.get("Provider Status")) != "Active":
            continue
        if not clean(row.get("Provider Postcode")):
            continue
        rows.append(row)
    log.info(f"Ofsted childcare: {len(rows)} active non-domestic-premises providers kept, by provider type (all rows): {subtype_counts.most_common()}")
    return rows


def load_postcode_lookup(zip_path: Path, needed: set):
    # The zip also ships one combined "Data/NSPL_..._UK.txt" file, but that
    # one is fixed-width (no delimiters) despite the .txt extension — the
    # per-postcode-area files under Data/multi_csv/ are the real CSVs
    # (each with its own header row), so read those instead.
    lookup = {}
    with zipfile.ZipFile(zip_path) as z:
        csv_names = [n for n in z.namelist() if n.startswith("Data/multi_csv/") and n.endswith(".csv")]
        if not csv_names:
            raise RuntimeError("Could not find per-area NSPL CSVs in zip")
        for name in csv_names:
            if len(lookup) >= len(needed):
                break
            with z.open(name) as raw:
                text = io.TextIOWrapper(raw, encoding="utf-8", errors="replace")
                for row in csv.DictReader(text):
                    pc = normalize_postcode(row.get("pcds", ""))
                    if pc not in needed or pc in lookup:
                        continue
                    if clean(row.get("doterm")):
                        continue  # terminated postcode
                    lat, lng = clean(row.get("lat")), clean(row.get("long"))
                    if not lat or not lng:
                        continue
                    lookup[pc] = (float(lat), float(lng))
    log.info(f"NSPL: geocoded {len(lookup)}/{len(needed)} needed postcodes")
    return lookup


def build_schools(gias_rows, ratings, postcode_lookup):
    out = []
    missing_geocode = 0
    for row in gias_rows:
        urn = clean(row.get("URN"))
        pc = normalize_postcode(row.get("Postcode", ""))
        coords = postcode_lookup.get(pc)
        if not coords:
            missing_geocode += 1
            continue
        lat, lng = coords
        rating = ratings.get(urn, {"framework": "none", "inspectionDate": None, "lastInspectionDate": None})
        address = ", ".join(filter(None, [
            clean(row.get("Street")), clean(row.get("Locality")), clean(row.get("Town")), pc,
        ]))
        out.append({
            "id": f"school-{urn}",
            "urn": urn,
            "name": clean(row.get("EstablishmentName")),
            "phase": clean(row.get("PhaseOfEducation (name)")),
            "establishmentType": clean(row.get("TypeOfEstablishment (name)")),
            "typeGroup": clean(row.get("EstablishmentTypeGroup (name)")),
            "ageRange": {
                "low": int(clean(row.get("StatutoryLowAge")) or 0) or None,
                "high": int(clean(row.get("StatutoryHighAge")) or 0) or None,
            },
            "gender": clean(row.get("Gender (name)")) or None,
            "religiousCharacter": clean(row.get("ReligiousCharacter (name)")) or None,
            "capacity": int(clean(row.get("SchoolCapacity")) or 0) or None,
            "pupilsOnRoll": int(clean(row.get("NumberOfPupils")) or 0) or None,
            "address": address,
            "postcode": pc,
            "lat": lat,
            "lng": lng,
            "rating": rating,
        })
    log.info(f"Schools: {len(out)} geocoded, {missing_geocode} dropped for missing/unmatched postcode")
    return out


def build_nurseries(childcare_rows, postcode_lookup):
    out = []
    missing_geocode = 0
    for row in childcare_rows:
        urn = clean(row.get("Provider URN"))
        pc = normalize_postcode(row.get("Provider Postcode", ""))
        coords = postcode_lookup.get(pc)
        if not coords:
            missing_geocode += 1
            continue
        lat, lng = coords
        grade = clean(row.get("Most Recent Full: Overall Effectiveness"))
        address = ", ".join(filter(None, [
            clean(row.get("Provider Address Line 1")), clean(row.get("Provider Address Line 2")),
            clean(row.get("Provider Town")), pc,
        ]))
        out.append({
            "id": f"nursery-{urn}",
            "providerUrn": urn,
            "name": clean(row.get("Provider Name")),
            "providerSubtype": clean(row.get("Provider Subtype")) or None,
            "places": int(clean(row.get("Places")) or 0) or None,
            "address": address,
            "postcode": pc,
            "lat": lat,
            "lng": lng,
            "rating": {
                "grade": int(grade) if grade.isdigit() else None,
                "inspectionDate": clean(row.get("Most Recent Full: Inspection Date")) or None,
            },
        })
    log.info(f"Nurseries: {len(out)} geocoded, {missing_geocode} dropped for missing/unmatched postcode")
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force-download", action="store_true", help="Re-download sources even if cached in data/raw/")
    args = parser.parse_args()

    gias_path = download_gias(force=args.force_download)
    ofsted_schools_path = download(OFSTED_SCHOOLS_URL, RAW_DIR / "ofsted_schools.csv", force=args.force_download)
    ofsted_childcare_path = download(OFSTED_CHILDCARE_URL, RAW_DIR / "ofsted_childcare.csv", force=args.force_download)
    nspl_path = download(NSPL_URL, RAW_DIR / "nspl.zip", force=args.force_download)

    gias_rows = load_gias(gias_path)
    ratings = load_ofsted_school_ratings(ofsted_schools_path)
    childcare_rows = load_ofsted_childcare(ofsted_childcare_path)

    needed_postcodes = {normalize_postcode(r.get("Postcode", "")) for r in gias_rows}
    needed_postcodes |= {normalize_postcode(r.get("Provider Postcode", "")) for r in childcare_rows}
    needed_postcodes.discard("")

    postcode_lookup = load_postcode_lookup(nspl_path, needed_postcodes)

    schools = build_schools(gias_rows, ratings, postcode_lookup)
    nurseries = build_nurseries(childcare_rows, postcode_lookup)

    with open(OUT_SCHOOLS, "w", encoding="utf-8") as f:
        json.dump(schools, f, ensure_ascii=False)
    with open(OUT_NURSERIES, "w", encoding="utf-8") as f:
        json.dump(nurseries, f, ensure_ascii=False)

    manifest = {
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "schoolsCount": len(schools),
        "nurseriesCount": len(nurseries),
        "sources": {
            "gias": str(gias_path.name),
            "ofstedSchools": OFSTED_SCHOOLS_URL,
            "ofstedChildcare": OFSTED_CHILDCARE_URL,
            "nspl": NSPL_URL,
        },
        "refreshCadence": "monthly (matches Ofsted's own publication cadence; nursery ratings only change ~twice a year)",
    }
    with open(OUT_MANIFEST, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    log.info(f"Wrote {OUT_SCHOOLS} ({len(schools)} schools), {OUT_NURSERIES} ({len(nurseries)} nurseries)")


if __name__ == "__main__":
    main()
