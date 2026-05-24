#!/usr/bin/env python3
"""
Augment seo-meta.csv with OG/canonical/Twitter card meta the original crawl missed.

The independent audit flagged that we never captured:
  - <link rel="canonical">
  - og:title, og:description, og:image, og:type
  - twitter:card, twitter:title, twitter:image

These are needed so post-migration we can populate Yoast's social-share
fields and preserve canonical signals. Without them, Yoast will pick
fallbacks that may use broken images and missing custom titles.

This script:
  1. Reads existing seo-meta.csv
  2. For each row with http_status == "200", re-fetches the URL and extracts
     the additional meta tags
  3. Writes seo-meta-augmented.csv with all original columns + new ones
  4. Skips rows that already errored (no point re-fetching deleted URLs)

Run (in same folder as seo-meta.csv):
  source venv/bin/activate
  python3 augment-seo-meta.py

Estimated time: ~15 min for 2,145 OK rows at 0.4s/req with 1 worker.
"""
import csv, re, time, sys, os
import requests
from bs4 import BeautifulSoup

IN_FILE  = "seo-meta.csv"
OUT_FILE = "seo-meta-augmented.csv"
DELAY    = 0.4
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124.0.0.0 Safari/537.36")

NEW_COLUMNS = [
    "canonical",
    "og_title", "og_description", "og_image", "og_type",
    "twitter_card", "twitter_title", "twitter_image",
]


def _meta_content(soup, **attrs):
    tag = soup.find("meta", attrs=attrs) if soup else None
    return tag["content"].strip() if tag and tag.get("content") else ""


def fetch_extra(url):
    try:
        r = requests.get(url, timeout=20, headers={"User-Agent": UA},
                         allow_redirects=True)
        if r.status_code != 200:
            return {c: "" for c in NEW_COLUMNS}
        soup = BeautifulSoup(r.text, "html.parser")
        link_can = soup.find("link", attrs={"rel": re.compile("^canonical$", re.I)})
        return {
            "canonical":      link_can["href"].strip() if link_can and link_can.get("href") else "",
            "og_title":       _meta_content(soup, property=re.compile("^og:title$", re.I)),
            "og_description": _meta_content(soup, property=re.compile("^og:description$", re.I)),
            "og_image":       _meta_content(soup, property=re.compile("^og:image$", re.I)),
            "og_type":        _meta_content(soup, property=re.compile("^og:type$", re.I)),
            "twitter_card":   _meta_content(soup, name=re.compile("^twitter:card$", re.I)),
            "twitter_title":  _meta_content(soup, name=re.compile("^twitter:title$", re.I)),
            "twitter_image":  _meta_content(soup, name=re.compile("^twitter:image$", re.I)),
        }
    except Exception as e:
        return {c: "" for c in NEW_COLUMNS}


def main():
    if not os.path.exists(IN_FILE):
        sys.exit(f"Missing {IN_FILE}")
    with open(IN_FILE, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
        in_fields = list(rows[0].keys()) if rows else []
    out_fields = in_fields + [c for c in NEW_COLUMNS if c not in in_fields]

    to_fetch = [r for r in rows if r.get("http_status") == "200"]
    skip = len(rows) - len(to_fetch)
    print(f"Augmenting {len(to_fetch)} 200-status rows (skipping {skip} non-200)\n")

    with open(OUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=out_fields)
        writer.writeheader()
        for i, r in enumerate(rows, 1):
            for c in NEW_COLUMNS:
                r.setdefault(c, "")
            if r.get("http_status") == "200":
                print(f"[{i}/{len(rows)}] {r['url'][:90]}", flush=True)
                extra = fetch_extra(r["url"])
                r.update(extra)
                time.sleep(DELAY)
            writer.writerow(r)

    print(f"\nDone. Wrote {OUT_FILE}")


if __name__ == "__main__":
    main()
