"""
Analysis service for LLM-based article analysis.

Encapsulates the article analysis logic, supporting both
single LLM and consensus-based analysis.
"""

import time
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict

from .base_service import BaseService, ServiceError
from observability import metrics


@dataclass
class AnalysisResult:
    """Single LLM analysis result."""
    provider: str
    sentences: Dict[str, str]  # {sentence: reason}
    model_name: Optional[str] = None
    duration_ms: Optional[int] = None
    success: bool = True
    error_message: Optional[str] = None


@dataclass
class ConsensusResult:
    """Multi-LLM consensus analysis result."""
    sentences: List[Dict[str, Any]]  # List of sentences with consensus metadata
    total_providers: int
    successful_providers: List[str]
    failed_providers: List[str] = field(default_factory=list)
    total_duration_ms: Optional[int] = None


class AnalysisError(ServiceError):
    """Exception raised when analysis fails."""
    pass


class AnalysisService(BaseService):
    """
    Service for LLM-based article analysis.

    Supports:
    - Single LLM analysis
    - Multi-LLM consensus analysis
    - Metrics collection
    - Error handling
    """

    def __init__(self, cache_service=None):
        super().__init__("AnalysisService")
        self._gemini_analyzer = None
        self._consensus_analyzer = None
        self._cache_service = cache_service
        self._gemini_system_prompt = None
        self._consensus_system_prompt = None

    def _get_gemini_analyzer(self):
        """Lazy load Gemini analyzer."""
        if self._gemini_analyzer is None:
            import sys
            import os
            sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
            from gemini_handler import GeminiAnalyzer
            self._gemini_analyzer = GeminiAnalyzer()
        return self._gemini_analyzer

    def _get_consensus_analyzer(self, providers: List[str]):
        """Lazy load consensus analyzer."""
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
        from consensus_analyzer import ConsensusAnalyzer
        return ConsensusAnalyzer(providers=providers)

    def _get_gemini_system_prompt(self) -> str:
        """Get the Gemini system prompt for token estimation."""
        if self._gemini_system_prompt is None:
            import sys
            import os
            sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
            from gemini_handler import SYSTEM_PROMPT
            self._gemini_system_prompt = SYSTEM_PROMPT
        return self._gemini_system_prompt

    def _get_consensus_system_prompt(self) -> str:
        """Get the consensus system prompt for token estimation."""
        if self._consensus_system_prompt is None:
            import sys
            import os
            sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
            from consensus_analyzer import ANALYSIS_PROMPT
            self._consensus_system_prompt = ANALYSIS_PROMPT
        return self._consensus_system_prompt

    def _build_prompt_text(self, system_prompt: str, article_text: str) -> str:
        """Build prompt text used for token estimation."""
        if not system_prompt:
            return article_text
        return f"{system_prompt}\n\n기사 본문:\n{article_text}"

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count from text length."""
        if not text:
            return 0
        from config import settings
        chars_per_token = settings.llm.estimated_chars_per_token or 4
        if chars_per_token <= 0:
            chars_per_token = 4
        return max(1, int(len(text) / chars_per_token))

    def _compute_cost(self, provider: str, total_tokens: int) -> Optional[float]:
        """Compute estimated cost for a provider and token count."""
        from config import settings
        pricing = settings.llm.token_pricing_per_1k or {}
        rate = pricing.get(provider)
        if rate is None:
            return None
        return round((total_tokens / 1000.0) * rate, 6)

    def _serialize_sentences(self, sentences: Dict[str, str]) -> str:
        """Serialize sentence-reason pairs for token estimation."""
        parts = []
        for sentence, reason in sentences.items():
            if reason:
                parts.append(f"{sentence} {reason}")
            else:
                parts.append(sentence)
        return " ".join(parts)

    def _record_single_token_usage(
        self,
        provider: str,
        article_text: str,
        sentences: Dict[str, str]
    ) -> Dict[str, Optional[float]]:
        """Estimate and record token usage for single-provider analysis."""
        prompt_text = self._build_prompt_text(self._get_gemini_system_prompt(), article_text)
        prompt_tokens = self._estimate_tokens(prompt_text)
        completion_text = self._serialize_sentences(sentences)
        completion_tokens = self._estimate_tokens(completion_text)
        total_tokens = prompt_tokens + completion_tokens
        cost_usd = self._compute_cost(provider, total_tokens)

        metrics.record_token_usage(
            provider,
            prompt_tokens,
            completion_tokens,
            total_tokens,
            cost_usd,
            tags={"mode": "single"},
            estimated=True
        )

        return {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "cost_usd": cost_usd,
            "token_estimated": True
        }

    def _record_consensus_token_usage(
        self,
        providers: List[str],
        article_text: str,
        sentences: List[Dict[str, Any]]
    ) -> Dict[str, Optional[float]]:
        """Estimate and record token usage per provider for consensus."""
        prompt_text = self._build_prompt_text(self._get_consensus_system_prompt(), article_text)
        prompt_tokens = self._estimate_tokens(prompt_text)

        provider_outputs = defaultdict(list)
        for sentence_data in sentences:
            text = sentence_data.get("text", "")
            reasons = sentence_data.get("reasons", {}) or {}
            for provider, reason in reasons.items():
                if text and reason:
                    provider_outputs[provider].append(f"{text} {reason}")
                elif text:
                    provider_outputs[provider].append(text)
                elif reason:
                    provider_outputs[provider].append(reason)

        total_tokens_sum = 0
        total_cost_usd = 0.0
        has_cost = False

        for provider in providers:
            completion_text = " ".join(provider_outputs.get(provider, []))
            completion_tokens = self._estimate_tokens(completion_text)
            total_tokens = prompt_tokens + completion_tokens
            cost_usd = self._compute_cost(provider, total_tokens)

            metrics.record_token_usage(
                provider,
                prompt_tokens,
                completion_tokens,
                total_tokens,
                cost_usd,
                tags={"mode": "consensus"},
                estimated=True
            )

            total_tokens_sum += total_tokens
            if cost_usd is not None:
                total_cost_usd += cost_usd
                has_cost = True

        return {
            "prompt_tokens": prompt_tokens,
            "total_tokens": total_tokens_sum,
            "cost_usd": total_cost_usd if has_cost else None,
            "token_estimated": True
        }

    def analyze_single(self, article_text: str, provider: str = 'gemini', url: Optional[str] = None, use_cache: bool = True) -> AnalysisResult:
        """
        Analyze article with a single LLM provider.

        Args:
            article_text: Article body text
            provider: LLM provider to use (default: 'gemini')
            url: Optional article URL for caching
            use_cache: Whether to use cache (default: True)

        Returns:
            AnalysisResult with selected sentences

        Raises:
            AnalysisError: If analysis fails

        Example:
            result = analysis_service.analyze_single(article_text, provider='gemini', url=url)
            for sentence, reason in result.sentences.items():
                print(f"{sentence}: {reason}")
        """
        start_time = time.time()

        self.log_info("Starting single LLM analysis", provider=provider, text_length=len(article_text))
        self.increment_counter("analysis_requests", tags={"mode": "single", "provider": provider})

        # Check cache if enabled
        if use_cache and url and self._cache_service and self._cache_service.is_enabled():
            cached_result = self._cache_service.get_analysis_result(url, [provider])
            if cached_result:
                self.log_info("Cache hit for single analysis", provider=provider, url=url[:50])

                return AnalysisResult(
                    provider=provider,
                    sentences=cached_result.get('sentences', {}),
                    duration_ms=cached_result.get('duration_ms'),
                    success=True
                )

        try:
            with metrics.timer("analysis_duration", tags={"mode": "single", "provider": provider}):
                if provider == 'gemini':
                    analyzer = self._get_gemini_analyzer()
                    sentences = analyzer.analyze_article(article_text)
                else:
                    raise AnalysisError(f"Unsupported provider for single analysis: {provider}")

            duration_ms = int((time.time() - start_time) * 1000)

            result = AnalysisResult(
                provider=provider,
                sentences=sentences,
                duration_ms=duration_ms,
                success=True
            )

            token_usage = self._record_single_token_usage(provider, article_text, sentences)

            self.log_info(
                "Single LLM analysis completed",
                provider=provider,
                sentence_count=len(sentences),
                duration_ms=duration_ms,
                **token_usage
            )

            self.increment_counter("analysis_success", tags={"mode": "single", "provider": provider})
            self.track_metric("sentence_count", len(sentences), tags={"mode": "single", "provider": provider})

            # Store in cache if enabled
            if use_cache and url and self._cache_service and self._cache_service.is_enabled():
                cache_data = {
                    'sentences': sentences,
                    'duration_ms': duration_ms,
                    'provider': provider
                }
                self._cache_service.set_analysis_result(url, [provider], cache_data)

            return result

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)

            self.log_error(
                "Single LLM analysis failed",
                exc=e,
                provider=provider,
                duration_ms=duration_ms
            )

            self.increment_counter("analysis_failures", tags={
                "mode": "single",
                "provider": provider,
                "error_type": type(e).__name__
            })

            raise AnalysisError(
                f"Analysis failed with provider {provider}",
                details={'provider': provider, 'error': str(e)}
            ) from e

    def analyze_consensus(
        self,
        article_text: str,
        providers: Optional[List[str]] = None,
        url: Optional[str] = None,
        use_cache: bool = True
    ) -> ConsensusResult:
        """
        Analyze article with multiple LLM providers for consensus.

        Args:
            article_text: Article body text
            providers: List of provider names (default: ['gemini', 'mistral'])
            url: Optional article URL for caching
            use_cache: Whether to use cache (default: True)

        Returns:
            ConsensusResult with consensus-scored sentences

        Raises:
            AnalysisError: If all providers fail

        Example:
            result = analysis_service.analyze_consensus(article_text, providers=['gemini', 'mistral'], url=url)
            for sentence_data in result.sentences:
                print(f"{sentence_data['text']}: consensus={sentence_data['consensus_level']}")
        """
        if providers is None:
            from config import settings
            providers = settings.consensus_providers

        start_time = time.time()

        self.log_info(
            "Starting consensus analysis",
            providers=providers,
            provider_count=len(providers),
            text_length=len(article_text)
        )

        self.increment_counter("analysis_requests", tags={
            "mode": "consensus",
            "provider_count": str(len(providers))
        })

        # Check cache if enabled
        if use_cache and url and self._cache_service and self._cache_service.is_enabled():
            cached_result = self._cache_service.get_analysis_result(url, providers)
            if cached_result:
                self.log_info("Cache hit for consensus analysis", providers=providers, url=url[:50])

                return ConsensusResult(
                    sentences=cached_result.get('sentences', []),
                    total_providers=cached_result.get('total_providers', len(providers)),
                    successful_providers=cached_result.get('successful_providers', []),
                    failed_providers=cached_result.get('failed_providers', []),
                    total_duration_ms=cached_result.get('total_duration_ms')
                )

        try:
            with metrics.timer("analysis_duration", tags={"mode": "consensus"}):
                analyzer = self._get_consensus_analyzer(providers)
                consensus_data = analyzer.analyze_article(article_text)

            duration_ms = int((time.time() - start_time) * 1000)

            result = ConsensusResult(
                sentences=consensus_data.get('sentences', []),
                total_providers=consensus_data.get('total_providers', len(providers)),
                successful_providers=consensus_data.get('successful_providers', []),
                failed_providers=consensus_data.get('failed_providers', []),
                total_duration_ms=duration_ms
            )

            token_usage = {}
            if result.successful_providers:
                token_usage = self._record_consensus_token_usage(
                    result.successful_providers,
                    article_text,
                    result.sentences
                )

            self.log_info(
                "Consensus analysis completed",
                sentence_count=len(result.sentences),
                successful_providers=result.successful_providers,
                failed_providers=result.failed_providers,
                duration_ms=duration_ms,
                **token_usage
            )

            # Track success metrics
            self.increment_counter("analysis_success", tags={"mode": "consensus"})
            self.track_metric("sentence_count", len(result.sentences), tags={"mode": "consensus"})
            self.track_metric("provider_success_rate", len(result.successful_providers) / result.total_providers, tags={"mode": "consensus"})

            # Track per-provider success/failure
            for provider in result.successful_providers:
                self.increment_counter("provider_results", tags={"provider": provider, "status": "success"})

            for provider in result.failed_providers:
                self.increment_counter("provider_results", tags={"provider": provider, "status": "failure"})

            # Store in cache if enabled and successful
            if use_cache and url and self._cache_service and self._cache_service.is_enabled() and result.successful_providers:
                cache_data = {
                    'sentences': result.sentences,
                    'total_providers': result.total_providers,
                    'successful_providers': result.successful_providers,
                    'failed_providers': result.failed_providers,
                    'total_duration_ms': duration_ms
                }
                self._cache_service.set_analysis_result(url, providers, cache_data)

            # If all providers failed, raise error
            if not result.successful_providers:
                raise AnalysisError(
                    "All LLM providers failed during consensus analysis",
                    details={
                        'providers': providers,
                        'failed_providers': result.failed_providers
                    }
                )

            return result

        except AnalysisError:
            raise

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)

            self.log_error(
                "Consensus analysis failed",
                exc=e,
                providers=providers,
                duration_ms=duration_ms
            )

            self.increment_counter("analysis_failures", tags={
                "mode": "consensus",
                "error_type": type(e).__name__
            })

            raise AnalysisError(
                "Consensus analysis failed",
                details={'providers': providers, 'error': str(e)}
            ) from e

    def get_available_providers(self) -> List[str]:
        """
        Get list of available LLM providers.

        Returns:
            List of provider names
        """
        return ['gemini', 'openai', 'claude', 'mistral', 'llama']
