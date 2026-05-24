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

# Category renames/merges:  (from-nicename → to-nicename, to-name)
CATEGORY_FIXES = {
    "whisky":            ("whisky-cat",          "Whisky"),    # collapses lowercase variant
    "scotch":            ("scotch-cat",          "Scotch"),
    "rye":               ("rye-cat",             "Rye"),
    "new-york":          ("new-york-cat",        "New York"),
    "gear-and-gadgets":  ("gear-gadgets",        "Gear & Gadgets"),
    "isaly":             ("islay",               "Islay"),
    "sinagpore":         ("singapore",           "Singapore"),
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

    # === Phase 1: Count tag usage in posts ===
    # Find all post_tag references inside post items (not attachments)
    tag_usage = Counter()
    # We do a simplified pass: capture every post_tag reference in any item;
    # final filtering will be done per-item later.
    for nicename in re.findall(
        r'<category domain="post_tag" nicename="([^"]+)"', xml
    ):
        tag_usage[nicename] += 1

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

        # --- Tag filtering ---
        # Remove <category domain="post_tag"> entries whose nicename isn't in keep_tags
        def repl_tag(m):
            nicename = m.group(1)
            return m.group(0) if nicename in keep_tags else ""
        item = re.sub(
            r'<category domain="post_tag" nicename="([^"]+)"><!\[CDATA\[[^\]]+\]\]></category>\s*',
            repl_tag, item
        )

        # --- Category renames/merges ---
        for from_slug, (to_slug, to_name) in CATEGORY_FIXES.items():
            pat = re.compile(
                rf'<category domain="category" nicename="{re.escape(from_slug)}"><!\[CDATA\[[^\]]+\]\]></category>'
            )
            replacement = f'<category domain="category" nicename="{to_slug}"><![CDATA[{to_name}]]></category>'
            item = pat.sub(replacement, item)

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

    # === Write redirect map ===
    with open(REDIRECT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["old_slug", "new_slug", "reason"])
        w.writeheader()
        w.writerows(redirects_needed)
    log(report, f"Wrote {REDIRECT} with {len(redirects_needed)} slug-change redirects")

    # === Write report ===
    with open(REPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(report))
    log(report, f"\nWrote {REPORT}")


if __name__ == "__main__":
    main()
