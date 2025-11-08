"""Comparison operations for model outputs and consensus verification."""

from typing import Any, Dict, Optional
import difflib

from .base import BaseOperation


class ComparisonOperation(BaseOperation):
    """
    Compare results from multiple sources (e.g., AI models).

    Performs:
    - Text similarity analysis
    - Length comparison
    - Structural similarity
    - Semantic overlap detection

    Inputs:
        - Multiple inputs ending with '_result' (e.g., model_1_result, model_2_result)
        - threshold: Similarity threshold (optional, default 0.75)

    Returns:
        - similarity_scores: Pairwise similarity scores
        - average_similarity: Average of all pairwise similarities
        - all_similar: Whether all pairs meet threshold
        - model_count: Number of models compared
        - differences: Analysis of differences
        - consensus: Consensus summary
    """

    def validate(self) -> Optional[str]:
        """Validate that we have at least 2 result inputs."""
        result_inputs = [k for k in self.inputs.keys() if k.endswith("_result")]
        if len(result_inputs) < 2:
            return "compare_results operation requires at least 2 inputs ending with '_result'"
        return None

    async def execute(self) -> Dict[str, Any]:
        """Execute model comparison."""
        # Get all model results from inputs
        model_results = {}
        for key, value in self.inputs.items():
            if key.endswith("_result") and value:
                model_name = key.replace("_result", "")
                model_results[model_name] = str(value)

        if len(model_results) < 2:
            return {
                "error": "Need at least 2 model results to compare",
                "all_similar": False,
                "similarity_scores": {},
            }

        # Calculate pairwise similarities
        model_names = list(model_results.keys())
        similarity_scores = {}

        for i, model_a in enumerate(model_names):
            for model_b in model_names[i + 1 :]:
                text_a = model_results[model_a]
                text_b = model_results[model_b]

                # Calculate text similarity
                similarity = self._calculate_similarity(text_a, text_b)
                pair_key = f"{model_a}_vs_{model_b}"
                similarity_scores[pair_key] = similarity

        # Calculate average similarity
        avg_similarity = (
            sum(similarity_scores.values()) / len(similarity_scores)
            if similarity_scores
            else 0.0
        )

        # Get threshold from inputs
        threshold = float(self.inputs.get("threshold", 0.75))

        # Check if all pairs meet threshold
        all_similar = all(score >= threshold for score in similarity_scores.values())

        # Analyze differences
        differences = self._analyze_differences(model_results)

        return {
            "similarity_scores": similarity_scores,
            "average_similarity": round(avg_similarity, 3),
            "threshold": threshold,
            "all_similar": all_similar,
            "model_count": len(model_results),
            "differences": differences,
            "consensus": self._build_consensus(model_results, similarity_scores),
        }

    def _calculate_similarity(self, text_a: str, text_b: str) -> float:
        """
        Calculate similarity between two text strings.

        Uses SequenceMatcher for text similarity and considers:
        - Character-level similarity
        - Word-level similarity
        - Length similarity

        Returns:
            Similarity score between 0.0 and 1.0
        """
        # Normalize whitespace
        text_a = " ".join(text_a.split())
        text_b = " ".join(text_b.split())

        # Character-level similarity
        char_similarity = difflib.SequenceMatcher(None, text_a, text_b).ratio()

        # Word-level similarity
        words_a = set(text_a.lower().split())
        words_b = set(text_b.lower().split())

        if not words_a and not words_b:
            word_similarity = 1.0
        elif not words_a or not words_b:
            word_similarity = 0.0
        else:
            word_similarity = len(words_a & words_b) / len(words_a | words_b)

        # Length similarity
        len_a, len_b = len(text_a), len(text_b)
        if len_a == 0 and len_b == 0:
            length_similarity = 1.0
        elif len_a == 0 or len_b == 0:
            length_similarity = 0.0
        else:
            length_similarity = min(len_a, len_b) / max(len_a, len_b)

        # Weighted average: character similarity is most important
        similarity = (
            0.5 * char_similarity + 0.3 * word_similarity + 0.2 * length_similarity
        )

        return round(similarity, 3)

    def _analyze_differences(self, model_results: Dict[str, str]) -> Dict[str, Any]:
        """
        Analyze key differences between model outputs.

        Returns:
            Analysis of differences including unique content per model
        """
        if len(model_results) < 2:
            return {}

        # Extract unique words per model
        all_words = set()
        model_words = {}

        for model, text in model_results.items():
            words = set(text.lower().split())
            model_words[model] = words
            all_words.update(words)

        # Find unique words per model
        unique_words = {}
        for model, words in model_words.items():
            other_words = set()
            for other_model, other_model_words in model_words.items():
                if other_model != model:
                    other_words.update(other_model_words)

            unique = words - other_words
            if unique:
                unique_words[model] = sorted(list(unique))[:10]  # Limit to 10 words

        # Calculate length differences
        lengths = {model: len(text) for model, text in model_results.items()}

        return {
            "unique_words_per_model": unique_words,
            "text_lengths": lengths,
            "length_variance": max(lengths.values()) - min(lengths.values()),
        }

    def _build_consensus(
        self, model_results: Dict[str, str], similarity_scores: Dict[str, float]
    ) -> str:
        """
        Build a consensus summary from model results.

        Returns:
            Consensus statement or indication of disagreement
        """
        avg_similarity = (
            sum(similarity_scores.values()) / len(similarity_scores)
            if similarity_scores
            else 0.0
        )

        if avg_similarity >= 0.9:
            return "Strong consensus: All models produced highly similar results"
        elif avg_similarity >= 0.75:
            return "Moderate consensus: Models generally agree with minor variations"
        elif avg_similarity >= 0.5:
            return "Weak consensus: Models show some agreement but notable differences"
        else:
            return "No consensus: Models produced significantly different results"


class ConsensusVerificationOperation(BaseOperation):
    """
    Verify if comparison results meet consensus criteria.

    Inputs:
        - comparison: Comparison result from ComparisonOperation
        - threshold: Similarity threshold (optional, default 0.75)

    Returns:
        - verified: Whether consensus is verified
        - average_similarity: Average similarity from comparison
        - threshold: Threshold used
        - passed_threshold: Whether threshold was passed
        - consensus_level: Consensus level from comparison
        - recommendation: Action recommendation
    """

    def validate(self) -> Optional[str]:
        """Validate that comparison input is provided."""
        if "comparison" not in self.inputs:
            return "verify_consensus operation requires 'comparison' input"
        return None

    async def execute(self) -> Dict[str, Any]:
        """Execute consensus verification."""
        comparison = self.inputs.get("comparison", {})
        threshold = float(self.inputs.get("threshold", 0.75))

        if not comparison:
            return {"verified": False, "reason": "No comparison data available"}

        all_similar = comparison.get("all_similar", False)
        avg_similarity = comparison.get("average_similarity", 0.0)

        return {
            "verified": all_similar,
            "average_similarity": avg_similarity,
            "threshold": threshold,
            "passed_threshold": avg_similarity >= threshold,
            "consensus_level": comparison.get("consensus", "Unknown"),
            "recommendation": self._get_recommendation(
                all_similar, avg_similarity, threshold
            ),
        }

    def _get_recommendation(
        self, all_similar: bool, avg_similarity: float, threshold: float
    ) -> str:
        """Generate recommendation based on verification results."""
        if all_similar:
            return "Models agree - results are reliable and can be used with high confidence"
        elif avg_similarity >= threshold - 0.1:
            return "Models mostly agree - results are generally reliable with minor variations"
        else:
            return "Models disagree significantly - manual review recommended or rerun with different models"
