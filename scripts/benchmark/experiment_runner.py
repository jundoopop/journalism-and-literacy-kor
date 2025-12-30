"""
Experiment Runner for Benchmark Evaluation

Runs the 2×3 experimental design (6 conditions × 50 articles = 300 API calls)
comparing baseline vs optimized prompts across 3 lightweight models.
"""

import json
import logging
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any
from tqdm import tqdm

from scripts.benchmark.data_loader import BenchmarkDataLoader, BenchmarkArticle
from scripts.benchmark.metrics import calculate_metrics, MatchScores, aggregate_metrics
from scripts.llm.factory import LLMFactory
from scripts.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ExperimentConfig:
    """Configuration for benchmark experiment"""
    models: Dict[str, str] = field(default_factory=lambda: {
        'openai': 'gpt-5-nano',
        'gemini': 'gemini-2.5-flash-lite',
        'mistral': 'ministral-3b-2512'
    })
    prompt_dirs: Dict[str, str] = field(default_factory=lambda: {
        'baseline': 'prompts/baseline/',
        'optimized': 'prompts/'
    })
    use_cache: bool = True
    max_retries: int = 3
    timeout: int = 60
    rate_limit_delay: float = 0.2  # 5 req/sec max


@dataclass
class ArticleResult:
    """Results for a single article evaluation"""
    article_id: str
    predicted_sentences: List[str]
    gold_sentences: List[str]
    exact_metrics: Dict[str, float]  # precision, recall, f1
    semantic_metrics: Dict[str, float]  # precision, recall, f1
    raw_response: Optional[str] = None
    duration_ms: Optional[int] = None
    tokens_used: Optional[int] = None
    json_valid: bool = True
    error: Optional[str] = None


@dataclass
class ConditionResult:
    """Results for one experimental condition (50 articles)"""
    condition_id: str  # A, B, C, D, E, F
    prompt_type: str  # 'baseline' or 'optimized'
    provider: str
    model: str
    articles: List[ArticleResult]
    aggregate_exact: Dict[str, float]
    aggregate_semantic: Dict[str, float]
    json_compliance_rate: float
    avg_duration_ms: float
    total_tokens: int


@dataclass
class ExperimentResults:
    """Complete experiment results"""
    experiment_id: str
    timestamp: str
    config: ExperimentConfig
    conditions: List[ConditionResult]

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'experiment_id': self.experiment_id,
            'timestamp': self.timestamp,
            'config': asdict(self.config),
            'conditions': [asdict(c) for c in self.conditions]
        }


