import argparse, json, time, re
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup
from readability import Document
from dateutil import parser as dateparser
from pathlib import Path
import orjson

from config import ensure_dir

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; W1-Starter/1.0)"}


def extract_main_html(url: str):
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    html = r.text
    # Readability 우선 → 실패 시 수동 파싱
    try:
        doc = Document(html)
        content_html = doc.summary(html_partial=True)
        title = doc.short_title()
    except Exception:
        soup = BeautifulSoup(html, "lxml")
        title = (soup.title.string or "").strip() if soup.title else ""
        # 신문사별 관용 클래스를 몇 개 커버
        candidates = [
            {"name": "article-body", "tag": "div"},
            {"name": "article", "tag": "article"},
            {"name": "content", "tag": "div"}
        ]
        node = None
        for c in candidates:
            node = soup.find(c["tag"], class_=re.compile(c["name"], re.I))
            if node:
                break
        content_html = str(node or soup.body or soup)
    return title, content_html


def html_to_text(content_html: str):
    soup = BeautifulSoup(content_html, "lxml")
    # 광고/스크립트 제거
    for bad in soup(["script", "style", "noscript", "iframe", "header", "footer", "aside"]):
        bad.decompose()
    # 흔한 광고/추천 박스 클래스 제거
    for cls in ["ad", "banner", "recommend", "related"]:
        for d in soup.find_all(class_=re.compile(cls, re.I)):
            d.decompose()
    text = "\n".join(t.strip() for t in soup.get_text("\n").splitlines() if t.strip())
    return text


def detect_date(html_text: str):
    # 단순 휴리스틱: ISO/국문 날짜 패턴 찾아 파싱
    m = re.search(r"(20\d{2}[./-]\d{1,2}[./-]\d{1,2})", html_text)
    if m:
        try:
            return dateparser.parse(m.group(1)).date().isoformat()
        except Exception:
            pass
    return None


def main(inp: str, out: str):
    ensure_dir(out)
    out_f = open(out, "ab")
    with open(inp, "r", encoding="utf-8") as f:
        for line in f:
            url = line.strip()
            if not url or url.startswith("#"): continue
            try:
                title, content_html = extract_main_html(url)
                body_text = html_to_text(content_html)
                domain = urlparse(url).netloc
                date_guess = detect_date(content_html) or detect_date(body_text)
                rec = {
                    "source": domain,
                    "url": url,
                    "headline": title,
                    "date": date_guess,
                    "author": None,
                    "section": None,
                    "body_text": body_text,
                    "domain": domain
                }
                out_f.write(orjson.dumps(rec) + b"\n")
                time.sleep(0.8)
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
