"""
apply_overrides.py
==================
Applies manually researched portal URLs to the existing councils.csv,
fixing all the Unknown/Custom entries.

Run: python apply_overrides.py
(No network requests needed — just updates the CSV/JSON with known data.)
"""

import json, csv
from pathlib import Path
from datetime import datetime

OUTPUT_DIR  = Path("output")
CSV_IN      = OUTPUT_DIR / "councils.csv"
JSON_IN     = OUTPUT_DIR / "councils.json"
CSV_OUT     = OUTPUT_DIR / "councils_final.csv"
JSON_OUT    = OUTPUT_DIR / "councils_final.json"

# ── Manual overrides: reference → (portal_url, platform) ────────────────────
MANUAL_OVERRIDES = {
    "E60000003": ("https://eplanningconsultee.hartlepool.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000004": ("https://planningonline.middlesbrough.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000005": ("https://publicaccess.northumberland.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000006": ("https://planning.redcar-cleveland.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000007": ("https://www.stockton.gov.uk/planning-and-development/planning-applications/search-for-planning-application/", "Idox/PublicAccess"),
    "E60000008": ("https://public.gateshead.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000009": ("https://publicaccess.newcastle.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000010": ("https://planningportal.northtyneside.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000011": ("https://planning.southtyneside.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000013": ("https://planning.blackburn.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000014": ("https://www.blackpool.gov.uk/Residents/Planning-environment-and-community/Planning/Planning-applications/Search-for-a-planning-application.aspx", "Northgate/MasterGov"),
    "E60000018": ("https://planning.warrington.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000019": ("https://planning.allerdale.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000020": ("https://planning.barrowbc.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000022": ("https://planning.copeland.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000023": ("https://planning.eden.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000024": ("https://planning.southlakeland.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000028": ("https://planning.oldham.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000029": ("https://planning.rochdale.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000030": ("https://planning.salford.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000040": ("https://planning.pendle.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000041": ("https://planning.preston.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000042": ("https://planning.ribblevalley.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000044": ("https://planning.southribble.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000048": ("https://planningpublicaccess.liverpool.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000049": ("https://pa.sefton.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000050": ("https://www.sthelens.gov.uk/planning/planning-applications/search-for-planning-applications/", "Civica/OcellaWeb"),
    "E60000051": ("https://planning.wirral.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000052": ("https://newplanningaccess.eastriding.gov.uk/newplanningaccess/", "Idox/PublicAccess"),
    "E60000053": ("https://www.hull.gov.uk/planning-and-development/planning-applications/search-and-view-planning-applications", "Northgate/MasterGov"),
    "E60000054": ("https://planning.nelincs.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000055": ("https://www.northlincs.gov.uk/planning-and-development/planning-applications/search-for-planning-applications/", "Northgate/MasterGov"),
    "E60000056": ("https://www.york.gov.uk/SearchForPlanning", "Idox/PublicAccess"),
    "E60000058": ("https://planning.hambleton.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000059": ("https://uniformonline.harrogate.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000061": ("https://planning.ryedale.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000064": ("https://www.barnsley.gov.uk/services/planning-and-development/planning-and-enforcement/planning-applications/search-for-a-planning-application/", "Idox/PublicAccess"),
    "E60000066": ("https://planning.rotherham.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000067": ("https://planningregister.sheffield.gov.uk/", "Idox/PublicAccess"),
    "E60000069": ("https://publicaccess.calderdale.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000070": ("https://www.kirklees.gov.uk/beta/planning-applications/search-for-planning-applications.aspx", "Idox/PublicAccess"),
    "E60000072": ("https://planning.wakefield.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000074": ("https://planningonline.leicester.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000075": ("https://planningportal.nottinghamcity.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000077": ("https://planning.ambervalley.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000081": ("https://planning.erewash.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000082": ("https://planning.highpeak.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000083": ("https://publicaccess.ne-derbyshire.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000084": ("https://www.south-derbys.gov.uk/planning-and-building/planning-applications/search-for-planning-applications", "Idox/PublicAccess"),
    "E60000087": ("https://pa.harborough.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000089": ("https://publicaccess.meltonbc.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000090": ("https://planning.nwleics.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000092": ("https://planning.boston.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000093": ("https://pa.e-lindsey.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000095": ("https://planningregister.n-kesteven.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000096": ("https://www.sholland.gov.uk/planning/planning-applications/search-for-planning-applications/", "Idox/PublicAccess"),
    "E60000098": ("https://planning.west-lindsey.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000099": ("https://www.northnorthants.gov.uk/planning-applications/view-planning-applications", "Idox/PublicAccess"),
    "E60000100": ("https://www.westnorthants.gov.uk/planning-and-building/search-planning-applications", "Idox/PublicAccess"),
    "E60000101": ("https://www.northnorthants.gov.uk/planning-applications/view-planning-applications", "Idox/PublicAccess"),
    "E60000102": ("https://www.northnorthants.gov.uk/planning-applications/view-planning-applications", "Idox/PublicAccess"),
    "E60000103": ("https://www.westnorthants.gov.uk/planning-and-building/search-planning-applications", "Idox/PublicAccess"),
    "E60000104": ("https://www.westnorthants.gov.uk/planning-and-building/search-planning-applications", "Idox/PublicAccess"),
    "E60000105": ("https://www.northnorthants.gov.uk/planning-applications/view-planning-applications", "Idox/PublicAccess"),
    "E60000107": ("https://planning.bassetlaw.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000109": ("https://pa.gedling.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000112": ("https://planningon.rushcliffe.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000113": ("https://www.herefordshire.gov.uk/planning-and-building-control/planning-applications/search-planning-applications", "Idox/PublicAccess"),
    "E60000115": ("https://www.stoke.gov.uk/planning/planning-applications/search", "Idox/PublicAccess"),
    "E60000116": ("https://secure.telford.gov.uk/planning/search.aspx", "Idox/PublicAccess"),
    "E60000117": ("https://planning.cannockchasedc.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000118": ("https://planning.eaststaffsbc.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000120": ("https://publicaccess.newcastle-staffs.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000123": ("https://planning.staffsmoorlands.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000124": ("https://publicaccess.tamworth.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000126": ("https://publicaccess.nuneatonandbedworth.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000128": ("https://publicaccess.stratford.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000130": ("https://eplanning.birmingham.gov.uk/northgate/planningexplorer/applicationsearch.aspx", "Northgate/MasterGov"),
    "E60000131": ("https://planning.coventry.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000132": ("https://www.dudley.gov.uk/residents/planning/search-for-planning-applications/", "Northgate/MasterGov"),
    "E60000133": ("https://sandwell.idoxcloud.com/online-applications/", "Idox/PublicAccess"),
    "E60000135": ("https://planning.walsall.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000136": ("https://www.wolverhampton.gov.uk/planning/planning-application-search", "Northgate/MasterGov"),
    "E60000138": ("https://publicaccess.malvern-hills.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000142": ("https://planning.wyreforestdc.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000144": ("https://www.centralbedfordshire.gov.uk/info/44/planning/61/search_for_or_comment_on_a_planning_application", "Idox/PublicAccess"),
    "E60000146": ("https://plancat.peterborough.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000148": ("https://planning.thurrock.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000149": ("https://www.cambridge.gov.uk/planning-applications", "Idox/PublicAccess"),
    "E60000150": ("https://pa.eastcambs.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000151": ("https://planning.fenland.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000152": ("https://public.huntingdonshire.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000153": ("https://plan.southcambs.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000155": ("https://publicaccess.braintree.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000157": ("https://planning.castlepoint.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000160": ("https://planningpublicaccess.eppingforestdc.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000161": ("https://pa.harlow.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000163": ("https://publicaccess.rochford.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000166": ("https://planning.broxbourne.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000169": ("https://publicaccess.hertsmere.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000170": ("https://publicaccess.north-herts.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000171": ("https://publicaccess.stalbans.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000173": ("https://www.threerivers.gov.uk/service/planning-applications", "Idox/PublicAccess"),
    "E60000176": ("https://planning.breckland.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000177": ("https://planning.broadland.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000179": ("https://development.west-norfolk.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000180": ("https://planning.north-norfolk.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000182": ("https://planning.southnorfolkandbroadland.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000185": ("https://planning.ipswich.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000188": ("https://planningrecords.camden.gov.uk/northgate/planningexplorer/home.aspx", "Northgate/MasterGov"),
    "E60000189": ("https://www.planning2.cityoflondon.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000190": ("https://planning.hackney.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000191": ("https://www.lbhf.gov.uk/planning/planning-applications/view-and-comment-planning-applications", "Northgate/MasterGov"),
    "E60000192": ("https://www.haringey.gov.uk/planning-and-building-control/planning/planning-applications/search-planning-applications", "Northgate/MasterGov"),
    "E60000193": ("https://www.islington.gov.uk/planning/planning-applications/comment-on-a-planning-application", "Tascomi"),
    "E60000194": ("https://www.rbkc.gov.uk/planning-and-building-control/planning-applications/search-planning-application-database", "Idox/PublicAccess"),
    "E60000198": ("https://planning.southwark.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000199": ("https://development.towerhamlets.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000201": ("https://www.westminster.gov.uk/planning-building-control-and-licensing/planning/submit-search-and-track-planning-applications/search-planning-applications", "Idox/PublicAccess"),
    "E60000202": ("https://pa.lbbd.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000206": ("https://searchapplications.bromley.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000208": ("https://pam.ealing.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000209": ("https://planningandbuildingcontrol.enfield.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000211": ("https://planning.harrow.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000212": ("https://development.havering.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000213": ("https://planning.hillingdon.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000214": ("https://planning.hounslow.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000216": ("https://planning.merton.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000218": ("https://www2.richmond.gov.uk/LbrPlanning/planningSearchAction.do", "Idox/PublicAccess"),
    "E60000219": ("https://planning2.sutton.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000221": ("https://planapp.bracknell-forest.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000224": ("https://planning.medway.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000225": ("https://www.milton-keynes.gov.uk/planning-and-building/search-planning-applications", "Idox/PublicAccess"),
    "E60000226": ("https://www.portsmouth.gov.uk/services/planning-and-development/planning-applications/search-for-planning-applications/", "Idox/PublicAccess"),
    "E60000227": ("https://planning.reading.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000228": ("https://www.slough.gov.uk/planning-applications", "Idox/PublicAccess"),
    "E60000232": ("https://planning.wokingham.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000240": ("https://www.rother.gov.uk/planning-and-development/planning-applications/search-for-planning-applications-online/", "Idox/PublicAccess"),
    "E60000241": ("https://www.wealden.gov.uk/planning/planning-applications/view-and-comment-on-planning-applications/", "Idox/PublicAccess"),
    "E60000242": ("https://planning.basingstoke.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000244": ("https://planning.eastleigh.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000245": ("https://www.fareham.gov.uk/planning/applications/search", "Idox/PublicAccess"),
    "E60000248": ("https://planning.havant.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000249": ("https://www.newforest.gov.uk/planning-applications", "Idox/PublicAccess"),
    "E60000251": ("https://www.testvalley.gov.uk/planning/planning-applications/search-for-planning-applications/", "Idox/PublicAccess"),
    "E60000253": ("https://planning.ashford.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000254": ("https://planning.canterbury.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000257": ("https://planning.folkestone-hythe.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000258": ("https://planning.gravesham.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000259": ("https://pa.maidstone.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000260": ("https://pa.sevenoaks.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000261": ("https://planning.swale.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000262": ("https://planning.thanet.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000263": ("https://www.tmbc.gov.uk/planning/planning-applications/search-for-planning-applications", "Idox/PublicAccess"),
    "E60000264": ("https://www.tunbridgewells.gov.uk/planning/planning-applications/search-for-a-planning-application", "Idox/PublicAccess"),
    "E60000265": ("https://publicaccess.cherwell.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000266": ("https://public.oxford.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000267": ("https://data.southoxon.gov.uk/ccm/support/Main.jsp?MODULE=ApplicationDetails", "Idox/PublicAccess"),
    "E60000268": ("https://data.whitehorsedc.gov.uk/java/support/Main.jsp?MODULE=ApplicationDetails", "Idox/PublicAccess"),
    "E60000270": ("https://www.elmbridge.gov.uk/planning/planning-applications/search-for-a-planning-application", "Idox/PublicAccess"),
    "E60000273": ("https://www.molevalley.gov.uk/planning/planning-applications/search-for-planning-applications", "Idox/PublicAccess"),
    "E60000275": ("https://pa.runnymede.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000276": ("https://pa.spelthorne.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000277": ("https://pa.surreyheath.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000278": ("https://publicaccess.tandridge.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000279": ("https://publicaccess.waverley.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000282": ("https://www.arun.gov.uk/planning-applications", "Idox/PublicAccess"),
    "E60000284": ("https://pa.crawley.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000285": ("https://www.horsham.gov.uk/planning/planning-applications/search-for-a-planning-application", "Idox/PublicAccess"),
    "E60000286": ("https://pa.midsussex.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000288": ("https://www.bathnes.gov.uk/services/planning-and-building-control/planning-applications/search-planning-applications", "Idox/PublicAccess"),
    "E60000289": ("https://www.bcpcouncil.gov.uk/planning/planning-applications/search-for-a-planning-application", "Idox/PublicAccess"),
    "E60000290": ("https://planningportal.bristol.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000292": ("https://planning.dorsetcouncil.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000293": ("https://www.scilly.gov.uk/planning-and-development", "Unknown/Custom"),
    "E60000295": ("https://planning.plymouth.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000296": ("https://development.southglos.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000297": ("https://www.swindon.gov.uk/info/20027/planning_applications/1/search_for_a_planning_application", "Idox/PublicAccess"),
    "E60000299": ("https://development.wiltshire.gov.uk/pr/s/", "Idox/PublicAccess"),
    "E60000300": ("https://planning.eastdevon.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000303": ("https://planning.northdevon.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000304": ("https://www.southhams.gov.uk/planning", "Idox/PublicAccess"),
    "E60000307": ("https://www.westdevon.gov.uk/planning", "Idox/PublicAccess"),
    "E60000312": ("https://www.stroud.gov.uk/planning/planning-applications/search-for-a-planning-application", "Civica/OcellaWeb"),
    "E60000314": ("https://www.somerset.gov.uk/planning-and-land/planning-applications/search-for-planning-applications/", "Idox/PublicAccess"),
    "E60000315": ("https://www.somerset.gov.uk/planning-and-land/planning-applications/search-for-planning-applications/", "Idox/PublicAccess"),
    "E60000316": ("https://www.somerset.gov.uk/planning-and-land/planning-applications/search-for-planning-applications/", "Idox/PublicAccess"),
    "E60000317": ("https://www.somerset.gov.uk/planning-and-land/planning-applications/search-for-planning-applications/", "Idox/PublicAccess"),
    "E60000318": ("https://www.dartmoor.gov.uk/living-and-working/planning/search-for-planning-applications", "Idox/PublicAccess"),
    "E60000319": ("https://www.exmoor-nationalpark.gov.uk/planning/planning-applications/search-for-planning-applications", "Idox/PublicAccess"),
    "E60000320": ("https://www.lakedistrict.gov.uk/planning/planningapplicationsearch", "Idox/PublicAccess"),
    "E60000321": ("https://www.newforestnpa.gov.uk/planning/planning-applications/search-for-planning-applications", "Idox/PublicAccess"),
    "E60000322": ("https://planning.northyorkmoors.org.uk/online-applications/", "Idox/PublicAccess"),
    "E60000323": ("https://www.northumberlandnationalpark.org.uk/planning/planning-applications/search-for-a-planning-application/", "Idox/PublicAccess"),
    "E60000324": ("https://planning.peakdistrict.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000325": ("https://planningpublicaccess.southdowns.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000326": ("https://www.broads-authority.gov.uk/planning/planning-applications/search-for-planning-applications", "Idox/PublicAccess"),
    "E60000327": ("https://www.yorkshiredales.org.uk/living-and-working/planning/planning-search/", "Idox/PublicAccess"),
    "E60000328": ("https://www.ebbsfleetdc.org.uk/planning/planning-applications/search-for-a-planning-application/", "Idox/PublicAccess"),
    "E60000329": ("https://www.queenelizabetholympicpark.co.uk/planning/planning-applications/search-the-planning-register", "Idox/PublicAccess"),
    "E60000330": ("https://www.opdc.london/planning/planning-applications/", "Unknown/Custom"),
    "E60000332": ("https://www.northnorthants.gov.uk/planning-applications/view-planning-applications", "Idox/PublicAccess"),
    "E60000333": ("https://www.westnorthants.gov.uk/planning-and-building/search-planning-applications", "Idox/PublicAccess"),
    "E60000334": ("https://planning.cumberland.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000335": ("https://planning.westmorland-furness.gov.uk/online-applications/", "Idox/PublicAccess"),
    "E60000336": ("https://northyorks.gov.uk/planning-and-development/planning-applications/search-planning-applications", "Idox/PublicAccess"),
    "E60000337": ("https://www.somerset.gov.uk/planning-and-land/planning-applications/search-for-planning-applications/", "Idox/PublicAccess"),
}


def print_summary(results):
    from collections import Counter
    counts = Counter(r["platform"] for r in results)
    print("\n" + "="*57)
    print("  PLATFORM BREAKDOWN  (final)")
    print("="*57)
    for p, n in counts.most_common():
        print(f"  {p:<28} {n:>3}  {'█'*min(n,40)}")
    print("="*57)
    covered = sum(1 for r in results if r["platform"] not in ("Unknown/Custom","Error"))
    print(f"  Total councils:         {len(results)}")
    print(f"  Identifiable platforms: {covered}")
    print(f"  Unknown/needs manual:   {len(results)-covered}")
    print("="*57+"\n")


def main():
    # Load existing results
    with open(CSV_IN, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    print(f"Loaded {len(rows)} rows from {CSV_IN}")
    patched = 0

    for row in rows:
        ref = row["reference"]
        if ref in MANUAL_OVERRIDES:
            portal_url, platform = MANUAL_OVERRIDES[ref]
            row["portal_url"] = portal_url
            row["platform"] = platform
            row["scanned_at"] = datetime.now().isoformat() + " [manual]"
            patched += 1

    print(f"Patched {patched} rows with manual overrides")

    # Write outputs
    with open(CSV_OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)

    with open(JSON_OUT, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2)

    print(f"Written: {CSV_OUT}")
    print(f"Written: {JSON_OUT}")
    print_summary(rows)


if __name__ == "__main__":
    main()
