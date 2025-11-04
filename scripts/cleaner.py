import argparse, json
import pandas as pd
import orjson
from jsonschema import validate, ValidationError
from urllib.parse import urlparse

from config import ensure_dir

from pathlib import Path

SCHEMA_PATH = Path("data/article_schema.json")
CRED_PATH = Path("data/credibility_map.csv")


def load_schema():
    import json
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def credibility_for(domain: str, df):
    try:
        row = df.loc[df["domain"] == domain].iloc[0]
        return float(row["score"])
    except Exception:
        return None


def main(inp: str, out: str):
    ensure_dir(out)
    schema = load_schema()
    cred_df = pd.read_csv(CRED_PATH)
    cred_df["domain"] = cred_df["domain"].astype(str)

    out_f = open(out, "wb")
    with open(inp, "rb") as f:
        for line in f:
            try:
                rec = orjson.loads(line)
                if "error" in rec:
                    continue
                # 기본 정리
                rec["domain"] = urlparse(rec.get("url", "")).netloc
                # 신뢰도 점수 매핑
                rec["credibility_score"] = credibility_for(rec["domain"], cred_df)
                # 언어 간단 감지(ko/other)
                try:
                    import langid
                    lang, _ = langid.classify(rec["body_text"][:2000])
                except Exception:
                    lang = None
                rec["lang"] = lang
                # 스키마 검증
                validate(instance=rec, schema=schema)
                out_f.write(orjson.dumps(rec) + b"\n")
            except ValidationError as ve:
                continue
            except Exception as e:
                continue
    out_f.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", dest="out", required=True)
    args = ap.parse_args()
    main(args.inp, args.out)
