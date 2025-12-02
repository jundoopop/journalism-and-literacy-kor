"""
Native Messaging Host for Chrome Extension
Communicates via stdin/stdout using Chrome's native messaging protocol
"""

import sys
import json
import struct
import logging
import os
from typing import Dict, Any, Optional
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from gemini_handler import GeminiAnalyzer, GeminiAPIError
from crawler_unified import parse_article, fetch
from consensus_analyzer import ConsensusAnalyzer

# Configure logging to file (can't use stdout - reserved for native messaging)
LOG_DIR = Path.home() / '.highright'
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / 'native_host.log'

logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================
# API Key Management
# ============================================

def get_api_key() -> Optional[str]:
    """
    Get Gemini API key from secure storage or environment

    Returns:
        API key string or None if not found
    """
    # Try environment variable first
    api_key = os.getenv('GEMINI_API_KEY')
    if api_key:
        return api_key

    # Try keyring (installed by installer)
    try:
        import keyring
        api_key = keyring.get_password('highright', 'gemini_api_key')
        if api_key:
            return api_key
    except ImportError:
        logger.warning("keyring module not available, using environment only")
    except Exception as e:
        logger.error(f"Error accessing keyring: {e}")

    # Try legacy .env file
    try:
        from dotenv import load_dotenv
        env_path = Path(__file__).parent.parent / '.env'
        if env_path.exists():
            load_dotenv(env_path)
            api_key = os.getenv('GEMINI_API_KEY')
            if api_key:
                return api_key
    except ImportError:
        pass
    except Exception as e:
        logger.error(f"Error loading .env: {e}")

    return None


# ============================================
# Native Messaging Protocol
# ============================================

def send_message(message: Dict[str, Any]) -> None:
    """
    Send message to Chrome extension via stdout

    Args:
        message: Dictionary to send (will be JSON encoded)
    """
    try:
        encoded_message = json.dumps(message).encode('utf-8')
        message_length = struct.pack('I', len(encoded_message))

        # Write to stdout in binary mode
        sys.stdout.buffer.write(message_length)
        sys.stdout.buffer.write(encoded_message)
        sys.stdout.buffer.flush()

        logger.debug(f"Sent message: {message}")
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        sys.exit(1)


def read_message() -> Optional[Dict[str, Any]]:
    """
    Read message from Chrome extension via stdin

    Returns:
        Decoded message dictionary or None on error
    """
    try:
        # Read message length (4 bytes)
        text_length_bytes = sys.stdin.buffer.read(4)

        if len(text_length_bytes) == 0:
            # EOF reached, extension closed
            logger.info("EOF reached, exiting")
            return None

        # Unpack message length
        text_length = struct.unpack('I', text_length_bytes)[0]

        # Read message content
        text = sys.stdin.buffer.read(text_length).decode('utf-8')

        # Parse JSON
        message = json.loads(text)
        logger.debug(f"Received message: {message}")

        return message
    except Exception as e:
        logger.error(f"Error reading message: {e}")
        return None


# ============================================
# Message Handlers
# ============================================

