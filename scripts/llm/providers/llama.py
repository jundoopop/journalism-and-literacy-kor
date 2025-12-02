"""
Llama provider implementation via Together AI

Uses meta-llama/Llama-3.1-8B-Instruct model (lightweight).
Together AI provides OpenAI-compatible API.
"""

from openai import OpenAI
from typing import Dict
from ..base import BaseLLMProvider, AnalysisResult, LLMConfig
from ..exceptions import LLMProviderError, ConfigurationError


class LlamaProvider(BaseLLMProvider):
    """
    Llama provider via Together AI API

    Uses OpenAI-compatible API interface for ease of integration.
    """

    DEFAULT_BASE_URL = "https://api.together.xyz/v1"

    def _validate_config(self) -> None:
        """Validate Llama configuration"""
        if not self.config.api_key:
            raise ConfigurationError("Llama (Together AI) API key is required")

        # Set default base URL if not provided
        if not self.config.base_url:
            self.config.base_url = self.DEFAULT_BASE_URL

        try:
            # Initialize Together AI client (OpenAI-compatible)
            self.client = OpenAI(
                api_key=self.config.api_key,
                base_url=self.config.base_url
            )

            self.logger.info(f"Llama initialized with model: {self.config.model_name}")
            self.logger.info(f"Using Together AI endpoint: {self.config.base_url}")
        except Exception as e:
            self.logger.error(f"Llama initialization failed: {e}")
            raise ConfigurationError(f"Failed to initialize Llama: {e}")

    def _call_api(self, prompt: str, system_prompt: str) -> str:
        """
        Call Together AI API

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
            self.logger.debug("Sending request to Together AI (Llama)...")
            response = self.client.chat.completions.create(
                model=self.config.model_name,
                messages=messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens or 4096
            )

            return response.choices[0].message.content

        except Exception as e:
            self.logger.error(f"Llama API call failed: {e}")
            raise LLMProviderError(f"Llama API error: {e}")

    def analyze_article(self, article_text: str, system_prompt: str) -> AnalysisResult:
        """
        Analyze article with Llama

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
                provider="llama",
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
                provider="llama",
                model=self.config.model_name,
                raw_response=raw_response
            )

        except Exception as e:
            self.logger.error(f"Llama analysis failed: {e}")
            raise LLMProviderError(f"Llama analysis error: {e}")
