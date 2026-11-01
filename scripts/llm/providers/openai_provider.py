"""
OpenAI GPT provider implementation

Uses the configured lightweight model.
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
                timeout=self.config.timeout,
                max_retries=0,
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
            options = {"model": self.config.model_name, "messages": messages,
                       "response_format": {"type": "json_object"}}
            if self.config.model_name.startswith(("gpt-5", "gpt-6", "o1", "o3", "o4")):
                options["max_completion_tokens"] = self.config.max_tokens or 2048
                # The pinned SDK forwards new API fields through extra_body.
                # Older reasoning models do not support temperature or effort=none.
                if self.config.model_name.startswith("gpt-6-luna"):
                    options["extra_body"] = {"reasoning_effort": "none"}
            else:
                options.update(temperature=self.config.temperature,
                               max_tokens=self.config.max_tokens or 2048)
            response = self.client.chat.completions.create(**options)
            choice = response.choices[0]
            if choice.finish_reason != "stop" or not choice.message.content:
                raise LLMProviderError("OpenAI returned incomplete or refused output")
            return choice.message.content

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
            sentences = self._validate_sentences(
                self._parse_json_response(raw_response), article_text)

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
