"""
UK Council Planning Portal Identifier v4
==========================================
Fetches all 337 LPAs from planning.data.gov.uk, looks up each council's
real website URL, then fingerprints their planning portal platform.

Run: python identify_councils_v4.py
"""

import requests, json, csv, time, logging, re
from pathlib import Path
from datetime import datetime
from urllib.parse import urljoin, urlparse

OUTPUT_DIR  = Path("output")
CSV_PATH    = OUTPUT_DIR / "councils.csv"
JSON_PATH   = OUTPUT_DIR / "councils.json"
RESUME_PATH = OUTPUT_DIR / "resume.json"
DELAY       = 1.5

logging.basicConfig(level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S")
log = logging.getLogger(__name__)
OUTPUT_DIR.mkdir(exist_ok=True)

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; UKCouncilPlatformResearch/1.0)"}

# ── Website lookup keyed on cleaned council name (lowercase, no "lpa") ───────
# Covers every council where the derived URL would be wrong.
# Key = lowercase name after stripping " lpa", " council", " borough" etc.
# We match by checking if the key is contained in the cleaned name.
WEBSITE_BY_NAME = {
    # North East
    "county durham":        "https://www.durham.gov.uk",
    "darlington":           "https://www.darlington.gov.uk",
    "hartlepool":           "https://www.hartlepool.gov.uk",
    "middlesbrough":        "https://www.middlesbrough.gov.uk",
    "northumberland":       "https://www.northumberland.gov.uk",
    "redcar and cleveland": "https://www.redcar-cleveland.gov.uk",
    "stockton-on-tees":     "https://www.stockton.gov.uk",
    "gateshead":            "https://www.gateshead.gov.uk",
    "newcastle upon tyne":  "https://www.newcastle.gov.uk",
    "north tyneside":       "https://www.northtyneside.gov.uk",
    "south tyneside":       "https://www.southtyneside.gov.uk",
    "sunderland":           "https://www.sunderland.gov.uk",
    # North West
    "blackburn with darwen":"https://www.blackburn.gov.uk",
    "blackpool":            "https://www.blackpool.gov.uk",
    "cheshire east":        "https://www.cheshireeast.gov.uk",
    "cheshire west and chester": "https://www.cheshirewestandchester.gov.uk",
    "halton":               "https://www.halton.gov.uk",
    "warrington":           "https://www.warrington.gov.uk",
    "allerdale":            "https://www.allerdale.gov.uk",
    "barrow-in-furness":    "https://www.barrow.gov.uk",
    "carlisle":             "https://www.carlisle.gov.uk",
    "copeland":             "https://www.copeland.gov.uk",
    "eden":                 "https://www.eden.gov.uk",
    "south lakeland":       "https://www.southlakeland.gov.uk",
    "cumberland":           "https://www.cumberland.gov.uk",
    "westmorland and furness": "https://www.westmorland-furness.gov.uk",
    "bolton":               "https://www.bolton.gov.uk",
    "bury":                 "https://www.bury.gov.uk",
    "manchester":           "https://www.manchester.gov.uk",
    "oldham":               "https://www.oldham.gov.uk",
    "rochdale":             "https://www.rochdale.gov.uk",
    "salford":              "https://www.salford.gov.uk",
    "stockport":            "https://www.stockport.gov.uk",
    "tameside":             "https://www.tameside.gov.uk",
    "trafford":             "https://www.trafford.gov.uk",
    "wigan":                "https://www.wigan.gov.uk",
    "burnley":              "https://www.burnley.gov.uk",
    "chorley":              "https://www.chorley.gov.uk",
    "fylde":                "https://www.fylde.gov.uk",
    "hyndburn":             "https://www.hyndburnbc.gov.uk",
    "lancaster":            "https://www.lancaster.gov.uk",
    "pendle":               "https://www.pendle.gov.uk",
    "preston":              "https://www.preston.gov.uk",
    "ribble valley":        "https://www.ribblevalley.gov.uk",
    "rossendale":           "https://www.rossendale.gov.uk",
    "south ribble":         "https://www.southribble.gov.uk",
    "west lancashire":      "https://www.westlancs.gov.uk",
    "wyre":                 "https://www.wyre.gov.uk",
    "knowsley":             "https://www.knowsley.gov.uk",
    "liverpool":            "https://www.liverpool.gov.uk",
    "sefton":               "https://www.sefton.gov.uk",
    "st. helens":           "https://www.sthelens.gov.uk",
    "st helens":            "https://www.sthelens.gov.uk",
    "wirral":               "https://www.wirral.gov.uk",
    # Yorkshire and the Humber
    "east riding of yorkshire": "https://www.eastriding.gov.uk",
    "kingston upon hull":   "https://www.hull.gov.uk",
    "north east lincolnshire": "https://www.nelincs.gov.uk",
    "north lincolnshire":   "https://www.northlincs.gov.uk",
    "york":                 "https://www.york.gov.uk",
    "craven":               "https://www.cravendc.gov.uk",
    "hambleton":            "https://www.hambleton.gov.uk",
    "harrogate":            "https://www.harrogate.gov.uk",
    "richmondshire":        "https://www.richmondshire.gov.uk",
    "ryedale":              "https://www.ryedale.gov.uk",
    "scarborough":          "https://www.scarborough.gov.uk",
    "selby":                "https://www.selby.gov.uk",
    "north yorkshire":      "https://www.northyorks.gov.uk",
    "barnsley":             "https://www.barnsley.gov.uk",
    "doncaster":            "https://www.doncaster.gov.uk",
    "rotherham":            "https://www.rotherham.gov.uk",
    "sheffield":            "https://www.sheffield.gov.uk",
    "bradford":             "https://www.bradford.gov.uk",
    "calderdale":           "https://www.calderdale.gov.uk",
    "kirklees":             "https://www.kirklees.gov.uk",
    "leeds":                "https://www.leeds.gov.uk",
    "wakefield":            "https://www.wakefield.gov.uk",
    # East Midlands
    "derby":                "https://www.derby.gov.uk",
    "leicester":            "https://www.leicester.gov.uk",
    "nottingham":           "https://www.nottinghamcity.gov.uk",
    "rutland":              "https://www.rutland.gov.uk",
    "amber valley":         "https://www.ambervalley.gov.uk",
    "bolsover":             "https://www.bolsover.gov.uk",
    "chesterfield":         "https://www.chesterfield.gov.uk",
    "derbyshire dales":     "https://www.derbyshiredales.gov.uk",
    "erewash":              "https://www.erewash.gov.uk",
    "high peak":            "https://www.highpeak.gov.uk",
    "north east derbyshire":"https://www.ne-derbyshire.gov.uk",
    "south derbyshire":     "https://www.south-derbys.gov.uk",
    "blaby":                "https://www.blaby.gov.uk",
    "charnwood":            "https://www.charnwood.gov.uk",
    "harborough":           "https://www.harborough.gov.uk",
    "hinckley and bosworth":"https://www.hinckley-bosworth.gov.uk",
    "melton":               "https://www.meltonbc.gov.uk",
    "north west leicestershire": "https://www.nwleics.gov.uk",
    "oadby and wigston":    "https://www.oadby-wigston.gov.uk",
    "boston":               "https://www.boston.gov.uk",
    "east lindsey":         "https://www.e-lindsey.gov.uk",
    "lincoln":              "https://www.lincoln.gov.uk",
    "north kesteven":       "https://www.n-kesteven.gov.uk",
    "south holland":        "https://www.sholland.gov.uk",
    "south kesteven":       "https://www.southkesteven.gov.uk",
    "west lindsey":         "https://www.west-lindsey.gov.uk",
    "corby":                "https://www.northnorthants.gov.uk",
    "daventry":             "https://www.westnorthants.gov.uk",
    "east northamptonshire":"https://www.northnorthants.gov.uk",
    "kettering":            "https://www.northnorthants.gov.uk",
    "northampton":          "https://www.westnorthants.gov.uk",
    "south northamptonshire":"https://www.westnorthants.gov.uk",
    "wellingborough":       "https://www.northnorthants.gov.uk",
    "north northamptonshire":"https://www.northnorthants.gov.uk",
    "west northamptonshire":"https://www.westnorthants.gov.uk",
    "ashfield":             "https://www.ashfield.gov.uk",
    "basford":              "https://www.nottinghamcity.gov.uk",
    "broxtowe":             "https://www.broxtowe.gov.uk",
    "gedling":              "https://www.gedling.gov.uk",
    "mansfield":            "https://www.mansfield.gov.uk",
    "newark and sherwood":  "https://www.newark-sherwooddc.gov.uk",
    "rushcliffe":           "https://www.rushcliffe.gov.uk",
    # West Midlands
    "birmingham":           "https://www.birmingham.gov.uk",
    "coventry":             "https://www.coventry.gov.uk",
    "dudley":               "https://www.dudley.gov.uk",
    "sandwell":             "https://www.sandwell.gov.uk",
    "solihull":             "https://www.solihull.gov.uk",
    "walsall":              "https://www.walsall.gov.uk",
    "wolverhampton":        "https://www.wolverhampton.gov.uk",
    "bromsgrove":           "https://www.bromsgrove.gov.uk",
    "cannock chase":        "https://www.cannockchasedc.gov.uk",
    "east staffordshire":   "https://www.eaststaffsbc.gov.uk",
    "lichfield":            "https://www.lichfielddc.gov.uk",
    "newcastle-under-lyme": "https://www.newcastle-staffs.gov.uk",
    "north warwickshire":   "https://www.northwarks.gov.uk",
    "nuneaton and bedworth":"https://www.nuneatonandbedworth.gov.uk",
    "redditch":             "https://www.redditchbc.gov.uk",
    "rugby":                "https://www.rugby.gov.uk",
    "south staffordshire":  "https://www.sstaffs.gov.uk",
    "stafford":             "https://www.staffordbc.gov.uk",
    "staffordshire moorlands": "https://www.staffsmoorlands.gov.uk",
    "stoke-on-trent":       "https://www.stoke.gov.uk",
    "stratford-on-avon":    "https://www.stratford.gov.uk",
    "tamworth":             "https://www.tamworth.gov.uk",
    "warwick":              "https://www.warwickdc.gov.uk",
    "worcester":            "https://www.worcester.gov.uk",
    "wychavon":             "https://www.wychavon.gov.uk",
    "wyre forest":          "https://www.wyreforestdc.gov.uk",
    # East of England
    "cambridge":            "https://www.cambridge.gov.uk",
    "east cambridgeshire":  "https://www.eastcambs.gov.uk",
    "fenland":              "https://www.fenland.gov.uk",
    "huntingdonshire":      "https://www.huntingdonshire.gov.uk",
    "peterborough":         "https://www.peterborough.gov.uk",
    "south cambridgeshire": "https://www.southcambs.gov.uk",
    "braintree":            "https://www.braintree.gov.uk",
    "brentwood":            "https://www.brentwood.gov.uk",
    "castle point":         "https://www.castlepoint.gov.uk",
    "chelmsford":           "https://www.chelmsford.gov.uk",
    "colchester":           "https://www.colchester.gov.uk",
    "epping forest":        "https://www.eppingforestdc.gov.uk",
    "harlow":               "https://www.harlow.gov.uk",
    "maldon":               "https://www.maldon.gov.uk",
    "rochford":             "https://www.rochford.gov.uk",
    "southend-on-sea":      "https://www.southend.gov.uk",
    "tendring":             "https://www.tendringdc.gov.uk",
    "uttlesford":           "https://www.uttlesford.gov.uk",
    "broxbourne":           "https://www.broxbourne.gov.uk",
    "dacorum":              "https://www.dacorum.gov.uk",
    "east hertfordshire":   "https://www.eastherts.gov.uk",
    "hertsmere":            "https://www.hertsmere.gov.uk",
    "north hertfordshire":  "https://www.north-herts.gov.uk",
    "st albans":            "https://www.stalbans.gov.uk",
    "stevenage":            "https://www.stevenage.gov.uk",
    "three rivers":         "https://www.threerivers.gov.uk",
    "watford":              "https://www.watford.gov.uk",
    "welwyn hatfield":      "https://www.welhat.gov.uk",
    "great yarmouth":       "https://www.great-yarmouth.gov.uk",
    "norwich":              "https://www.norwich.gov.uk",
    "north norfolk":        "https://www.north-norfolk.gov.uk",
    "broadland":            "https://www.broadland.gov.uk",
    "south norfolk":        "https://www.southnorfolkandbroadland.gov.uk",
    "breckland":            "https://www.breckland.gov.uk",
    "king's lynn and west norfolk": "https://www.west-norfolk.gov.uk",
    "babergh":              "https://www.babergh.gov.uk",
    "east suffolk":         "https://www.eastsuffolk.gov.uk",
    "ipswich":              "https://www.ipswich.gov.uk",
    "mid suffolk":          "https://www.midsuffolk.gov.uk",
    "west suffolk":         "https://www.westsuffolk.gov.uk",
    "bedford":              "https://www.bedford.gov.uk",
    "central bedfordshire": "https://www.centralbedfordshire.gov.uk",
    "luton":                "https://www.luton.gov.uk",
    # London
    "barking and dagenham": "https://www.lbbd.gov.uk",
    "barnet":               "https://www.barnet.gov.uk",
    "bexley":               "https://www.bexley.gov.uk",
    "brent":                "https://www.brent.gov.uk",
    "bromley":              "https://www.bromley.gov.uk",
    "camden":               "https://www.camden.gov.uk",
    "city of london":       "https://www.cityoflondon.gov.uk",
    "croydon":              "https://www.croydon.gov.uk",
    "ealing":               "https://www.ealing.gov.uk",
    "enfield":              "https://www.enfield.gov.uk",
    "greenwich":            "https://www.royalgreenwich.gov.uk",
    "hackney":              "https://www.hackney.gov.uk",
    "hammersmith and fulham":"https://www.lbhf.gov.uk",
    "haringey":             "https://www.haringey.gov.uk",
    "harrow":               "https://www.harrow.gov.uk",
    "havering":             "https://www.havering.gov.uk",
    "hillingdon":           "https://www.hillingdon.gov.uk",
    "hounslow":             "https://www.hounslow.gov.uk",
    "islington":            "https://www.islington.gov.uk",
    "kensington and chelsea":"https://www.rbkc.gov.uk",
    "kingston upon thames": "https://www.kingston.gov.uk",
    "lambeth":              "https://www.lambeth.gov.uk",
    "lewisham":             "https://www.lewisham.gov.uk",
    "merton":               "https://www.merton.gov.uk",
    "newham":               "https://www.newham.gov.uk",
    "redbridge":            "https://www.redbridge.gov.uk",
    "richmond upon thames": "https://www.richmond.gov.uk",
    "southwark":            "https://www.southwark.gov.uk",
    "sutton":               "https://www.sutton.gov.uk",
    "tower hamlets":        "https://www.towerhamlets.gov.uk",
    "waltham forest":       "https://www.walthamforest.gov.uk",
    "wandsworth":           "https://www.wandsworth.gov.uk",
    "westminster":          "https://www.westminster.gov.uk",
    # South East
    "bracknell forest":     "https://www.bracknell-forest.gov.uk",
    "reading":              "https://www.reading.gov.uk",
    "slough":               "https://www.slough.gov.uk",
    "west berkshire":       "https://www.westberks.gov.uk",
    "windsor and maidenhead":"https://www.rbwm.gov.uk",
    "wokingham":            "https://www.wokingham.gov.uk",
    "aylesbury vale":       "https://www.buckinghamshire.gov.uk",
    "buckinghamshire":      "https://www.buckinghamshire.gov.uk",
    "chiltern":             "https://www.buckinghamshire.gov.uk",
    "south bucks":          "https://www.buckinghamshire.gov.uk",
    "wycombe":              "https://www.buckinghamshire.gov.uk",
    "brighton and hove":    "https://www.brighton-hove.gov.uk",
    "east sussex":          "https://www.eastsussex.gov.uk",
    "hastings":             "https://www.hastings.gov.uk",
    "lewes":                "https://www.lewes-eastbourne.gov.uk",
    "eastbourne":           "https://www.lewes-eastbourne.gov.uk",
    "rother":               "https://www.rother.gov.uk",
    "wealden":              "https://www.wealden.gov.uk",
    "west sussex":          "https://www.westsussex.gov.uk",
    "adur":                 "https://www.adur-worthing.gov.uk",
    "worthing":             "https://www.adur-worthing.gov.uk",
    "arun":                 "https://www.arun.gov.uk",
    "chichester":           "https://www.chichester.gov.uk",
    "crawley":              "https://www.crawley.gov.uk",
    "horsham":              "https://www.horsham.gov.uk",
    "mid sussex":           "https://www.midsussex.gov.uk",
    "ashford":              "https://www.ashford.gov.uk",
    "canterbury":           "https://www.canterbury.gov.uk",
    "dartford":             "https://www.dartford.gov.uk",
    "dover":                "https://www.dover.gov.uk",
    "folkestone and hythe": "https://www.folkestone-hythe.gov.uk",
    "gravesham":            "https://www.gravesham.gov.uk",
    "maidstone":            "https://www.maidstone.gov.uk",
    "medway":               "https://www.medway.gov.uk",
    "sevenoaks":            "https://www.sevenoaks.gov.uk",
    "swale":                "https://www.swale.gov.uk",
    "thanet":               "https://www.thanet.gov.uk",
    "tonbridge and malling":"https://www.tmbc.gov.uk",
    "tunbridge wells":      "https://www.tunbridgewells.gov.uk",
    "elmbridge":            "https://www.elmbridge.gov.uk",
    "epsom and ewell":      "https://www.epsom-ewell.gov.uk",
    "guildford":            "https://www.guildford.gov.uk",
    "mole valley":          "https://www.molevalley.gov.uk",
    "reigate and banstead": "https://www.reigate-banstead.gov.uk",
    "runnymede":            "https://www.runnymede.gov.uk",
    "spelthorne":           "https://www.spelthorne.gov.uk",
    "surrey heath":         "https://www.surreyheath.gov.uk",
    "tandridge":            "https://www.tandridge.gov.uk",
    "waverley":             "https://www.waverley.gov.uk",
    "woking":               "https://www.woking.gov.uk",
    "basingstoke and deane":"https://www.basingstoke.gov.uk",
    "east hampshire":       "https://www.easthants.gov.uk",
    "eastleigh":            "https://www.eastleigh.gov.uk",
    "fareham":              "https://www.fareham.gov.uk",
    "gosport":              "https://www.gosport.gov.uk",
    "hart":                 "https://www.hart.gov.uk",
    "havant":               "https://www.havant.gov.uk",
    "new forest":           "https://www.newforest.gov.uk",
    "portsmouth":           "https://www.portsmouth.gov.uk",
    "rushmoor":             "https://www.rushmoor.gov.uk",
    "southampton":          "https://www.southampton.gov.uk",
    "test valley":          "https://www.testvalley.gov.uk",
    "winchester":           "https://www.winchester.gov.uk",
    "isle of wight":        "https://www.iow.gov.uk",
    "cherwell":             "https://www.cherwell.gov.uk",
    "oxford":               "https://www.oxford.gov.uk",
    "south oxfordshire":    "https://www.southoxon.gov.uk",
    "vale of white horse":  "https://www.whitehorsedc.gov.uk",
    "west oxfordshire":     "https://www.westoxon.gov.uk",
    "milton keynes":        "https://www.milton-keynes.gov.uk",
    # South West
    "bath and north east somerset": "https://www.bathnes.gov.uk",
    "bristol":              "https://www.bristol.gov.uk",
    "north somerset":       "https://www.n-somerset.gov.uk",
    "south gloucestershire":"https://www.southglos.gov.uk",
    "cornwall":             "https://www.cornwall.gov.uk",
    "isles of scilly":      "https://www.scilly.gov.uk",
    "dorset":               "https://www.dorsetcouncil.gov.uk",
    "bournemouth, christchurch and poole": "https://www.bcpcouncil.gov.uk",
    "bcp":                  "https://www.bcpcouncil.gov.uk",
    "exeter":               "https://www.exeter.gov.uk",
    "east devon":           "https://www.eastdevon.gov.uk",
    "mid devon":            "https://www.middevon.gov.uk",
    "north devon":          "https://www.northdevon.gov.uk",
    "south hams":           "https://www.southhams.gov.uk",
    "teignbridge":          "https://www.teignbridge.gov.uk",
    "torridge":             "https://www.torridge.gov.uk",
    "torbay":               "https://www.torbay.gov.uk",
    "west devon":           "https://www.westdevon.gov.uk",
    "cheltenham":           "https://www.cheltenham.gov.uk",
    "cotswold":             "https://www.cotswold.gov.uk",
    "forest of dean":       "https://www.fdean.gov.uk",
    "gloucester":           "https://www.gloucester.gov.uk",
    "stroud":               "https://www.stroud.gov.uk",
    "tewkesbury":           "https://www.tewkesbury.gov.uk",
    "mendip":               "https://www.somerset.gov.uk",
    "sedgemoor":            "https://www.somerset.gov.uk",
    "somerset":             "https://www.somerset.gov.uk",
    "south somerset":       "https://www.somerset.gov.uk",
    "taunton deane":        "https://www.somerset.gov.uk",
    "wellington":           "https://www.somerset.gov.uk",
    "swindon":              "https://www.swindon.gov.uk",
    "wiltshire":            "https://www.wiltshire.gov.uk",
    "herefordshire":        "https://www.herefordshire.gov.uk",
    "shropshire":           "https://www.shropshire.gov.uk",
    "telford and wrekin":   "https://www.telford.gov.uk",
    "worcestershire":       "https://www.worcestershire.gov.uk",
    # Other
    "plymouth":             "https://www.plymouth.gov.uk",
    "torquay":              "https://www.torbay.gov.uk",
}


