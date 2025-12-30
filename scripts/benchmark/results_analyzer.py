"""
Results Analyzer for Benchmark Experiments

Analyzes experiment results, calculates PIR, IMA, statistical significance,
and generates reports for research paper.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any
from scipy import stats
import numpy as np

logger = logging.getLogger(__name__)


class ResultsAnalyzer:
    """Analyzes benchmark experiment results"""

    def __init__(self, results_file: Path):
        self.results_file = Path(results_file)
        self.results = self.load_results()

    def load_results(self) -> Dict:
        """Load results from JSON file"""
        with open(self.results_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def get_condition(self, condition_id: str) -> Dict:
        """Get specific condition results"""
        for cond in self.results['conditions']:
            if cond['condition_id'] == condition_id:
                return cond
        raise ValueError(f"Condition {condition_id} not found")

    def calculate_pir(self) -> Dict[str, Dict]:
        """
        Calculate Prompt Improvement Rate (PIR) for each model.

        PIR = (Optimized_F1 - Baseline_F1) / Baseline_F1 × 100%

        Returns:
            Dict with PIR for each model (openai, gemini, mistral)
        """
        pir_results = {}

        # Map models to condition pairs
        model_conditions = {
            'openai': ('A', 'B'),  # A=baseline, B=optimized
            'gemini': ('C', 'D'),
            'mistral': ('E', 'F')
        }

        for model, (baseline_id, optimized_id) in model_conditions.items():
            baseline = self.get_condition(baseline_id)
            optimized = self.get_condition(optimized_id)

            baseline_f1 = baseline['aggregate_semantic']['f1']
            optimized_f1 = optimized['aggregate_semantic']['f1']

            if baseline_f1 == 0:
                pir = float('inf') if optimized_f1 > 0 else 0.0
            else:
                pir = ((optimized_f1 - baseline_f1) / baseline_f1) * 100

            pir_results[model] = {
                'baseline_f1': baseline_f1,
                'optimized_f1': optimized_f1,
                'pir': pir,
                'absolute_improvement': optimized_f1 - baseline_f1
            }

        return pir_results

    def calculate_ima(self) -> Dict[str, float]:
        """
        Calculate Inter-Model Agreement (IMA).

        Measures semantic overlap between models on the same articles.

        Returns:
            {'baseline': IMA, 'optimized': IMA}
        """
        # Get baseline conditions (A, C, E)
        baseline_conditions = [
            self.get_condition('A'),  # OpenAI baseline
            self.get_condition('C'),  # Gemini baseline
            self.get_condition('E')   # Mistral baseline
        ]

        # Get optimized conditions (B, D, F)
        optimized_conditions = [
            self.get_condition('B'),  # OpenAI optimized
            self.get_condition('D'),  # Gemini optimized
            self.get_condition('F')   # Mistral optimized
        ]

        baseline_ima = self._calculate_agreement(baseline_conditions)
        optimized_ima = self._calculate_agreement(optimized_conditions)

        return {
            'baseline': baseline_ima,
            'optimized': optimized_ima,
            'improvement': optimized_ima - baseline_ima
        }

    def _calculate_agreement(self, conditions: List[Dict]) -> float:
        """
        Calculate average pairwise agreement across conditions.

        Args:
            conditions: List of 3 condition results

        Returns:
            Average agreement score
        """
        if len(conditions) != 3:
            raise ValueError("Expected 3 conditions for IMA calculation")

        # For each article, calculate pairwise overlap
        article_agreements = []

        # Assume all conditions have same articles in same order
        num_articles = len(conditions[0]['articles'])

        for i in range(num_articles):
            # Get predicted sentences from each model for this article
            pred_sets = [
                set(cond['articles'][i]['predicted_sentences'])
                for cond in conditions
            ]

            # Calculate Jaccard similarity for all pairs
            pairs = [(0, 1), (0, 2), (1, 2)]
            pair_scores = []

            for idx1, idx2 in pairs:
                intersection = len(pred_sets[idx1] & pred_sets[idx2])
                union = len(pred_sets[idx1] | pred_sets[idx2])

                if union > 0:
                    jaccard = intersection / union
                    pair_scores.append(jaccard)

            # Average across pairs for this article
            if pair_scores:
                article_agreements.append(np.mean(pair_scores))

        # Average across all articles
        return np.mean(article_agreements) if article_agreements else 0.0

    def statistical_significance_tests(self) -> Dict[str, Dict]:
        """
        Perform paired t-tests for baseline vs optimized.

        Tests null hypothesis: no difference in F1 scores.

        Returns:
            Dict with t-test results for each model
        """
        tests = {}

        model_conditions = {
            'openai': ('A', 'B'),
            'gemini': ('C', 'D'),
            'mistral': ('E', 'F')
        }

        for model, (baseline_id, optimized_id) in model_conditions.items():
            baseline = self.get_condition(baseline_id)
            optimized = self.get_condition(optimized_id)

            # Extract F1 scores for each article
            baseline_f1s = [
                article['semantic_metrics']['f1']
                for article in baseline['articles']
            ]

            optimized_f1s = [
                article['semantic_metrics']['f1']
                for article in optimized['articles']
            ]

            # Paired t-test
            t_stat, p_value = stats.ttest_rel(optimized_f1s, baseline_f1s)

            tests[model] = {
                't_statistic': float(t_stat),
                'p_value': float(p_value),
                'significant': p_value < 0.05,
                'alpha': 0.05
            }

        return tests

    def analyze(self) -> Dict[str, Any]:
        """
        Perform full analysis.

        Returns:
            Dict with all analysis results
        """
        logger.info("Analyzing experiment results...")

        analysis = {
            'experiment_id': self.results['experiment_id'],
            'timestamp': self.results['timestamp'],
            'pir': self.calculate_pir(),
            'ima': self.calculate_ima(),
            'significance_tests': self.statistical_significance_tests(),
            'summary': self._generate_summary()
        }

        return analysis

    def _generate_summary(self) -> Dict:
        """Generate summary statistics"""
        summary = {
            'total_conditions': len(self.results['conditions']),
            'total_articles': len(self.results['conditions'][0]['articles']),
            'total_api_calls': sum(
                len(cond['articles']) for cond in self.results['conditions']
            )
        }

        return summary

    def generate_markdown_report(self) -> str:
        """
        Generate markdown report for research paper.

        Returns:
            Markdown-formatted report string
        """
        analysis = self.analyze()

        report = f"""# Benchmark Evaluation Results

