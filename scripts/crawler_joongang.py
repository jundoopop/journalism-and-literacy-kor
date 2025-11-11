import re
import time
import argparse
from urllib.parse import urlparse
import orjson
import requests
from bs4 import BeautifulSoup
from readability import Document
from dateutil import parser as dateparser
from pathlib import Path

from config import ensure_dir

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; W1-JoongangCrawler/1.0)"}

JOONGANG_BODY_CANDIDATES = [
    ("div", {"class": re.compile(
        r"(article_body|article_content|article_text|article|content)", re.I)}),
    ("section", {"class": re.compile(r"(article|contents?)", re.I)}),
    ("article", {"class": re.compile(r"article", re.I)}),
]


def _clean_html(node: BeautifulSoup) -> str:
    """광고/공유/스크립트/추천영역 제거"""
    # 광고/스크립트 제거
    for bad in node(["script", "style", "noscript", "iframe", "aside", "footer", "header"]):
        bad.decompose()
    junk_patterns = ["ad", "banner", "recommend",
                     "related", "share", "sns", "utility"]
    for pat in junk_patterns:
        for d in node.find_all(attrs={"class": re.compile(pat, re.I)}):
            d.decompose()
        for d in node.find_all(id=re.compile(pat, re.I)):
            d.decompose()
    # 텍스트 추출
    lines = [t.strip() for t in node.get_text("\n").splitlines() if t.strip()]
    return "\n".join(lines)


def _parse_window_article(js_text: str) -> dict:
    """
    window.article = { TITLE: "...", SERVICE_DAYTIME: "YYYY-MM-DD HH:MM:SS", ... };
    """
    out = {}
    m_title = re.search(r'TITLE:\s*"([^"]+)"', js_text)
    if m_title:
        out["title_js"] = m_title.group(1)
    m_time = re.search(r'SERVICE_DAYTIME:\s*"([^"]+)"', js_text)
    if m_time:
        out["published_js"] = m_time.group(1)
    return out


def parse_joongang(url: str, html: str):
    soup = BeautifulSoup(html, "lxml")

    # 1) 메타/JS에서 제목·날짜 우선 추출
    #   - meta property="published_date" (예: 2025-11-11T05:00:00+09:00)
    meta_date = soup.find("meta", attrs={"property": "published_date"})
    meta_date_str = meta_date.get("content") if meta_date else None
    time_tag = soup.select_one("time[datetime]")  # 2025.11.11 05:00 형태도 표기됨

    # window.article 블록 파싱 (TITLE, SERVICE_DAYTIME)
    title_js, published_js = None, None
    for sc in soup.find_all("script"):
        if sc.string and "window.article" in sc.string:
            parsed = _parse_window_article(sc.string)
            title_js = parsed.get("title_js")
            published_js = parsed.get("published_js")
            break

    # 2) 제목: JS → <h1.headline> → <title> 순
    h1 = soup.select_one("h1.headline")
    title = title_js or (h1.get_text(strip=True) if h1 else None) or (
        soup.title.string.strip() if soup.title else "")

    # 3) 섹션/카테고리(상단 빵부스러기)
    #    ex) <a class="title">사회</a>, <a>검찰・법원</a>
    section = None
    crumb = soup.select_one(
        "section.contents article.article header.article_header .subhead")
    if crumb:
        cats = [a.get_text(strip=True) for a in crumb.find_all("a")]
        section = " > ".join([c for c in cats if c])

    # 4) 기자명(상단 byline anchor 텍스트)
    author = None
    byline = soup.select_one(".byline")
    if byline:
        names = [a.get_text(strip=True)
                 for a in byline.find_all("a") if a.get_text(strip=True)]
        author = ", ".join(names) if names else None

    # 5) 본문: Readability → 후보 선택자 스캔
    body_text = ""
    try:
        doc = Document(html)
        content_html = doc.summary(html_partial=True)
        body_text = _clean_html(BeautifulSoup(content_html, "lxml"))
    except Exception:
        pass

    if not body_text or len(body_text) < 400:
        node = None
        for tag, attrs in JOONGANG_BODY_CANDIDATES:
            node = soup.find(tag, attrs=attrs)
            if node:
                break
        if node:
            body_text = _clean_html(node)

    # 6) 날짜 정리: JS → meta → time[datetime] → 텍스트 휴리스틱
    published = None
    for cand in [published_js, meta_date_str, (time_tag.get("datetime") if time_tag else None)]:
        if cand:
            try:
                published = dateparser.parse(cand).date().isoformat()
                break
            except Exception:
                continue
    if not published:
        # 페이지 내 YYYY.MM.DD HH:MM or YYYY-MM-DD 휴리스틱
        m = re.search(
            r"(20\d{2}[.\-\/]\d{1,2}[.\-\/]\d{1,2}(\s+\d{1,2}:\d{2})?)", soup.get_text(" "))
        if m:
            try:
                published = dateparser.parse(m.group(1)).date().isoformat()
            except Exception:
                pass

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
                if "joongang.co.kr" not in url:
                    rec = {"url": url, "error": "not_joongang"}
                    out_f.write(orjson.dumps(rec) + b"\n")
                    continue
                html = fetch(url)
                rec = parse_joongang(url, html)
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
