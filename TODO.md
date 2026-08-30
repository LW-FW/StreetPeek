# StreetPeek — Project TODO

Living checklist. Update items to `[x]` as they're completed; add new items under
the relevant section as they come up. Last reviewed: 2026-08-29.

## Planning scraper (idox_scraper.py)

- [x] Idox scraper built — `--test` / `--full` / `--update` / `--council` / `--export` / `--stats` modes, resumable via `scrape_log` table
- [x] Portal re-discovery pass v1 (2026-07-12) — diagnosed 64 broken portals (`data/failure_diagnosis.json`), verified 26 replacement URLs (`data/verified_candidates.json`), applied via `update_councils.py`
- [x] Re-ran diagnosis on the current 226 failures (2026-08-29) — 85 are already working again (`data/failure_diagnosis.json`), the rest broke down as 56 wrong-path (404), 54 domain moved (DNS), 8 bot-blocked (403), plus a long tail
- [x] Built `portal_healthcheck.py` — checks ALL 337 council entries (not just previously-failed ones), auto-rediscovers and applies fixes only when a candidate is both reachable AND shows a fresh (current month) listing, keeps a run-over-run diff in `data/portal_health.json`. First run: 133 already healthy, 24 auto-fixed, 118 need manual research (see `data/portal_health_reports/`)
- [x] Found and fixed a false-positive in the very first auto-fix run: 4 National Park entries (New Forest, North York Moors, Northumberland, Yorkshire Dales) had their `website` field mis-recorded as their host council's site, so rediscovery pointed them at that council's own portal instead of leaving them broken. Reverted all 4 to their own (still-broken) domains + corrected `website`, and hardened `portal_healthcheck.py` to refuse to auto-apply any candidate whose host is already claimed by a *different* council — it now downgrades those to manual review instead
- [x] Extended `portal_healthcheck.py` with a website-crawl fallback (2026-08-30) — when Idox-pattern-guessing finds nothing, it now fetches the council's own homepage and follows planning-related links up to 3 hops deep (mirrors how a human would research it by hand). Recovers genuine Idox instances the subdomain guesser missed, and for councils on a different platform entirely, surfaces the actual current URL + a rough platform guess (Northgate/Planning Explorer, Arcus, Agile, Idox Cloud, etc.) instead of a bare "not found" — cuts most of the 118 down to "here's the URL, confirm and wire up a scraper" rather than needing manual research from scratch. Confirmed working: found Milton Keynes' real portal is now Arcus (`be.milton-keynes.gov.uk/pr/s/...`), 3 hops deep from their homepage
- [ ] Review `data/portal_health_reports/` latest run for platform leads found by the crawl fallback; group by platform (Northgate/Arcus/etc.) to see which is worth writing a second scraper for vs. one-off/custom pages needing individual handling
- [ ] A handful of councils (e.g. Manchester) 403-block plain HTTP requests entirely, including to their own homepage — crawling can't get past that; genuinely needs a human (or a headless-browser approach) to look up
- [ ] Known legitimate multi-council-shared-portal cases (won't need "fixing", just don't be alarmed if they show up flagged): Buckinghamshire (4 pre-2020 districts), Somerset (4 pre-2023 districts), Adur & Worthing (joint service) — added Wellingborough → North Northamptonshire to the DEFUNCT map in `rediscover_portals.py` as the same pattern
- [ ] Run `--full` once to backfill history for everything newly fixed — note `--full` marks a council permanently "done" after one success and skips it forever, it is NOT a refresh; it will never re-check the 49 councils that already succeeded even though new applications keep being added there
- [ ] Then switch to a recurring `--update` (last 8 weeks) run for ongoing new-entry coverage across ALL working councils — this is the one that actually needs to run repeatedly, `--full` is a one-time-per-council backfill
- [x] Fixed a false-"broken" bug in `portal_healthcheck.py` (2026-08-30): a single failed probe under the 8-way concurrent sweep was being trusted as real (confirmed via Cornwall LPA — failed under load, passed instantly alone). Added one retry-after-pause before declaring a portal broken; cut a run's "newly broken" noise from 6 councils down to 1 genuine case
- [ ] Decide a recurring cadence for `portal_healthcheck.py` (weekly suggested) and how to run it unattended — deferred for now, running manually
- [ ] Confirm `idox_scraper_1.py` and `identify_councils_v4.py` are fully superseded, then remove them

