#!/usr/bin/env python3
"""
Squarespace SEO meta crawler for The Three Drinkers.

Crawls every URL that matters for SEO preservation:
  1. Article URLs from the WXR export (published posts)
  2. Tag / category / other URLs from Google Search Console export
     (Pages.csv) — these include the long-tail tag landing pages that
     drive ~52% of organic traffic.

For each URL it fetches the live page from Squarespace and extracts:
  <title>, <meta name="description">, H1, http status, byte size.

Output: seo-meta.csv (one row per URL, deduplicated).

Setup (run once):
  python3 -m venv venv
  source venv/bin/activate
  pip install requests beautifulsoup4

Then run:
  python3 crawlseometa.py

Configuration: edit the constants below if your filenames differ.
"""
import csv, re, time, os
import requests
from bs4 import BeautifulSoup

WXR_FILE  = "SquarespaceWordpressExport05232026.xml"
GSC_FILE  = "Pages.csv"            # GSC Pages export (optional)
BASE_URL  = "https://www.thethreedrinkers.com"
OUT_FILE  = "seo-meta.csv"
DELAY_SEC = 0.5                    # polite delay between requests

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124.0.0.0 Safari/537.36")


def url_type(path):
    """Classify a URL path so we know what we're looking at."""
    parts = path.strip("/").split("/")
    if not parts or parts == [""]:
        return "homepage"
    if parts[0] == "magazine-content":
        if len(parts) >= 2 and parts[1] == "tag":
            return "tag"
        if len(parts) >= 2 and parts[1] == "category":
            return "category"
        if len(parts) >= 2:
            return "article"
        return "blog-index"
    return "other"


def parse_wxr(path):
    """Yield (live_url, slug, title, source) tuples for every published post."""
    if not os.path.exists(path):
        print(f"  WARN: {path} not found, skipping WXR parse")
        return []
    with open(path, encoding="utf-8", errors="replace") as f:
        xml = f.read()
    items = re.findall(r"<item>(.*?)</item>", xml, re.DOTALL)
    out = []
    for item in items:
        post_type = re.search(r"<wp:post_type>([^<]+)", item)
        status    = re.search(r"<wp:status>([^<]+)", item)
        if not post_type or post_type.group(1).strip() != "post":
            continue
        if not status or status.group(1).strip() != "publish":
            continue
        link  = re.search(r"<link>([^<]+)", item)
        title = re.search(r"<title>([^<]*)", item)
        slug  = re.search(r"<wp:post_name>([^<]+)", item)
        link_val  = link.group(1).strip()  if link  else ""
        title_val = title.group(1).strip() if title else ""
        slug_val  = slug.group(1).strip()  if slug  else ""
        if not link_val:
            continue
        live = BASE_URL + link_val if link_val.startswith("/") else link_val
        out.append((live, slug_val, title_val, "wxr"))
    return out


def parse_gsc(path):
    """Yield (live_url, slug, title, source, clicks) for every URL in GSC Pages export."""
    if not os.path.exists(path):
        print(f"  WARN: {path} not found, skipping GSC parse "
              "(SEO meta for tag pages won't be captured)")
        return []
    out = []
    with open(path, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            url = (row.get("Top pages") or row.get("URL") or "").strip()
            if not url or not url.startswith("http"):
                continue
            clicks = int((row.get("Clicks") or "0").replace(",", ""))
            # derive a "slug" for matching purposes (last path segment)
            tail = url.rstrip("/").split("/")[-1]
            out.append((url, tail, "", "gsc", clicks))
    return out


def extract_meta(url):
    try:
        r = requests.get(url, timeout=20, headers={"User-Agent": UA})
        soup = BeautifulSoup(r.text, "html.parser") if r.text else None
        title = soup.title.string.strip() if soup and soup.title and soup.title.string else ""
        desc, h1 = "", ""
        if soup:
            d = soup.find("meta", attrs={"name": re.compile("^description$", re.I)})
            desc = d["content"].strip() if d and d.get("content") else ""
            # Squarespace often puts OG description if no meta description
            if not desc:
                og = soup.find("meta", attrs={"property": re.compile("^og:description$", re.I)})
                desc = og["content"].strip() if og and og.get("content") else ""
            h_tag = soup.find("h1")
            h1 = h_tag.get_text(strip=True) if h_tag else ""
        return title, desc, h1, str(r.status_code), len(r.content)
    except Exception as e:
        return "", "", "", f"ERROR: {e}", 0


def main():
    print(f"Parsing {WXR_FILE} ...")
    wxr_rows = parse_wxr(WXR_FILE)
    print(f"  {len(wxr_rows)} published articles found")

    print(f"Parsing {GSC_FILE} ...")
    gsc_rows = parse_gsc(GSC_FILE)
    print(f"  {len(gsc_rows)} URLs found in GSC export")

    # Build deduped URL list. Article URLs from WXR get priority for slug/title;
    # GSC adds tag pages and any URLs the WXR missed. Track clicks if known.
    by_url = {}
    for url, slug, title, src in wxr_rows:
        by_url[url] = {"url": url, "slug": slug, "post_title": title,
                       "source": src, "gsc_clicks": 0}
    for url, slug, title, src, clicks in gsc_rows:
        if url in by_url:
            by_url[url]["gsc_clicks"] = clicks
            by_url[url]["source"] = by_url[url]["source"] + "+gsc"
        else:
            by_url[url] = {"url": url, "slug": slug, "post_title": title,
                           "source": src, "gsc_clicks": clicks}

    # Order: highest GSC clicks first (so we get the important pages even if interrupted)
    rows = sorted(by_url.values(), key=lambda r: -r["gsc_clicks"])
    print(f"\nTotal unique URLs to crawl: {len(rows)}")
    type_counts = {}
    for r in rows:
        path = r["url"].replace(BASE_URL, "")
        t = url_type(path)
        r["url_type"] = t
        type_counts[t] = type_counts.get(t, 0) + 1
    print(f"By type: {type_counts}")

    with open(OUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["url", "url_type", "slug", "post_title",
                         "seo_title", "meta_description", "h1",
                         "http_status", "byte_size", "gsc_clicks", "source"])
        for i, r in enumerate(rows, 1):
            tag = f"[{i}/{len(rows)}] ({r['url_type']:8s}) clicks={r['gsc_clicks']:>5}"
            print(f"{tag}  {r['url']}", flush=True)
            seo_title, meta_desc, h1, status, size = extract_meta(r["url"])
            writer.writerow([r["url"], r["url_type"], r["slug"], r["post_title"],
                             seo_title, meta_desc, h1, status, size,
                             r["gsc_clicks"], r["source"]])
            time.sleep(DELAY_SEC)

    print(f"\nDone. Saved to {OUT_FILE}")


if __name__ == "__main__":
    main()
