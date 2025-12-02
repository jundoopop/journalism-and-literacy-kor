"""
Prompt templates for article analysis

Contains system prompts for extracting notable sentences from news articles.
Supports Korean language journalism analysis.
"""

# Korean prompt for extracting literacy-enhancing sentences
# Ported from scripts/gemini_handler.py
ARTICLE_ANALYSIS_PROMPT = """시스템 역할: 당신은 비판적 읽기 훈련 코치이자 언론 분석가입니다.
주어진 기사 본문에서 **문해력 향상에 도움이 되는 문장**을 선별하고,
각 문장을 선택한 **이유**를 설명하세요.

출력 형식(JSON):
{
  "나는 배고프다": "단문 구조로 명확한 사실 진술을 보여주어 문장 명료성 학습에 유용함.",
  "정책은 사회적 합의를 필요로 한다": "추상적 개념을 구체적 행위와 연결하여 논리적 사고력 향상에 도움을 줌."
}

규칙:
- 기사에서 문해력, 논리적 사고, 비판적 읽기에 기여하는 문장 3~7개를 선택합니다.
- 이유는 (1) 문체·명료성, (2) 논리 구조, (3) 비판적 사고 유도 중 하나 이상에 근거해야 합니다.
- JSON 외 다른 텍스트를 출력하지 마세요.
"""

# Comprehensive analysis prompt for batch processing (from llm_tuner.py)
COMPREHENSIVE_ANALYSIS_PROMPT = """시스템 역할: 당신은 한국어 저널리즘 비평가이자 논증 분석가입니다.
주어진 텍스트에서 주장(claim), 근거(evidence), 논리적 오류(fallacy)를 찾아 구조화하여 반환합니다.
가능하면 텍스트의 실제 span 오프셋을 포함하세요. 출력은 반드시 JSON 하나로만, 다른 텍스트 없이 반환합니다.

입력: 기사 제목(title), 본문(body_text), URL(url, 선택), 발행일(published_at, 선택)

요구 포맷(JSON):
{
  "claims": [
    {"span": [start, end], "text": "...", "evidence_spans": [[s,e],[s,e]], "source_citations": ["..."]}
  ],
  "fallacies": [
    {"type": "false_dilemma|strawman|ad_hominem|hasty_generalization|appeal_to_authority|slippery_slope|circular_reasoning|others", "span": [start, end], "note": "..."}
  ],
  "quality_scores": {"argument_coherence": 0-5, "citation_sufficiency": 0-5, "clarity": 0-5},
  "headline_features": {"len": int, "negativity": 0.0-1.0, "clickbait_flags": ["..."]},
  "highlight_spans": [ {"span": [start, end], "tag": "claim|evidence|fallacy|fact"} ],
  "study_tips": ["1문장", "1문장", "1문장"]
}

규칙:
- 근거 없는 주장은 "evidence_spans": []로 비워둡니다.
- 수치/날짜/고유명사는 evidence 후보로 우선 표기합니다.
- JSON 이외 텍스트를 출력하지 마세요.
"""
