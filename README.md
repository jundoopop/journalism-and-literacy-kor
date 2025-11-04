# W1 Starter Kit — 뉴스 품질·LLM 탐지 스캐폴딩

한 주 차에 필요한 **데이터 스캐폴딩 + LLM 출력 안정화**를 위한 최소 실행 패키지입니다.

## 빠른 시작

1. Python 3.10+ 설치 후 의존성 설치

```bash
pip install -r requirements.txt
```

2. 환경변수 설정 (.env 복사)

```bash
cp .env.example .env
# .env 파일에 OPENAI_API_KEY, MODEL 지정
```

3. 수집 대상 URL 준비

* `data/input_urls.txt`에 기사 URL 30개 이상을 줄바꿈으로 입력

4. 크롤링 & 정제

```bash
python scripts/crawler.py --in data/input_urls.txt --out results/articles_raw.jsonl
python scripts/cleaner.py --in results/articles_raw.jsonl --out results/articles_clean.jsonl
```

5. 기본 지표 계산(문해력/LLM 단서용 베이스라인)

```bash
python scripts/metrics_baseline.py --in results/articles_clean.jsonl --out results/articles_clean.jsonl
```

6. LLM 분석 스키마 튜닝(샘플 30편)

```bash
python scripts/llm_tuner.py --in results/articles_clean.jsonl --out results/llm_samples.jsonl --n 30
```

## 산출물

* `results/articles_raw.jsonl` : 크롤러 원본(간단 정리 포함)
* `results/articles_clean.jsonl` : 정제 완료(스키마 준수 + 베이스라인 지표 컬럼 일부 추가)
* `results/llm_samples.jsonl` : LLM 분석 JSON(주장/근거/오류/하이라이트 등)
* `results/tuning_log.csv` : 프롬프트 안정화 로그(성공/실패/재시도)

## 참고

* 신뢰도 매핑: `data/credibility_map.csv` (도메인→점수). 실제 배포 시 최신화 필요.
* 스키마: `data/article_schema.json` 을 기준으로 데이터 검증.

## 실행 체크리스트 (W1 목표 달성 기준)

- [ ] `results/articles_raw.jsonl` 생성 (30편+)
- [ ] `results/articles_clean.jsonl` 생성 (스키마 준수, lang/credibility_score 포함)
- [ ] `results/articles_clean.jsonl`에 `metrics.ttr/modal_ratio/avg_sent_len` 추가됨
- [ ] `results/llm_samples.jsonl`에 최소 25편 이상 성공(JSON 유효)
- [ ] `results/tuning_log.csv`에서 실패율 < 20%

## 다음 단계(W2 예고)

* 규칙기반 품질지표 고도화(헤드라인 극성, 근거 연결, fallacy 룰셋)
* LLM 출력과 품질지표 결합 및 신뢰도 상관분석 파이프라인
* 크롬 확장 content-script 시제품 연결(API: `/analyze`)
