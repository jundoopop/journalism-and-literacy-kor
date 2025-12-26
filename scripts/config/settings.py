"""
Centralized configuration using Pydantic settings.

All configuration is loaded from environment variables or .env file
with type validation and sensible defaults.
"""

import os
from typing import Optional, List, Dict
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMSettings(BaseSettings):
    """LLM provider configuration."""

    # API Keys
    gemini_api_key: Optional[str] = Field(None, validation_alias='GEMINI_API_KEY')
    openai_api_key: Optional[str] = Field(None, validation_alias='OPENAI_API_KEY')
    claude_api_key: Optional[str] = Field(None, validation_alias='CLAUDE_API_KEY')
    mistral_api_key: Optional[str] = Field(None, validation_alias='MISTRAL_API_KEY')
    llama_api_key: Optional[str] = Field(None, validation_alias='LLAMA_API_KEY')

    # Performance settings
    timeout: int = Field(40, validation_alias='LLM_TIMEOUT', description='LLM API timeout in seconds')
    max_retries: int = Field(3, validation_alias='LLM_MAX_RETRIES', description='Maximum retry attempts')
    temperature: float = Field(0.2, validation_alias='LLM_TEMPERATURE', description='LLM temperature parameter')
    max_tokens: Optional[int] = Field(None, validation_alias='LLM_MAX_TOKENS', description='Maximum output tokens')
    max_tokens_per_provider: Dict[str, int] = Field(
        default_factory=dict,
        validation_alias='LLM_MAX_TOKENS_PER_PROVIDER',
        description='Per-provider max output tokens'
    )
    token_pricing_per_1k: Dict[str, float] = Field(
        default_factory=dict,
        validation_alias='LLM_TOKEN_PRICING_PER_1K',
        description='Per-provider USD cost per 1k tokens'
    )
    estimated_chars_per_token: int = Field(
        4,
        validation_alias='LLM_EST_CHARS_PER_TOKEN',
        description='Heuristic chars per token for estimation'
    )

    model_config = SettingsConfigDict(env_prefix='llm_', case_sensitive=False)

    @field_validator('timeout')
    @classmethod
    def validate_timeout(cls, v):
        if v <= 0 or v > 300:
            raise ValueError('Timeout must be between 1 and 300 seconds')
        return v

    @field_validator('temperature')
    @classmethod
    def validate_temperature(cls, v):
        if v < 0 or v > 2:
            raise ValueError('Temperature must be between 0 and 2')
        return v

    @field_validator('estimated_chars_per_token')
    @classmethod
    def validate_estimated_chars_per_token(cls, v):
        if v <= 0:
            raise ValueError('Estimated chars per token must be greater than 0')
        return v


class CacheSettings(BaseSettings):
    """Redis cache configuration."""

    enabled: bool = Field(True, validation_alias='CACHE_ENABLED', description='Enable/disable caching')
    redis_host: str = Field('localhost', validation_alias='REDIS_HOST')
    redis_port: int = Field(6379, validation_alias='REDIS_PORT')
    redis_db: int = Field(0, validation_alias='REDIS_DB')
    redis_password: Optional[str] = Field(None, validation_alias='REDIS_PASSWORD')
    ttl: int = Field(3600, validation_alias='CACHE_TTL', description='Default TTL in seconds')

    model_config = SettingsConfigDict(env_prefix='cache_', case_sensitive=False)

    @field_validator('redis_port')
    @classmethod
    def validate_port(cls, v):
        if v <= 0 or v > 65535:
            raise ValueError('Redis port must be between 1 and 65535')
        return v


class DatabaseSettings(BaseSettings):
    """Database configuration."""

    path: str = Field('data/analytics.db', validation_alias='DATABASE_PATH', description='SQLite database path')
    echo: bool = Field(False, validation_alias='DATABASE_ECHO', description='Echo SQL queries')
    pool_size: int = Field(5, validation_alias='DATABASE_POOL_SIZE')

    model_config = SettingsConfigDict(env_prefix='database_', case_sensitive=False)


class ObservabilitySettings(BaseSettings):
    """Observability configuration."""

    log_level: str = Field('INFO', validation_alias='LOG_LEVEL')
    log_format: str = Field('json', validation_alias='LOG_FORMAT', description='Log format: json or text')
    log_dir: str = Field('data/logs', validation_alias='LOG_DIR')
    metrics_enabled: bool = Field(True, validation_alias='METRICS_ENABLED')

    model_config = SettingsConfigDict(env_prefix='observability_', case_sensitive=False)

    @field_validator('log_level')
    @classmethod
    def validate_log_level(cls, v):
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        v = v.upper()
        if v not in valid_levels:
            raise ValueError(f'Log level must be one of {valid_levels}')
        return v

    @field_validator('log_format')
    @classmethod
    def validate_log_format(cls, v):
        v = v.lower()
        if v not in ['json', 'text']:
            raise ValueError('Log format must be "json" or "text"')
        return v


class Settings(BaseSettings):
    """Main application settings."""

    # Flask server settings
    flask_host: str = Field('0.0.0.0', validation_alias='FLASK_HOST')
    flask_port: int = Field(5001, validation_alias='FLASK_PORT')
    flask_debug: bool = Field(True, validation_alias='FLASK_DEBUG')

    # Admin authentication
    admin_token: Optional[str] = Field(None, validation_alias='ADMIN_TOKEN', description='Token for admin endpoints')

    # Consensus settings
    consensus_enabled: bool = Field(True, validation_alias='CONSENSUS_ENABLED')
    consensus_providers: List[str] = Field(
        default=['gemini', 'mistral'],
        validation_alias='CONSENSUS_PROVIDERS',
        description='Default providers for consensus analysis'
    )

    # Feature flags
    enable_cache: bool = Field(True, validation_alias='ENABLE_CACHE')
    enable_metrics: bool = Field(True, validation_alias='ENABLE_METRICS')
    enable_admin_api: bool = Field(True, validation_alias='ENABLE_ADMIN_API')

    # Sub-settings
    llm: LLMSettings = Field(default_factory=LLMSettings)
    cache: CacheSettings = Field(default_factory=CacheSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    observability: ObservabilitySettings = Field(default_factory=ObservabilitySettings)

    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=False,
        extra='ignore'
    )

    @field_validator('flask_port')
    @classmethod
    def validate_flask_port(cls, v):
        if v <= 0 or v > 65535:
            raise ValueError('Flask port must be between 1 and 65535')
        return v

    @field_validator('consensus_providers')
    @classmethod
    def validate_consensus_providers(cls, v):
        if isinstance(v, str):
            # Handle comma-separated string from env var
            v = [p.strip() for p in v.split(',')]

        valid_providers = {'gemini', 'openai', 'claude', 'mistral', 'llama'}
        for provider in v:
            if provider not in valid_providers:
                raise ValueError(f'Invalid provider: {provider}. Must be one of {valid_providers}')

        if len(v) < 1:
            raise ValueError('At least one provider must be specified')

        return v


# Global settings instance
# This can be imported throughout the application
settings = Settings()
