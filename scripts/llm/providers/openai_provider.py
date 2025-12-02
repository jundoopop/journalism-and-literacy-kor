"""
OpenAI GPT provider implementation

Uses gpt-5-nano model (NEWEST 2025).
Supports JSON mode for structured output.
"""

from openai import OpenAI
from typing import Dict
from ..base import BaseLLMProvider, AnalysisResult, LLMConfig
from ..exceptions import LLMProviderError, ConfigurationError


class OpenAIProvider(BaseLLMProvider):
    """OpenAI GPT API provider"""

    def _validate_config(self) -> None:
        """Validate OpenAI configuration"""
        if not self.config.api_key:
            raise ConfigurationError("OpenAI API key is required")

        try:
            # Initialize OpenAI client
            self.client = OpenAI(
                api_key=self.config.api_key,
                base_url=self.config.base_url  # Allows custom endpoints
            )

            self.logger.info(f"OpenAI initialized with model: {self.config.model_name}")
        except Exception as e:
            self.logger.error(f"OpenAI initialization failed: {e}")
            raise ConfigurationError(f"Failed to initialize OpenAI: {e}")

    def _call_api(self, prompt: str, system_prompt: str) -> str:
        """
        Call OpenAI API

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
            self.logger.debug("Sending request to OpenAI API...")
            response = self.client.chat.completions.create(
                model=self.config.model_name,
                messages=messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                response_format={"type": "json_object"}  # Enforce JSON output
            )

            return response.choices[0].message.content

        except Exception as e:
            self.logger.error(f"OpenAI API call failed: {e}")
            raise LLMProviderError(f"OpenAI API error: {e}")

    def analyze_article(self, article_text: str, system_prompt: str) -> AnalysisResult:
        """
        Analyze article with OpenAI GPT

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
                provider="openai",
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
                provider="openai",
                model=self.config.model_name,
                raw_response=raw_response
            )

        except Exception as e:
            self.logger.error(f"OpenAI analysis failed: {e}")
            raise LLMProviderError(f"OpenAI analysis error: {e}")
