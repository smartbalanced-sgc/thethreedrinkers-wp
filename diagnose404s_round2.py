#!/usr/bin/env python3
"""
Round-2 diagnostic for the 283 URLs that still 404 after round-1.

Fixes:
  1. Better WXR normalization (strip punctuation BEFORE collapsing hyphens;
     handle slashes; handle curly quotes, em-dashes, accents).
  2. Fuzzy WXR matching for tags not found by exact lookup.
  3. Retry on 429 with exponential backoff.
  4. Low concurrency (2 workers) + delay to avoid rate-limiting.

Run:
  source venv/bin/activate
  python3 diagnose404s_round2.py
"""
import csv, re, os, sys, time, unicodedata
from urllib.parse import quote, urlsplit
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

CSV_FILE = "seo-meta.csv"
WXR_FILE = "SquarespaceWordpressExport05232026.xml"
BASE     = "https://www.thethreedrinkers.com"
WORKERS  = 2
DELAY    = 0.4
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124.0.0.0 Safari/537.36")


def load_wxr_tags(path):
    """Return list of (nicename, name) for all tags + categories."""
    with open(path, encoding="utf-8", errors="replace") as f:
        xml = f.read()
    pat = re.compile(
        r'<category domain="(post_tag|category)" nicename="([^"]+)"><!\[CDATA\[([^\]]+)\]\]></category>'
    )
    seen = set()
    out = []
    for domain, nicename, name in pat.findall(xml):
        key = (domain, nicename)
        if key in seen:
            continue
        seen.add(key)
        out.append((domain, nicename, name))
    return out


def slugify_like_wp(text):
    """Mimic WP's sanitize_title: lowercase, accents stripped, non-alnum -> hyphen, collapse, trim."""
    s = unicodedata.normalize("NFKD", text)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    # Normalize curly quotes / em-dashes BEFORE stripping
    s = s.replace("’", "").replace("‘", "").replace("'", "")
    s = s.replace("“", "").replace("”", "").replace("\"", "")
    s = s.replace("–", "-").replace("—", "-")
    # Strip punctuation entirely
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"\s+", "-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s


def lookup_wxr(slug_raw, wxr_tags, kind):
    """Return canonical NAME from WXR matching slug_raw, or None."""
    target = slugify_like_wp(slug_raw)
    target_domain = "post_tag" if kind == "tag" else "category"
    # Exact match on WP-style nicename
    for d, nic, name in wxr_tags:
        if d == target_domain and nic == target:
            return name
    # Fallback: re-slugify each WXR name and compare
    for d, nic, name in wxr_tags:
        if d == target_domain and slugify_like_wp(name) == target:
            return name
    return None


def url_kind_and_slug(url):
    path = urlsplit(url).path
    m = re.match(r"^/magazine-content/tag/(.+)$", path, re.DOTALL)
    if m: return "tag", m.group(1)
    m = re.match(r"^/magazine-content/category/(.+)$", path, re.DOTALL)
    if m: return "category", m.group(1)
    return "other", path


def build_candidates(url, wxr_tags):
    kind, slug = url_kind_and_slug(url)
    cands = []
    if kind not in ("tag", "category"):
        return kind, slug, cands

    base = "tag" if kind == "tag" else "category"

    # A: WXR canonical (with improved lookup)
    canonical = lookup_wxr(slug, wxr_tags, kind)
    if canonical:
        cands.append(("A:wxr-canonical",
                      f"{BASE}/magazine-content/{base}/{quote(canonical, safe='')}"))

    # B: encoded original (preserve all whitespace/newlines as spaces, then encode)
    raw = slug.replace("\n", " ").replace("\r", "")
    cands.append(("B:encoded-raw",
                  f"{BASE}/magazine-content/{base}/{quote(raw, safe='')}"))

    # C: WP-slugified version (what nicename normalization might produce)
    wp_slug = slugify_like_wp(slug)
    if wp_slug:
        cands.append(("C:wp-slugified",
                      f"{BASE}/magazine-content/{base}/{wp_slug}"))

    return kind, slug, cands


def try_url(url, max_retries=3):
    """GET with retry on 429."""
    backoff = 2
    for attempt in range(max_retries):
        try:
            r = requests.get(url, timeout=15,
                             headers={"User-Agent": UA},
                             allow_redirects=True)
            if r.status_code == 429:
                time.sleep(backoff)
                backoff *= 2
                continue
            return r.status_code
        except Exception as e:
            return f"ERR:{type(e).__name__}"
    return 429


def probe(row, wxr_tags):
    kind, slug, cands = build_candidates(row["url"], wxr_tags)
    res = {"url": row["url"], "kind": kind, "gsc_clicks": int(row.get("gsc_clicks") or "0"),
           "winning": None, "attempts": []}
    for label, cand in cands:
        time.sleep(DELAY)
        status = try_url(cand)
        res["attempts"].append((label, status, cand))
        if str(status) == "200":
            res["winning"] = (label, cand)
            break
    return res


def main():
    if not os.path.exists(WXR_FILE):
        sys.exit(f"Missing {WXR_FILE}")
    print(f"Loading WXR tags from {WXR_FILE} ...")
    wxr_tags = load_wxr_tags(WXR_FILE)
    print(f"  {len(wxr_tags)} unique tag/category entries\n")

    with open(CSV_FILE, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    # Only the still-failing ones
    still_failing = [r for r in rows if r.get("http_status") != "200"]
    # Sort by clicks so highest-value tested first
    still_failing.sort(key=lambda r: -int(r.get("gsc_clicks") or "0"))
    print(f"Probing {len(still_failing)} previously-failed URLs "
          f"with {WORKERS} workers (max ~3 attempts each, 0.4s delay, retry on 429)\n")
    print(f"Estimated time: ~{len(still_failing)*3*DELAY/WORKERS/60:.1f} minutes\n")

    results = []
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futures = {ex.submit(probe, r, wxr_tags): r for r in still_failing}
        done = 0
        for fut in as_completed(futures):
            results.append(fut.result())
            done += 1
            if done % 25 == 0:
                rec = sum(1 for r in results if r["winning"])
                print(f"  {done}/{len(still_failing)} probed, {rec} recovered so far", flush=True)

    print("\n" + "=" * 64)
    print("ROUND 2 RESULTS")
    print("=" * 64)

    rec = [r for r in results if r["winning"]]
    fail = [r for r in results if not r["winning"]]
    print(f"\nRecovered: {len(rec)} / {len(results)}")
    print(f"Clicks recovered: {sum(r['gsc_clicks'] for r in rec):,}")
    print(f"Clicks still missing: {sum(r['gsc_clicks'] for r in fail):,}")

    by_winner = {}
    for r in rec:
        label = r["winning"][0]
        by_winner[label] = by_winner.get(label, 0) + 1
    print(f"\nWinning strategies:")
    for s, v in sorted(by_winner.items(), key=lambda x: -x[1]):
        print(f"  {s}: {v}")

    # Categorize the still-failing
    print(f"\nStill failing: {len(fail)}")
    status_counts = {}
    for r in fail:
        last = r["attempts"][-1][1] if r["attempts"] else "no-attempt"
        status_counts[str(last)] = status_counts.get(str(last), 0) + 1
    print(f"  Final status distribution: {status_counts}")

    print(f"\nTop 15 still-failing URLs by clicks:")
    for r in sorted(fail, key=lambda x: -x["gsc_clicks"])[:15]:
        print(f"  clicks={r['gsc_clicks']:>5}  {r['url']!r}")
        for label, status, cand in r["attempts"][:3]:
            print(f"    {label:18s} -> {status}")


if __name__ == "__main__":
    main()