**Experiment ID**: `{analysis['experiment_id']}`
**Timestamp**: {analysis['timestamp']}
**Total API Calls**: {analysis['summary']['total_api_calls']}

---

## Table 10. Model Performance Comparison (Baseline vs Optimized)

| Model | Baseline F1 | Optimized F1 | PIR (%) | Statistical Significance |
|-------|-------------|--------------|---------|--------------------------|
"""

        # Add model rows
        for model in ['openai', 'gemini', 'mistral']:
            pir_data = analysis['pir'][model]
            sig_data = analysis['significance_tests'][model]

            sig_marker = "✓ (p<0.05)" if sig_data['significant'] else "✗ (n.s.)"

            report += f"| {model.title()} | {pir_data['baseline_f1']:.3f} | {pir_data['optimized_f1']:.3f} | "
            report += f"{pir_data['pir']:+.1f}% | {sig_marker} |\n"

        report += f"""
---

## Inter-Model Agreement (IMA)

| Metric | Baseline | Optimized | Improvement |
|--------|----------|-----------|-------------|
| IMA | {analysis['ima']['baseline']:.3f} | {analysis['ima']['optimized']:.3f} | {analysis['ima']['improvement']:+.3f} |

**Interpretation**: Higher IMA indicates prompts constrain the task more clearly, reducing model-specific biases.

---

## Hypothesis Testing Results

### H1: Task Clarity Effect
"""
        # Check if all models show improvement
        all_improved = all(p['pir'] > 0 for p in analysis['pir'].values())
        report += f"**Result**: {'✓ SUPPORTED' if all_improved else '✗ NOT SUPPORTED'}\n\n"

        for model, pir_data in analysis['pir'].items():
            report += f"- {model.title()}: PIR = {pir_data['pir']:+.1f}%\n"

        report += f"""
### H2: Model Consistency
**Result**: {'✓ SUPPORTED' if analysis['ima']['improvement'] > 0 else '✗ NOT SUPPORTED'}

IMA increased by {analysis['ima']['improvement']:+.3f}, indicating optimized prompts reduce inter-model variance.

### H3: Output Stability
"""
        # Extract JSON compliance rates
        for cond in self.results['conditions']:
            if cond['prompt_type'] == 'optimized':
                report += f"- {cond['provider'].title()}: JSON compliance = {cond['json_compliance_rate']*100:.1f}%\n"

        report += f"""
### H4: Lightweight Model Effect
**Hypothesis**: Smaller models show higher PIR (more prompt-sensitive).

"""
        # Sort models by parameter size (approximate)
        model_sizes = {'mistral': 3, 'gemini': 8, 'openai': 7}  # Estimated B
        sorted_models = sorted(analysis['pir'].items(),
                              key=lambda x: model_sizes.get(x[0], 0))

        for model, pir_data in sorted_models:
            report += f"- {model.title()} (~{model_sizes.get(model, '?')}B): PIR = {pir_data['pir']:+.1f}%\n"

        # Check if PIR correlates negatively with model size
        pirs = [analysis['pir'][m]['pir'] for m, _ in sorted_models]
        correlation_holds = pirs == sorted(pirs, reverse=True)

        report += f"\n**Result**: {'✓ SUPPORTED' if correlation_holds else '✗ PARTIAL SUPPORT'}\n"

        report += """
---

## Detailed Condition Results

| Condition | Prompt | Model | Exact F1 | Semantic F1 | JSON % | Avg Duration (ms) |
|-----------|--------|-------|----------|-------------|--------|-------------------|
"""

        for cond in self.results['conditions']:
            report += f"| {cond['condition_id']} | {cond['prompt_type']} | {cond['provider']} | "
            report += f"{cond['aggregate_exact']['f1']:.3f} | {cond['aggregate_semantic']['f1']:.3f} | "
            report += f"{cond['json_compliance_rate']*100:.0f}% | {cond['avg_duration_ms']:.0f} |\n"

        report += "\n---\n\n*Generated by Benchmark Evaluation System*\n"

        return report


def main():
    """Test results analyzer"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python results_analyzer.py <results_file.json>")
        sys.exit(1)

    results_file = Path(sys.argv[1])

    if not results_file.exists():
        print(f"Error: File not found: {results_file}")
        sys.exit(1)

    analyzer = ResultsAnalyzer(results_file)
    analysis = analyzer.analyze()

    print("\n=== ANALYSIS RESULTS ===\n")
    print(json.dumps(analysis, indent=2))

    print("\n=== MARKDOWN REPORT ===\n")
    print(analyzer.generate_markdown_report())


if __name__ == '__main__':
    main()
