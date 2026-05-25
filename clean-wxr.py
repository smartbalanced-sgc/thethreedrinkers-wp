#!/usr/bin/env python3
"""
Clean the Squarespace WXR export for safe import into WordPress.

Operations:
  1. Keep attachment items (WP Importer downloads them so _thumbnail_id refs resolve).
     Note: post-import, also run Auto Upload Images plugin for any inline imagery
     in post content not registered as attachments.
  2. Drop draft / pending posts (per user decision).
  3. Build "keep" set for tags from GSC traffic + WXR usage; remove all
     other tag references from posts.
  4. Fix malformed article slugs (leading dash, date-pathed).
  5. Detect slug collisions and warn before import.
  6. Merge duplicate author accounts (Helena's email login into HelenaNicklin).
  7. Strip orphaned author blocks from WXR header (no phantom user accounts).
  8. Override author display names (e.g., TheThreeDrinkers -> The Three Drinkers).
  9. Normalize duplicate / typo'd categories with full 301 redirect map.
 10. Normalize inconsistent tag display names (most-frequent + capital tiebreaker).

Inputs (in same folder):
  SquarespaceWordpressExport05232026.xml
  Pages.csv                                 (GSC export, optional but recommended)

Output:
  SquarespaceWordpressExport-cleaned.xml    (ready for WP Importer)
  cleanup-report.txt                        (audit log of all changes including collision warnings)
  redirects-needed.csv                      (slug + category-rename redirects)
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
KEEP_ATTACHMENTS  = True             # AUDIT FIX: keep attachments so _thumbnail_id refs resolve

# Author merge map: (dc:creator value → canonical wp:author_login that exists in WXR header)
# Adrian only has ONE account in the WXR (login = his email) so no merge needed for him.
# Helena has two accounts -> we collapse her email login into her HelenaNicklin account.
AUTHOR_MERGES = {
    "helena@thethreedrinkers.com": "HelenaNicklin",
}

# Author logins to strip from the WXR header entirely (the source side of a merge).
# Without this, WP Importer creates a phantom user account with 0 posts.
AUTHOR_HEADER_REMOVE = set(AUTHOR_MERGES.keys())

# Author display-name overrides applied to <wp:author> blocks in the header.
# Used to give the collective byline a proper-cased display name.
AUTHOR_DISPLAY_OVERRIDES = {
    "TheThreeDrinkers": "The Three Drinkers",
    # Adrian Smith goes by "Aidy" on all bylines — login stays as the email
    "adrian@thethreedrinkers.com": "Aidy Smith",
}

# Category renames: from-nicename -> (new-nicename, new-name).
# Use this when the slug actually changes (different URL).
# Each one will produce a 301 redirect entry in redirects-needed.csv.
CATEGORY_RENAMES = {
    "isaly":            ("islay",         "Islay"),         # typo fix
    "sinagpore":        ("singapore",     "Singapore"),     # typo fix
    "gear-and-gadgets": ("gear-gadgets",  "Gear & Gadgets"),# merge into ampersand variant
}

# Page slugs to force to draft status on export.
# aidy-helena-1/2/3 are SS-generated "Copy" duplicates of the real aidy-helena page.
# Importing them as published would create duplicate content and canonical confusion.
FORCE_DRAFT_SLUGS = {
    "aidy-helena-1",
    "aidy-helena-2",
    "aidy-helena-3",
}

# Per-post curation file: editorial decisions on which posts to drop and which
# to reassign to a different author. Columns: slug, action, reassign_to.
# - action='drop' removes the post and emits a 301 redirect to its category archive
# - reassign_to='AidySmith' (or any login) overrides the post's dc:creator
CURATION_FILE = "helena-curation.csv"

# Map human-friendly names used in the curation CSV → real wp:author_login values
# present in the WXR header. Without this, WP Importer would create phantom users
# for any reassign_to value that doesn't exactly match an existing login.
REASSIGN_ALIASES = {
    "AidySmith": "adrian@thethreedrinkers.com",
}

# One-off authorship reassignments for articles whose inline byline disagrees with
# the dc:creator (e.g. body says "Words by Helena Nicklin" but post is attributed
# to someone else in the WXR). Applied in addition to the curation CSV.
MANUAL_REASSIGNS = {
    "sake-beginners-guide": "HelenaNicklin",  # body byline credits Helena
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


def load_curation(path):
    """Load editorial decisions from helena-curation.csv (or similar).
    Returns (drop_slugs, reassign_map) where:
      drop_slugs = set of slugs to remove from import
      reassign_map = {slug: new_dc_creator_value}
    Missing file → returns empty structures (no curation applied).
    """
    drop_slugs = set()
    reassign_map = {}
    if not os.path.exists(path):
        return drop_slugs, reassign_map
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            slug = (row.get("slug") or "").strip()
            if not slug:
                continue
            action = (row.get("action") or "").strip().lower()
            reassign = (row.get("reassign_to") or "").strip()
            if action == "drop":
                drop_slugs.add(slug)
            elif reassign:
                # Resolve friendly alias to the real wp:author_login value
                reassign_map[slug] = REASSIGN_ALIASES.get(reassign, reassign)
    # Layer in manual one-off reassignments (apply on top of CSV-based ones)
    for slug, login in MANUAL_REASSIGNS.items():
        reassign_map[slug] = REASSIGN_ALIASES.get(login, login)
    return drop_slugs, reassign_map


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
    # Canonical name per tag = most-frequent variant, with a capitalization tiebreaker:
    # on ties, prefer the variant starting with a capital letter (better display).
    def pick_canonical(names_counter):
        ordered = names_counter.most_common()
        top_count = ordered[0][1]
        tied = [n for n, c in ordered if c == top_count]
        if len(tied) == 1:
            return tied[0]
        # Prefer first variant that starts with a capital letter
        for n in tied:
            if n and n[0].isupper():
                return n
        return tied[0]
    tag_canonical_name = {slug: pick_canonical(names)
                          for slug, names in tag_name_freq.items()}
    multi_variant = sum(1 for names in tag_name_freq.values() if len(names) > 1)
    log(report, f"Tag display-name variants normalized: {multi_variant} slugs had "
                f"multiple case/spelling variants; using the most-frequent for each\n")

    # === Phase 2: Load GSC traffic ===
    gsc = load_gsc_tag_clicks(GSC_FILE, set(tag_usage.keys()))
    log(report, f"GSC tag traffic loaded: {len(gsc)} tags with clicks "
                f"(sum {sum(gsc.values()):,} clicks)\n")

    # === Phase 2b: Load editorial curation decisions ===
    drop_slugs, reassign_map = load_curation(CURATION_FILE)
    log(report, f"Curation loaded from {CURATION_FILE}: "
                f"{len(drop_slugs)} drops, {len(reassign_map)} reassignments\n")

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

    # === Header cleanup: strip merged-source <wp:author> blocks; rewrite display names ===
    cleaned_header = header
    for login in AUTHOR_HEADER_REMOVE:
        pat = re.compile(
            rf'\s*<wp:author>\s*(?:(?!</wp:author>).)*?<wp:author_login>{re.escape(login)}</wp:author_login>.*?</wp:author>\s*',
            re.DOTALL
        )
        cleaned_header, n = pat.subn("\n    ", cleaned_header)
        if n > 0:
            log(report, f"Stripped {n} orphaned <wp:author> block(s) for login={login!r}")
    for login, new_display in AUTHOR_DISPLAY_OVERRIDES.items():
        pat = re.compile(
            rf'(<wp:author>\s*(?:(?!</wp:author>).)*?<wp:author_login>{re.escape(login)}</wp:author_login>(?:(?!</wp:author>).)*?<wp:author_display_name>)<!\[CDATA\[[^\]]*\]\]>',
            re.DOTALL
        )
        cleaned_header, n = pat.subn(rf'\g<1><![CDATA[{new_display}]]>', cleaned_header)
        if n > 0:
            log(report, f"Renamed display name for login={login!r} -> {new_display!r}")

    # === Pre-pass: detect slug collisions BEFORE we write anything ===
    # Build map of {final_slug: [(post_id, original_slug, status)]} so we can warn
    # when fix_slug() would collapse two different posts to the same slug.
    slug_universe = defaultdict(list)
    for it in items:
        ptype_m = re.search(r"<wp:post_type>([^<]+)", it)
        status_m = re.search(r"<wp:status>([^<]+)", it)
        slug_m = re.search(r"<wp:post_name>([^<]*)</wp:post_name>", it)
        post_id_m = re.search(r"<wp:post_id>([^<]+)", it)
        if not (ptype_m and status_m and slug_m): continue
        ptype = ptype_m.group(1).strip()
        status = status_m.group(1).strip()
        if ptype != "post": continue
        if status not in ("publish",): continue
        original = slug_m.group(1)
        fixed, _ = fix_slug(original)
        slug_universe[fixed].append((post_id_m.group(1) if post_id_m else "?",
                                      original, status))
    collisions = {s: v for s, v in slug_universe.items() if len(v) > 1}
    if collisions:
        log(report, f"\n⚠️  SLUG COLLISION WARNING: {len(collisions)} slugs collide after normalization:")
        for slug, hits in collisions.items():
            log(report, f"   '{slug}' would be shared by:")
            for pid, orig, st in hits:
                log(report, f"     post_id={pid}  original_slug={orig!r}  status={st}")
        log(report, "   → WP Importer will append -2/-3/... suffixes silently.")
        log(report, "   → Resolve manually in WXR before importing, or accept the suffixing.\n")

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

        # --- Force-draft slugs (SS "Copy" duplicates that must not publish) ---
        slug_early_m = re.search(r"<wp:post_name>([^<]*)</wp:post_name>", item)
        if slug_early_m and slug_early_m.group(1).strip() in FORCE_DRAFT_SLUGS:
            item = re.sub(r"<wp:status>[^<]+</wp:status>", "<wp:status>draft</wp:status>", item)

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

        # --- Curation: drop posts/pages marked for removal, emit redirect ---
        # Runs AFTER slug fix so we match against the post-fix (canonical) slug,
        # which is what the curation CSV was generated from.
        slug_now = re.search(r"<wp:post_name>([^<]*)</wp:post_name>", item)
        current_slug = slug_now.group(1).strip() if slug_now else ""
        if current_slug and current_slug in drop_slugs and ptype in ("post", "page"):
            # Find the first category to use as the redirect target (posts only)
            cat_m = re.search(
                r'<category domain="category" nicename="([^"]+)"',
                item
            )
            if cat_m and ptype == "post":
                cat_slug = cat_m.group(1).strip()
                if cat_slug in CATEGORY_RENAMES:
                    cat_slug = CATEGORY_RENAMES[cat_slug][0]
                redirect_target = f"/magazine-content/category/{cat_slug}/"
                reason = f"curated-drop:cat-{cat_slug}"
            else:
                redirect_target = "/"
                reason = f"curated-drop:{ptype}-no-category"
            redirects_needed.append({
                "old_slug": f"/magazine-content/{current_slug}/",
                "new_slug": redirect_target,
                "reason":   reason,
            })
            dropped_items["curated-drop"] += 1
            continue

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

        # --- Curation: reassign authorship for specific slugs ---
        if current_slug and current_slug in reassign_map:
            new_creator = reassign_map[current_slug]
            item = re.sub(
                r"<dc:creator>[^<]+</dc:creator>",
                f"<dc:creator>{new_creator}</dc:creator>",
                item,
                count=1,
            )

        kept_items.append(item)

    log(report, f"Items kept: {len(kept_items)}")
    log(report, f"Items dropped:")
    for k, v in dropped_items.most_common():
        log(report, f"  {k}: {v}")

    # === Write output ===
    # Strip XML 1.0 control characters that the SS export sometimes leaves in
    # post content (e.g. lone \x03 bytes). These crash strict XML parsers and
    # cause WP Importer to silently fail on the containing item.
    # Allowed by XML 1.0: \t (0x09), \n (0x0A), \r (0x0D); 0x20+.
    invalid_xml_chars = re.compile(r'[\x00-\x08\x0B\x0C\x0E-\x1F]')
    body = invalid_xml_chars.sub('', "\n    ".join(kept_items))
    cleaned_header_safe = invalid_xml_chars.sub('', cleaned_header)
    footer_safe = invalid_xml_chars.sub('', footer)

    with open(WXR_OUT, "w", encoding="utf-8") as f:
        f.write(cleaned_header_safe)
        f.write(body)
        f.write("\n  " + footer_safe)
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