def clean_name(name: str) -> str:
    """Strip ' LPA' suffix and normalise to lowercase."""
    n = name.strip()
    if n.lower().endswith(" lpa"):
        n = n[:-4].strip()
    return n.lower()


def lookup_website(name: str) -> str:
    """Look up the real website URL for a council by name."""
    cleaned = clean_name(name)
    # Exact match first
    if cleaned in WEBSITE_BY_NAME:
        return WEBSITE_BY_NAME[cleaned]
    # Partial match — check if any key is contained in the cleaned name
    for key, url in WEBSITE_BY_NAME.items():
        if key in cleaned:
            return url
    return ""


def derive_website(name: str) -> str:
    """Last-resort derivation from council name."""
    clean = clean_name(name)
    for suffix in [
        " city council", " county council", " borough council",
        " district council", " metropolitan borough council",
        " london borough council", " royal borough council",
        " city and county of", " unitary authority",
        " mbc", " lbc", " dc", " bc", " mdc", " city",
    ]:
        clean = clean.replace(suffix, "")
    slug = re.sub(r"[^a-z0-9]+", "-", clean.strip()).strip("-")
    return f"https://www.{slug}.gov.uk"


def get_website(name: str) -> str:
    return lookup_website(name) or derive_website(name)


# ── Platform fingerprints ────────────────────────────────────────────────────
FINGERPRINTS = [
    ("Idox/PublicAccess", [
        "publicaccess", "/online-applications/", "idoxlive",
        "pa.idox", "idox.public", "planning.idox",
    ], ["PublicAccess", "idox", "public access portal"]),
    ("Northgate/MasterGov", [
        "mastergov", "/MasterGov", "planning.northgate", "northgate-ps",
    ], ["MasterGov", "mastergov", "Northgate"]),
    ("Civica/OcellaWeb", [
        "ocella", "/PlanningExplorer/", "civicacloud",
    ], ["OcellaWeb", "Civica", "PlanningExplorer", "ocella"]),
    ("Tascomi", [
        "tascomi",
    ], ["tascomi", "Tascomi"]),
    ("Uniform/Capita", [
        "uniformonline", "uniform.net",
    ], ["UniformOnline", "Uniform Online"]),
    ("iApply/Agile", [
        "iapply", "agileapplications",
    ], ["iApply", "Agile Applications"]),
    ("Arcus/PlanX", [
        "arcusglobal", "planx", "editor.planx",
    ], ["Arcus Global", "PlanX"]),
]

