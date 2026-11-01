"""Backward-compatible Gemini entry point using the common provider configuration."""
from typing import Dict, List, Optional
from llm.factory import LLMFactory
from llm.base import LLMProvider
from llm.config import DEFAULT_MODELS
from llm.prompts.article_analysis import ARTICLE_ANALYSIS_PROMPT as SYSTEM_PROMPT

GEMINI_MODEL = DEFAULT_MODELS[LLMProvider.GEMINI]
MIN_SENTENCES = 3
MAX_SENTENCES = 5

class GeminiAPIError(Exception):
    pass

class GeminiAnalyzer:
    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        self.provider = LLMFactory.create("gemini", api_key=api_key, model_name=model_name)
        self.model_name = self.provider.config.model_name

    def analyze_article(self, article_text: str) -> Dict[str, str]:
        try:
            return self.provider.analyze_article(article_text, SYSTEM_PROMPT).sentences
        except Exception as exc:
            raise GeminiAPIError(str(exc)) from exc

    def get_highlight_sentences(self, article_text: str) -> List[str]:
        try:
            return list(self.analyze_article(article_text))
        except GeminiAPIError:
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
