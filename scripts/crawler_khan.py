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

KHAN_BODY_CANDIDATES = [
    ("div", {"id": "articleBody"}),
    ("div", {"class": "art_body"}),
    ("section", {"class": re.compile(r"art_cont", re.I)}),
]


def _clean_html(node: BeautifulSoup) -> str:
    """광고/공유/스크립트/추천영역 제거"""
    # 광고/스크립트 제거
    for bad in node(["script", "style", "noscript", "iframe", "aside", "footer", "header"]):
        bad.decompose()

    # 광고 및 불필요한 영역 제거
    junk_patterns = ["ad", "banner", "recommend",
                     "related", "share", "sns", "utility", "KH_View"]
    for pat in junk_patterns:
        for d in node.find_all(attrs={"class": re.compile(pat, re.I)}):
            d.decompose()
        for d in node.find_all(id=re.compile(pat, re.I)):
            d.decompose()

    # 배너 관련 div 제거
    for d in node.find_all("div", class_=re.compile(r"banner", re.I)):
        d.decompose()

    # 텍스트 추출
    lines = [t.strip() for t in node.get_text("\n").splitlines() if t.strip()]
    return "\n".join(lines)


def parse_khan(url: str, html: str):
    soup = BeautifulSoup(html, "lxml")

    # 1) 제목: <h1> 태그
    h1 = soup.select_one("article header h1")
    title = h1.get_text(strip=True) if h1 else None

    # 제목이 없으면 <title> 태그에서 추출
    if not title and soup.title:
        title = soup.title.string.strip().split("|")[0].strip()

    # 2) 카테고리/섹션: <ul class="category"> 내의 <a> 태그
    section = None
    category_link = soup.select_one("article header ul.category li a")
    if category_link:
        section = category_link.get_text(strip=True)

    # 3) 날짜: <div class="date"> 내의 텍스트에서 추출
    published = None
    date_div = soup.select_one("article header div.date")
    if date_div:
        # "입력 2025.11.11 06:00" 형태의 텍스트에서 날짜 추출
        date_text = date_div.get_text(" ", strip=True)
        # "입력" 다음의 날짜를 찾음
        m = re.search(
            r"입력\s+(20\d{2}\.\d{1,2}\.\d{1,2}(?:\s+\d{1,2}:\d{2})?)", date_text)
        if m:
            try:
                published = dateparser.parse(m.group(1)).date().isoformat()
            except Exception:
                pass

    # 날짜를 찾지 못한 경우 meta 태그에서 시도
    if not published:
        meta_date = soup.find(
            "meta", attrs={"property": "article:published_time"})
        if meta_date and meta_date.get("content"):
            try:
                published = dateparser.parse(
                    meta_date.get("content")).date().isoformat()
            except Exception:
                pass

    # 4) 기자명: <li class="editor"> 내의 <a> 태그
    author = None
    editor_li = soup.select_one("article header ul.bottom li.editor a")
    if editor_li:
        author_text = editor_li.get_text(strip=True)
        # "박은경 기자" 형태에서 이름만 추출
        author = author_text.split()[0] if author_text else None

    # 5) 본문: <div class="art_body" id="articleBody"> 내의 텍스트
    body_text = ""
    article_body = soup.select_one("div#articleBody")

    if article_body:
        # 부제목 추출 (있는 경우)
        subtitle_div = article_body.select_one("div.editor-subtitle")
        subtitle = ""
        if subtitle_div:
            subtitle = subtitle_div.get_text("\n", strip=True)
            subtitle_div.decompose()  # 본문에서 제거

        # 중간 제목도 포함하여 추출
        middle_titles = article_body.find_all(
            "div", class_="editor-middle-title")

        # 본문 단락들 추출 (<p class="content_text">)
        paragraphs = []

        # 부제목 추가
        if subtitle:
            paragraphs.append(subtitle)

        # 본문 내용 순서대로 추출
        for elem in article_body.find_all(["p", "div"], class_=["content_text", "editor-middle-title"]):
            text = elem.get_text(strip=True)
            if text:
                paragraphs.append(text)

        body_text = "\n\n".join(paragraphs)

    # 본문이 충분하지 않은 경우 후보 선택자로 다시 시도
    if not body_text or len(body_text) < 200:
        node = None
        for tag, attrs in KHAN_BODY_CANDIDATES:
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
                if "khan.co.kr" not in url:
                    rec = {"url": url, "error": "not_khan"}
                    out_f.write(orjson.dumps(rec) + b"\n")
                    continue
                html = fetch(url)
                rec = parse_khan(url, html)
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
