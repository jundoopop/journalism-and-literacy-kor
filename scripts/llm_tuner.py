import argparse
import time
import json
import random
from pathlib import Path
import orjson
import pandas as pd
from jsonschema import validate
from jsonschema.exceptions import ValidationError
from tqdm import tqdm

from config import OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL, REQUEST_TIMEOUT, MAX_RETRIES, ensure_dir

# OpenAI SDK v1
from openai import OpenAI
client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)

PROMPT_PATH = Path("prompts/base_prompt_ko.txt")
SCHEMA = {
    "type": "object",
    "properties": {
        "claims": {"type": "array"},
        "fallacies": {"type": "array"},
        "quality_scores": {"type": "object"},
        "headline_features": {"type": "object"},
        "highlight_spans": {"type": "array"},
        "study_tips": {"type": "array"}
    },
    "required": ["claims", "fallacies", "quality_scores", "highlight_spans", "study_tips"]
}


def call_llm(payload: dict, sys_prompt: str):
    messages = [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}
    ]
    resp = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=messages,
        temperature=0.2,
        response_format={"type": "json_object"}
    )
    return resp.choices[0].message.content


def main(inp: str, out: str, n: int):
    ensure_dir(out)
    sys_prompt = PROMPT_PATH.read_text(encoding="utf-8")

    # 입력 JSONL 로드
    rows = []
    with open(inp, "rb") as f:
        for line in f:
            try:
                rec = orjson.loads(line)
                if not rec.get("body_text"):
                    continue
                rows.append(rec)
            except Exception:
                continue
    random.shuffle(rows)
    rows = rows[:n]

    log_path = Path("results/tuning_log.csv")
    if not log_path.exists():
        log_path.write_text("url,status,tries\n", encoding="utf-8")

    with open(out, "wb") as out_f:
        for rec in tqdm(rows, desc="LLM Tuning"):
            payload = {
                "title": rec.get("headline"),
                "url": rec.get("url"),
                "published_at": rec.get("date"),
                "body_text": rec.get("body_text")[:12000]
            }
            ok = False
            err_msg = ""
            for attempt in range(MAX_RETRIES + 1):
                try:
                    content = call_llm(payload, sys_prompt)
                    data = json.loads(content)
                    validate(instance=data, schema=SCHEMA)
                    rec_out = {
                        "url": rec.get("url"),
                        "domain": rec.get("domain"),
                        "headline": rec.get("headline"),
                        "date": rec.get("date"),
                        "credibility_score": rec.get("credibility_score"),
                        "llm_analysis": data
                    }
                    out_f.write(orjson.dumps(rec_out) + b"\n")
                    ok = True
                    break
                except Exception as e:
                    err_msg = str(e)
                    time.sleep(1.2)
            with open(log_path, "a", encoding="utf-8") as lg:
                lg.write(
                    f"{rec.get('url')},{'ok' if ok else 'fail'},{attempt+1}\n")
            if not ok:
                # 실패 샘플도 기록(디버그용)
                fail_dump = Path("results/failed_samples.jsonl")
                with open(fail_dump, "ab") as fd:
                    fd.write(orjson.dumps(
                        {"url": rec.get("url"), "error": err_msg}) + b"\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", dest="out", required=True)
    ap.add_argument("--n", dest="n", type=int, default=30)
    args = ap.parse_args()
    main(args.inp, args.out, args.n)
