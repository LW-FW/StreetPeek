"""
Debug mechanize — see exactly what Leeds returns.
"""
import mechanize
import http.cookiejar
import re
from bs4 import BeautifulSoup

PORTAL_URL = "https://publicaccess.leeds.gov.uk/online-applications/"

def make_browser():
    br = mechanize.Browser()
    cj = http.cookiejar.LWPCookieJar()
    br.set_cookiejar(cj)
    br.set_handle_equiv(True)
    br.set_handle_redirect(True)
    br.set_handle_referer(True)
    br.set_handle_robots(False)
    br.set_handle_refresh(mechanize._http.HTTPRefreshProcessor(), max_time=1)
    br.addheaders = [
        ("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"),
        ("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"),
        ("Accept-Language", "en-GB,en;q=0.9"),
    ]
    return br

br = make_browser()
base = "https://publicaccess.leeds.gov.uk/online-applications"
search_url = f"{base}/search.do"

print("=== Step 1: Open search page ===")
resp = br.open(f"{search_url}?action=advanced", timeout=20)
html = resp.read().decode("utf-8", errors="replace")
soup = BeautifulSoup(html, "html.parser")
print(f"Title: {soup.title.string.strip() if soup.title else 'none'}")
print(f"Forms found: {len(list(br.forms()))}")
for i, form in enumerate(br.forms()):
    print(f"  Form {i}: action={form.action!r} method={form.method!r}")
    controls = [(c.name, c.__class__.__name__, getattr(c, 'value', '?')) 
                for c in form.controls if c.name]
    for name, type_, val in controls[:15]:
        print(f"    {name!r} ({type_}): {str(val)[:50]!r}")
print()

print("=== Step 2: Fill and submit form ===")
br.select_form(nr=0)
try:
    br["date(applicationValidatedStart)"] = "01/02/2026"
    br["date(applicationValidatedEnd)"]   = "01/05/2026"
    print("Date fields set OK")
except Exception as e:
    print(f"Error setting date fields: {e}")
    # Show available controls
    form = list(br.forms())[0]
    print("Available controls:")
    for c in form.controls:
        print(f"  {c.name!r}")

resp2 = br.submit()
html2 = resp2.read().decode("utf-8", errors="replace")
soup2 = BeautifulSoup(html2, "html.parser")

print(f"Response title: {soup2.title.string.strip() if soup2.title else 'none'}")
print(f"Response URL: {resp2.geturl()}")
print()

# Check what's in the response
results_li   = soup2.find_all("li", class_=re.compile(r"searchresult", re.I))
results_text = "searchresult" in html2.lower()
key_vals     = re.findall(r"keyVal=([^&\"]+)", html2)
print(f"<li class=searchresult> found: {len(results_li)}")
print(f"'searchresult' in HTML: {results_text}")
print(f"keyVal= occurrences: {len(key_vals)}")

if key_vals:
    print(f"First keyVal: {key_vals[0]}")
    # Show surrounding HTML
    idx = html2.find("keyVal=")
    print(f"Context: {html2[max(0,idx-200):idx+300]}")
else:
    # Show what classes are on <li> elements
    all_li = soup2.find_all("li")
    li_classes = set()
    for li in all_li[:50]:
        if li.get("class"):
            li_classes.add(tuple(li["class"]))
    print(f"Li classes found: {li_classes}")
    
    # Show a chunk of the body
    body = soup2.find("body")
    if body:
        text = body.get_text()[:1000]
        print(f"Body text: {text}")
