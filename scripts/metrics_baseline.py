import argparse, re
import orjson
from collections import Counter

MODALS_KO = ["수도", "수도있", "수도 있", "듯", "같", "아마", "가능", "추정"]


def sentences(text: str):
    # 매우 단순한 문장 분할(1주차용)
    return [s for s in re.split(r"[\.!?\n]+", text) if s.strip()]


def tokens(text: str):
    # 공백기반 토큰화(한국어 정교화 전 단계)
    return [t for t in re.split(r"\s+", text) if t]


def ttr(text: str):
    ts = tokens(text)
    if not ts: return 0.0
    return len(set(ts)) / len(ts)


def modal_ratio(text: str):
    ts = tokens(text)
    if not ts: return 0.0
    cnt = 0
    for w in ts:
        if any(m in w for m in MODALS_KO):
            cnt += 1
    return cnt / len(ts)


def avg_sent_len(text: str):
    ss = sentences(text)
    if not ss: return 0.0
    return sum(len(tokens(s)) for s in ss) / len(ss)


def enrich(rec: dict):
    text = rec.get("body_text", "")
    rec.setdefault("metrics", {})
    rec["metrics"].update({
        "ttr": round(ttr(text), 4),
        "modal_ratio": round(modal_ratio(text), 4),
        "avg_sent_len": round(avg_sent_len(text), 2)
    })
    return rec


def main(inp: str, out: str):
    import sys
    tmp_lines = []
    with open(inp, "rb") as f:
        for line in f:
            try:
                rec = orjson.loads(line)
                rec = enrich(rec)
                tmp_lines.append(orjson.dumps(rec))
            except Exception:
                continue
    with open(out, "wb") as g:
        for b in tmp_lines:
            g.write(b + b"\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", dest="out", required=True)
    args = ap.parse_args()
    main(args.inp, args.out)
