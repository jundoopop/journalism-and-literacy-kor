"""
Flask API Server for Chrome Extension
Receives article URLs → Crawls content → Analyzes with Gemini → Returns highlight sentences
"""

import os
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
from gemini_handler import GeminiAnalyzer, GeminiAPIError
from crawler_unified import parse_article, fetch
from consensus_analyzer import ConsensusAnalyzer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Flask app initialization
app = Flask(__name__)
CORS(app)  # Enable CORS for Chrome extension access

# Global analyzer instance
analyzer = None


def initialize_analyzer():
    """
    Initialize Gemini analyzer with error handling

    Returns:
        bool: True if initialization successful, False otherwise
    """
    global analyzer
    try:
        analyzer = GeminiAnalyzer()
        logger.info("✓ Gemini API initialized successfully")
        return True
    except ValueError as e:
        logger.error(f"✗ Gemini API initialization failed: {e}")
        analyzer = None
        return False


# Initialize on startup
initialize_analyzer()


@app.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint

    Returns:
        JSON response with server and Gemini API status
    """
    return jsonify({
        "status": "ok",
        "gemini_ready": analyzer is not None
    })


@app.route('/test', methods=['GET'])
def test():
    """
    Test endpoint to verify server is running

    Returns:
        JSON response with status message
    """
    return jsonify({
        "message": "Flask server is running!",
        "gemini_ready": analyzer is not None
    })


def validate_request_data(data):
    """
    Validate request data for /analyze endpoint

    Args:
        data: Request JSON data

    Returns:
        tuple: (is_valid, error_message, url)
    """
    if not data:
        return False, "No JSON data provided", None

    url = data.get('url')
    if not url:
        return False, "URL field is required", None

    if not isinstance(url, str) or not url.strip():
        return False, "URL must be a non-empty string", None

    return True, None, url


def crawl_article(url):
    """
    Crawl article from given URL

    Args:
        url: Article URL

    Returns:
        tuple: (success, error_message, article_data)
    """
    try:
        logger.info(f"[1/3] Crawling article from: {url}")
        html = fetch(url)
        article = parse_article(url, html)

        if 'error' in article:
            error_msg = f"Crawling failed: {article['error']}"
            logger.error(error_msg)
            return False, error_msg, None

        headline = article.get('headline', '')
        body_text = article.get('body_text', '')

        if not body_text:
            error_msg = "Failed to extract article body text"
            logger.error(error_msg)
            return False, error_msg, None

        logger.info(f"✓ Crawling complete: {headline[:50]}...")
        return True, None, {'headline': headline, 'body_text': body_text}

    except Exception as e:
        error_msg = f"Crawling error: {str(e)}"
        logger.error(error_msg)
        return False, error_msg, None


def analyze_with_gemini(body_text):
    """
    Analyze article body with Gemini API

    Args:
        body_text: Article body text

    Returns:
        tuple: (success, error_message, sentences_list)
    """
    try:
        logger.info("[2/3] Analyzing with Gemini API...")
        sentences = analyzer.get_highlight_sentences(body_text)
        logger.info(f"✓ Analysis complete: {len(sentences)} sentences extracted")
        return True, None, sentences

    except GeminiAPIError as e:
        error_msg = f"Gemini API error: {str(e)}"
        logger.error(error_msg)
        return False, error_msg, []

    except Exception as e:
        error_msg = f"Unexpected analysis error: {str(e)}"
        logger.error(error_msg)
        return False, error_msg, []


@app.route('/analyze', methods=['POST'])
def analyze_article_endpoint():
    """
    Analyze article endpoint
    Receives URL → Crawls article → Analyzes with Gemini → Returns sentences

    Request Body:
        {
            "url": "https://www.chosun.com/..."
        }

    Response (Success):
        {
            "success": true,
            "url": "...",
            "headline": "...",
            "sentences": ["Sentence 1", "Sentence 2", ...],
            "count": 5
        }

    Response (Error):
        {
            "success": false,
            "error": "Error message"
        }
    """
    # Check if Gemini API is ready
    if not analyzer:
        logger.error("Gemini API not initialized")
        return jsonify({
            "success": False,
            "error": "Gemini API not initialized. Please set GEMINI_API_KEY environment variable."
        }), 500

    # Validate request data
    data = request.get_json()
    is_valid, error_msg, url = validate_request_data(data)

    if not is_valid:
        logger.warning(f"Invalid request: {error_msg}")
        return jsonify({
            "success": False,
            "error": error_msg
        }), 400

    logger.info(f"\n[Request] URL: {url}")

    # Step 1: Crawl article
    success, error_msg, article_data = crawl_article(url)
    if not success:
        return jsonify({
            "success": False,
            "error": error_msg
        }), 400

    # Step 2: Analyze with Gemini
    success, error_msg, sentences = analyze_with_gemini(article_data['body_text'])
    if not success:
        return jsonify({
            "success": False,
            "error": error_msg
        }), 500

    # Step 3: Return response
    logger.info("[3/3] Sending response")
    response = {
        "success": True,
        "url": url,
        "headline": article_data['headline'],
        "sentences": sentences,
        "count": len(sentences)
    }

    return jsonify(response)


@app.route('/analyze_consensus', methods=['POST'])
def analyze_consensus_endpoint():
    """
    Analyze article with multiple LLM providers (consensus mode)

    Request Body:
        {
            "url": "https://www.chosun.com/...",
            "providers": ["gemini", "openai"]  # optional, defaults to ['gemini', 'openai']
        }

    Response (Success):
        {
            "success": true,
            "url": "...",
            "headline": "...",
            "total_providers": 2,
            "successful_providers": ["gemini", "openai"],
            "sentences": [
                {
                    "text": "sentence text",
                    "consensus_score": 2,
                    "consensus_level": "high",
                    "selected_by": ["gemini", "openai"],
                    "reasons": {
                        "gemini": "reason...",
                        "openai": "reason..."
                    }
                }
            ],
            "count": 5
        }

    Response (Error):
        {
            "success": false,
            "error": "Error message"
        }
    """
    # Validate request data
    data = request.get_json()
    is_valid, error_msg, url = validate_request_data(data)

    if not is_valid:
        logger.warning(f"Invalid request: {error_msg}")
        return jsonify({
            "success": False,
            "error": error_msg
        }), 400

    providers = data.get('providers', ['gemini', 'openai'])

    logger.info(f"\n[Consensus Request] URL: {url}, Providers: {providers}")

    # Step 1: Crawl article
    success, error_msg, article_data = crawl_article(url)
    if not success:
        return jsonify({
            "success": False,
            "error": error_msg
        }), 400

    # Step 2: Analyze with consensus analyzer
    try:
        logger.info(f"[2/3] Analyzing with {len(providers)} providers...")
        consensus_analyzer = ConsensusAnalyzer(providers=providers)
        result = consensus_analyzer.analyze_article(article_data['body_text'])

        if not result['success']:
            return jsonify(result), 500

        logger.info(f"✓ Consensus analysis complete: {result['count']} sentences")

        # Step 3: Return response
        logger.info("[3/3] Sending response")
        result['url'] = url
        result['headline'] = article_data['headline']

        return jsonify(result)

    except Exception as e:
        error_msg = f"Consensus analysis error: {str(e)}"
        logger.error(error_msg)
        return jsonify({
            "success": False,
            "error": error_msg
        }), 500


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({
        "success": False,
        "error": "Endpoint not found"
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {error}")
    return jsonify({
        "success": False,
        "error": "Internal server error"
    }), 500


def print_startup_banner():
    """Print server startup information"""
    gemini_status = '설정됨 ✓' if os.getenv('GEMINI_API_KEY') else '미설정 ✗'
    analyzer_status = '정상 ✓' if analyzer else '실패 ✗'

    banner = f"""
{'='*50}
Chrome Extension API Server
{'='*50}
✓ Server: http://localhost:5000
✓ Health check: http://localhost:5000/health
✓ Test: http://localhost:5000/test
✓ Analyze: POST http://localhost:5000/analyze

Environment:
  GEMINI_API_KEY: {gemini_status}
  Analyzer Status: {analyzer_status}
{'='*50}
"""
    print(banner)


if __name__ == '__main__':
    print_startup_banner()

    # Run Flask server
    port = int(os.getenv('FLASK_PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'

    app.run(host='0.0.0.0', port=port, debug=debug)