class BenchmarkExperiment:
    """Orchestrates benchmark evaluation experiments"""

    def __init__(self, config: Optional[ExperimentConfig] = None):
        self.config = config or ExperimentConfig()
        self.data_loader = BenchmarkDataLoader()
        self.llm_factory = LLMFactory

    def load_prompt(self, provider: str, prompt_type: str) -> str:
        """
        Load prompt file for given provider and type.

        Args:
            provider: 'openai', 'gemini', or 'mistral'
            prompt_type: 'baseline' or 'optimized'

        Returns:
            Prompt text
        """
        prompt_dir = Path(self.config.prompt_dirs[prompt_type])

        if prompt_type == 'baseline':
            prompt_file = prompt_dir / f"base_prompt_ko_{provider}.txt"
        else:
            # Optimized prompts have different filenames
            if provider == 'openai':
                prompt_file = Path(self.config.prompt_dirs[prompt_type]) / "base_prompt_ko_openai_nano.txt"
            else:
                prompt_file = Path(self.config.prompt_dirs[prompt_type]) / f"base_prompt_ko_{provider}.txt"

        if not prompt_file.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_file}")

        with open(prompt_file, 'r', encoding='utf-8') as f:
            return f.read()

    def extract_core_sentences(self, response: str) -> List[str]:
        """
        Extract core sentences from LLM response.

        Handles both baseline (claims schema) and optimized (core_sentences schema).

        Args:
            response: Raw LLM response (JSON string)

        Returns:
            List of extracted sentences
        """
        try:
            data = json.loads(response)

            # Optimized schema: core_sentences
            if 'core_sentences' in data:
                return [item['sentence'] for item in data['core_sentences']]

            # Baseline schema: claims
            elif 'claims' in data:
                return [claim['text'] for claim in data['claims']]

            else:
                logger.warning(f"Unknown response schema: {list(data.keys())}")
                return []

        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            return []
        except (KeyError, TypeError) as e:
            logger.error(f"Schema extraction error: {e}")
            return []

    def call_llm(
        self,
        provider: str,
        model: str,
        system_prompt: str,
        article_text: str
    ) -> tuple[str, int, int]:
        """
        Call LLM API with retry logic.

        Args:
            provider: Provider name
            model: Model name
            system_prompt: System prompt
            article_text: Article text

        Returns:
            (response_text, duration_ms, tokens_used)
        """
        # Get API key from settings
        api_keys = {
            'openai': settings.llm.openai_api_key,
            'gemini': settings.llm.gemini_api_key,
            'mistral': settings.llm.mistral_api_key
        }

        api_key = api_keys.get(provider)
        if not api_key:
            raise ValueError(f"API key not configured for provider: {provider}")

        # Create LLM instance
        llm = self.llm_factory.create(
            provider=provider,
            api_key=api_key,
            model_name=model
        )

        # Call with retries
        for attempt in range(self.config.max_retries):
            try:
                start_time = time.time()

                response = llm.analyze(
                    article_text=article_text,
                    system_prompt=system_prompt
                )

                duration_ms = int((time.time() - start_time) * 1000)

                # Extract response text
                if hasattr(response, 'raw_response'):
                    response_text = response.raw_response
                else:
                    response_text = str(response)

                # Estimate tokens (rough estimate)
                tokens_used = len(article_text.split()) + len(response_text.split())

                return response_text, duration_ms, tokens_used

            except Exception as e:
                logger.warning(f"API call failed (attempt {attempt + 1}/{self.config.max_retries}): {e}")
                if attempt < self.config.max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    raise

    def run_single_article(
        self,
        article: BenchmarkArticle,
        provider: str,
        model: str,
        prompt_type: str
    ) -> ArticleResult:
        """
        Run evaluation on a single article.

        Args:
            article: Benchmark article
            provider: Provider name
            model: Model name
            prompt_type: 'baseline' or 'optimized'

        Returns:
            ArticleResult with metrics
        """
        try:
            # Load prompt
            system_prompt = self.load_prompt(provider, prompt_type)

            # Call LLM
            response, duration_ms, tokens_used = self.call_llm(
                provider=provider,
                model=model,
                system_prompt=system_prompt,
                article_text=article.body_text
            )

            # Extract sentences
            predicted_sentences = self.extract_core_sentences(response)

            # Calculate metrics
            exact_result = calculate_metrics(
                predicted=predicted_sentences,
                gold=article.gold_sentences,
                match_type='exact'
            )

            semantic_result = calculate_metrics(
                predicted=predicted_sentences,
                gold=article.gold_sentences,
                match_type='semantic'
            )

            return ArticleResult(
                article_id=article.article_id,
                predicted_sentences=predicted_sentences,
                gold_sentences=article.gold_sentences,
                exact_metrics={
                    'precision': exact_result.precision,
                    'recall': exact_result.recall,
                    'f1': exact_result.f1
                },
                semantic_metrics={
                    'precision': semantic_result.precision,
                    'recall': semantic_result.recall,
                    'f1': semantic_result.f1
                },
                raw_response=response,
                duration_ms=duration_ms,
                tokens_used=tokens_used,
                json_valid=len(predicted_sentences) > 0
            )

        except Exception as e:
            logger.error(f"Error processing article {article.article_id}: {e}")
            return ArticleResult(
                article_id=article.article_id,
                predicted_sentences=[],
                gold_sentences=article.gold_sentences,
                exact_metrics={'precision': 0.0, 'recall': 0.0, 'f1': 0.0},
                semantic_metrics={'precision': 0.0, 'recall': 0.0, 'f1': 0.0},
                error=str(e),
                json_valid=False
            )

    def run_single_condition(
        self,
        articles: List[BenchmarkArticle],
        provider: str,
        model: str,
        prompt_type: str,
        condition_id: str
    ) -> ConditionResult:
        """
        Run one experimental condition (e.g., Condition A: Before + GPT-5 Nano).

        Args:
            articles: List of 50 benchmark articles
            provider: Provider name
            model: Model name
            prompt_type: 'baseline' or 'optimized'
            condition_id: 'A', 'B', 'C', 'D', 'E', or 'F'

        Returns:
            ConditionResult with aggregated metrics
        """
        logger.info(f"Running Condition {condition_id}: {prompt_type} + {provider}/{model}")

        results = []
        for article in tqdm(articles, desc=f"Condition {condition_id}"):
            result = self.run_single_article(article, provider, model, prompt_type)
            results.append(result)

            # Rate limiting
            time.sleep(self.config.rate_limit_delay)

        # Aggregate metrics
        exact_scores = [
            MatchScores(
                predicted_scores=[],
                gold_coverage=[],
                precision=r.exact_metrics['precision'],
                recall=r.exact_metrics['recall'],
                f1=r.exact_metrics['f1']
            )
            for r in results
        ]

        semantic_scores = [
            MatchScores(
                predicted_scores=[],
                gold_coverage=[],
                precision=r.semantic_metrics['precision'],
                recall=r.semantic_metrics['recall'],
                f1=r.semantic_metrics['f1']
            )
            for r in results
        ]

        aggregate_exact = aggregate_metrics(exact_scores)
        aggregate_semantic = aggregate_metrics(semantic_scores)

        # Calculate additional statistics
        json_compliance = sum(1 for r in results if r.json_valid) / len(results)
        avg_duration = sum(r.duration_ms for r in results if r.duration_ms) / len(results)
        total_tokens = sum(r.tokens_used for r in results if r.tokens_used)

        return ConditionResult(
            condition_id=condition_id,
            prompt_type=prompt_type,
            provider=provider,
            model=model,
            articles=results,
            aggregate_exact=aggregate_exact,
            aggregate_semantic=aggregate_semantic,
            json_compliance_rate=json_compliance,
            avg_duration_ms=avg_duration,
            total_tokens=total_tokens
        )

    def run_full_experiment(self) -> ExperimentResults:
        """
        Run all 6 conditions (A-F) across 50 articles.
        Total: 300 API calls.

        Returns:
            ExperimentResults with all conditions
        """
        # Load articles
        logger.info("Loading benchmark dataset...")
        articles = self.data_loader.process_dataset(use_cache=self.config.use_cache)
        logger.info(f"Loaded {len(articles)} articles")

        # Generate experiment ID
        experiment_id = f"exp_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        timestamp = datetime.now().isoformat()

        # Define 6 conditions (2×3 matrix)
        conditions_spec = [
            ('A', 'baseline', 'openai', self.config.models['openai']),
            ('B', 'optimized', 'openai', self.config.models['openai']),
            ('C', 'baseline', 'gemini', self.config.models['gemini']),
            ('D', 'optimized', 'gemini', self.config.models['gemini']),
            ('E', 'baseline', 'mistral', self.config.models['mistral']),
            ('F', 'optimized', 'mistral', self.config.models['mistral']),
        ]

        # Run each condition
        condition_results = []
        for cond_id, prompt_type, provider, model in conditions_spec:
            result = self.run_single_condition(
                articles=articles,
                provider=provider,
                model=model,
                prompt_type=prompt_type,
                condition_id=cond_id
            )
            condition_results.append(result)

            logger.info(f"Condition {cond_id} complete: "
                       f"Exact F1={result.aggregate_exact['f1']:.3f}, "
                       f"Semantic F1={result.aggregate_semantic['f1']:.3f}")

        # Create experiment results
        return ExperimentResults(
            experiment_id=experiment_id,
            timestamp=timestamp,
            config=self.config,
            conditions=condition_results
        )

    def save_results(self, results: ExperimentResults, output_dir: str = "data/benchset/experiments"):
        """
        Save experiment results to JSON file.

        Args:
            results: Experiment results
            output_dir: Output directory
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        output_file = output_path / f"{results.experiment_id}_results.json"

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results.to_dict(), f, ensure_ascii=False, indent=2)

        logger.info(f"Results saved to: {output_file}")


def main():
    """Run full benchmark experiment"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Create experiment runner
    config = ExperimentConfig()
    runner = BenchmarkExperiment(config)

    # Run experiment
    logger.info("Starting full benchmark experiment (300 API calls)")
    results = runner.run_full_experiment()

    # Save results
    runner.save_results(results)

    # Print summary
    print("\n" + "="*80)
    print("EXPERIMENT COMPLETE")
    print("="*80)
    print(f"Experiment ID: {results.experiment_id}")
    print(f"Total conditions: {len(results.conditions)}")
    print("\nResults Summary:")
    print(f"{'Condition':<12} {'Prompt':<12} {'Model':<20} {'Exact F1':<10} {'Semantic F1':<12} {'JSON %':<8}")
    print("-" * 80)

    for cond in results.conditions:
        print(f"{cond.condition_id:<12} {cond.prompt_type:<12} {cond.provider:<20} "
              f"{cond.aggregate_exact['f1']:.3f}      {cond.aggregate_semantic['f1']:.3f}        "
              f"{cond.json_compliance_rate*100:.1f}%")


if __name__ == '__main__':
    main()
