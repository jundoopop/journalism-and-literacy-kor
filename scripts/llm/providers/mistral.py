"""
Mistral AI provider implementation

Uses mistral-small-2506 model (NEWEST 2025, 24B params).
Improved accuracy with 2x fewer infinite generations.
"""

from mistralai import Mistral
from typing import Dict
from ..base import BaseLLMProvider, AnalysisResult, LLMConfig
from ..exceptions import LLMProviderError, ConfigurationError


class MistralProvider(BaseLLMProvider):
    """Mistral AI API provider"""

    def _validate_config(self) -> None:
        """Validate Mistral configuration"""
        if not self.config.api_key:
            raise ConfigurationError("Mistral API key is required")

        try:
            # Initialize Mistral client
            self.client = Mistral(api_key=self.config.api_key)

            self.logger.info(f"Mistral initialized with model: {self.config.model_name}")
        except Exception as e:
            self.logger.error(f"Mistral initialization failed: {e}")
            raise ConfigurationError(f"Failed to initialize Mistral: {e}")

    def _call_api(self, prompt: str, system_prompt: str) -> str:
        """
        Call Mistral API

        Args:
            prompt: User prompt (article text)
            system_prompt: System instructions

        Returns:
            Raw response text

        Raises:
            LLMProviderError: If API call fails
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]

        try:
            self.logger.debug("Sending request to Mistral API...")
            response = self.client.chat.complete(
                model=self.config.model_name,
                messages=messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens
            )

            return response.choices[0].message.content

        except Exception as e:
            self.logger.error(f"Mistral API call failed: {e}")
            raise LLMProviderError(f"Mistral API error: {e}")

    def analyze_article(self, article_text: str, system_prompt: str) -> AnalysisResult:
        """
        Analyze article with Mistral

        Args:
            article_text: Article body text
            system_prompt: System prompt for analysis

        Returns:
            AnalysisResult with extracted sentences

        Raises:
            LLMProviderError: If analysis fails
        """
        if not article_text or not article_text.strip():
            self.logger.warning("Empty article text provided")
            return AnalysisResult(
                sentences={},
                provider="mistral",
                model=self.config.model_name
            )

        try:
            # Call API
            raw_response = self._call_api(article_text, system_prompt)

            # Parse JSON response
            sentences = self._parse_json_response(raw_response)

            self.logger.info(f"Successfully extracted {len(sentences)} sentences")

            return AnalysisResult(
                sentences=sentences,
                provider="mistral",
                model=self.config.model_name,
                raw_response=raw_response
            )

        except Exception as e:
            self.logger.error(f"Mistral analysis failed: {e}")
            raise LLMProviderError(f"Mistral analysis error: {e}")
