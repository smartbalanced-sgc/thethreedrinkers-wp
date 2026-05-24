#!/usr/bin/env python3
"""
Comprehensive 404 diagnostic: test ALL failed URLs concurrently and
categorize them by failure mode. No assumptions. Writes nothing.

For each failed URL it tries these candidate URLs in order:
  A. WXR-canonical-name (look up slug in WXR, use original name URL-encoded)
  B. Hyphen-lower (collapse whitespace -> hyphen, lowercase)
  C. Encoded-single-spaces (collapse whitespace -> single space, URL-encode)
  D. Raw URL with literal whitespace replaced by single space, URL-encoded

Reports:
  - Total failed
  - How many succeeded with each strategy
  - How many still 404 (with sample URLs)
  - How many slugs don't exist in WXR at all (sample URLs)
  - URL-type breakdown of the remaining failures

Run:
  source venv/bin/activate
  pip install requests   (already installed if you ran the crawler)
  python3 diagnose404s.py
"""
import csv, re, os, sys
from urllib.parse import quote, urlsplit
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

CSV_FILE = "seo-meta.csv"
WXR_FILE = "SquarespaceWordpressExport05232026.xml"
BASE     = "https://www.thethreedrinkers.com"
WORKERS  = 12
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124.0.0.0 Safari/537.36")


