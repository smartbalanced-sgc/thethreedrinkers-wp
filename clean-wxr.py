#!/usr/bin/env python3
"""
Clean the Squarespace WXR export for safe import into WordPress.

Operations:
  1. Drop attachment items (we sideload with Auto Upload Images post-import).
  2. Drop draft / pending posts (per user decision).
  3. Build "keep" set for tags from GSC traffic + WXR usage; remove all
     other tag references from posts.
  4. Fix malformed article slugs (leading dash, date-pathed).
  5. Merge duplicate author accounts (Adrian, Helena).
  6. Normalize duplicate / typo'd categories.

Inputs (in same folder):
  SquarespaceWordpressExport05232026.xml
  Pages.csv                                 (GSC export, optional but recommended)

Output:
  SquarespaceWordpressExport-cleaned.xml    (ready for WP Importer)
  cleanup-report.txt                        (audit log of all changes)
  redirects-needed.csv                      (list of slug changes needing 301s)
"""
import csv, re, sys, os, unicodedata
from collections import Counter, defaultdict


def slugify_like_wp(text):
    """Mimic WP's sanitize_title: accents stripped, punctuation removed, hyphenated."""
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

WXR_IN   = "SquarespaceWordpressExport05232026.xml"
WXR_OUT  = "SquarespaceWordpressExport-cleaned.xml"
GSC_FILE = "Pages.csv"
REPORT   = "cleanup-report.txt"
REDIRECT = "redirects-needed.csv"

TAG_KEEP_MIN_USES = 3                # keep tags used >= 3 times even without GSC clicks
KEEP_DRAFTS       = False
KEEP_ATTACHMENTS  = False

# Author merge map: (dc:creator value → canonical wp:author_login that exists in WXR header)
# Adrian only has ONE account in the WXR (login = his email) so no merge needed for him.
# Helena has two accounts -> we collapse her email login into her HelenaNicklin account.
AUTHOR_MERGES = {
    "helena@thethreedrinkers.com": "HelenaNicklin",
}

# Category renames: from-nicename -> (new-nicename, new-name).
# Use this when the slug actually changes (different URL).
# Each one will produce a 301 redirect entry in redirects-needed.csv.
CATEGORY_RENAMES = {
    "isaly":            ("islay",         "Islay"),         # typo fix
    "sinagpore":        ("singapore",     "Singapore"),     # typo fix
    "gear-and-gadgets": ("gear-gadgets",  "Gear & Gadgets"),# merge into ampersand variant
}

# Category name normalizations: slug STAYS THE SAME, only the display name
# changes. WP de-dupes terms by slug on import, so these auto-merge without
# any URL change. No redirect needed.
CATEGORY_NAME_NORMALIZE = {
    "whisky":   "Whisky",      # collapse 'whisky' (45 posts) into 'Whisky' (257 posts)
    "scotch":   "Scotch",
    "rye":      "Rye",
    "new-york": "New York",
}


def log(report, msg):
    report.append(msg)
    print(msg)


