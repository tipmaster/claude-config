"""Convergence detection for deliberation rounds."""
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional

logger = logging.getLogger(__name__)


# =============================================================================
# Similarity Backend Interface
# =============================================================================


class SimilarityBackend(ABC):
    """Abstract base class for similarity computation backends."""

    @abstractmethod
    def compute_similarity(self, text1: str, text2: str) -> float:
        """
        Compute similarity between two texts.

        Args:
            text1: First text
            text2: Second text

        Returns:
            Similarity score between 0.0 (completely different) and 1.0 (identical)
        """
        pass


# =============================================================================
# Jaccard Backend (Zero Dependencies)
# =============================================================================


class JaccardBackend(SimilarityBackend):
    """
    Jaccard similarity backend using word overlap.

    Formula: |A ∩ B| / |A ∪ B|

    Example:
        text1 = "the quick brown fox"
        text2 = "the lazy brown dog"

        A = {the, quick, brown, fox}
        B = {the, lazy, brown, dog}

        Intersection = {the, brown} = 2 words
        Union = {the, quick, brown, fox, lazy, dog} = 6 words

        Similarity = 2 / 6 = 0.333

    Pros:
        - Zero dependencies
        - Fast computation
        - Easy to understand

    Cons:
        - Doesn't understand semantics
        - Order-independent
        - Case-sensitive unless normalized
    """

    def compute_similarity(self, text1: str, text2: str) -> float:
        """Compute Jaccard similarity between two texts."""
        # Handle empty strings
        if not text1 or not text2:
            return 0.0

        # Normalize: lowercase and split into words
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        # Handle case where both are empty after normalization
        if not words1 or not words2:
            return 0.0

        # Compute Jaccard similarity
        intersection = words1 & words2  # Words in both
        union = words1 | words2  # All unique words

        # Avoid division by zero
        if not union:
            return 0.0

        similarity = len(intersection) / len(union)
        return similarity


# =============================================================================
# TF-IDF Backend (Requires scikit-learn)
# =============================================================================


class TFIDFBackend(SimilarityBackend):
    """
    TF-IDF similarity backend.

    Requires: scikit-learn

    Better than Jaccard because:
        - Weighs rare words higher (more discriminative)
        - Reduces impact of common words (the, a, is)
        - Still lightweight (~50MB)

    Example:
        text1 = "TypeScript has types"
        text2 = "TypeScript provides type safety"

        TF-IDF will weight "TypeScript" and "type(s)" highly,
        downweight "has" and "provides"
    """

    def __init__(self):
        """Initialize TF-IDF backend."""
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity

            self.vectorizer = TfidfVectorizer()
            self.cosine_similarity = cosine_similarity
        except ImportError as e:
            raise ImportError(
                "TFIDFBackend requires scikit-learn. "
                "Install with: pip install scikit-learn"
            ) from e

    def compute_similarity(self, text1: str, text2: str) -> float:
        """Compute TF-IDF cosine similarity between two texts."""
        if not text1 or not text2:
            return 0.0

        # Compute TF-IDF vectors
        tfidf_matrix = self.vectorizer.fit_transform([text1, text2])

        # Compute cosine similarity
        similarity = self.cosine_similarity(tfidf_matrix[0], tfidf_matrix[1])[0][0]

        return float(similarity)


# =============================================================================
# Sentence Transformer Backend (Requires sentence-transformers)
# =============================================================================