## Data sources dashboard (2026-08-30)

- [x] Built `check_live_sources.py` — pings the 6 live third-party APIs the app calls per-request (postcode lookup, crime, planning, environment/flood, nearby amenities, live schools) and records up/down + a shape-check into `data/source_health.json`. **Found a real bug while building this**: the GIAS live schools endpoint `pages/api/schools.ts` depends on (`get-information-schools.service.gov.uk/api/v1/Establishments/search`) now returns HTTP 404 — same URL, same params as the code uses. The Schools panel is very likely silently failing in production right now (the API falls back to an empty-result error state rather than crashing). Needs its own investigation — GIAS may have moved/retired that endpoint
- [x] Built `build_dashboard.py` — generates a local-only `dashboard.html` (gitignored, never published) from councils_final.json + planning.db + portal_health.json/reports + source_health.json + education_manifest.json. Shows per-council portal/scrape status with filters, live API health, and education pipeline freshness. Re-run after any health check to refresh; open the file directly in a browser
- [ ] Investigate the GIAS 404 and fix `pages/api/schools.ts` (or find the new endpoint) — this is a live bug, not just a data-freshness gap
- [ ] Once education_scraper.py has been run at least once, `build_dashboard.py`'s education section will show real freshness data instead of "never run"

## Education data pipeline (education_scraper.py)

- [x] Pipeline written — GIAS (schools register) + Ofsted (schools + childcare ratings) + ONS NSPL (postcode lookup) → `data/schools.json` / `data/nurseries.json`
- [ ] Run the pipeline to actually produce `data/schools.json` / `data/nurseries.json` (doesn't exist yet)
- [ ] Wire `pages/api/schools.ts` to read the local dataset instead of hitting the live GIAS API per-request
- [ ] Set a monthly re-run reminder (Ofsted CSV + NSPL URLs are versioned one-off links that go stale — see script docstring)
- [ ] Re-add a "school-run traffic" indicator to `SchoolsPanel` — removed 2026-08-29 because it read `summary.trafficRisk`, a field the real `EducationResponse` never had (was built against an earlier mocked API shape). No traffic data exists in GIAS/Ofsted; needs a real signal (e.g. a heuristic off school density/proximity within the search radius) before it can come back.

## Frontend

- [x] Landing page, results page (overview/nearby/planning/crime/environment/map tabs), pricing page
- [x] Nearby feature rebuilt — `NearbyTab`/`NearbySummary`/`NearbyMap` replacing the old `NearbyPanel` (currently uncommitted)
- [x] `AreaMap` React-StrictMode double map-init race fixed (currently uncommitted)
- [x] Nearby data now fetched once per postcode at the results-page level instead of per-tab-mount, fixing repeated Overpass hits (currently uncommitted)
- [ ] Commit the current working-tree changes (Nearby rework, AreaMap fix, Navbar simplification, HeroMap)
- [ ] Decide whether Pricing should be back in primary nav or stay CTA-only
- [ ] Factor schools/nearby-amenities data into `computeAreaScore` (currently only crime/flood/conservation/brownfield)

## Monetization

- [ ] Payment integration (Stripe or similar) — "Buy report" buttons currently link to `/` or `#`, nothing is wired up
- [ ] Gate full-report content behind actual payment/access control

## Infra / data sources

- [ ] Move off the public `tile.openstreetmap.org` tile server and public Overpass instance before real traffic — both are shared community resources not meant for commercial-scale use
- [ ] Add automated tests (none exist yet, frontend or scraper)
