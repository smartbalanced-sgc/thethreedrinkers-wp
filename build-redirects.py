#!/usr/bin/env python3
"""
Generate the production redirect map for the SS→WP migration.

The independent SEO audit found that 544 of 707 traffic-driving tag URLs
contain URL-encoded characters (spaces, ?, &, /, +, !, comma) that WordPress
slugifies away. Without redirects, those URLs 404 on launch — costing
~150,000+ clicks/16 months.

This script:
  1. Reads seo-meta.csv (every URL we crawled, with GSC clicks attached).
  2. For each TAG URL, computes the WP-equivalent URL (using sanitize_title rules).
  3. Where SS URL ≠ WP URL, emits a redirect.
  4. Also reads redirects-needed.csv (slug fixes + category renames produced by
     clean-wxr.py) and converts to the same format.
  5. Outputs redirects.csv in **Redirection-plugin-compatible** format:
        source_url, target_url, code, regex
     - source_url: full path (with leading /, trailing slash where applicable)
     - target_url: full path (likewise)
     - code: always 301
     - regex: 0 (literal match)

Inputs (in same folder):
  seo-meta.csv                          (from crawlseometa.py + fix-seo-meta.py)
  redirects-needed.csv                  (from clean-wxr.py)
  SquarespaceWordpressExport-cleaned.xml (to map tag slugs to canonical WP slugs)

Output:
  redirects.csv                         (import-ready for Redirection plugin)
  redirects-summary.txt                 (audit log: clicks preserved, types of redirect)
"""
import csv, re, sys, os, unicodedata
from collections import defaultdict
from urllib.parse import urlsplit, unquote

CSV_IN_META   = "seo-meta.csv"
CSV_IN_FIXES  = "redirects-needed.csv"
WXR_FILE      = "SquarespaceWordpressExport-cleaned.xml"
CSV_OUT       = "redirects.csv"
SUMMARY_OUT   = "redirects-summary.txt"
BASE          = "/magazine-content"


def slugify_like_wp(text):
    """Mimic WP's sanitize_title()."""
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


def normalize_path(path):
    """Ensure a path starts with / and ends with / (WP convention for archives)."""
    if not path.startswith("/"):
        path = "/" + path
    if not path.endswith("/"):
        path = path + "/"
    return path


def load_wxr_tag_slugs(wxr_path):
    """Return set of WXR tag nicenames so we know what WP will create."""
    if not os.path.exists(wxr_path):
        return set()
    with open(wxr_path, encoding="utf-8", errors="replace") as f:
        xml = f.read()
    nicenames = set(re.findall(
        r'<category domain="post_tag" nicename="([^"]+)"', xml
    ))
    return nicenames


def main():
    # === Step 1: Load existing redirects (slug fixes + category renames) ===
    fixes = []
    if os.path.exists(CSV_IN_FIXES):
        with open(CSV_IN_FIXES, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                fixes.append(row)

    # === Step 2: Load crawl CSV ===
    if not os.path.exists(CSV_IN_META):
        sys.exit(f"Missing {CSV_IN_META}")
    with open(CSV_IN_META, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    # === Step 3: Build redirects ===
    redirects = []          # list of dicts: source_url, target_url, code, regex, reason, clicks
    seen_sources = set()    # prevent duplicate source URLs

    def add(source, target, reason, clicks=0, regex=False):
        if source in seen_sources:
            return
        if source == target:
            return  # no redirect needed
        seen_sources.add(source)
        redirects.append({
            "source_url": source,
            "target_url": target,
            "code": "301",
            "regex": "1" if regex else "0",
            "reason": reason,
            "clicks": clicks,
        })

    # 3a. Tag URLs: compare SS-encoded form to WP slug
    tag_count = 0
    tag_clicks_at_risk = 0
    for r in rows:
        if r.get("url_type") != "tag":
            continue
        url = r["url"]
        parts = urlsplit(url)
        # Extract the part after /magazine-content/tag/
        m = re.match(r"^/magazine-content/tag/(.+)$", parts.path, re.DOTALL)
        if not m:
            continue
        ss_tag_raw = m.group(1)
        # Decode what GSC passed us — could be %20-encoded or have spaces
        ss_decoded = unquote(ss_tag_raw)
        wp_slug = slugify_like_wp(ss_decoded)
        if not wp_slug:
            continue

        ss_source = normalize_path(parts.path)
        wp_target = normalize_path(f"/magazine-content/tag/{wp_slug}")

        if ss_source != wp_target:
            clicks = int(r.get("gsc_clicks") or "0")
            tag_clicks_at_risk += clicks
            tag_count += 1
            add(ss_source, wp_target, "tag-url-encoding", clicks=clicks)

    # 3b. Slug fixes (date-pathed posts, leading dashes)
    slug_fix_count = 0
    for f in fixes:
        old = f.get("old_slug","")
        new = f.get("new_slug","")
        reason = f.get("reason","")
        if reason.startswith("category-rename:"):
            # already a full path - use as-is
            add(normalize_path(old), normalize_path(new), reason)
        elif old and new:
            # slug-only entries — prepend /magazine-content/
            old_url = normalize_path(f"/magazine-content/{old}")
            new_url = normalize_path(f"/magazine-content/{new}")
            slug_fix_count += 1
            add(old_url, new_url, "slug-normalize")
            # Also handle the /venues/ prefix variant for date-pathed slugs
            if old.startswith("2") and "/" in old:
                venues_url = normalize_path(f"/venues/{old}")
                add(venues_url, new_url, "venues-prefix-flatten")

    # 3c. Known prefix changes (shop-content, three-drinkers-news, venues)
    # These are emitted as regex redirects so any future URL under those prefixes also redirects
    prefix_redirects = [
        (r"^/shop-content/(.*)$", "/magazine-content/$1", "prefix:shop-content"),
        (r"^/three-drinkers-news/(.*)$", "/magazine-content/$1", "prefix:three-drinkers-news"),
    ]
    for pattern, target, reason in prefix_redirects:
        add(pattern, target, reason, regex=True)

    # 3d. Known SS-only pages that have no WP equivalent — redirect to homepage
    # /welcome was a SS welcome page (72 GSC clicks) not imported to WP
    add("/welcome/", "/", "page-gone:welcome", clicks=72)

    # === Step 4: Write outputs ===
    fieldnames = ["source_url", "target_url", "code", "regex", "reason", "clicks"]
    with open(CSV_OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        # Sort: literal redirects first (alphabetical), regex redirects last
        for r in sorted(redirects, key=lambda x: (x["regex"] == "1", x["source_url"])):
            w.writerow(r)

    # === Summary ===
    summary = []
    summary.append(f"Total redirects generated: {len(redirects)}\n")
    by_reason = defaultdict(lambda: {"count": 0, "clicks": 0})
    for r in redirects:
        by_reason[r["reason"]]["count"] += 1
        by_reason[r["reason"]]["clicks"] += int(r.get("clicks") or 0)
    summary.append(f"{'Reason':<30s}  {'Count':>6s}  {'Clicks/16mo':>11s}")
    summary.append("-" * 55)
    for reason, data in sorted(by_reason.items(), key=lambda x: -x[1]["clicks"]):
        summary.append(f"{reason:<30s}  {data['count']:>6}  {data['clicks']:>11,}")
    summary.append(f"\nTotal clicks protected by redirects: {sum(d['clicks'] for d in by_reason.values()):,}")

    with open(SUMMARY_OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(summary))

    print("\n".join(summary))
    print(f"\nWrote {CSV_OUT} ({len(redirects)} redirects)")
    print(f"Wrote {SUMMARY_OUT}")


if __name__ == "__main__":
    main()