class NativeHost:
    """Native messaging host handler"""

    def __init__(self):
        """Initialize native host with Gemini analyzer"""
        self.analyzer = None
        self.initialize_analyzer()

    def initialize_analyzer(self) -> bool:
        """
        Initialize Gemini analyzer

        Returns:
            True if successful, False otherwise
        """
        try:
            api_key = get_api_key()
            if not api_key:
                logger.error("GEMINI_API_KEY not found")
                return False

            self.analyzer = GeminiAnalyzer(api_key=api_key)
            logger.info("✓ Gemini API initialized successfully")
            return True
        except Exception as e:
            logger.error(f"✗ Gemini API initialization failed: {e}")
            self.analyzer = None
            return False

    def handle_get_highlight_sentences(self, url: str) -> Dict[str, Any]:
        """
        Handle getHighlightSentences request

        Args:
            url: Article URL to analyze

        Returns:
            Response dictionary
        """
        logger.info(f"Analyzing: {url}")

        if not self.analyzer:
            return {
                'success': False,
                'error': 'Gemini API not initialized. Please check API key.'
            }

        try:
            # Step 1: Crawl article
            logger.info("[1/3] Crawling article...")
            html = fetch(url)
            article = parse_article(url, html)

            if 'error' in article:
                error_msg = f"Crawling failed: {article['error']}"
                logger.error(error_msg)
                return {'success': False, 'error': error_msg}

            headline = article.get('headline', '')
            body_text = article.get('body_text', '')

            if not body_text:
                error_msg = "Failed to extract article body text"
                logger.error(error_msg)
                return {'success': False, 'error': error_msg}

            logger.info(f"✓ Crawling complete: {headline[:50]}...")

            # Step 2: Analyze with Gemini
            logger.info("[2/3] Analyzing with Gemini API...")
            sentences = self.analyzer.get_highlight_sentences(body_text)
            logger.info(f"✓ Analysis complete: {len(sentences)} sentences")

            # Step 3: Return response
            logger.info("[3/3] Returning response")
            return {
                'success': True,
                'url': url,
                'headline': headline,
                'sentences': sentences,
                'count': len(sentences)
            }

        except GeminiAPIError as e:
            error_msg = f"Gemini API error: {str(e)}"
            logger.error(error_msg)
            return {'success': False, 'error': error_msg}

        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(error_msg)
            return {'success': False, 'error': error_msg}

    def handle_get_consensus_highlights(self, url: str, providers: list) -> Dict[str, Any]:
        """
        Handle getConsensusHighlights request (multi-LLM analysis)

        Args:
            url: Article URL to analyze
            providers: List of provider names to use (e.g., ['gemini', 'openai'])

        Returns:
            Response dictionary with consensus data
        """
        logger.info(f"Consensus analysis: {url} with providers: {providers}")

        try:
            # Step 1: Crawl article
            logger.info("[1/3] Crawling article...")
            html = fetch(url)
            article = parse_article(url, html)

            if 'error' in article:
                error_msg = f"Crawling failed: {article['error']}"
                logger.error(error_msg)
                return {'success': False, 'error': error_msg}

            headline = article.get('headline', '')
            body_text = article.get('body_text', '')

            if not body_text:
                error_msg = "Failed to extract article body text"
                logger.error(error_msg)
                return {'success': False, 'error': error_msg}

            logger.info(f"✓ Crawling complete: {headline[:50]}...")

            # Step 2: Analyze with consensus analyzer
            logger.info("[2/3] Analyzing with consensus analyzer...")
            consensus_analyzer = ConsensusAnalyzer(providers=providers)
            result = consensus_analyzer.analyze_article(body_text)

            if not result['success']:
                return result

            logger.info(f"✓ Consensus analysis complete: {result['count']} sentences")

            # Step 3: Return response
            logger.info("[3/3] Returning consensus response")
            result['url'] = url
            result['headline'] = headline

            return result

        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(error_msg)
            return {'success': False, 'error': error_msg}

    def handle_check_health(self) -> Dict[str, Any]:
        """
        Handle health check request

        Returns:
            Health status dictionary
        """
        return {
            'status': 'ok',
            'gemini_ready': self.analyzer is not None
        }

    def handle_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Route incoming message to appropriate handler

        Args:
            message: Incoming message dictionary

        Returns:
            Response dictionary
        """
        action = message.get('action')

        if action == 'getHighlightSentences':
            url = message.get('url')
            if not url:
                return {'success': False, 'error': 'URL is required'}
            return self.handle_get_highlight_sentences(url)

        elif action == 'getConsensusHighlights':
            url = message.get('url')
            providers = message.get('providers', ['gemini', 'openai'])
            if not url:
                return {'success': False, 'error': 'URL is required'}
            return self.handle_get_consensus_highlights(url, providers)

        elif action == 'checkHealth':
            return self.handle_check_health()

        else:
            logger.warning(f"Unknown action: {action}")
            return {
                'success': False,
                'error': f'Unknown action: {action}'
            }


# ============================================
# Main Loop
# ============================================

def main():
    """Main message loop"""
    logger.info("=" * 50)
    logger.info("Native Messaging Host Started")
    logger.info("=" * 50)
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Working directory: {os.getcwd()}")
    logger.info(f"Script path: {__file__}")
    logger.info(f"Log file: {LOG_FILE}")
    logger.info("=" * 50)

    # Initialize host
    host = NativeHost()

    if not host.analyzer:
        logger.warning("Starting without Gemini API (check API key)")

    # Main message loop
    while True:
        try:
            # Read message from extension
            message = read_message()

            if message is None:
                # EOF or error - exit gracefully
                break

            # Handle message
            response = host.handle_message(message)

            # Send response back to extension
            send_message(response)

        except KeyboardInterrupt:
            logger.info("Interrupted by user")
            break
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            send_message({
                'success': False,
                'error': f'Internal error: {str(e)}'
            })

    logger.info("Native Messaging Host Stopped")


if __name__ == '__main__':
    main()
