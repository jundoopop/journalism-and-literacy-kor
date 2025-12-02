"""
Secure API key management

Supports multiple layers of key storage with fallback:
1. Environment variables (highest priority)
2. System keyring (macOS Keychain, Windows Credential Manager)
3. .env file (fallback for development)
"""

import os
from typing import Optional
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def get_api_key(provider_name: str) -> Optional[str]:
    """
    Get API key for provider from secure sources

    Priority order:
    1. Environment variable (highest priority)
    2. System keyring (secure OS-level storage)
    3. .env file (fallback for development)

    Args:
        provider_name: Provider name (e.g., "gemini", "openai", "claude")

    Returns:
        API key string or None if not found
    """
    # Normalize provider name for key lookup
    if hasattr(provider_name, 'value'):  # If it's an enum
        provider_name = provider_name.value

    key_name = f"{provider_name.upper()}_API_KEY"

    # 1. Try environment variable first (highest priority)
    api_key = os.getenv(key_name)
    if api_key:
        logger.debug(f"Found {key_name} in environment variables")
        return api_key

    # 2. Try system keyring (secure storage)
    try:
        import keyring
        service_name = "highright"
        username = f"{provider_name}_api_key"
        api_key = keyring.get_password(service_name, username)
        if api_key:
            logger.debug(f"Found {key_name} in system keyring")
            return api_key
    except ImportError:
        logger.debug("keyring module not available")
    except Exception as e:
        logger.warning(f"Error accessing keyring: {e}")

    # 3. Try .env file (fallback for development)
    try:
        from dotenv import load_dotenv

        # Look for .env in project root (4 levels up from this file)
        current_file = Path(__file__)
        project_root = current_file.parent.parent.parent.parent
        env_path = project_root / '.env'

        if env_path.exists():
            load_dotenv(env_path)
            api_key = os.getenv(key_name)
            if api_key:
                logger.debug(f"Found {key_name} in .env file")
                return api_key
    except ImportError:
        logger.debug("python-dotenv not available")
    except Exception as e:
        logger.warning(f"Error loading .env file: {e}")

    logger.warning(f"{key_name} not found in any source")
    return None


def set_api_key_in_keyring(provider_name: str, api_key: str) -> bool:
    """
    Store API key securely in system keyring

    Args:
        provider_name: Provider name (e.g., "gemini", "openai")
        api_key: API key to store

    Returns:
        True if successful, False otherwise
    """
    if hasattr(provider_name, 'value'):  # If it's an enum
        provider_name = provider_name.value

    try:
        import keyring
        service_name = "highright"
        username = f"{provider_name}_api_key"
        keyring.set_password(service_name, username, api_key)
        logger.info(f"Stored {provider_name} API key in system keyring")
        return True
    except ImportError:
        logger.error("keyring module not installed")
        return False
    except Exception as e:
        logger.error(f"Failed to store API key in keyring: {e}")
        return False


def delete_api_key_from_keyring(provider_name: str) -> bool:
    """
    Delete API key from system keyring

    Args:
        provider_name: Provider name (e.g., "gemini", "openai")

    Returns:
        True if successful, False otherwise
    """
    if hasattr(provider_name, 'value'):  # If it's an enum
        provider_name = provider_name.value

    try:
        import keyring
        service_name = "highright"
        username = f"{provider_name}_api_key"
        keyring.delete_password(service_name, username)
        logger.info(f"Deleted {provider_name} API key from system keyring")
        return True
    except ImportError:
        logger.error("keyring module not installed")
        return False
    except Exception as e:
        logger.error(f"Failed to delete API key from keyring: {e}")
        return False