PORTAL_PATHS = [
    "/online-applications/",
    "/planning/search",
    "/planning-applications",
    "/planning/applications",
    "/planningapps/",
    "/PlanningExplorer/GeneralSearch.aspx",
    "/planning/planningsearch",
    "/planning/",
    "/services/planning/",
    "/planning-and-building/planning/",
]


def try_url(url, timeout=10):
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        if r.status_code < 400:
            return r.url, r.text
    except Exception:
        pass
    return None, None


def fp_url(url):
    u = url.lower()
    for platform, upats, _ in FINGERPRINTS:
        if any(p in u for p in upats):
            return platform
    return None


def fp_html(html):
    for platform, _, cpats in FINGERPRINTS:
        if any(p in html for p in cpats):
            return platform
    return None


def find_portal(base_url):
    base   = base_url.rstrip("/")
    parsed = urlparse(base)
    bare   = parsed.netloc.replace("www.", "")

    # 1. Try planning subdomains
    for sub in ["publicaccess", "pa", "planning"]:
        for path in ["/online-applications/", "/planning/search", "/"]:
            url = f"https://{sub}.{bare}{path}"
            final, html = try_url(url)
            if html:
                p = fp_url(final or url) or fp_html(html)
                if p:
                    return final or url, p

    # 2. Probe homepage
    _, home_html = try_url(base)
    if home_html:
        links = re.findall(
            r'href=["\']([^"\']*(?:planning|PublicAccess|mastergov|tascomi|ocella|uniform)[^"\']*)["\']',
            home_html, re.IGNORECASE)
        for link in links[:10]:
            full = link if link.startswith("http") else urljoin(base, link)
            p = fp_url(full)
            if p:
                return full, p
        p = fp_html(home_html)
        if p:
            return base, p

    # 3. Probe common paths
    for path in PORTAL_PATHS:
        url = base + path
        final, html = try_url(url)
        if html:
            p = fp_url(final or url) or fp_html(html)
            if p:
                return final or url, p

    return base, "Unknown/Custom"