def load_tag_index(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        xml = f.read()
    pat = re.compile(
        r'<category domain="(post_tag|category)" nicename="([^"]+)"><!\[CDATA\[([^\]]+)\]\]></category>'
    )
    idx = {}
    for domain, nicename, name in pat.findall(xml):
        key = (domain, nicename)
        if key not in idx:
            idx[key] = name
    return idx


def normalize_for_lookup(slug_raw):
    s = re.sub(r"\s+", "-", slug_raw).lower()
    s = re.sub(r"-{2,}", "-", s).strip("-")
    s = re.sub(r"[?!&,'\"`’]", "", s)
    return s


def url_type_and_slug(url):
    path = urlsplit(url).path
    m = re.match(r"^/magazine-content/tag/(.+)$", path, re.DOTALL)
    if m:
        return "tag", m.group(1)
    m = re.match(r"^/magazine-content/category/(.+)$", path, re.DOTALL)
    if m:
        return "category", m.group(1)
    m = re.match(r"^/magazine-content/(.+)$", path, re.DOTALL)
    if m:
        return "article", m.group(1)
    return "other", path


def build_candidates(url, tag_idx):
    """Return list of (label, candidate_url) to try."""
    cands = []
    kind, slug = url_type_and_slug(url)

    # A: WXR canonical-name
    if kind in ("tag", "category"):
        domain = "post_tag" if kind == "tag" else "category"
        key = (domain, normalize_for_lookup(slug))
        if key in tag_idx:
            name = tag_idx[key]
            base = "tag" if kind == "tag" else "category"
            cands.append(("A:wxr-canonical",
                          f"{BASE}/magazine-content/{base}/{quote(name, safe='')}"))

    # B: hyphen-lower
    hyphen_lower = re.sub(r"\s+", "-", slug.strip()).lower()
    hyphen_lower = re.sub(r"-{2,}", "-", hyphen_lower).strip("-")
    if kind == "tag":
        cands.append(("B:hyphen-lower", f"{BASE}/magazine-content/tag/{hyphen_lower}"))
    elif kind == "category":
        cands.append(("B:hyphen-lower", f"{BASE}/magazine-content/category/{hyphen_lower}"))

    # C: encoded with single spaces
    single = re.sub(r"\s+", " ", slug).strip()
    if kind == "tag":
        cands.append(("C:encoded-single",
                      f"{BASE}/magazine-content/tag/{quote(single, safe='')}"))
    elif kind == "category":
        cands.append(("C:encoded-single",
                      f"{BASE}/magazine-content/category/{quote(single, safe='')}"))

    # D: encoded preserving newlines as spaces (do not collapse)
    raw = slug.replace("\n", " ").replace("\r", "")
    if kind == "tag":
        cands.append(("D:encoded-as-is",
                      f"{BASE}/magazine-content/tag/{quote(raw, safe='')}"))
    elif kind == "category":
        cands.append(("D:encoded-as-is",
                      f"{BASE}/magazine-content/category/{quote(raw, safe='')}"))

    return kind, slug, cands


def try_url(url):
    try:
        r = requests.get(url, timeout=15,
                         headers={"User-Agent": UA}, allow_redirects=True)
        return r.status_code
    except Exception as e:
        return f"ERR:{type(e).__name__}"


def probe_row(row, tag_idx):
    kind, slug, cands = build_candidates(row["url"], tag_idx)
    result = {"url": row["url"], "kind": kind, "slug": slug,
              "gsc_clicks": int(row.get("gsc_clicks") or "0"),
              "winning_strategy": None,
              "winning_url": None,
              "wxr_match": any(label.startswith("A:") for label, _ in cands),
              "attempts": []}
    for label, cand in cands:
        status = try_url(cand)
        result["attempts"].append((label, status, cand))
        if str(status) == "200":
            result["winning_strategy"] = label
            result["winning_url"] = cand
            break
    return result


def main():
    if not os.path.exists(WXR_FILE):
        sys.exit(f"Missing {WXR_FILE}")
    print(f"Loading tag/category index from {WXR_FILE} ...")
    tag_idx = load_tag_index(WXR_FILE)
    print(f"  loaded {len(tag_idx)} unique slugs\n")

    with open(CSV_FILE, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    failed = [r for r in rows if r.get("http_status") != "200"]
    print(f"Probing {len(failed)} failed URLs with {WORKERS} workers...\n")

    results = []
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futures = {ex.submit(probe_row, r, tag_idx): r for r in failed}
        done = 0
        for fut in as_completed(futures):
            results.append(fut.result())
            done += 1
            if done % 50 == 0:
                print(f"  {done}/{len(failed)} probed", flush=True)

    # Summary
    print("\n" + "=" * 64)
    print("RESULTS")
    print("=" * 64)

    by_kind = {}
    by_winner = {}
    no_wxr_match = []
    still_failing = []
    for r in results:
        by_kind[r["kind"]] = by_kind.get(r["kind"], 0) + 1
        if r["winning_strategy"]:
            by_winner[r["winning_strategy"]] = by_winner.get(r["winning_strategy"], 0) + 1
        else:
            still_failing.append(r)
        if r["kind"] in ("tag", "category") and not r["wxr_match"]:
            no_wxr_match.append(r)

    print(f"\nTotal failed: {len(results)}")
    print(f"\nBy URL type:")
    for k, v in sorted(by_kind.items(), key=lambda x: -x[1]):
        print(f"  {k:10s}: {v}")

    print(f"\nRecovered by strategy:")
    for s, v in sorted(by_winner.items(), key=lambda x: -x[1]):
        print(f"  {s:20s}: {v}")
    recovered = sum(by_winner.values())
    print(f"  -------- recovered: {recovered} ({recovered/len(results)*100:.1f}%)")

    print(f"\nSlugs with NO WXR match: {len(no_wxr_match)}")
    if no_wxr_match:
        print("  (sample, top 10 by clicks):")
        for r in sorted(no_wxr_match, key=lambda x: -x["gsc_clicks"])[:10]:
            print(f"    clicks={r['gsc_clicks']:>5}  {r['url']!r}")

    print(f"\nStill failing after all strategies: {len(still_failing)}")
    if still_failing:
        print("  (sample, top 15 by clicks):")
        for r in sorted(still_failing, key=lambda x: -x["gsc_clicks"])[:15]:
            print(f"    clicks={r['gsc_clicks']:>5}  kind={r['kind']:8s}")
            print(f"      url: {r['url']!r}")
            for label, status, cand in r["attempts"][:4]:
                print(f"        {label:20s} -> {status}  {cand[:80]}...")

    # Total clicks recovered vs unrecovered
    rec_clicks = sum(r["gsc_clicks"] for r in results if r["winning_strategy"])
    lost_clicks = sum(r["gsc_clicks"] for r in results if not r["winning_strategy"])
    print(f"\nClicks recovered: {rec_clicks:,}")
    print(f"Clicks still missing: {lost_clicks:,}")


if __name__ == "__main__":
    main()
