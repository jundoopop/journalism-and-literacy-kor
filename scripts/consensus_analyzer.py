"""
Multi-LLM Consensus Analyzer
Analyzes articles using multiple LLM providers and calculates consensus scores
"""

import os
import logging
from typing import List, Dict, Optional, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict

# Import LLM providers
from llm.factory import LLMFactory
from llm.exceptions import APIKeyError, UnsupportedProviderError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Supported providers for consensus analysis
SUPPORTED_PROVIDERS = ['gemini', 'openai', 'claude', 'mistral']

# Analysis prompt (same as gemini_handler.py for consistency)
ANALYSIS_PROMPT = """시스템 역할: 당신은 비판적 읽기 훈련 코치이자 언론 분석가입니다.
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


class ConsensusAnalyzer:
    """
    Analyzes articles using multiple LLM providers and calculates consensus
    """

    def __init__(self, providers: Optional[List[str]] = None):
        """
        Initialize consensus analyzer

        Args:
            providers: List of provider names to use (default: ['gemini', 'mistral'])
        """
        self.providers = providers or ['gemini', 'mistral']
        self.llm_instances = {}

        logger.info(f"Initializing ConsensusAnalyzer with providers: {self.providers}")
        self._initialize_providers()

    def _initialize_providers(self):
        """Initialize LLM provider instances"""
        for provider_name in self.providers:
            if provider_name not in SUPPORTED_PROVIDERS:
                logger.warning(f"Provider '{provider_name}' not supported, skipping")
                continue

            try:
                llm = LLMFactory.create(provider=provider_name)
                self.llm_instances[provider_name] = llm
                logger.info(f"✓ Initialized {provider_name}")
            except (APIKeyError, UnsupportedProviderError) as e:
                logger.warning(f"✗ Failed to initialize {provider_name}: {e}")
            except Exception as e:
                logger.error(f"✗ Unexpected error initializing {provider_name}: {e}")

        if not self.llm_instances:
            raise ValueError(
                f"No LLM providers initialized. "
                f"Check API keys for: {self.providers}"
            )

        logger.info(f"Successfully initialized {len(self.llm_instances)} providers")

    def _analyze_with_provider(
        self,
        provider_name: str,
        article_text: str
    ) -> Dict[str, Any]:
        """
        Analyze article with a single provider

        Args:
            provider_name: Name of the provider
            article_text: Article text to analyze

        Returns:
            Dict with provider name, sentences, and success status
        """
        try:
            llm = self.llm_instances[provider_name]
            prompt = f"{ANALYSIS_PROMPT}\n\n기사 본문:\n{article_text}"

            logger.info(f"[{provider_name}] Analyzing article...")
            response = llm.analyze(prompt)

            # Parse response (expecting JSON dict: {sentence: reason})
            sentences_dict = response if isinstance(response, dict) else {}

            logger.info(f"[{provider_name}] ✓ Found {len(sentences_dict)} sentences")

            return {
                'provider': provider_name,
                'success': True,
                'sentences': sentences_dict,
                'error': None
            }

        except Exception as e:
            logger.error(f"[{provider_name}] ✗ Analysis failed: {e}")
            return {
                'provider': provider_name,
                'success': False,
                'sentences': {},
                'error': str(e)
            }

    def analyze_article(self, article_text: str) -> Dict[str, Any]:
        """
        Analyze article with all providers in parallel and calculate consensus

        Args:
            article_text: Article body text to analyze

        Returns:
            Dict containing consensus results with structure:
            {
                'success': True,
                'total_providers': 2,
                'successful_providers': ['gemini', 'openai'],
                'sentences': [
                    {
                        'text': 'sentence text',
                        'consensus_score': 2,
                        'consensus_level': 'high',
                        'selected_by': ['gemini', 'openai'],
                        'reasons': {
                            'gemini': 'reason text',
                            'openai': 'reason text'
                        }
                    }
                ]
            }
        """
        if not article_text or not article_text.strip():
            logger.warning("Empty article text provided")
            return {
                'success': False,
                'error': 'Empty article text',
                'sentences': []
            }

        # Analyze with all providers in parallel
        logger.info(f"Starting parallel analysis with {len(self.llm_instances)} providers")

        results = []
        with ThreadPoolExecutor(max_workers=len(self.llm_instances)) as executor:
            futures = {
                executor.submit(self._analyze_with_provider, name, article_text): name
                for name in self.llm_instances.keys()
            }

            for future in as_completed(futures):
                provider_name = futures[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    logger.error(f"[{provider_name}] Thread execution error: {e}")
                    results.append({
                        'provider': provider_name,
                        'success': False,
                        'sentences': {},
                        'error': str(e)
                    })

        # Calculate consensus
        consensus_data = self._calculate_consensus(results)

        return consensus_data

    def _normalize_sentence(self, sentence: str) -> str:
        """
        Normalize sentence for exact matching

        Args:
            sentence: Raw sentence text

        Returns:
            Normalized sentence (trimmed whitespace)
        """
        return sentence.strip()

    def _calculate_consensus(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate consensus from multiple provider results

        Args:
            results: List of provider analysis results

        Returns:
            Consensus data structure
        """
        successful_results = [r for r in results if r['success']]

        if not successful_results:
            logger.error("No successful provider results")
            return {
                'success': False,
                'error': 'All providers failed',
                'sentences': []
            }

        # Build sentence consensus map
        sentence_map = defaultdict(lambda: {
            'selected_by': [],
            'reasons': {}
        })

        for result in successful_results:
            provider = result['provider']
            sentences = result['sentences']

            for sentence, reason in sentences.items():
                normalized = self._normalize_sentence(sentence)
                sentence_map[normalized]['selected_by'].append(provider)
                sentence_map[normalized]['reasons'][provider] = reason

        # Convert to list with consensus scores
        consensus_sentences = []
        total_providers = len(successful_results)

        for sentence, data in sentence_map.items():
            consensus_score = len(data['selected_by'])

            # Determine consensus level based on number of providers
            if total_providers == 1:
                consensus_level = 'high'  # Single provider mode
            elif total_providers == 2:
                consensus_level = 'high' if consensus_score == 2 else 'low'
            else:  # 3+ providers
                if consensus_score >= 3:
                    consensus_level = 'high'
                elif consensus_score == 2:
                    consensus_level = 'medium'
                else:
                    consensus_level = 'low'

            consensus_sentences.append({
                'text': sentence,
                'consensus_score': consensus_score,
                'consensus_level': consensus_level,
                'selected_by': data['selected_by'],
                'reasons': data['reasons']
            })

        # Sort by consensus score (highest first)
        consensus_sentences.sort(key=lambda x: x['consensus_score'], reverse=True)

        logger.info(
            f"✓ Consensus calculated: {len(consensus_sentences)} unique sentences "
            f"from {len(successful_results)} providers"
        )

        return {
            'success': True,
            'total_providers': len(self.llm_instances),
            'successful_providers': [r['provider'] for r in successful_results],
            'failed_providers': [r['provider'] for r in results if not r['success']],
            'sentences': consensus_sentences,
            'count': len(consensus_sentences)
        }

    def get_highlight_sentences(self, article_text: str) -> List[str]:
        """
        Get only sentence texts (for backward compatibility)

        Args:
            article_text: Article body text

        Returns:
            List of sentence texts
        """
        result = self.analyze_article(article_text)

        if result['success']:
            return [s['text'] for s in result['sentences']]
        else:
            logger.error(f"Analysis failed: {result.get('error')}")
            return []


