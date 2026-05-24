#!/usr/bin/env python3
"""
Fix 404s in seo-meta.csv by normalizing URLs and refetching.

The GSC export contained URL-decoded tag names (spaces, newlines), but
Squarespace tag URLs actually use hyphenated lowercase slugs. This script:
  1. Reads seo-meta.csv
  2. For rows with http_status != 200, normalizes the URL
     (whitespace -> hyphens, lowercase, collapsed) and refetches
  3. Falls back to URL-encoding if hyphen-normalization still 404s
  4. Writes the updated rows back to seo-meta.csv

Run after crawlseometa.py if there are 404s:
  source venv/bin/activate
  python3 fix-seo-meta-404s.py
"""
import csv, re, time
from urllib.parse import quote, urlsplit, urlunsplit
import requests
from bs4 import BeautifulSoup

CSV_FILE  = "seo-meta.csv"
DELAY_SEC = 0.5
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124.0.0.0 Safari/537.36")


def normalize_url(url):
    """Return one or more candidate URLs to try, in order of likelihood."""
    parts = urlsplit(url)
    raw_path = parts.path

    # Strip whitespace at edges; collapse internal whitespace runs to single hyphen
    path = re.sub(r"\s+", "-", raw_path.strip())
    path = re.sub(r"-{2,}", "-", path)            # collapse multiple hyphens
    path = re.sub(r"-+/", "/", path)              # no trailing hyphen before /
    path = re.sub(r"/-+", "/", path)              # no leading hyphen after /

    # Variant 1: hyphenated lowercase (most common SS convention)
    v1 = urlunsplit((parts.scheme, parts.netloc, path.lower(), "", ""))

    # Variant 2: hyphenated, original case
    v2 = urlunsplit((parts.scheme, parts.netloc, path, "", ""))

    # Variant 3: URL-encoded spaces (in case slug actually has spaces)
    raw_path_clean = re.sub(r"\s+", " ", raw_path.strip())
    v3 = urlunsplit((parts.scheme, parts.netloc, quote(raw_path_clean, safe="/"), "", ""))

    seen, out = set(), []
    for v in (v1, v2, v3):
        if v not in seen:
            seen.add(v)
            out.append(v)
    return out


def fetch(url):
    try:
        r = requests.get(url, timeout=20, headers={"User-Agent": UA},
                         allow_redirects=True)
        return r
    except Exception as e:
        return None


def extract_meta(resp):
    soup = BeautifulSoup(resp.text, "html.parser") if resp and resp.text else None
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
        h_tag = soup.find("h1")
        h1 = h_tag.get_text(strip=True) if h_tag else ""
    return title, desc, h1


def main():
    with open(CSV_FILE, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
        fieldnames = rows[0].keys() if rows else []

    failed = [r for r in rows if r.get("http_status") != "200"]
    print(f"Total rows: {len(rows)}, failed (non-200): {len(failed)}")

    fixed = 0
    for i, r in enumerate(failed, 1):
        original = r["url"]
        candidates = normalize_url(original)
        print(f"[{i}/{len(failed)}] {original[:90]}")

        for cand in candidates:
            resp = fetch(cand)
            if resp is None:
                continue
            print(f"      try {cand[:90]} -> {resp.status_code}")
            if resp.status_code == 200:
                title, desc, h1 = extract_meta(resp)
                r["url"] = resp.url  # final URL after any redirects
                r["seo_title"] = title
                r["meta_description"] = desc
                r["h1"] = h1
                r["http_status"] = "200"
                r["byte_size"] = str(len(resp.content))
                fixed += 1
                break
            time.sleep(DELAY_SEC)
        time.sleep(DELAY_SEC)

    print(f"\nFixed {fixed} / {len(failed)} previously-404 URLs")

    with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Updated {CSV_FILE}")


if __name__ == "__main__":
    main()
