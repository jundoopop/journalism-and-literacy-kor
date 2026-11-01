"""
Google Gemini provider implementation

Ported from scripts/gemini_handler.py with unified interface.
Uses the official generateContent REST API and isolated per-request credentials.
"""

import requests
from urllib.parse import quote
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
            if not self.config.model_name:
                raise ConfigurationError("Gemini model name is required")

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
        payload = {
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "maxOutputTokens": self.config.max_tokens or 2048,
            },
        }
        # Keep Gemini 3's provider sampling defaults; tune on real articles.
        if not self.config.model_name.startswith("gemini-3"):
            payload["generationConfig"]["temperature"] = self.config.temperature
        endpoint = ("https://generativelanguage.googleapis.com/v1beta/models/"
                    + quote(self.config.model_name, safe="") + ":generateContent")
        try:
            with requests.post(endpoint, headers={"x-goog-api-key": self.config.api_key},
                               json=payload, timeout=self.config.timeout,
                               allow_redirects=False) as response:
                if response.status_code != 200:
                    raise LLMProviderError(f"Gemini HTTP {response.status_code}")
                data = response.json()
            candidates = data.get("candidates", [])
            if not candidates or candidates[0].get("finishReason") != "STOP":
                raise LLMProviderError("Gemini returned incomplete or blocked output")
            text = "".join(p.get("text", "") for p in candidates[0].get("content", {}).get("parts", [])
                           if not p.get("thought"))
            if not text:
                raise LLMProviderError("Gemini returned no text")
            return text
        except LLMProviderError:
            raise
        except Exception as exc:
            # Do not include upstream response bodies or credentials in logs.
            raise LLMProviderError(f"Gemini request failed ({type(exc).__name__})") from exc

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
            sentences = self._validate_sentences(
                self._parse_json_response(raw_response), article_text)

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
