"""
Command-Line Interface for Benchmark Experiments

Provides commands to prepare data, run experiments, and analyze results.
"""

import argparse
import logging
import sys
from pathlib import Path

from scripts.benchmark.data_loader import BenchmarkDataLoader
from scripts.benchmark.experiment_runner import BenchmarkExperiment, ExperimentConfig
from scripts.benchmark.results_analyzer import ResultsAnalyzer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def cmd_prepare(args):
    """Prepare dataset: load Excel and fetch articles from URLs"""
    logger.info("Preparing benchmark dataset...")

    loader = BenchmarkDataLoader()
    articles = loader.process_dataset(use_cache=args.no_cache is False)

    print(f"\n✓ Dataset prepared: {len(articles)} articles")
    print(f"  - Successfully fetched: {sum(1 for a in articles if a.body_text)}")
    print(f"  - Failed fetches: {sum(1 for a in articles if not a.body_text)}")
    print(f"  - Avg gold sentences: {sum(len(a.gold_sentences) for a in articles) / len(articles):.2f}")
    print(f"\n  Cache saved to: {loader.cache_path}")


def cmd_run(args):
    """Run benchmark experiment"""
    # Create config
    config = ExperimentConfig()

    if args.no_cache:
        config.use_cache = False

    # Create experiment runner
    runner = BenchmarkExperiment(config)

    if args.condition:
        # Run single condition
        logger.info(f"Running single condition: {args.condition}")

        # Map condition ID to parameters
        conditions_map = {
            'A': ('baseline', 'openai', config.models['openai']),
            'B': ('optimized', 'openai', config.models['openai']),
            'C': ('baseline', 'gemini', config.models['gemini']),
            'D': ('optimized', 'gemini', config.models['gemini']),
            'E': ('baseline', 'mistral', config.models['mistral']),
            'F': ('optimized', 'mistral', config.models['mistral']),
        }

        if args.condition not in conditions_map:
            print(f"Error: Invalid condition '{args.condition}'. Use A, B, C, D, E, or F.")
            sys.exit(1)

        prompt_type, provider, model = conditions_map[args.condition]

        # Load articles
        articles = runner.data_loader.process_dataset(use_cache=config.use_cache)

        # Run condition
        result = runner.run_single_condition(
            articles=articles,
            provider=provider,
            model=model,
            prompt_type=prompt_type,
            condition_id=args.condition
        )

        # Print results
        print(f"\n✓ Condition {args.condition} complete")
        print(f"  Prompt: {prompt_type}")
        print(f"  Model: {provider}/{model}")
        print(f"  Exact Match F1: {result.aggregate_exact['f1']:.3f}")
        print(f"  Semantic Match F1: {result.aggregate_semantic['f1']:.3f}")
        print(f"  JSON Compliance: {result.json_compliance_rate*100:.1f}%")
        print(f"  Avg Duration: {result.avg_duration_ms:.0f}ms")
        print(f"  Total Tokens: {result.total_tokens:,}")

    else:
        # Run full experiment (6 conditions × 50 articles = 300 calls)
        logger.info("Running full benchmark experiment (300 API calls)")

        if not args.yes:
            response = input("\nThis will make 300 API calls. Continue? [y/N]: ")
            if response.lower() != 'y':
                print("Cancelled.")
                sys.exit(0)

        results = runner.run_full_experiment()

        # Save results
        runner.save_results(results)

        # Print summary
        print("\n" + "="*80)
        print("EXPERIMENT COMPLETE")
        print("="*80)
        print(f"Experiment ID: {results.experiment_id}")
        print(f"\nResults saved to: data/benchset/experiments/{results.experiment_id}_results.json")
        print("\nResults Summary:")
        print(f"{'Condition':<12} {'Prompt':<12} {'Model':<20} {'Exact F1':<10} {'Semantic F1':<12} {'JSON %':<8}")
        print("-" * 80)

        for cond in results.conditions:
            print(f"{cond.condition_id:<12} {cond.prompt_type:<12} {cond.provider:<20} "
                  f"{cond.aggregate_exact['f1']:.3f}      {cond.aggregate_semantic['f1']:.3f}        "
                  f"{cond.json_compliance_rate*100:.1f}%")


