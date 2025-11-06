"""Question similarity detection for Decision Graph Memory."""
import logging
from typing import Dict, List, Optional, Tuple

from deliberation.convergence import (JaccardBackend,
                                      SentenceTransformerBackend,
                                      SimilarityBackend, TFIDFBackend)

logger = logging.getLogger(__name__)


class QuestionSimilarityDetector:
    """
    Detects semantic similarity between questions.

    Reuses the convergence detection backend infrastructure with automatic
    fallback chain: SentenceTransformer → TF-IDF → Jaccard.

    Example:
        >>> detector = QuestionSimilarityDetector()
        >>> score = detector.compute_similarity(
        ...     "What is the capital of France?",
        ...     "What is France's capital city?"
        ... )
        >>> print(f"Similarity: {score:.2f}")  # High score (e.g., 0.85)

        >>> candidates = [
        ...     ("q1", "What is the capital of France?"),
        ...     ("q2", "How do I install Python?"),
        ...     ("q3", "What is France's capital city?"),
        ... ]
        >>> similar = detector.find_similar(
        ...     "What is the capital of France?",
        ...     candidates,
        ...     threshold=0.7
        ... )
        >>> # Returns: [{"id": "q1", "question": "...", "score": 1.0},
        ...             {"id": "q3", "question": "...", "score": 0.85}]
    """

    def __init__(self, backend: Optional[SimilarityBackend] = None):
        """
        Initialize question similarity detector.

        Args:
            backend: Optional similarity backend to use. If None, automatically
                    selects best available backend using fallback chain.
        """
        if backend is not None:
            self.backend = backend
            logger.info(f"Using provided backend: {backend.__class__.__name__}")
        else:
            self.backend = self._select_backend()
            logger.info(
                f"QuestionSimilarityDetector initialized with {self.backend.__class__.__name__}"
            )

    def _select_backend(self) -> SimilarityBackend:
        """
        Select best available similarity backend.

        Tries in order:
            1. SentenceTransformerBackend (best - semantic understanding)
            2. TFIDFBackend (good - weighted word matching)
            3. JaccardBackend (fallback - simple word overlap)

        Returns:
            Selected backend instance
        """
        # Try sentence transformers (best)
        try:
            backend = SentenceTransformerBackend()
            logger.info("Using SentenceTransformerBackend (best semantic accuracy)")
            return backend
        except ImportError:
            logger.debug("sentence-transformers not available, trying TF-IDF")

        # Try TF-IDF (good)
        try:
            backend = TFIDFBackend()
            logger.info("Using TFIDFBackend (good weighted matching)")
            return backend
        except ImportError:
            logger.debug("scikit-learn not available, falling back to Jaccard")

        # Fallback to Jaccard (always available)
        logger.info("Using JaccardBackend (fallback, zero dependencies)")
        return JaccardBackend()

    def compute_similarity(self, question1: str, question2: str) -> float:
        """
        Compute semantic similarity between two questions.

        Args:
            question1: First question text
            question2: Second question text

        Returns:
            Similarity score between 0.0 (completely different) and 1.0 (identical)

        Example:
            >>> detector = QuestionSimilarityDetector()
            >>> score = detector.compute_similarity(
            ...     "What is Python?",
            ...     "What is Python programming language?"
            ... )
            >>> print(score)  # e.g., 0.82
        """
        # Handle edge cases
        if not question1 or not question2:
            logger.warning("Empty question(s) provided to compute_similarity")
            return 0.0

        # Normalize whitespace
        question1 = " ".join(question1.split())
        question2 = " ".join(question2.split())

        # Compute similarity using backend
        try:
            similarity = self.backend.compute_similarity(question1, question2)
            return float(similarity)
        except Exception as e:
            logger.error(f"Error computing similarity: {e}", exc_info=True)
            return 0.0

    def find_similar(
        self,
        query_question: str,
        candidate_questions: List[Tuple[str, str]],
        threshold: float = 0.7,
    ) -> List[Dict]:
        """
        Find similar questions from a list of candidates.

        Args:
            query_question: Question to find matches for
            candidate_questions: List of (id, question_text) tuples to search
            threshold: Minimum similarity score (0.0-1.0). Questions with scores
                      below this threshold are excluded from results.

        Returns:
            List of dicts with keys: {id, question, score}
            Sorted by score descending (highest similarity first)

        Example:
            >>> detector = QuestionSimilarityDetector()
            >>> candidates = [
            ...     ("q1", "What is the capital of France?"),
            ...     ("q2", "How do I install Python?"),
            ...     ("q3", "What is France's capital city?"),
            ...     ("q4", "What is the weather in Paris?"),
            ... ]
            >>> similar = detector.find_similar(
            ...     "What is the capital of France?",
            ...     candidates,
            ...     threshold=0.7
            ... )
            >>> for match in similar:
            ...     print(f"{match['id']}: {match['score']:.2f}")
            # Output:
            # q1: 1.00
            # q3: 0.85
        """
        # Validate threshold
        if not (0.0 <= threshold <= 1.0):
            logger.warning(f"Invalid threshold {threshold}, clamping to [0.0, 1.0]")
            threshold = max(0.0, min(1.0, threshold))

        # Handle edge cases
        if not query_question:
            logger.warning("Empty query_question provided to find_similar")
            return []

        if not candidate_questions:
            logger.debug("Empty candidate_questions list provided to find_similar")
            return []

        # Normalize query question
        query_question = " ".join(query_question.split())

        # Compute similarity for each candidate
        results = []
        for question_id, question_text in candidate_questions:
            # Skip empty candidates
            if not question_text:
                logger.warning(
                    f"Skipping empty candidate question with id: {question_id}"
                )
                continue

            # Compute similarity
            try:
                score = self.compute_similarity(query_question, question_text)

                # Filter by threshold
                if score >= threshold:
                    results.append(
                        {"id": question_id, "question": question_text, "score": score}
                    )
            except Exception as e:
                logger.error(
                    f"Error processing candidate {question_id}: {e}", exc_info=True
                )
                continue

        # Sort by score descending (highest similarity first)
        results.sort(key=lambda x: x["score"], reverse=True)

        logger.debug(
            f"Found {len(results)} similar questions above threshold {threshold} "
            f"out of {len(candidate_questions)} candidates"
        )

        return results