def load_gsc_tag_clicks(path, wxr_nicenames):
    """Return dict: nicename -> total clicks. Match GSC URLs to WXR nicenames
    by slugifying the GSC tag path and exact-match-then-fuzzy-match against
    the set of real nicenames from the WXR."""
    out = {}
    if not os.path.exists(path):
        return out
    # Build WP-slug -> nicename lookup (some nicenames are already that, some need re-slugifying)
    nicename_set = set(wxr_nicenames)
    re_slugified = {slugify_like_wp(n): n for n in wxr_nicenames}

    unmatched = 0
    with open(path, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            url = (row.get("Top pages") or "").strip()
            m = re.search(r"/magazine-content/tag/(.+)$", url, re.DOTALL)
            if not m:
                continue
            clicks = int((row.get("Clicks") or "0").replace(",", ""))
            target = slugify_like_wp(m.group(1))
            # Try exact nicename match (WP slug == WXR nicename)
            if target in nicename_set:
                out[target] = out.get(target, 0) + clicks
                continue
            # Fall back to re-slugified lookup
            if target in re_slugified:
                hit = re_slugified[target]
                out[hit] = out.get(hit, 0) + clicks
                continue
            unmatched += 1
    if unmatched:
        print(f"  WARN: {unmatched} GSC tag URLs did not match any WXR nicename")
    return out


def fix_slug(slug):
    """Return cleaned slug + reason if changed, else (slug, None)."""
    original = slug
    # Flatten date-pathed: 2019/2/24/foo -> foo
    if "/" in slug:
        slug = slug.rstrip("/").split("/")[-1]
    # Strip leading/trailing dashes
    slug = slug.strip("-")
    slug = re.sub(r"-{2,}", "-", slug)
    if slug != original:
        return slug, f"slug:{original}->{slug}"
    return slug, None


def main():
    report = []
    log(report, f"Reading {WXR_IN} ...")
    if not os.path.exists(WXR_IN):
        sys.exit(f"Missing {WXR_IN}")
    with open(WXR_IN, encoding="utf-8", errors="replace") as f:
        xml = f.read()
    log(report, f"  {len(xml):,} bytes\n")

    # === Phase 1: Count tag usage + find canonical name per tag ===
    # For each tag slug, also track which DISPLAY NAME is used most often
    # so we can normalize inconsistent capitalisation.
    tag_usage = Counter()
    tag_name_freq = defaultdict(Counter)  # slug -> Counter of names
    for slug, name in re.findall(
        r'<category domain="post_tag" nicename="([^"]+)"><!\[CDATA\[([^\]]+)\]\]></category>',
        xml
    ):
        tag_usage[slug] += 1
        tag_name_freq[slug][name] += 1
    # Canonical name per tag = most-frequent variant
    tag_canonical_name = {slug: names.most_common(1)[0][0]
                          for slug, names in tag_name_freq.items()}
    multi_variant = sum(1 for names in tag_name_freq.values() if len(names) > 1)
    log(report, f"Tag display-name variants normalized: {multi_variant} slugs had "
                f"multiple case/spelling variants; using the most-frequent for each\n")

    # === Phase 2: Load GSC traffic ===
    gsc = load_gsc_tag_clicks(GSC_FILE, set(tag_usage.keys()))
    log(report, f"GSC tag traffic loaded: {len(gsc)} tags with clicks "
                f"(sum {sum(gsc.values()):,} clicks)\n")

    # === Phase 3: Build keep set ===
    keep_tags = set()
    for slug in gsc:
        keep_tags.add(slug)
    for slug, uses in tag_usage.items():
        if uses >= TAG_KEEP_MIN_USES:
            keep_tags.add(slug)

    total_tags = len(tag_usage)
    drop_count = sum(1 for t in tag_usage if t not in keep_tags)
    log(report, f"Tag pruning: {len(keep_tags)} kept, {drop_count} dropped "
                f"(of {total_tags} unique tags)\n")

    # === Phase 4: Walk items, build cleaned XML ===
    # Split file: everything up to first <item> = header, then items, then footer
    pre_items_match = re.search(r'^(.*?)(?=<item>)', xml, re.DOTALL)
    if not pre_items_match:
        sys.exit("No <item> tags found in WXR")
    header = pre_items_match.group(1)
    post_items_match = re.search(r'(</item>\s*)([^<]*</channel>\s*</rss>\s*)$',
                                   xml, re.DOTALL)
    footer = post_items_match.group(2) if post_items_match else "</channel></rss>\n"

    items = re.findall(r'<item>.*?</item>', xml, re.DOTALL)
    log(report, f"Items found: {len(items)}\n")

    # === Author merges in header ===
    cleaned_header = header
    for src, dst in AUTHOR_MERGES.items():
        # We just leave both authors in the export; reassignments happen via dc:creator below
        pass

    kept_items, dropped_items = [], Counter()
    redirects_needed = []

    for item in items:
        ptype_m = re.search(r"<wp:post_type>([^<]+)", item)
        status_m = re.search(r"<wp:status>([^<]+)", item)
        ptype = ptype_m.group(1).strip() if ptype_m else "unknown"
        status = status_m.group(1).strip() if status_m else "unknown"

        # Drop attachments
        if ptype == "attachment" and not KEEP_ATTACHMENTS:
            dropped_items["attachment"] += 1
            continue
        # Drop drafts / pending
        if status in ("draft", "pending", "trash", "auto-draft") and not KEEP_DRAFTS:
            dropped_items[f"status:{status}"] += 1
            continue

        # --- Slug fix ---
        slug_m = re.search(r"<wp:post_name>([^<]*)</wp:post_name>", item)
        if slug_m and slug_m.group(1):
            old_slug = slug_m.group(1)
            new_slug, reason = fix_slug(old_slug)
            if reason:
                item = item.replace(f"<wp:post_name>{old_slug}</wp:post_name>",
                                     f"<wp:post_name>{new_slug}</wp:post_name>")
                # Also update the <link> if it referenced the old slug
                redirects_needed.append({
                    "old_slug": old_slug,
                    "new_slug": new_slug,
                    "reason": reason,
                })

        # --- Tag filtering + display-name normalization ---
        # Remove tags not in keep_tags; for kept tags, force the canonical (most-frequent) name.
        def repl_tag(m):
            nicename = m.group(1)
            if nicename not in keep_tags:
                return ""
            canonical = tag_canonical_name.get(nicename, m.group(2))
            return f'<category domain="post_tag" nicename="{nicename}"><![CDATA[{canonical}]]></category>'
        item = re.sub(
            r'<category domain="post_tag" nicename="([^"]+)"><!\[CDATA\[([^\]]+)\]\]></category>\s*',
            repl_tag, item
        )

        # --- Category renames (slug + name change, redirect needed) ---
        for from_slug, (to_slug, to_name) in CATEGORY_RENAMES.items():
            pat = re.compile(
                rf'<category domain="category" nicename="{re.escape(from_slug)}"><!\[CDATA\[[^\]]+\]\]></category>'
            )
            replacement = f'<category domain="category" nicename="{to_slug}"><![CDATA[{to_name}]]></category>'
            item = pat.sub(replacement, item)

        # --- Category name normalizations (slug stays same; only the display name is rewritten) ---
        for slug, canonical_name in CATEGORY_NAME_NORMALIZE.items():
            pat = re.compile(
                rf'<category domain="category" nicename="{re.escape(slug)}"><!\[CDATA\[([^\]]+)\]\]></category>'
            )
            def _norm(m, slug=slug, canonical_name=canonical_name):
                return f'<category domain="category" nicename="{slug}"><![CDATA[{canonical_name}]]></category>'
            item = pat.sub(_norm, item)

        # --- Author merges ---
        creator_m = re.search(r"<dc:creator>([^<]+)</dc:creator>", item)
        if creator_m:
            creator = creator_m.group(1).strip()
            if creator in AUTHOR_MERGES:
                new = AUTHOR_MERGES[creator]
                item = item.replace(
                    f"<dc:creator>{creator}</dc:creator>",
                    f"<dc:creator>{new}</dc:creator>"
                )

        kept_items.append(item)

    log(report, f"Items kept: {len(kept_items)}")
    log(report, f"Items dropped:")
    for k, v in dropped_items.most_common():
        log(report, f"  {k}: {v}")

    # === Write output ===
    with open(WXR_OUT, "w", encoding="utf-8") as f:
        f.write(cleaned_header)
        f.write("\n    ".join(kept_items))
        f.write("\n  " + footer)
    log(report, f"\nWrote {WXR_OUT}\n")

    # Add category rename redirects (full URL pattern this time, not just slug)
    category_redirects = []
    for from_slug, (to_slug, to_name) in CATEGORY_RENAMES.items():
        category_redirects.append({
            "old_slug": f"/magazine-content/category/{from_slug}",
            "new_slug": f"/magazine-content/category/{to_slug}",
            "reason":   f"category-rename:{from_slug}->{to_slug} ({to_name})",
        })

    # === Write redirect map ===
    with open(REDIRECT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["old_slug", "new_slug", "reason"])
        w.writeheader()
        w.writerows(redirects_needed)
        w.writerows(category_redirects)
    log(report, f"Wrote {REDIRECT} with {len(redirects_needed)} slug-change "
                f"+ {len(category_redirects)} category-rename redirects "
                f"= {len(redirects_needed) + len(category_redirects)} total")

    # === Write report ===
    with open(REPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(report))
    log(report, f"\nWrote {REPORT}")


if __name__ == "__main__":
    main()