def fetch_all_lpas():
    log.info("Fetching LPA list from planning.data.gov.uk ...")
    url = ("https://www.planning.data.gov.uk/entity.json"
           "?dataset=local-planning-authority&limit=500"
           "&field=name&field=reference&field=website&field=entity")
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        r.raise_for_status()
        entities = r.json().get("entities", [])
        log.info(f"  → {len(entities)} LPAs retrieved")
    except Exception as e:
        log.error(f"Failed to fetch LPAs: {e}")
        return []

    result = []
    for e in entities:
        ref     = e.get("reference", "")
        name    = e.get("name", "")
        # API website field is usually blank — use our lookup
        website = e.get("website", "").strip() or get_website(name)
        result.append({"reference": ref, "name": name, "website": website})
    return result


def load_progress():
    return json.loads(RESUME_PATH.read_text()) if RESUME_PATH.exists() else {}

def save_progress(data):
    RESUME_PATH.write_text(json.dumps(data, indent=2))

def save_results(results):
    JSON_PATH.write_text(json.dumps(results, indent=2))
    if results:
        with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=results[0].keys())
            w.writeheader(); w.writerows(results)

def print_summary(results):
    from collections import Counter
    counts = Counter(r["platform"] for r in results)
    print("\n" + "="*57)
    print("  PLATFORM BREAKDOWN")
    print("="*57)
    for p, n in counts.most_common():
        print(f"  {p:<28} {n:>3}  {'█'*min(n,40)}")
    print("="*57)
    covered = sum(1 for r in results if r["platform"] not in ("Unknown/Custom","Error"))
    print(f"  Total councils scanned: {len(results)}")
    print(f"  Identifiable platforms: {covered}")
    print(f"  Unknown/needs manual:   {len(results)-covered}")
    print("="*57+"\n")


