"""
Gemini API Handler for Article Analysis
Extracts literacy-enhancing sentences from news articles
"""

import os
import json
import logging
from typing import List, Dict, Optional
import google.generativeai as genai

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
GEMINI_MODEL = 'gemini-1.5-flash'
MIN_SENTENCES = 3
MAX_SENTENCES = 7

# System prompt for Gemini API
SYSTEM_PROMPT = """시스템 역할: 당신은 비판적 읽기 훈련 코치이자 언론 분석가입니다.
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


class GeminiAPIError(Exception):
    """Custom exception for Gemini API errors"""
    pass


class GeminiAnalyzer:
    """
    Analyzer for extracting literacy-enhancing sentences using Gemini API
    """

    def __init__(self, api_key: Optional[str] = None, model_name: str = GEMINI_MODEL):
        """
        Initialize Gemini API client

        Args:
            api_key: Gemini API key (defaults to GEMINI_API_KEY env variable)
            model_name: Gemini model to use

        Raises:
            ValueError: If API key is not provided
        """
        api_key = api_key or os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY not configured. "
                "Provide via environment variable or constructor argument."
            )

        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)
        logger.info(f"Gemini API initialized with model: {model_name}")

    def _clean_json_response(self, text: str) -> str:
        """
        Clean Gemini response text to extract pure JSON

        Args:
            text: Raw response text from Gemini

        Returns:
            Cleaned JSON string
        """
        text = text.strip()

        # Remove markdown code blocks if present
        if text.startswith("```"):
            parts = text.split("```")
            if len(parts) >= 2:
                text = parts[1]
                # Remove language identifier (e.g., "json")
                if text.startswith("json"):
                    text = text[4:].strip()

        return text

    def analyze_article(self, article_text: str) -> Dict[str, str]:
        """
        Analyze article and extract literacy-enhancing sentences

        Args:
            article_text: Article body text to analyze

        Returns:
            Dictionary mapping sentences to selection reasons

        Raises:
            GeminiAPIError: If API call or parsing fails
        """
        if not article_text or not article_text.strip():
            logger.warning("Empty article text provided")
            return {}

        prompt = f"{SYSTEM_PROMPT}\n\n기사 본문:\n{article_text}"

        try:
            logger.info("Sending request to Gemini API...")
            response = self.model.generate_content(prompt)
            result_text = self._clean_json_response(response.text)

            logger.debug(f"Cleaned response: {result_text[:200]}...")
            parsed = json.loads(result_text)

            logger.info(f"Successfully extracted {len(parsed)} sentences")
            return parsed

        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {e}")
            logger.error(f"Raw response: {response.text}")
            raise GeminiAPIError(f"Failed to parse JSON response: {e}")

        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            raise GeminiAPIError(f"API call failed: {e}")

    def get_highlight_sentences(self, article_text: str) -> List[str]:
        """
        Extract only the sentences to highlight (without reasons)

        Args:
            article_text: Article body text to analyze

        Returns:
            List of sentences to highlight
        """
        try:
            analysis = self.analyze_article(article_text)
            sentences = list(analysis.keys())

            logger.info(f"Extracted {len(sentences)} highlight sentences")
            return sentences

        except GeminiAPIError as e:
            logger.error(f"Failed to extract sentences: {e}")
            return []


# CLI 테스트용
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Gemini API로 기사 분석")
    parser.add_argument("--text", type=str, help="분석할 기사 텍스트")
    parser.add_argument("--file", type=str, help="분석할 기사 파일 경로")
    parser.add_argument("--api-key", type=str, help="Gemini API 키")

    args = parser.parse_args()

    # 텍스트 로드
    if args.file:
        with open(args.file, 'r', encoding='utf-8') as f:
            text = f.read()
    elif args.text:
        text = args.text
    else:
        print("--text 또는 --file 인자가 필요합니다.")
        exit(1)

    # 분석 실행
    analyzer = GeminiAnalyzer(api_key=args.api_key)
    result = analyzer.analyze_article(text)

    print("\n=== 분석 결과 ===")
    for sentence, reason in result.items():
        print(f"\n문장: {sentence}")
        print(f"이유: {reason}")

    print(f"\n총 {len(result)}개 문장 선택됨")
