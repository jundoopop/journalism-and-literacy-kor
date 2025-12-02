"""
Google Gemini provider implementation

Ported from scripts/gemini_handler.py with unified interface.
Uses gemini-2.5-flash-lite model (NEWEST 2025).
"""

import google.generativeai as genai
from typing import Dict
from ..base import BaseLLMProvider, AnalysisResult, LLMConfig
from ..exceptions import LLMProviderError, ConfigurationError


class GeminiProvider(BaseLLMProvider):
    """Google Gemini API provider"""

    def _validate_config(self) -> None:
        """Validate Gemini configuration"""
        if not self.config.api_key:
            raise ConfigurationError("Gemini API key is required")

        try:
            # Initialize Gemini
            genai.configure(api_key=self.config.api_key)
            self.model = genai.GenerativeModel(self.config.model_name)

            self.logger.info(f"Gemini initialized with model: {self.config.model_name}")
        except Exception as e:
            self.logger.error(f"Gemini initialization failed: {e}")
            raise ConfigurationError(f"Failed to initialize Gemini: {e}")

    def _call_api(self, prompt: str, system_prompt: str) -> str:
        """
        Call Gemini API

        Args:
            prompt: User prompt (article text)
            system_prompt: System instructions

        Returns:
            Raw response text

        Raises:
            LLMProviderError: If API call fails
        """
        # Gemini combines system prompt and user prompt
        full_prompt = f"{system_prompt}\n\n기사 본문:\n{prompt}"

        try:
            self.logger.debug("Sending request to Gemini API...")
            response = self.model.generate_content(full_prompt)
            return response.text
        except Exception as e:
            self.logger.error(f"Gemini API call failed: {e}")
            raise LLMProviderError(f"Gemini API error: {e}")

    def analyze_article(self, article_text: str, system_prompt: str) -> AnalysisResult:
        """
        Analyze article with Gemini

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
                provider="gemini",
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
                provider="gemini",
                model=self.config.model_name,
                raw_response=raw_response
            )

        except Exception as e:
            self.logger.error(f"Gemini analysis failed: {e}")
            raise LLMProviderError(f"Gemini analysis error: {e}")