# CLI testing
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Multi-LLM 합의 분석 테스트")
    parser.add_argument("--text", type=str, help="분석할 기사 텍스트")
    parser.add_argument("--file", type=str, help="분석할 기사 파일 경로")
    parser.add_argument("--providers", nargs='+', default=['gemini', 'mistral'],
                        help="사용할 LLM 제공자 목록 (gemini, openai, claude, mistral)")

    args = parser.parse_args()

    # Load text
    if args.file:
        with open(args.file, 'r', encoding='utf-8') as f:
            text = f.read()
    elif args.text:
        text = args.text
    else:
        print("--text 또는 --file 인자가 필요합니다.")
        exit(1)

    # Run analysis
    try:
        analyzer = ConsensusAnalyzer(providers=args.providers)
        result = analyzer.analyze_article(text)

        print("\n=== 합의 분석 결과 ===")
        print(f"총 제공자: {result['total_providers']}")
        print(f"성공한 제공자: {', '.join(result['successful_providers'])}")

        if result['failed_providers']:
            print(f"실패한 제공자: {', '.join(result['failed_providers'])}")

        print(f"\n총 {result['count']}개 문장 발견\n")

        for i, item in enumerate(result['sentences'], 1):
            print(f"{i}. [{item['consensus_level'].upper()}] {item['text']}")
            print(f"   합의 점수: {item['consensus_score']}/{result['total_providers']}")
            print(f"   선택한 모델: {', '.join(item['selected_by'])}")
            print(f"   이유:")
            for provider, reason in item['reasons'].items():
                print(f"     - {provider}: {reason}")
            print()

    except Exception as e:
        print(f"오류 발생: {e}")
        exit(1)
