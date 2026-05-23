#!/usr/bin/env python3
"""
Squarespace SEO meta crawler for The Three Drinkers.
Reads all post slugs from the WXR export, fetches each live URL,
extracts title / meta description / H1, and saves to seo-meta.csv.

Usage:
  pip install requests beautifulsoup4
  python3 crawl-seo-meta.py
"""
import csv, re, sys, time
import xml.etree.ElementTree as ET
import requests
from bs4 import BeautifulSoup

WXR_FILE  = "SquarespaceWordpressExport05232026.xml"
BASE_URL  = "https://www.thethreedrinkers.com"
OUT_FILE  = "seo-meta.csv"
DELAY_SEC = 0.5   # polite delay between requests

NS = {
    "wp":      "http://wordpress.org/export/1.2/",
    "content": "http://purl.org/rss/1.0/modules/content/",
    "excerpt": "http://wordpress.org/export/1.2/excerpt/",
    "dc":      "http://purl.org/dc/elements/1.1/",
}

def get_text(el, tag, ns=None):
    child = el.find(tag, ns) if ns else el.find(tag)
    return child.text.strip() if child is not None and child.text else ""

def extract_meta(url):
    try:
        r = requests.get(url, timeout=15, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/124.0.0.0 Safari/537.36"
        })
        if r.status_code != 200:
            return "", "", "", str(r.status_code)
        soup = BeautifulSoup(r.text, "html.parser")
        title = soup.title.string.strip() if soup.title else ""
        desc_tag = soup.find("meta", attrs={"name": re.compile("^description$", re.I)})
        desc = desc_tag["content"].strip() if desc_tag and desc_tag.get("content") else ""
        h1_tag = soup.find("h1")
        h1 = h1_tag.get_text(strip=True) if h1_tag else ""
        return title, desc, h1, "200"
    except Exception as e:
        return "", "", "", f"ERROR: {e}"

def main():
    tree = ET.parse(WXR_FILE)
    root = tree.getroot()
    channel = root.find("channel")

    items = []
    for item in channel.findall("item"):
        post_type = get_text(item, "wp:post_type", NS)
        status    = get_text(item, "wp:status", NS)
        if post_type != "post" or status != "publish":
            continue
        link  = get_text(item, "link")
        slug  = get_text(item, "wp:post_name", NS)
        title = get_text(item, "title")
        # Build the live URL from the <link> value
        live_url = BASE_URL + link if link.startswith("/") else link
        items.append((live_url, slug, title))

    print(f"Found {len(items)} published posts to crawl")

    with open(OUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["squarespace_url", "slug", "post_title",
                         "seo_title", "meta_description", "h1", "status"])
        for i, (url, slug, post_title) in enumerate(items, 1):
            print(f"[{i}/{len(items)}] {url}", flush=True)
            seo_title, meta_desc, h1, status = extract_meta(url)
            writer.writerow([url, slug, post_title, seo_title, meta_desc, h1, status])
            time.sleep(DELAY_SEC)

    print(f"\nDone. Results saved to {OUT_FILE}")

if __name__ == "__main__":
    main()
