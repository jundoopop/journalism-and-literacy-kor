"""
통합 크롤러: 신문사별 플러그인 패턴
URL 도메인에 따라 최적화된 파서를 자동 선택합니다.

지원 신문사:
- 조선일보 (chosun.com): Arc/Fusion JSON 파싱
- 중앙일보 (joongang.co.kr): window.article + meta 파싱
- 기타: 범용 Readability 파서
"""

import argparse
import time
from urllib.parse import urlparse
import orjson
import requests

from config import ensure_dir

# 신문사별 파서 임포트
from crawler_chosun import parse_chosun
from crawler_joongang import parse_joongang
from crawler import extract_main_html, html_to_text, detect_date

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; W1-UnifiedCrawler/1.0)"}

# 신문사별 파서 매핑
PARSER_MAP = {
    "chosun.com": "chosun",
    "joongang.co.kr": "joongang",
}


def detect_parser(url: str) -> str:
    """URL에서 적절한 파서 유형을 결정합니다."""
    domain = urlparse(url).netloc.lower()
    for key, parser_type in PARSER_MAP.items():
        if key in domain:
            return parser_type
    return "generic"


def fetch(url: str) -> str:
    """URL에서 HTML을 가져옵니다."""
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.text


def parse_generic(url: str, html: str) -> dict:
    """범용 파서 (기존 crawler.py 로직)"""
    try:
        title, content_html = extract_main_html(url)
        body_text = html_to_text(content_html)
        domain = urlparse(url).netloc
        date_guess = detect_date(content_html) or detect_date(body_text)

        return {
            "source": domain,
            "url": url,
            "headline": title,
            "date": date_guess,
            "author": None,
            "section": None,
            "body_text": body_text,
            "domain": domain
        }
    except Exception as e:
        raise RuntimeError(f"Generic parsing failed: {e}")


def parse_article(url: str, html: str) -> dict:
    """
    URL에 맞는 파서를 선택하여 기사를 파싱합니다.

    Returns:
        dict: {source, url, headline, date, author, section, body_text, domain}
    """
    parser_type = detect_parser(url)

    if parser_type == "chosun":
        return parse_chosun(url, html)
    elif parser_type == "joongang":
        return parse_joongang(url, html)
    else:
        return parse_generic(url, html)


def main(inp: str, out: str):
    ensure_dir(out)

    stats = {"total": 0, "success": 0, "error": 0, "by_parser": {}}

    with open(out, "ab") as out_f, open(inp, "r", encoding="utf-8") as in_f:
        for line in in_f:
            url = line.strip()
            if not url or url.startswith("#"):
                continue

            stats["total"] += 1
            parser_type = detect_parser(url)
            stats["by_parser"][parser_type] = stats["by_parser"].get(
                parser_type, 0) + 1

            try:
                html = fetch(url)
                rec = parse_article(url, html)
                rec["parser_used"] = parser_type  # 어떤 파서를 사용했는지 기록
                out_f.write(orjson.dumps(rec) + b"\n")
                stats["success"] += 1
                time.sleep(0.5)
            except Exception as e:
                rec = {"url": url, "error": str(e), "parser_used": parser_type}
                out_f.write(orjson.dumps(rec) + b"\n")
                stats["error"] += 1
                time.sleep(0.2)

    # 통계 출력
    print(f"\n=== Crawling Statistics ===")
    print(f"Total URLs: {stats['total']}")
    print(f"Success: {stats['success']}")
    print(f"Error: {stats['error']}")
    print(f"\nBy Parser:")
    for parser, count in stats["by_parser"].items():
        print(f"  {parser}: {count}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description="통합 크롤러: URL 도메인에 따라 최적화된 파서를 자동 선택"
    )
    ap.add_argument("--in", dest="inp", required=True, help="입력 URL 목록 파일")
    ap.add_argument("--out", dest="out", required=True, help="출력 JSONL 파일")
    args = ap.parse_args()
    main(args.inp, args.out)
