import os
import sys
import logging
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Add project root to path so we can import scripts
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from scripts.llm.factory import LLMFactory
    from scripts.llm.base import LLMProvider
except ImportError as e:
    logger.error(f"Failed to import LLM modules: {e}")
    sys.exit(1)


def test_provider(provider_name: str):
    logger.info(f"--- Testing {provider_name.upper()} ---")
    try:
        # Create provider
        provider = LLMFactory.create(provider=provider_name)
        logger.info(
            f"Successfully created {provider_name} provider with model: {provider.config.model_name}"
        )

        # Test API call
        # We use a system prompt that asks for JSON to satisfy OpenAI's requirement if it's enforced
        system_prompt = (
            'You are a test assistant. Respond with a valid JSON object containing {"status": "ok", "message": "Hello from '
            + provider_name
            + '"}. Use DOUBLE QUOTES for keys and values. Do not output markdown.'
        )
        article_text = "Test connection"

        logger.info("Sending test request...")
        # We use analyze_article because it handles the JSON parsing which is what we want to verify too
        result = provider.analyze_article(article_text, system_prompt)

        logger.info(f"Success! Response: {result.sentences}")
        return True

    except Exception as e:
        logger.error(f"Failed to test {provider_name}: {e}")
        return False


def main():
    print("=" * 60)
    print("API CONNECTION TEST - ALL PROVIDERS")
    print("=" * 60)
    print()

    # Define providers to test (in order of priority)
    providers_to_test = ["gemini", "openai", "claude", "mistral"]

    results = {}

    for provider in providers_to_test:
        # Check if API key exists in environment
        api_key_var = f"{provider.upper()}_API_KEY"
        api_key = os.getenv(api_key_var)

        if not api_key or api_key.strip() == "":
            logger.warning(f"⚠️  {provider.upper()}: API key not configured (skipping)")
            results[provider] = "SKIP"
            print()
            continue

        success = test_provider(provider)
        results[provider] = "PASS" if success else "FAIL"
        print()

    # Print summary
    print("=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    for provider, status in results.items():
        if status == "PASS":
            print(f"✅ {provider.upper()}: CONNECTED")
        elif status == "FAIL":
            print(f"❌ {provider.upper()}: FAILED (check logs above)")
        else:
            print(f"⚠️  {provider.upper()}: NOT CONFIGURED")

    print()

    # Print recommendations
    passed = [p for p, s in results.items() if s == "PASS"]
    failed = [p for p, s in results.items() if s == "FAIL"]
    skipped = [p for p, s in results.items() if s == "SKIP"]

    if passed:
        print(f"✓ Working providers: {', '.join(passed)}")
    if failed:
        print(f"✗ Failed providers: {', '.join(failed)}")
    if skipped:
        print(f"⚠ Not configured: {', '.join(skipped)}")

    print()
    print("=" * 60)

    # Return exit code
    return 0 if passed and not failed else 1


if __name__ == "__main__":
    main()