def main():
    lpas = fetch_all_lpas()
    if not lpas:
        log.error("No LPAs retrieved — check your internet connection")
        return

    # Quick sanity check on first few
    log.info("First 3 councils with resolved websites:")
    for lpa in lpas[:3]:
        log.info(f"  {lpa['name']} → {lpa['website']}")

    progress  = load_progress()
    results   = list(progress.values())
    remaining = [l for l in lpas if l["reference"] not in progress]
    log.info(f"Total: {len(lpas)} | Done: {len(progress)} | Remaining: {len(remaining)}")
    log.info(f"Output: {OUTPUT_DIR.absolute()}")

    for i, lpa in enumerate(remaining, 1):
        ref, name, website = lpa["reference"], lpa["name"], lpa["website"]
        log.info(f"[{i}/{len(remaining)}] {name}  →  {website}")

        if not website:
            result = dict(reference=ref, name=name, website="",
                          portal_url="", platform="No website",
                          scanned_at=datetime.now().isoformat())
        else:
            portal_url, platform = find_portal(website)
            log.info(f"  → {platform}  ({portal_url})")
            result = dict(reference=ref, name=name, website=website,
                          portal_url=portal_url, platform=platform,
                          scanned_at=datetime.now().isoformat())

        results.append(result)
        progress[ref] = result

        if i % 10 == 0:
            save_progress(progress); save_results(results)
            log.info(f"  Progress saved ({len(results)} total)")

        time.sleep(DELAY)

    save_progress(progress); save_results(results)
    print_summary(results)
    log.info("Scan complete.")


if __name__ == "__main__":
    main()
