"""
Evaluation Metrics for Benchmark

Implements Exact Match, Semantic Match, Precision, Recall, and F1 score
following the methodology in Section 2 of the research proposal.
"""

import re
import unicodedata
from typing import List, Dict, Tuple, Callable, Optional
import numpy as np
from dataclasses import dataclass


@dataclass
class MatchScores:
    """Scores for a single article evaluation"""
    predicted_scores: List[float]  # Score for each predicted sentence
    gold_coverage: List[float]  # Which gold sentences were matched
    precision: float
    recall: float
    f1: float


def normalize_sentence(text: str) -> str:
    """
    Normalize sentence for exact matching.

    Following Section 2.2.1 preprocessing rules:
    1. Strip leading/trailing whitespace
    2. Collapse multiple spaces to single
    3. Normalize quotes (' → ', " → ")
    4. Normalize numbers (fullwidth → halfwidth)
    5. Standardize sentence-ending periods

    Args:
        text: Raw sentence text

    Returns:
        Normalized sentence
    """
    if not text:
        return ""

    # Strip whitespace
    text = text.strip()

    # Normalize unicode (NFKC: fullwidth → halfwidth)
    text = unicodedata.normalize('NFKC', text)

    # Collapse multiple spaces
    text = re.sub(r'\s+', ' ', text)

    # Normalize quotes
    text = text.replace(''', "'").replace(''', "'")
    text = text.replace('"', '"').replace('"', '"')

    # Standardize sentence-ending period (optional: ensure consistent)
    # Keep as-is - some sentences may not have periods

    return text


def exact_match_score(predicted: str, gold: str) -> float:
    """
    Calculate exact match score between two sentences.

    Args:
        predicted: Predicted sentence
        gold: Gold standard sentence

    Returns:
        1.0 if normalized strings are identical, else 0.0
    """
    pred_norm = normalize_sentence(predicted)
    gold_norm = normalize_sentence(gold)

    return 1.0 if pred_norm == gold_norm else 0.0


def semantic_match_score(
    predicted: str,
    gold: str,
    embedder: Optional[object] = None,
    threshold_high: float = 0.85,
    threshold_mid: float = 0.70
) -> float:
    """
    Calculate semantic match score using sentence embeddings.

    Following Table 8 in methodology:
    - similarity >= 0.85: 완전 일치 (1.0)
    - similarity >= 0.70: 부분 일치 (0.5)
    - similarity < 0.70: 불일치 (0.0)

    Args:
        predicted: Predicted sentence
        gold: Gold standard sentence
        embedder: SentenceTransformer model (lazy loaded if None)
        threshold_high: Threshold for perfect match (default 0.85)
        threshold_mid: Threshold for partial match (default 0.70)

    Returns:
        Match score (0.0, 0.5, or 1.0)
    """
    if embedder is None:
        # Lazy load SentenceTransformer
        try:
            from sentence_transformers import SentenceTransformer
            # Use Korean-optimized model
            embedder = SentenceTransformer('jhgan/ko-sbert-multitask')
        except ImportError:
            raise ImportError(
                "sentence-transformers required for semantic matching. "
                "Install with: pip install sentence-transformers"
            )

    # Compute embeddings
    embeddings = embedder.encode([predicted, gold])
    pred_emb = embeddings[0]
    gold_emb = embeddings[1]

    # Compute cosine similarity
    similarity = np.dot(pred_emb, gold_emb) / (
        np.linalg.norm(pred_emb) * np.linalg.norm(gold_emb)
    )

    # Apply thresholds (Table 8)
    if similarity >= threshold_high:
        return 1.0  # 완전 일치
    elif similarity >= threshold_mid:
        return 0.5  # 부분 일치
    else:
        return 0.0  # 불일치


def match_sentences(
    predicted_sentences: List[str],
    gold_sentences: List[str],
    match_fn: Callable[[str, str], float],
    **match_kwargs
) -> Tuple[List[float], List[float]]:
    """
    Match predicted sentences against gold standard.

    For each predicted sentence, finds the best match in the gold set.

    Args:
        predicted_sentences: List of predicted sentences
        gold_sentences: List of gold standard sentences
        match_fn: Matching function (exact_match_score or semantic_match_score)
        **match_kwargs: Additional arguments for match_fn

    Returns:
        (predicted_scores, gold_coverage)
        - predicted_scores: Score for each predicted sentence (max over all gold)
        - gold_coverage: Binary indicator if each gold sentence was matched
    """
    if not predicted_sentences or not gold_sentences:
        return [], []

    predicted_scores = []
    gold_matched = [False] * len(gold_sentences)

    # For each predicted sentence
    for pred in predicted_sentences:
        # Find best match in gold set
        max_score = 0.0
        best_gold_idx = -1

        for gold_idx, gold in enumerate(gold_sentences):
            score = match_fn(pred, gold, **match_kwargs)
            if score > max_score:
                max_score = score
                best_gold_idx = gold_idx

        predicted_scores.append(max_score)

        # Mark gold sentence as matched if score > 0
        if max_score > 0 and best_gold_idx >= 0:
            gold_matched[best_gold_idx] = True

    gold_coverage = [1.0 if matched else 0.0 for matched in gold_matched]

    return predicted_scores, gold_coverage


