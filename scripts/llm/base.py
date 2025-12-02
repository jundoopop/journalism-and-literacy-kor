"""
Base abstract interface for LLM providers

Defines the contract that all providers must implement for consistency.
All providers inherit from BaseLLMProvider and must implement abstract methods.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import logging
import json


class LLMProvider(Enum):
    """Supported LLM providers"""
    GEMINI = "gemini"
    OPENAI = "openai"
    CLAUDE = "claude"
    LLAMA = "llama"
    MISTRAL = "mistral"


@dataclass
class LLMConfig:
    """Configuration for LLM provider"""
    provider: LLMProvider
    api_key: str
    model_name: str
    temperature: float = 0.2
    max_tokens: Optional[int] = None
    timeout: int = 40
    max_retries: int = 3
    base_url: Optional[str] = None  # For custom endpoints
    additional_params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AnalysisResult:
    """Standardized analysis result across all providers"""
    sentences: Dict[str, str]  # {sentence: reason}
    provider: str
    model: str
    raw_response: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseLLMProvider(ABC):
    """
    Abstract base class for all LLM providers

    All providers must implement analyze_article() and _call_api().
    Common functionality like JSON parsing is provided in this base class.
    """

    def __init__(self, config: LLMConfig):
        """
        Initialize provider with configuration

        Args:
            config: LLMConfig instance with provider settings
        """
        self.config = config
        self.logger = self._setup_logger()
        self._validate_config()

    @abstractmethod
    def _validate_config(self) -> None:
        """
        Validate provider-specific configuration

        Should check API keys, models, and any provider-specific requirements.
        Raise ValueError or ConfigurationError if invalid.
        """
        pass

    @abstractmethod
    def analyze_article(self, article_text: str, system_prompt: str) -> AnalysisResult:
        """
        Analyze article and extract notable sentences

        Args:
            article_text: Full article body text
            system_prompt: System prompt for analysis

        Returns:
            AnalysisResult with extracted sentences and metadata

        Raises:
            LLMProviderError: If analysis fails
        """
        pass

    @abstractmethod
    def _call_api(self, prompt: str, system_prompt: str) -> str:
        """
        Make API call to provider

        Args:
            prompt: User prompt (article text)
            system_prompt: System instructions

        Returns:
            Raw API response text

        Raises:
            LLMProviderError: If API call fails
        """
        pass

    def _clean_json_response(self, text: str) -> str:
        """
        Clean response text to extract pure JSON

        Handles markdown code blocks and other formatting that LLMs may add.

        Args:
            text: Raw response text

        Returns:
            Cleaned JSON string
        """
        text = text.strip()

        # Remove markdown code blocks if present
        if text.startswith("```"):
            parts = text.split("```")
            if len(parts) >= 2:
                text = parts[1]
                # Remove language identifier (e.g., "json")
                if text.startswith("json"):
                    text = text[4:].strip()
                elif text.startswith("JSON"):
                    text = text[4:].strip()

        return text

    def _parse_json_response(self, text: str) -> Dict[str, str]:
        """
        Parse JSON response with error handling

        Args:
            text: JSON text to parse

        Returns:
            Parsed dictionary mapping sentences to reasons

        Raises:
            JSONParseError: If parsing fails
        """
        from .exceptions import JSONParseError

        try:
            cleaned = self._clean_json_response(text)
            parsed = json.loads(cleaned)

            # Validate format: should be {sentence: reason}
            if not isinstance(parsed, dict):
                raise JSONParseError(f"Expected dict, got {type(parsed)}")

            # Ensure all values are strings
            for key, value in parsed.items():
                if not isinstance(key, str) or not isinstance(value, str):
                    raise JSONParseError(f"All keys and values must be strings")

            return parsed

        except json.JSONDecodeError as e:
            self.logger.error(f"JSON parsing failed: {e}")
            self.logger.error(f"Raw text: {text[:500]}...")
            raise JSONParseError(f"Failed to parse JSON: {e}")
        except JSONParseError:
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error during JSON parsing: {e}")
            raise JSONParseError(f"Unexpected parsing error: {e}")

    def get_highlight_sentences(self, article_text: str) -> List[str]:
        """
        Extract only sentence list (without reasons)

        Convenience method for Chrome extension that only needs the list
        of sentences to highlight, not the reasons.

        Args:
            article_text: Article body text

        Returns:
            List of sentences to highlight
        """
        from .prompts.article_analysis import ARTICLE_ANALYSIS_PROMPT

        try:
            result = self.analyze_article(article_text, ARTICLE_ANALYSIS_PROMPT)
            return list(result.sentences.keys())
        except Exception as e:
            self.logger.error(f"Failed to extract sentences: {e}")
            return []

    def _setup_logger(self):
        """Setup provider-specific logger"""
        logger_name = f"llm.{self.config.provider.value}"
        return logging.getLogger(logger_name)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(model={self.config.model_name})"
