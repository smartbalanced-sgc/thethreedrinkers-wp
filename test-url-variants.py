#!/usr/bin/env python3
"""
Diagnostic: test URL-normalization variants against the top 5 failed URLs
to confirm the right approach BEFORE running the full fixer.

Run:
  source venv/bin/activate
  python3 test-url-variants.py
"""
import csv, re
from urllib.parse import quote, urlsplit, urlunsplit
import requests

CSV_FILE = "seo-meta.csv"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124.0.0.0 Safari/537.36")
SAMPLE_SIZE = 5

def variants(url):
    parts = urlsplit(url)
    raw = parts.path
    # Strip control chars and collapse whitespace
    clean = re.sub(r"\s+", " ", raw).strip()

    # Build variants of the path
    hyphen_lower = re.sub(r"\s+", "-", clean).lower()
    hyphen_lower = re.sub(r"-{2,}", "-", hyphen_lower).strip("-")
    hyphen_lower = re.sub(r"^-|-$", "", hyphen_lower)
    # Re-insert leading slash if path started with /
    if not hyphen_lower.startswith("/"):
        hyphen_lower = "/" + hyphen_lower.lstrip("/")

    hyphen_original = re.sub(r"\s+", "-", clean)
    if not hyphen_original.startswith("/"):
        hyphen_original = "/" + hyphen_original.lstrip("/")

    encoded = quote(clean, safe="/")

    # Strip punctuation entirely (?, !, &, etc.) — SS slugs often drop these
    no_punct = re.sub(r"[^\w\s/]+", "", clean)
    no_punct = re.sub(r"\s+", "-", no_punct).lower().strip("-")
    if not no_punct.startswith("/"):
        no_punct = "/" + no_punct.lstrip("/")
    no_punct = re.sub(r"-{2,}", "-", no_punct)

    cands = [
        ("hyphen-lower",       hyphen_lower),
        ("hyphen-original",    hyphen_original),
        ("encoded-spaces",     encoded),
        ("no-punct-lower",     no_punct),
    ]
    out = []
    seen = set()
    for label, p in cands:
        full = urlunsplit((parts.scheme, parts.netloc, p, "", ""))
        if full not in seen:
            seen.add(full)
            out.append((label, full))
    return out


def main():
    with open(CSV_FILE, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    failed = [r for r in rows if r.get("http_status") != "200"]
    failed.sort(key=lambda r: -int(r.get("gsc_clicks") or "0"))
    sample = failed[:SAMPLE_SIZE]

    print(f"Testing top {len(sample)} failed URLs (by GSC clicks)\n")
    for i, r in enumerate(sample, 1):
        print(f"=== [{i}] clicks={r['gsc_clicks']} ===")
        print(f"ORIGINAL: {r['url']!r}")
        for label, cand in variants(r["url"]):
            try:
                resp = requests.get(cand, timeout=15,
                                    headers={"User-Agent": UA},
                                    allow_redirects=True)
                status = resp.status_code
                final = resp.url if resp.url != cand else ""
            except Exception as e:
                status = f"ERR:{e}"
                final = ""
            mark = "✓" if str(status) == "200" else "✗"
            print(f"  {mark} {label:<18s} {status}  {cand}")
            if final:
                print(f"     -> final: {final}")
        print()


if __name__ == "__main__":
    main()