def cmd_analyze(args):
    """Analyze experiment results"""
    logger.info(f"Analyzing results: {args.experiment_id}")

    # Load results
    results_file = Path(f"data/benchset/experiments/{args.experiment_id}_results.json")

    if not results_file.exists():
        print(f"Error: Results file not found: {results_file}")
        sys.exit(1)

    # Analyze
    analyzer = ResultsAnalyzer(results_file)
    analysis = analyzer.analyze()

    # Print analysis
    print("\n" + "="*80)
    print("ANALYSIS REPORT")
    print("="*80)

    print("\n## Prompt Improvement Rate (PIR)")
    print(f"{'Model':<20} {'Baseline F1':<12} {'Optimized F1':<14} {'PIR %':<10}")
    print("-" * 60)
    for model, pir_data in analysis['pir'].items():
        print(f"{model:<20} {pir_data['baseline_f1']:.3f}        {pir_data['optimized_f1']:.3f}          "
              f"{pir_data['pir']:.1f}%")

    print("\n## Inter-Model Agreement (IMA)")
    print(f"Baseline IMA: {analysis['ima']['baseline']:.3f}")
    print(f"Optimized IMA: {analysis['ima']['optimized']:.3f}")
    print(f"Improvement: {(analysis['ima']['optimized'] - analysis['ima']['baseline']):.3f}")

    print("\n## Statistical Significance (Paired t-test)")
    for model, test in analysis['significance_tests'].items():
        print(f"{model}: t={test['t_statistic']:.3f}, p={test['p_value']:.4f} "
              f"({'significant' if test['p_value'] < 0.05 else 'not significant'})")


def cmd_report(args):
    """Generate report in specified format"""
    logger.info(f"Generating {args.format} report: {args.experiment_id}")

    # Load results
    results_file = Path(f"data/benchset/experiments/{args.experiment_id}_results.json")

    if not results_file.exists():
        print(f"Error: Results file not found: {results_file}")
        sys.exit(1)

    # Generate report
    analyzer = ResultsAnalyzer(results_file)

    if args.format == 'markdown':
        report = analyzer.generate_markdown_report()
        output_file = results_file.parent / f"{args.experiment_id}_report.md"

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report)

        print(f"\n✓ Markdown report generated: {output_file}")

    elif args.format == 'json':
        analysis = analyzer.analyze()
        output_file = results_file.parent / f"{args.experiment_id}_analysis.json"

        import json
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, indent=2)

        print(f"\n✓ JSON analysis generated: {output_file}")

    else:
        print(f"Error: Unknown format '{args.format}'")
        sys.exit(1)


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Benchmark Evaluation CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Prepare dataset (fetch articles from URLs)
  python -m scripts.benchmark.cli prepare

  # Run full experiment (300 API calls)
  python -m scripts.benchmark.cli run --yes

  # Run single condition (50 API calls)
  python -m scripts.benchmark.cli run --condition A

  # Analyze results
  python -m scripts.benchmark.cli analyze --experiment-id exp_20250101_120000

  # Generate markdown report
  python -m scripts.benchmark.cli report --experiment-id exp_20250101_120000 --format markdown
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # Prepare command
    prepare_parser = subparsers.add_parser('prepare', help='Prepare benchmark dataset')
    prepare_parser.add_argument('--no-cache', action='store_true', help='Force re-fetch articles')

    # Run command
    run_parser = subparsers.add_parser('run', help='Run benchmark experiment')
    run_parser.add_argument('--condition', choices=['A', 'B', 'C', 'D', 'E', 'F'],
                           help='Run single condition (default: run all 6)')
    run_parser.add_argument('--no-cache', action='store_true', help='Disable caching')
    run_parser.add_argument('--yes', '-y', action='store_true', help='Skip confirmation prompt')

    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze experiment results')
    analyze_parser.add_argument('--experiment-id', required=True, help='Experiment ID to analyze')

    # Report command
    report_parser = subparsers.add_parser('report', help='Generate report')
    report_parser.add_argument('--experiment-id', required=True, help='Experiment ID')
    report_parser.add_argument('--format', choices=['markdown', 'json'], default='markdown',
                              help='Output format (default: markdown)')

    # Parse arguments
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Execute command
    if args.command == 'prepare':
        cmd_prepare(args)
    elif args.command == 'run':
        cmd_run(args)
    elif args.command == 'analyze':
        cmd_analyze(args)
    elif args.command == 'report':
        cmd_report(args)


if __name__ == '__main__':
    main()