def calculate_metrics(
    predicted: List[str],
    gold: List[str],
    match_type: str = 'exact',
    embedder: Optional[object] = None
) -> MatchScores:
    """
    Calculate Precision, Recall, and F1 score for an article.

    Following Section 2.3 formulas:
    - Precision = Σscore(predicted) / |predicted|
    - Recall = Σscore(predicted) / |gold|
    - F1 = 2 × P × R / (P + R)

    Args:
        predicted: List of predicted core sentences
        gold: List of gold standard core sentences
        match_type: 'exact' or 'semantic'
        embedder: SentenceTransformer model (for semantic matching)

    Returns:
        MatchScores with precision, recall, f1, and detailed scores
    """
    # Edge cases
    if not predicted and not gold:
        return MatchScores([], [], 1.0, 1.0, 1.0)  # Both empty = perfect
    if not predicted:
        return MatchScores([], [0.0] * len(gold), 0.0, 0.0, 0.0)  # No predictions
    if not gold:
        return MatchScores([0.0] * len(predicted), [], 0.0, 0.0, 0.0)  # No gold

    # Select matching function
    if match_type == 'exact':
        match_fn = exact_match_score
        match_kwargs = {}
    elif match_type == 'semantic':
        match_fn = semantic_match_score
        match_kwargs = {'embedder': embedder}
    else:
        raise ValueError(f"Unknown match_type: {match_type}. Use 'exact' or 'semantic'")

    # Match sentences
    predicted_scores, gold_coverage = match_sentences(
        predicted, gold, match_fn, **match_kwargs
    )

    # Calculate metrics (Section 2.3)
    precision = sum(predicted_scores) / len(predicted) if predicted else 0.0
    recall = sum(predicted_scores) / len(gold) if gold else 0.0

    if precision + recall > 0:
        f1 = 2 * precision * recall / (precision + recall)
    else:
        f1 = 0.0

    return MatchScores(
        predicted_scores=predicted_scores,
        gold_coverage=gold_coverage,
        precision=precision,
        recall=recall,
        f1=f1
    )


def aggregate_metrics(results: List[MatchScores]) -> Dict[str, float]:
    """
    Aggregate metrics across multiple articles.

    Args:
        results: List of MatchScores for each article

    Returns:
        Dictionary with mean precision, recall, F1
    """
    if not results:
        return {'precision': 0.0, 'recall': 0.0, 'f1': 0.0}

    return {
        'precision': np.mean([r.precision for r in results]),
        'recall': np.mean([r.recall for r in results]),
        'f1': np.mean([r.f1 for r in results]),
        'precision_std': np.std([r.precision for r in results]),
        'recall_std': np.std([r.recall for r in results]),
        'f1_std': np.std([r.f1 for r in results])
    }


def calculate_pir(baseline_f1: float, optimized_f1: float) -> float:
    """
    Calculate Prompt Improvement Rate (PIR).

    PIR = (Optimized_F1 - Baseline_F1) / Baseline_F1 × 100%

    Args:
        baseline_f1: F1 score for baseline prompt
        optimized_f1: F1 score for optimized prompt

    Returns:
        PIR as percentage
    """
    if baseline_f1 == 0:
        return float('inf') if optimized_f1 > 0 else 0.0

    return ((optimized_f1 - baseline_f1) / baseline_f1) * 100


def main():
    """Test metrics calculation"""
    # Test exact match
    print("=== Test Exact Match ===")
    pred = ["정부는 특별법 제정을 약속했다", "유족들은 반발했다"]
    gold = ["정부는 특별법 제정을 약속했다", "세월호는 침몰했다"]

    exact_result = calculate_metrics(pred, gold, match_type='exact')
    print(f"Precision: {exact_result.precision:.2f}")
    print(f"Recall: {exact_result.recall:.2f}")
    print(f"F1: {exact_result.f1:.2f}")

    # Test semantic match (requires sentence-transformers)
    try:
        print("\n=== Test Semantic Match ===")
        pred2 = ["정부가 특별법 제정 의지를 밝혔다", "유족들은 반발했다"]

        semantic_result = calculate_metrics(pred2, gold, match_type='semantic')
        print(f"Precision: {semantic_result.precision:.2f}")
        print(f"Recall: {semantic_result.recall:.2f}")
        print(f"F1: {semantic_result.f1:.2f}")
    except ImportError:
        print("sentence-transformers not installed, skipping semantic test")

    # Test PIR
    print("\n=== Test PIR ===")
    pir = calculate_pir(0.50, 0.75)
    print(f"PIR: {pir:.1f}%")


if __name__ == '__main__':
    main()
