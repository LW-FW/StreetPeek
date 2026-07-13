"""
Debug pagination - see what the next page link looks like on County Durham.
"""
import requests, re
from bs4 import BeautifulSoup

s = requests.Session()
s.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
})

base = "https://publicaccess.durham.gov.uk/online-applications"
search_url = f"{base}/search.do"

# GET monthly list page
r = s.get(f"{search_url}?action=monthlyList&searchType=Application", timeout=20)
csrf = re.search(r'name="_csrf"[^>]*value="([^"]+)"', r.text).group(1)

# Submit for Apr 26
soup = BeautifulSoup(r.text, "html.parser")
post_data = {"_csrf": csrf, "searchType": "Application", "dateType": "DC_Validated"}
for inp in soup.find_all("input", type="hidden"):
    name = inp.get("name")
    if name and name != "_csrf":
        post_data[name] = inp.get("value", "")
for sel in soup.find_all("select"):
    name = sel.get("name")
    if name and name not in post_data:
        post_data[name] = ""
post_data["month"] = "Apr 26"

r2 = s.post(f"{base}/monthlyListResults.do",
    data=post_data,
    params={"action": "firstPage"},
    headers={"Referer": r.url, "Origin": "https://publicaccess.durham.gov.uk",
             "Content-Type": "application/x-www-form-urlencoded"},
    timeout=25, allow_redirects=True)

print(f"Status: {r2.status_code} | URL: {r2.url}")
kv = re.findall(r"keyVal=([^&\"]+)", r2.text)
print(f"keyVals on page 1: {len(kv)}")

soup2 = BeautifulSoup(r2.text, "html.parser")

# Find ALL links that might be pagination
print("\nAll <a> tags with possible pagination:")
for a in soup2.find_all("a"):
    txt = a.get_text(strip=True)
    href = a.get("href", "")
    if any(x in txt.lower() for x in ["next", "page", "›", "»", ">"]) or \
       any(x in href.lower() for x in ["page", "paged", "next"]):
        print(f"  text={txt!r} href={href!r}")

# Also look for pagination container
print("\nPagination container HTML:")
for cls in ["pagination", "pager", "pages", "searchresults"]:
    el = soup2.find(class_=re.compile(cls, re.I))
    if el:
        print(f"  .{cls}: {str(el)[:300]}")

# Check total results count
print("\nResults count text:")
for el in soup2.find_all(string=re.compile(r'\d+\s*(?:result|application|record)', re.I)):
    print(f"  {el.strip()[:100]}")
