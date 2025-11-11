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

HANI_BODY_CANDIDATES = [
    ("div", {"class": "article-text"}),
    ("div", {"class": re.compile(r"ArticleDetailContent", re.I)}),
    ("article", {"id": "renewal2023"}),
]


def _clean_html(node: BeautifulSoup) -> str:
    """Remove ads, scripts, and unwanted elements"""
    # Remove ads and scripts
    for bad in node(["script", "style", "noscript", "iframe", "aside", "footer", "header"]):
        bad.decompose()

    # Remove ads and unwanted sections
    junk_patterns = ["ad", "banner", "recommend",
                     "related", "share", "sns", "BaseAd"]
    for pat in junk_patterns:
        for d in node.find_all(attrs={"class": re.compile(pat, re.I)}):
            d.decompose()
        for d in node.find_all(id=re.compile(pat, re.I)):
            d.decompose()

    # Remove audio player
    for d in node.find_all("div", class_=re.compile(r"AudioPlayer", re.I)):
        d.decompose()

    # Remove image containers (extract text only)
    for d in node.find_all("div", class_=re.compile(r"imageContainer", re.I)):
        d.decompose()

    # Extract text
    lines = [t.strip() for t in node.get_text("\n").splitlines() if t.strip()]
    return "\n".join(lines)


def parse_hani(url: str, html: str):
    soup = BeautifulSoup(html, "lxml")

    # 1) Title: <h3 class="ArticleDetailView_title__*">
    title_h3 = soup.select_one("h3[class*='ArticleDetailView_title']")
    title = title_h3.get_text(strip=True) if title_h3 else None

    # Fallback to <title> tag
    if not title and soup.title:
        title = soup.title.string.strip().split("|")[0].strip()

    # 2) Subtitle: <h4 class="ArticleDetailView_subtitle__*">
    subtitle_h4 = soup.select_one("h4[class*='ArticleDetailView_subtitle']")
    subtitle = None
    if subtitle_h4:
        subtitle = subtitle_h4.get_text("\n", strip=True)

    # 3) Section/Category: <div class="ArticleDetailView_breadcrumb___*">
    section = None
    breadcrumb_div = soup.select_one(
        "div[class*='ArticleDetailView_breadcrumb']")
    if breadcrumb_div:
        categories = [a.get_text(strip=True)
                      for a in breadcrumb_div.find_all("a")]
        section = " > ".join(categories) if categories else None

    # 4) Author: <div class="ArticleDetailView_reporterList__*">
    author = None
    reporter_div = soup.select_one(
        "div[class*='ArticleDetailView_reporterList']")
    if reporter_div:
        reporters = [a.get_text(strip=True)
                     for a in reporter_div.find_all("a")]
        if reporters:
            cleaned_reporters = [r.rstrip(",").strip() for r in reporters]
            author = ", ".join(cleaned_reporters)

    # Handle "reporter" text at the end
    if reporter_div and not author:
        text = reporter_div.get_text(strip=True)
        if "기자" in text:
            text = text.replace("기자", "").strip()
            author = text

    # 5) Date: <ul class="ArticleDetailView_dateList__*">
    published = None
    date_list = soup.select_one("ul[class*='ArticleDetailView_dateList']")
    if date_list:
        for li in date_list.find_all("li"):
            li_text = li.get_text(strip=True)
            if "등록" in li_text:
                date_span = li.find("span")
                if date_span:
                    try:
                        published = dateparser.parse(
                            date_span.get_text(strip=True)).date().isoformat()
                        break
                    except Exception:
                        pass

    # Fallback to meta tag
    if not published:
        meta_date = soup.find(
            "meta", attrs={"property": "article:published_time"})
        if meta_date and meta_date.get("content"):
            try:
                published = dateparser.parse(
                    meta_date.get("content")).date().isoformat()
            except Exception:
                pass

    # 6) Body: <div class="article-text">
    body_text = ""
    article_text_div = soup.select_one("div.article-text")

    if article_text_div:
        # Remove ads and audio player
        for ad in article_text_div.find_all("div", class_=re.compile(r"BaseAd|AudioPlayer", re.I)):
            ad.decompose()

        # Remove image containers
        for img_container in article_text_div.find_all("div", class_=re.compile(r"imageContainer", re.I)):
            img_container.decompose()

        # Extract paragraphs
        paragraphs = []

        # Add subtitle
        if subtitle:
            paragraphs.append(subtitle)

        # Extract body content
        for p in article_text_div.find_all("p", class_="text"):
            text = p.get_text(strip=True)
            # Exclude newsletter subscription links
            if text and not text.startswith("(☞"):
                paragraphs.append(text)

        body_text = "\n\n".join(paragraphs)

    # Fallback if body is too short
    if not body_text or len(body_text) < 200:
        node = None
        for tag, attrs in HANI_BODY_CANDIDATES:
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
                if "hani.co.kr" not in url:
                    rec = {"url": url, "error": "not_hani"}
                    out_f.write(orjson.dumps(rec) + b"\n")
                    continue
                html = fetch(url)
                rec = parse_hani(url, html)
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
