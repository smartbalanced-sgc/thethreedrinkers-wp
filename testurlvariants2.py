#!/usr/bin/env python3
"""
Diagnostic v2: use the WXR file as the source of truth for tag URL slugs.

For each failed GSC URL, look up the matching tag in the WXR by hyphenated
nicename, then URL-encode the canonical original NAME (preserving whitespace,
capitals, punctuation) to construct the real SS URL.

Run:
  source venv/bin/activate
  python3 testurlvariants2.py
"""
import csv, re, sys, os
from urllib.parse import quote, urlsplit
import requests

CSV_FILE  = "seo-meta.csv"
WXR_FILE  = "SquarespaceWordpressExport05232026.xml"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124.0.0.0 Safari/537.36")
SAMPLE_SIZE = 10
BASE = "https://www.thethreedrinkers.com"


def load_tag_index(wxr_path):
    """Return dict: hyphenated-slug -> canonical name (with original whitespace)."""
    with open(wxr_path, encoding="utf-8", errors="replace") as f:
        xml = f.read()
    pat = re.compile(
        r'<category domain="post_tag" nicename="([^"]+)"><!\[CDATA\[([^\]]+)\]\]></category>'
    )
    idx = {}
    for nicename, name in pat.findall(xml):
        if nicename not in idx:
            idx[nicename] = name
    return idx


def slug_from_gsc(url):
    """Extract the tag slug part of a GSC URL and normalize to hyphenated form for lookup."""
    path = urlsplit(url).path  # /magazine-content/tag/adults-only soft play \ncentre nottingham
    m = re.match(r"/magazine-content/tag/(.+)$", path, re.DOTALL)
    if not m:
        return None
    raw = m.group(1)
    norm = re.sub(r"\s+", "-", raw).lower()
    norm = re.sub(r"-{2,}", "-", norm).strip("-")
    # strip common URL punctuation that doesn't appear in WP nicenames
    norm = re.sub(r"[?!&,'\"]", "", norm)
    return norm


def fetch(url):
    try:
        r = requests.get(url, timeout=15,
                         headers={"User-Agent": UA}, allow_redirects=True)
        return r.status_code, r.url
    except Exception as e:
        return f"ERR:{e}", ""


def main():
    if not os.path.exists(WXR_FILE):
        sys.exit(f"Missing {WXR_FILE} - put the SS export in this folder")
    print(f"Loading tag index from {WXR_FILE} ...")
    tag_idx = load_tag_index(WXR_FILE)
    print(f"  loaded {len(tag_idx)} unique tag slugs\n")

    with open(CSV_FILE, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    failed = [r for r in rows if r.get("http_status") != "200"
              and "/tag/" in r.get("url", "")]
    failed.sort(key=lambda r: -int(r.get("gsc_clicks") or "0"))
    sample = failed[:SAMPLE_SIZE]

    print(f"Testing top {len(sample)} failed TAG URLs against WXR-derived URLs:\n")
    matched, hit = 0, 0
    for i, r in enumerate(sample, 1):
        print(f"=== [{i}] clicks={r['gsc_clicks']} ===")
        print(f"GSC URL: {r['url']!r}")
        slug = slug_from_gsc(r["url"])
        print(f"  derived slug: {slug!r}")
        canonical = tag_idx.get(slug)
        if not canonical:
            # try fuzzy: find any nicename that startswith / equals normalized form
            cands = [k for k in tag_idx if k == slug]
            if not cands:
                # fallback: try first-100-char prefix match
                cands = [k for k in tag_idx if k.startswith(slug[:30])]
            print(f"  WXR lookup: NOT FOUND. Closest matches: {cands[:3]}")
            print()
            continue
        matched += 1
        print(f"  WXR name (canonical): {canonical!r}")

        # Build URL with canonical name url-encoded
        url = f"{BASE}/magazine-content/tag/{quote(canonical, safe='')}"
        status, final = fetch(url)
        mark = "✓" if str(status) == "200" else "✗"
        print(f"  {mark} {status}  {url}")
        if str(status) == "200":
            hit += 1
        if final and final != url:
            print(f"     -> redirected to: {final}")
        print()

    print(f"=== SUMMARY: {matched}/{len(sample)} matched in WXR, "
          f"{hit}/{len(sample)} returned 200 ===")


if __name__ == "__main__":
    main()
