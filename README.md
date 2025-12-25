# News Literacy Highlighter — Chrome Extension + Flask LLM Backend

크롬 확장과 Flask 서버가 연동되어 뉴스 기사에 **문해력·비판적 읽기용 하이라이트**를 적용합니다. 기본 LLM은 **Gemini + Mistral 합의 모드**이며, API 연결 테스트/설정 문서가 포함되어 있습니다.

## 빠른 시작

1) 의존성 설치
```bash
pip install -r requirements.txt
```

2) 환경변수 설정 (루트에 `.env` 작성)
```bash
GEMINI_API_KEY=...
MISTRAL_API_KEY=...          # 추천, 합의 모드 기본값
OPENAI_API_KEY=...           # 선택
CLAUDE_API_KEY=...           # 선택
FLASK_PORT=5001              # 크롬 확장 기본 포트와 일치
CONSENSUS_ENABLED=True
CONSENSUS_PROVIDERS=gemini,mistral
LLM_PROVIDER=gemini          # 단일 모드 기본값
```

3) API 연결 자가진단
```bash
python scripts/test_api_connection.py
```
로그에서 각 프로바이더의 `CONNECTED/FAILED/NOT CONFIGURED` 상태를 확인합니다. 자세한 해석은 `docs/API_CONNECTION_GUIDE.md` 참고.

4) 서버 실행
```bash
python scripts/server.py
```
기본 엔드포인트:
- `GET /health`
- `POST /analyze` (단일 LLM)
- `POST /analyze_consensus` (기본: gemini + mistral)

5) 크롬 확장 로드
- `chrome://extensions` → 개발자 모드 → **Load unpacked** → `chrome-ex` 폴더 선택
- 백그라운드가 `http://localhost:5001`로 Flask 서버에 HTTP 요청을 보냅니다. 포트를 바꿀 경우 `chrome-ex/background.js`의 `SERVER_URL`과 `manifest.json`의 `host_permissions`를 함께 수정하세요.

6) 사용
- 지원 도메인: `chosun.com`, `hani.co.kr`, `hankookilbo.com`, `joongang.co.kr`, `khan.co.kr`
- 기사 페이지 접속 후 자동으로 0.3s 뒤 분석/하이라이팅이 실행되며, 콘솔 로그(`[하이라이터]`, `[Background]`)에서 진행 상황을 볼 수 있습니다.

## 아키텍처
```
News page
  ↓
chrome-ex/content.js  (DOM 추출 + 하이라이트)
  ↓
chrome-ex/background.js (HTTP → Flask 서버, 캐싱)
  ↓
scripts/server.py  (기사 크롤링 + LLM/합의 분석)
  ↓
scripts/gemini_handler.py, mistral provider 등
```

## 주요 구성/기능
- **합의 분석 기본값**: `['gemini', 'mistral']` (`scripts/consensus_analyzer.py`, `/analyze_consensus`)
- **Mistral 지원**: 모델 기본값 `mistral-small-2506` (`docs/MISTRAL_SETUP.md`)
- **Gemini 모델**: `gemini-2.5-flash-lite` 기본값 (`scripts/gemini_handler.py`)
- **API 테스트 유틸**: `scripts/test_api_connection.py` (모든 프로바이더 키/호출 점검)
- **확장 HTTP 모드**: Native Messaging 대신 Flask HTTP(5001)로 통신 (`chrome-ex/background.js`, `manifest.json`)

## API 요약 (기본 포트 5001)
- `GET /health` : 서버/키 준비 상태 확인
- `GET /test` : 간단 응답
- `POST /analyze` : 단일 LLM 분석
- `POST /analyze_consensus` : 다중 LLM 합의 분석 (`providers` 파라미터 없으면 gemini+mistral 사용)

## 문서 바로가기
- `docs/MISTRAL_SETUP.md` : Mistral 키 발급/모델 설정/트러블슈팅
- `docs/API_CONNECTION_GUIDE.md` : `scripts/test_api_connection.py` 로그 해석
- `README_EXTENSION.md` : 확장 작동 방식/디버깅 가이드

## 체크리스트
- [ ] `.env`에 `GEMINI_API_KEY`와 `MISTRAL_API_KEY`가 설정됨
- [ ] `python scripts/test_api_connection.py`에서 필요한 프로바이더가 `CONNECTED`
- [ ] `python scripts/server.py` 정상 기동 (`/health` OK)
- [ ] 크롬 확장 로드 후 기사 페이지에서 자동 하이라이팅 동작