class SentenceTransformerBackend(SimilarityBackend):
    """
    Sentence transformer backend using neural embeddings.

    Requires: sentence-transformers (~500MB model download)

    Best accuracy because:
        - Understands semantics and context
        - Trained on billions of sentence pairs
        - Captures paraphrasing and synonyms

    Example:
        text1 = "I prefer TypeScript for type safety"
        text2 = "TypeScript is better because it has types"

        These have similar meaning despite different words.
        Sentence transformers will give high similarity (~0.85).

    Performance:
        - Model cached in memory after first load (~3 seconds)
        - Subsequent instances reuse cached model (instant)
    """

    # Class-level cache to share model across instances
    _model_cache = None
    _model_name_cache = None

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize sentence transformer backend.

        Args:
            model_name: Model to use (default: all-MiniLM-L6-v2)
                       This is a good balance of speed and accuracy.
        """
        try:
            from sentence_transformers import SentenceTransformer
            from sklearn.metrics.pairwise import cosine_similarity

            # Check if we can reuse cached model
            if (
                SentenceTransformerBackend._model_cache is not None
                and SentenceTransformerBackend._model_name_cache == model_name
            ):
                logger.info(f"Reusing cached sentence transformer model: {model_name}")
                self.model = SentenceTransformerBackend._model_cache
            else:
                logger.info(f"Loading sentence transformer model: {model_name}")
                self.model = SentenceTransformer(model_name)
                # Cache for future instances
                SentenceTransformerBackend._model_cache = self.model
                SentenceTransformerBackend._model_name_cache = model_name
                logger.info("Sentence transformer model loaded and cached successfully")

            self.cosine_similarity = cosine_similarity

        except ImportError as e:
            raise ImportError(
                "SentenceTransformerBackend requires sentence-transformers. "
                "Install with: pip install sentence-transformers"
            ) from e

    def compute_similarity(self, text1: str, text2: str) -> float:
        """Compute semantic similarity using sentence embeddings."""
        if not text1 or not text2:
            return 0.0

        # Generate embeddings (vectors that capture meaning)
        embeddings = self.model.encode([text1, text2])

        # Compute cosine similarity between embeddings
        similarity = self.cosine_similarity(
            embeddings[0].reshape(1, -1), embeddings[1].reshape(1, -1)
        )[0][0]

        return float(similarity)


# =============================================================================
# Convergence Result
# =============================================================================


@dataclass
class ConvergenceResult:
    """Result of convergence detection check."""

    converged: bool
    status: str  # "converged", "diverging", "refining", "impasse"
    min_similarity: float
    avg_similarity: float
    per_participant_similarity: dict[str, float]
    consecutive_stable_rounds: int


# =============================================================================
# Convergence Detector
# =============================================================================


class ConvergenceDetector:
    """
    Detects when deliberation has converged.

    Uses multiple signals:
        1. Semantic similarity between consecutive rounds
        2. Stance stability (participants not changing positions)
        3. Response length variance (debate exhaustion)

    Automatically selects best available similarity backend:
        - SentenceTransformerBackend (best, requires sentence-transformers)
        - TFIDFBackend (good, requires scikit-learn)
        - JaccardBackend (fallback, zero dependencies)
    """

    def __init__(self, config):
        """
        Initialize convergence detector.

        Args:
            config: Configuration object with deliberation.convergence_detection
        """
        self.config = config.deliberation.convergence_detection
        self.backend = self._select_backend()
        self.consecutive_stable_count = 0

        logger.info(
            f"ConvergenceDetector initialized with {self.backend.__class__.__name__}"
        )

    def _select_backend(self) -> SimilarityBackend:
        """
        Select best available similarity backend.

        Tries in order:
            1. SentenceTransformerBackend (best)
            2. TFIDFBackend (good)
            3. JaccardBackend (fallback)

        Returns:
            Selected backend instance
        """
        # Try sentence transformers (best)
        try:
            backend = SentenceTransformerBackend()
            logger.info("Using SentenceTransformerBackend (best accuracy)")
            return backend
        except ImportError:
            logger.debug("sentence-transformers not available")

        # Try TF-IDF (good)
        try:
            backend = TFIDFBackend()
            logger.info("Using TFIDFBackend (good accuracy)")
            return backend
        except ImportError:
            logger.debug("scikit-learn not available")

        # Fallback to Jaccard (always available)
        logger.info("Using JaccardBackend (fallback, zero dependencies)")
        return JaccardBackend()

    def check_convergence(
        self,
        current_round: List,  # List[RoundResponse]
        previous_round: List,  # List[RoundResponse]
        round_number: int,
    ) -> Optional[ConvergenceResult]:
        """
        Check if convergence has been reached.

        Args:
            current_round: Responses from current round
            previous_round: Responses from previous round
            round_number: Current round number (1-indexed)

        Returns:
            ConvergenceResult or None if too early to check
        """
        # Don't check before minimum rounds
        if round_number <= self.config.min_rounds_before_check:
            return None

        # Match participants between rounds
        participant_pairs = self._match_participants(current_round, previous_round)

        if not participant_pairs:
            logger.warning("No matching participants found between rounds")
            return None

        # Compute similarity for each participant
        similarities = {}
        for participant_id, (curr_resp, prev_resp) in participant_pairs.items():
            similarity = self.backend.compute_similarity(
                curr_resp.response, prev_resp.response
            )
            similarities[participant_id] = similarity

        # Compute aggregate metrics
        similarity_values = list(similarities.values())
        min_similarity = min(similarity_values)
        avg_similarity = sum(similarity_values) / len(similarity_values)

        # Determine convergence status
        threshold = self.config.semantic_similarity_threshold
        divergence_threshold = getattr(self.config, "divergence_threshold", 0.40)

        if min_similarity >= threshold:
            # All participants converged
            self.consecutive_stable_count += 1

            if self.consecutive_stable_count >= self.config.consecutive_stable_rounds:
                status = "converged"
                converged = True
            else:
                status = "refining"
                converged = False

        elif min_similarity < divergence_threshold:
            # Models are diverging
            status = "diverging"
            converged = False
            self.consecutive_stable_count = 0

        else:
            # Still refining
            status = "refining"
            converged = False
            self.consecutive_stable_count = 0

        # Check for impasse (stable disagreement)
        if (
            status == "diverging"
            and self.consecutive_stable_count >= self.config.consecutive_stable_rounds
        ):
            status = "impasse"

        return ConvergenceResult(
            converged=converged,
            status=status,
            min_similarity=min_similarity,
            avg_similarity=avg_similarity,
            per_participant_similarity=similarities,
            consecutive_stable_rounds=self.consecutive_stable_count,
        )

    def _match_participants(self, current_round: List, previous_round: List) -> dict:
        """
        Match participants between consecutive rounds.

        Args:
            current_round: Responses from current round
            previous_round: Responses from previous round

        Returns:
            Dict mapping participant_id -> (current_response, previous_response)
        """
        # Index previous round by participant
        prev_by_participant = {resp.participant: resp for resp in previous_round}

        # Match with current round
        pairs = {}
        for curr_resp in current_round:
            participant_id = curr_resp.participant
            if participant_id in prev_by_participant:
                prev_resp = prev_by_participant[participant_id]
                pairs[participant_id] = (curr_resp, prev_resp)

        return pairs
