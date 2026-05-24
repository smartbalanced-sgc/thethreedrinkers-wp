#!/usr/bin/env python3
"""
Final fixer: recover SEO meta for the 545 URLs that 404'd in the initial crawl.

Uses the proven WXR-canonical strategy (validated at 99.8% success in
diagnose404s_round2.py). Fetches each failed URL using its canonical
Squarespace name, extracts title / meta description / H1, and updates
seo-meta.csv in place.

Run:
  source venv/bin/activate
  python3 fix-seo-meta.py

Backup of original csv is written to seo-meta.csv.bak before modification.
"""
import csv, re, os, sys, time, unicodedata, shutil
from urllib.parse import quote, urlsplit
import requests
from bs4 import BeautifulSoup

CSV_FILE = "seo-meta.csv"
WXR_FILE = "SquarespaceWordpressExport05232026.xml"
BASE     = "https://www.thethreedrinkers.com"
DELAY    = 0.4
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124.0.0.0 Safari/537.36")


def load_wxr_tags(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        xml = f.read()
    pat = re.compile(
        r'<category domain="(post_tag|category)" nicename="([^"]+)"><!\[CDATA\[([^\]]+)\]\]></category>'
    )
    seen, out = set(), []
    for domain, nicename, name in pat.findall(xml):
        key = (domain, nicename)
        if key in seen:
            continue
        seen.add(key)
        out.append((domain, nicename, name))
    return out


def slugify_like_wp(text):
    s = unicodedata.normalize("NFKD", text)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    s = s.replace("’", "").replace("‘", "").replace("'", "")
    s = s.replace("“", "").replace("”", "").replace("\"", "")
    s = s.replace("–", "-").replace("—", "-")
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"\s+", "-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s


def url_kind_and_slug(url):
    path = urlsplit(url).path
    m = re.match(r"^/magazine-content/tag/(.+)$", path, re.DOTALL)
    if m: return "tag", m.group(1)
    m = re.match(r"^/magazine-content/category/(.+)$", path, re.DOTALL)
    if m: return "category", m.group(1)
    return "other", path


def lookup_canonical(slug_raw, wxr_tags, kind):
    target = slugify_like_wp(slug_raw)
    target_domain = "post_tag" if kind == "tag" else "category"
    for d, nic, name in wxr_tags:
        if d == target_domain and nic == target:
            return name
    for d, nic, name in wxr_tags:
        if d == target_domain and slugify_like_wp(name) == target:
            return name
    return None


def build_canonical_url(failed_url, wxr_tags):
    kind, slug = url_kind_and_slug(failed_url)
    if kind not in ("tag", "category"):
        return None
    canonical = lookup_canonical(slug, wxr_tags, kind)
    if not canonical:
        return None
    base = "tag" if kind == "tag" else "category"
    return f"{BASE}/magazine-content/{base}/{quote(canonical, safe='')}"


def fetch_meta(url, max_retries=4):
    backoff = 2
    for _ in range(max_retries):
        try:
            r = requests.get(url, timeout=20,
                             headers={"User-Agent": UA},
                             allow_redirects=True)
            if r.status_code == 429:
                time.sleep(backoff); backoff *= 2; continue
            soup = BeautifulSoup(r.text, "html.parser") if r.text else None
            title = soup.title.string.strip() if soup and soup.title and soup.title.string else ""
            desc = ""
            if soup:
                d = soup.find("meta", attrs={"name": re.compile("^description$", re.I)})
                desc = d["content"].strip() if d and d.get("content") else ""
                if not desc:
                    og = soup.find("meta", attrs={"property": re.compile("^og:description$", re.I)})
                    desc = og["content"].strip() if og and og.get("content") else ""
            h1 = ""
            if soup:
                h = soup.find("h1")
                h1 = h.get_text(strip=True) if h else ""
            return r.url, str(r.status_code), title, desc, h1, len(r.content)
        except Exception as e:
            return url, f"ERR:{type(e).__name__}", "", "", "", 0
    return url, "429", "", "", "", 0


def main():
    if not os.path.exists(WXR_FILE):
        sys.exit(f"Missing {WXR_FILE}")
    if not os.path.exists(CSV_FILE):
        sys.exit(f"Missing {CSV_FILE}")

    print(f"Backing up {CSV_FILE} -> {CSV_FILE}.bak")
    shutil.copyfile(CSV_FILE, CSV_FILE + ".bak")

    print(f"Loading WXR tags ...")
    wxr_tags = load_wxr_tags(WXR_FILE)
    print(f"  {len(wxr_tags)} tag/category entries\n")

    with open(CSV_FILE, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
        fieldnames = list(rows[0].keys()) if rows else []

    failed_idx = [i for i, r in enumerate(rows) if r.get("http_status") != "200"]
    print(f"Recovering {len(failed_idx)} previously-404'd URLs sequentially (~5 min)\n")

    fixed = 0
    for n, i in enumerate(failed_idx, 1):
        r = rows[i]
        canonical_url = build_canonical_url(r["url"], wxr_tags)
        if not canonical_url:
            print(f"[{n}/{len(failed_idx)}] SKIP (no WXR match): {r['url'][:80]}")
            continue
        time.sleep(DELAY)
        final, status, title, desc, h1, size = fetch_meta(canonical_url)
        if status == "200":
            r["url"] = final
            r["seo_title"] = title
            r["meta_description"] = desc
            r["h1"] = h1
            r["http_status"] = "200"
            r["byte_size"] = str(size)
            fixed += 1
            print(f"[{n}/{len(failed_idx)}] OK   clicks={r.get('gsc_clicks','0'):>5}  {canonical_url[:90]}")
        else:
            r["http_status"] = status
            print(f"[{n}/{len(failed_idx)}] {status:>4} clicks={r.get('gsc_clicks','0'):>5}  {canonical_url[:90]}")

    with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    print(f"\nDone. Recovered {fixed} / {len(failed_idx)} URLs.")
    print(f"{CSV_FILE} updated. Original kept as {CSV_FILE}.bak.")


if __name__ == "__main__":
    main()
