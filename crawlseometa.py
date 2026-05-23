#!/usr/bin/env python3
"""
Squarespace SEO meta crawler for The Three Drinkers.
Reads all post slugs from the WXR export via regex (tolerates malformed XML),
fetches each live URL, extracts title / meta description / H1,
and saves to seo-meta.csv.

Setup (run once):
  python3 -m venv venv
  source venv/bin/activate
  pip install requests beautifulsoup4

Then run:
  python3 crawlseometa.py
"""
import csv, re, time
import requests
from bs4 import BeautifulSoup

WXR_FILE  = "SquarespaceWordpressExport05232026.xml"
BASE_URL  = "https://www.thethreedrinkers.com"
OUT_FILE  = "seo-meta.csv"
DELAY_SEC = 0.5

def parse_posts(wxr_file):
    with open(wxr_file, encoding="utf-8", errors="replace") as f:
        xml = f.read()

    items = re.findall(r'<item>(.*?)</item>', xml, re.DOTALL)
    posts = []
    for item in items:
        post_type = re.search(r'<wp:post_type>([^<]+)', item)
        status    = re.search(r'<wp:status>([^<]+)', item)
        if not post_type or post_type.group(1).strip() != 'post':
            continue
        if not status or status.group(1).strip() != 'publish':
            continue
        link  = re.search(r'<link>([^<]+)', item)
        title = re.search(r'<title>([^<]*)', item)
        slug  = re.search(r'<wp:post_name>([^<]+)', item)
        link_val  = link.group(1).strip()  if link  else ''
        title_val = title.group(1).strip() if title else ''
        slug_val  = slug.group(1).strip()  if slug  else ''
        live_url = BASE_URL + link_val if link_val.startswith('/') else link_val
        posts.append((live_url, slug_val, title_val))
    return posts

def extract_meta(url):
    try:
        r = requests.get(url, timeout=15, headers={
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        })
        if r.status_code != 200:
            return '', '', '', str(r.status_code)
        soup = BeautifulSoup(r.text, 'html.parser')
        title = soup.title.string.strip() if soup.title else ''
        desc_tag = soup.find('meta', attrs={'name': re.compile('^description$', re.I)})
        desc = desc_tag['content'].strip() if desc_tag and desc_tag.get('content') else ''
        h1_tag = soup.find('h1')
        h1 = h1_tag.get_text(strip=True) if h1_tag else ''
        return title, desc, h1, '200'
    except Exception as e:
        return '', '', '', f'ERROR: {e}'

def main():
    print(f"Parsing {WXR_FILE} ...")
    posts = parse_posts(WXR_FILE)
    print(f"Found {len(posts)} published posts to crawl\n")

    with open(OUT_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['squarespace_url', 'slug', 'post_title',
                         'seo_title', 'meta_description', 'h1', 'http_status'])
        for i, (url, slug, post_title) in enumerate(posts, 1):
            print(f'[{i}/{len(posts)}] {url}', flush=True)
            seo_title, meta_desc, h1, status = extract_meta(url)
            writer.writerow([url, slug, post_title, seo_title, meta_desc, h1, status])
            time.sleep(DELAY_SEC)

    print(f'\nDone. Saved to {OUT_FILE}')

if __name__ == '__main__':
    main()
