Private/independent schools are in GIAS but Ofsted ratings won't apply
(they're inspected by ISI instead)
The GIAS search API uses a radius in metres — currently set to 1500m (~1 mile)
You can adjust this in pages/api/schools.ts: const radiusMetres = 1500;
Ofsted ratings are embedded in the GIAS record and may lag the latest
published inspection report by a few weeks.

./venv/Scripts/python.exe idox_scraper.py --full

to refresh dashboard:
 portal_healthcheck.py → 
 check_live_sources.py → 
 build_dashboard.py, 
 then reopen the file.