"""
Anthropic Claude provider implementation

Uses claude-4.5-haiku model (NEWEST 2025).
Fastest Claude model with excellent coding capability.
"""

from anthropic import Anthropic
from typing import Dict
from ..base import BaseLLMProvider, AnalysisResult, LLMConfig
from ..exceptions import LLMProviderError, ConfigurationError


class ClaudeProvider(BaseLLMProvider):
    """Anthropic Claude API provider"""

    def _validate_config(self) -> None:
        """Validate Claude configuration"""
        if not self.config.api_key:
            raise ConfigurationError("Claude API key is required")

        try:
            # Initialize Anthropic client
            self.client = Anthropic(api_key=self.config.api_key)

            self.logger.info(f"Claude initialized with model: {self.config.model_name}")
        except Exception as e:
            self.logger.error(f"Claude initialization failed: {e}")
            raise ConfigurationError(f"Failed to initialize Claude: {e}")

    def _call_api(self, prompt: str, system_prompt: str) -> str:
        """
        Call Claude API

        Args:
            prompt: User prompt (article text)
            system_prompt: System instructions

        Returns:
            Raw response text

        Raises:
            LLMProviderError: If API call fails
        """
        try:
            self.logger.debug("Sending request to Claude API...")
            message = self.client.messages.create(
                model=self.config.model_name,
                max_tokens=self.config.max_tokens or 4096,
                temperature=self.config.temperature,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            return message.content[0].text

        except Exception as e:
            self.logger.error(f"Claude API call failed: {e}")
            raise LLMProviderError(f"Claude API error: {e}")

    def analyze_article(self, article_text: str, system_prompt: str) -> AnalysisResult:
        """
        Analyze article with Claude

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
                provider="claude",
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
                provider="claude",
                model=self.config.model_name,
                raw_response=raw_response
            )

        except Exception as e:
            self.logger.error(f"Claude analysis failed: {e}")
            raise LLMProviderError(f"Claude analysis error: {e}")
