import re, json, time, argparse
from urllib.parse import urlparse
import orjson
import requests
from dateutil import parser as dateparser
from pathlib import Path

from config import ensure_dir

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; W1-ChosunCrawler/1.0)"}


def _find_fusion_json(html: str):
    """
    조선일보(Arc/Fusion) 내장 스크립트에서 Fusion.globalContent JSON을 뽑아낸다.
    """
    # 가장 안전한 패턴: globalContent 시작 ~ globalContentConfig 직전까지 캡쳐
    m = re.search(
        r"Fusion\.globalContent\s*=\s*(\{.*?\});\s*Fusion\.globalContentConfig",
        html,
        flags=re.DOTALL
    )
    if not m:
        return None
    raw = m.group(1)
    # Arc JSON 안에는 자주 trailing comma 문제 없음. 그대로 파싱 시도.
    try:
        return json.loads(raw)
    except Exception:
        # 가끔 특수제어문자/주석 등으로 실패하는 경우 대비: 느슨한 정리
        cleaned = re.sub(r"/\*.*?\*/", "", raw, flags=re.DOTALL)
        cleaned = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", "", cleaned)
        return json.loads(cleaned)


def _extract_text_from_content_elements(global_content: dict) -> str:
    """
    Arc content_elements 배열에서 type=='text' 항목의 content를 모아 본문 생성.
    필요시 'list', 'oembed', 'quote' 등 추가 처리 가능.
    """
    elems = global_content.get("content_elements") or []
    texts = []
    for el in elems:
        t = el.get("type")
        if t == "text":
            c = (el.get("content") or "").strip()
            if c:
                texts.append(c)
        # 캡션, 인용, 리스트 등 확장 필요 시 여기에 분기 추가
    return "\n".join(texts).strip()


def parse_chosun(url: str, html: str):
    gc = _find_fusion_json(html)
    if not gc:
        # 아주 드물게 Fusion 블록이 없을 때: readability 등으로 폴백 권장
        raise RuntimeError("Fusion.globalContent not found")

    # 제목
    headline = (gc.get("headlines") or {}).get("basic")
    # 날짜
    published = gc.get("display_date") or gc.get("first_publish_date")  # ISO8601
    if published:
        try:
            published = dateparser.parse(published).date().isoformat()
        except Exception:
            pass
    # 섹션
    section = None
    tax = gc.get("taxonomy") or {}
    prim = tax.get("primary_section") or {}
    section = prim.get("name") or prim.get("_id")

    # 본문
    body_text = _extract_text_from_content_elements(gc)

    # 작성자(있으면)
    author = None
    # Arc의 credits/authors 구조가 페이지마다 다름. 필요 시 확장:
    # author_elems = gc.get("credits", {}).get("by", [])
    # if author_elems:
    #     author = ", ".join([a.get("name") for a in author_elems if a.get("name")])

    domain = urlparse(url).netloc
    return {
        "source": domain,
        "url": url,
        "headline": headline,
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
                if "chosun.com" not in url:
                    rec = {"url": url, "error": "not_chosun"}
                    out_f.write(orjson.dumps(rec) + b"\n")
                    continue
                html = fetch(url)
                rec = parse_chosun(url, html)
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
