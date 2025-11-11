# 신문사별 크롤러 가이드

## 개요

이 프로젝트는 **신문사별 플러그인 패턴**을 사용하는 통합 크롤러를 제공합니다. 각 신문사의 웹사이트 구조에 최적화된 파서를 자동으로 선택하여 정확하고 안정적인 데이터 추출이 가능합니다.

## 지원 신문사

| 신문사 | 도메인 | 파서 타입 | 특징 |
|--------|--------|-----------|------|
| 조선일보 | chosun.com | `chosun` | Arc Publishing (Fusion) JSON 파싱 |
| 중앙일보 | joongang.co.kr | `joongang` | window.article + meta 파싱 |
| 기타 | - | `generic` | Readability 기반 범용 파서 |

---

## 크롤러 종류

### 1. 통합 크롤러 (권장)

**파일**: `scripts/crawler_unified.py`

URL 도메인을 자동 감지하여 최적의 파서를 선택합니다.

```bash
# 사용법
PYTHONPATH=. python scripts/crawler_unified.py \
  --in data/urls.txt \
  --out results/articles.jsonl
```

**장점**:
- 여러 신문사 URL을 한 번에 처리
- 자동 파서 선택
- 통계 출력 (성공/실패/파서별 사용 현황)

**출력 예시**:
```
=== Crawling Statistics ===
Total URLs: 100
Success: 98
Error: 2

By Parser:
  chosun: 45
  joongang: 32
  generic: 21
```

### 2. 신문사별 전용 크롤러

특정 신문사만 크롤링할 때 사용합니다.

#### 조선일보 전용

**파일**: `scripts/crawler_chosun.py`

```bash
PYTHONPATH=. python scripts/crawler_chosun.py \
  --in data/chosun_urls.txt \
  --out results/chosun_articles.jsonl
```

**추출 데이터**:
- `headlines.basic` → 제목
- `display_date/first_publish_date` → 발행일
- `taxonomy.primary_section.name` → 섹션
- `content_elements[type='text'].content` → 본문

#### 중앙일보 전용

**파일**: `scripts/crawler_joongang.py`

```bash
PYTHONPATH=. python scripts/crawler_joongang.py \
  --in data/joongang_urls.txt \
  --out results/joongang_articles.jsonl
```

**추출 데이터**:
- `window.article.TITLE` → 제목
- `window.article.SERVICE_DAYTIME` → 발행일
- `meta[property="published_date"]` → 발행일 (보조)
- `<h1.headline>` → 제목 (보조)
- `.byline a` → 기자명
- `.subhead a` → 섹션/카테고리

#### 범용 크롤러

**파일**: `scripts/crawler.py`

```bash
PYTHONPATH=. python scripts/crawler.py \
  --in data/other_urls.txt \
  --out results/other_articles.jsonl
```

Readability 라이브러리 기반으로 다양한 웹사이트 지원.

---

## 출력 포맷

모든 크롤러는 동일한 **W1 스키마**를 따릅니다:

```json
{
  "source": "www.chosun.com",
  "url": "https://www.chosun.com/...",
  "headline": "기사 제목",
  "date": "2025-11-10",
  "author": "기자명" or null,
  "section": "섹션명" or null,
  "body_text": "본문 전체 텍스트...",
  "domain": "www.chosun.com",
  "parser_used": "chosun"
}
```

**주요 필드**:
- `source`/`domain`: 출처 도메인
- `headline`: 기사 제목
- `date`: ISO 8601 날짜 (YYYY-MM-DD)
- `author`: 작성자 (없으면 null)
- `section`: 섹션/카테고리
- `body_text`: 광고/배너 제거된 본문
- `parser_used`: 사용된 파서 타입 (통합 크롤러만)

---

## 파이프라인 통합

크롤링 결과는 기존 W1 파이프라인과 바로 연결됩니다:

```bash
# 1. 크롤링
PYTHONPATH=. python scripts/crawler_unified.py \
  --in data/urls.txt \
  --out results/articles_raw.jsonl

# 2. 정제 (중복 제거, 언어 필터링 등)
PYTHONPATH=. python scripts/cleaner.py \
  --in results/articles_raw.jsonl \
  --out results/articles_clean.jsonl

# 3. 품질 메트릭 분석
PYTHONPATH=. python scripts/metrics_baseline.py \
  --in results/articles_clean.jsonl \
  --out results/metrics.json
```

---

## 고급 사용법

### 혼합 수집 전략

여러 신문사를 효율적으로 수집하는 방법:

```bash
# 방법 1: 통합 크롤러로 한 번에 처리
cat data/chosun_urls.txt data/joongang_urls.txt data/other_urls.txt > data/all_urls.txt
PYTHONPATH=. python scripts/crawler_unified.py --in data/all_urls.txt --out results/all.jsonl

# 방법 2: 신문사별로 분리 수집 후 병합
PYTHONPATH=. python scripts/crawler_chosun.py --in data/chosun_urls.txt --out results/chosun.jsonl
PYTHONPATH=. python scripts/crawler_joongang.py --in data/joongang_urls.txt --out results/joongang.jsonl
cat results/chosun.jsonl results/joongang.jsonl > results/merged.jsonl
```

### 에러 핸들링

크롤링 실패한 URL은 에러 메시지와 함께 JSONL에 기록됩니다:

```json
{
  "url": "https://example.com/article",
  "error": "Fusion.globalContent not found",
  "parser_used": "chosun"
}
```

에러만 추출하려면:

```bash
# 에러 항목만 필터링
grep '"error"' results/articles.jsonl > results/errors.jsonl

# 성공한 항목만 필터링
grep -v '"error"' results/articles.jsonl > results/success.jsonl
```

---

## 신문사 추가하기

새로운 신문사를 추가하려면:

### 1. 전용 파서 작성

`scripts/crawler_newsite.py`:

```python
from config import ensure_dir
import orjson

def parse_newsite(url: str, html: str):
    # 신문사별 파싱 로직
    return {
        "source": "newsite.com",
        "url": url,
        "headline": "...",
        "date": "...",
        "author": "...",
        "section": "...",
        "body_text": "...",
        "domain": "newsite.com"
    }
```

### 2. 통합 크롤러에 등록

`scripts/crawler_unified.py`:

```python
# 파서 임포트 추가
from crawler_newsite import parse_newsite

# 매핑 추가
PARSER_MAP = {
    "chosun.com": "chosun",
    "joongang.co.kr": "joongang",
    "newsite.com": "newsite",  # 추가
}

# parse_article 함수에 분기 추가
def parse_article(url: str, html: str) -> dict:
    parser_type = detect_parser(url)

    if parser_type == "chosun":
        return parse_chosun(url, html)
    elif parser_type == "joongang":
        return parse_joongang(url, html)
    elif parser_type == "newsite":  # 추가
        return parse_newsite(url, html)
    else:
        return parse_generic(url, html)
```

---

## 테스트

### 단일 URL 테스트

```bash
# 테스트 URL 파일 생성
echo "https://www.chosun.com/politics/..." > data/test.txt

# 크롤링
PYTHONPATH=. python scripts/crawler_unified.py --in data/test.txt --out results/test.jsonl

# 결과 확인
cat results/test.jsonl | python -m json.tool
```

### 검증 스크립트

```python
import orjson

# JSONL 로드 및 검증
with open("results/articles.jsonl", "rb") as f:
    for line in f:
        rec = orjson.loads(line)

        # 필수 필드 체크
        assert "url" in rec
        assert "headline" in rec or "error" in rec

        # 성공 케이스 검증
        if "error" not in rec:
            assert rec["body_text"]
            assert len(rec["body_text"]) > 100
            print(f"✓ {rec['url'][:50]}... [{rec.get('parser_used', 'unknown')}]")
```

---

## 트러블슈팅

### PYTHONPATH 오류

```bash
# 오류: ModuleNotFoundError: No module named 'config'
# 해결: PYTHONPATH 설정
PYTHONPATH=. python scripts/crawler_unified.py --in ... --out ...
```

### 의존성 오류

```bash
# 필수 패키지 설치
pip install orjson requests beautifulsoup4 lxml readability-lxml python-dateutil
```

### 타임아웃 오류

크롤러 코드에서 `timeout` 값 조정:

```python
r = requests.get(url, headers=HEADERS, timeout=60)  # 30 → 60초로 증가
```

---

## 성능 팁

1. **병렬 처리**: URL 파일을 분할하여 여러 프로세스 실행
   ```bash
   split -l 100 data/urls.txt data/urls_part_
   for file in data/urls_part_*; do
       PYTHONPATH=. python scripts/crawler_unified.py --in "$file" --out "results/$(basename $file).jsonl" &
   done
   wait
   cat results/urls_part_*.jsonl > results/all.jsonl
   ```

2. **속도 조절**: 크롤러 내 `time.sleep()` 값 조정
   - 기본값: 성공 시 0.5초, 실패 시 0.2초
   - 서버 부하 고려하여 조정

3. **재시도 로직**: 실패한 URL만 재수집
   ```bash
   grep '"error"' results/articles.jsonl | jq -r '.url' > data/retry_urls.txt
   PYTHONPATH=. python scripts/crawler_unified.py --in data/retry_urls.txt --out results/retry.jsonl
   ```

---

## 참고

- **Arc Publishing**: 조선일보, 일부 한겨레/경향 섹션에서 사용
- **window.article**: 중앙일보 특유의 JS 객체
- **Readability**: Mozilla의 오픈소스 본문 추출 라이브러리
