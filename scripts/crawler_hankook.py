import re
import time
import argparse
from urllib.parse import urlparse
import orjson
import requests
from bs4 import BeautifulSoup
from dateutil import parser as dateparser
from pathlib import Path

from config import ensure_dir

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

HANKOOK_BODY_CANDIDATES = [
    ("div", {"class": "col-main", "itemprop": "articleBody"}),
    ("div", {"class": "article-body"}),
    ("div", {"itemprop": "articleBody"}),
]


def _clean_html(node: BeautifulSoup) -> str:
    """Remove ads, scripts, and unwanted elements"""
    # Remove ads and scripts
    for bad in node(["script", "style", "noscript", "iframe", "aside", "footer", "header"]):
        bad.decompose()

    # Remove ads and unwanted sections
    junk_patterns = ["ad", "banner", "recommend",
                     "related", "share", "sns", "utility", "end-ad", "module"]
    for pat in junk_patterns:
        for d in node.find_all(attrs={"class": re.compile(pat, re.I)}):
            d.decompose()
        for d in node.find_all(id=re.compile(pat, re.I)):
            d.decompose()

    # Remove image boxes
    for d in node.find_all("div", class_=re.compile(r"editor-img-box", re.I)):
        d.decompose()

    # Remove editor notes
    for d in node.find_all("div", class_="editor-note"):
        d.decompose()

    # Remove div-line
    for d in node.find_all("div", class_="div-line"):
        d.decompose()

    # Extract text
    lines = [t.strip() for t in node.get_text("\n").splitlines() if t.strip()]
    return "\n".join(lines)


def parse_hankook(url: str, html: str):
    soup = BeautifulSoup(html, "lxml")

    # 1) Title: <h1 class="headline"> or <h1 class="tit">
    title_h1 = soup.select_one("h1.headline, h1.tit")
    title = title_h1.get_text(strip=True) if title_h1 else None

    # Fallback to <title> tag
    if not title and soup.title:
        title_text = soup.title.string.strip() if soup.title.string else ""
        # Remove site name (e.g., " - 한국일보")
        title = title_text.split(" - ")[0].strip() if title_text else None

    # Fallback to meta tag
    if not title:
        meta_title = soup.find("meta", attrs={"property": "og:title"})
        if meta_title and meta_title.get("content"):
            title = meta_title.get("content")

    # 2) Subtitle: <h2 class="sub-tit-ll">
    subtitle_h2 = soup.select_one("h2.sub-tit-ll, h2.sub-title")
    subtitle = None
    if subtitle_h2:
        subtitle = subtitle_h2.get_text("\n", strip=True)

    # 3) Section/Category: meta tag or breadcrumb
    section = None
    meta_section = soup.find("meta", attrs={"property": "article:section"})
    if meta_section and meta_section.get("content"):
        section = meta_section.get("content")

    # Fallback to breadcrumb
    if not section:
        breadcrumb = soup.select_one("div.breadcrumb, nav.breadcrumb")
        if breadcrumb:
            categories = [a.get_text(strip=True)
                          for a in breadcrumb.find_all("a")]
            section = " > ".join(categories) if categories else None

    # 4) Author: meta tag or byline
    author = None
    author_meta = soup.find("meta", attrs={"name": "author"})
    if author_meta and author_meta.get("content"):
        author = author_meta.get("content")

    # Fallback to byline class
    if not author:
        byline = soup.select_one(".byline, .reporter, .author")
        if byline:
            author_text = byline.get_text(strip=True)
            # Extract reporter names
            # Pattern: "신은별 기자", "신은별•이유진 기자" etc.
            if "기자" in author_text:
                author = author_text.replace("기자", "").strip()

    # 5) Date: meta tag
    published = None
    date_meta = soup.find(
        "meta", attrs={"property": "article:published_time"})
    if date_meta and date_meta.get("content"):
        try:
            published = dateparser.parse(
                date_meta.get("content")).date().isoformat()
        except Exception:
            pass

    # Fallback to other meta tags
    if not published:
        date_meta2 = soup.find("meta", attrs={"name": "article:published_time"})
        if date_meta2 and date_meta2.get("content"):
            try:
                published = dateparser.parse(
                    date_meta2.get("content")).date().isoformat()
            except Exception:
                pass

    # Fallback to date in text
    if not published:
        date_div = soup.select_one(".date, .datetime, time")
        if date_div:
            date_text = date_div.get_text(strip=True)
            m = re.search(
                r"(20\d{2}[.\-\/]\d{1,2}[.\-\/]\d{1,2})", date_text)
            if m:
                try:
                    published = dateparser.parse(
                        m.group(1)).date().isoformat()
                except Exception:
                    pass

    # 6) Body: <div class="col-main" itemprop="articleBody">
    body_text = ""
    article_body = soup.select_one('div.col-main[itemprop="articleBody"]')

    if not article_body:
        article_body = soup.select_one('div[itemprop="articleBody"]')

    if article_body:
        # Remove ads, editor notes, images
        for ad in article_body.find_all("div", class_=re.compile(r"ad|banner|module", re.I)):
            ad.decompose()

        for editor_note in article_body.find_all("div", class_="editor-note"):
            editor_note.decompose()

        for img_box in article_body.find_all("div", class_=re.compile(r"editor-img-box|img-box", re.I)):
            img_box.decompose()

        for div_line in article_body.find_all("div", class_="div-line"):
            div_line.decompose()

        # Extract paragraphs
        paragraphs = []

        # Add subtitle
        if subtitle:
            paragraphs.append(subtitle)

        # Extract section titles
        for h3 in article_body.find_all("h3", class_="editor-tit"):
            text = h3.get_text(strip=True)
            if text:
                paragraphs.append(f"## {text}")

        # Extract body content (<p class="editor-p">)
        for p in article_body.find_all("p", class_=re.compile(r"editor-p")):
            # Skip if it's just a break
            if p.get("data-break-type") == "break":
                continue

            text = p.get_text(strip=True)
            if text and len(text) > 10:
                paragraphs.append(text)

        body_text = "\n\n".join(paragraphs)

    # Fallback if body is too short
    if not body_text or len(body_text) < 200:
        node = None
        for tag, attrs in HANKOOK_BODY_CANDIDATES:
            node = soup.find(tag, attrs=attrs)
            if node:
                break
        if node:
            body_text = _clean_html(node)

    domain = urlparse(url).netloc
    return {
        "source": domain,
        "url": url,
        "headline": title,
        "date": published,
        "author": author,
        "section": section,
        "body_text": body_text,
        "domain": domain
    }


def fetch(url: str) -> str:
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.text


def main(inp: str, out: str):
    ensure_dir(out)
    out_f = open(out, "ab")
    with open(inp, "r", encoding="utf-8") as fi:
        for line in fi:
            url = line.strip()
            if not url or url.startswith("#"):
                continue
            try:
                if "hankookilbo.com" not in url:
                    rec = {"url": url, "error": "not_hankook"}
                    out_f.write(orjson.dumps(rec) + b"\n")
                    continue
                html = fetch(url)
                rec = parse_hankook(url, html)
                out_f.write(orjson.dumps(rec) + b"\n")
                time.sleep(0.5)
            except Exception as e:
                rec = {"url": url, "error": str(e)}
                out_f.write(orjson.dumps(rec) + b"\n")
                time.sleep(0.2)
    out_f.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", dest="out", required=True)
    args = ap.parse_args()
    main(args.inp, args.out)
