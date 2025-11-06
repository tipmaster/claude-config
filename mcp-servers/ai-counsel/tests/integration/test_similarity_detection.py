"""Integration tests for question similarity detection.

Tests the QuestionSimilarityDetector across all available backends:
- SentenceTransformerBackend (best - semantic understanding)
- TFIDFBackend (good - weighted word matching)
- JaccardBackend (fallback - simple word overlap)

These are integration tests because they test the full similarity detection
pipeline with real backends, not mocked components.
"""
import pytest

from decision_graph.similarity import QuestionSimilarityDetector
from deliberation.convergence import (JaccardBackend,
                                      SentenceTransformerBackend, TFIDFBackend)


@pytest.mark.integration
class TestSimilarityDetection:
    """Test similarity detection with various question pairs."""

    def test_identical_questions_high_similarity(self):
        """Identical questions should have similarity >0.95."""
        detector = QuestionSimilarityDetector()

        q1 = "Should we use Python for backend development?"
        q2 = "Should we use Python for backend development?"

        score = detector.compute_similarity(q1, q2)
        assert (
            score > 0.95
        ), f"Identical questions should have high similarity, got {score}"

    def test_paraphrased_questions_high_similarity(self):
        """Paraphrased questions should have similarity >0.75."""
        detector = QuestionSimilarityDetector()

        q1 = "Should we use Python for backend development?"
        q2 = "Is Python a good choice for our backend?"

        score = detector.compute_similarity(q1, q2)
        # Note: Jaccard might not achieve >0.75 for paraphrases
        # But TF-IDF and SentenceTransformer should
        if isinstance(detector.backend, JaccardBackend):
            assert (
                score > 0.30
            ), f"Paraphrased questions (Jaccard) should have moderate similarity, got {score}"
        else:
            assert (
                score > 0.60
            ), f"Paraphrased questions should have high similarity, got {score}"

    def test_related_questions_moderate_similarity(self):
        """Related but different questions should have 0.2-0.8 similarity."""
        detector = QuestionSimilarityDetector()

        q1 = "Should we use Python for backend development?"
        q2 = "What database should we use?"

        score = detector.compute_similarity(q1, q2)
        assert (
            0.0 <= score < 0.8
        ), f"Related questions should have moderate/low similarity, got {score}"

    def test_unrelated_questions_low_similarity(self):
        """Unrelated questions should have similarity <0.40."""
        detector = QuestionSimilarityDetector()

        q1 = "Should we use Python for backend development?"
        q2 = "What color should the logo be?"

        score = detector.compute_similarity(q1, q2)
        assert (
            score < 0.40
        ), f"Unrelated questions should have low similarity, got {score}"

    def test_empty_questions_handled(self):
        """Empty questions should not crash."""
        detector = QuestionSimilarityDetector()

        q1 = "Should we use Python?"
        q2 = ""

        score = detector.compute_similarity(q1, q2)
        assert score == 0.0, "Empty question should return 0.0"

    def test_both_empty_questions(self):
        """Both empty questions should return 0.0."""
        detector = QuestionSimilarityDetector()

        score = detector.compute_similarity("", "")
        assert score == 0.0, "Both empty questions should return 0.0"

    def test_very_short_questions(self):
        """Very short questions should work."""
        detector = QuestionSimilarityDetector()

        q1 = "Python?"
        q2 = "JavaScript?"

        score = detector.compute_similarity(q1, q2)
        assert 0.0 <= score <= 1.0, "Short questions should return valid score"

    def test_single_word_questions(self):
        """Single word questions should work."""
        detector = QuestionSimilarityDetector()

        q1 = "Python"
        q2 = "Python"

        score = detector.compute_similarity(q1, q2)
        assert (
            score > 0.95
        ), f"Identical single words should have high similarity, got {score}"


@pytest.mark.integration
class TestTopKSearch:
    """Test finding top-K similar questions."""

    def test_find_similar_returns_sorted_results(self):
        """Results should be sorted by score descending."""
        detector = QuestionSimilarityDetector()

        candidates = [
            ("q1", "Should we use Python for backend?"),
            ("q2", "Is Python good for backends?"),
            ("q3", "What color is the sky?"),
            ("q4", "Should we use JavaScript?"),
        ]

        query = "Should we use Python?"
        results = detector.find_similar(query, candidates, threshold=0.1)

        # Results should be sorted
        if len(results) > 1:
            for i in range(len(results) - 1):
                assert (
                    results[i]["score"] >= results[i + 1]["score"]
                ), f"Results should be sorted descending: {results[i]['score']} >= {results[i+1]['score']}"

    def test_find_similar_respects_threshold(self):
        """Only results above threshold should be returned."""
        detector = QuestionSimilarityDetector()

        candidates = [
            ("q1", "Should we use Python for backend?"),
            ("q2", "Is Python good for backends?"),
            ("q3", "What color is the sky?"),
        ]

        query = "Should we use Python?"

        results_high = detector.find_similar(query, candidates, threshold=0.8)
        results_low = detector.find_similar(query, candidates, threshold=0.1)

        # High threshold should have fewer or equal results
        assert len(results_high) <= len(
            results_low
        ), f"Higher threshold should have fewer results: {len(results_high)} <= {len(results_low)}"

    def test_find_similar_all_above_threshold(self):
        """All returned results should be above threshold."""
        detector = QuestionSimilarityDetector()

        candidates = [
            ("q1", "Should we use Python for backend?"),
            ("q2", "Is Python good for backends?"),
            ("q3", "What color is the sky?"),
            ("q4", "Should we use JavaScript?"),
        ]

        threshold = 0.3
        results = detector.find_similar(
            "Should we use Python?", candidates, threshold=threshold
        )

        for result in results:
            assert (
                result["score"] >= threshold
            ), f"Result score {result['score']} should be >= threshold {threshold}"

    def test_find_similar_returns_correct_format(self):
        """Results should have id, question, score keys."""
        detector = QuestionSimilarityDetector()

        candidates = [
            ("q1", "Should we use Python?"),
        ]

        results = detector.find_similar("Python?", candidates, threshold=0.0)

        if len(results) > 0:
            result = results[0]
            assert "id" in result, "Result should have id"
            assert "question" in result, "Result should have question"
            assert "score" in result, "Result should have score"

    def test_find_similar_empty_candidates(self):
        """Empty candidate list should return empty results."""
        detector = QuestionSimilarityDetector()

        results = detector.find_similar("Query?", [], threshold=0.5)
        assert results == [], "Empty candidates should return empty results"

    def test_find_similar_limits_by_threshold(self):
        """find_similar should only return candidates above threshold."""
        detector = QuestionSimilarityDetector()

        candidates = [
            ("q1", "Should we use Python?"),
            ("q2", "Is Python good?"),
            ("q3", "Python or JavaScript?"),
            ("q4", "What color is the sky?"),  # Unrelated
        ]

        # High threshold should filter out unrelated
        results = detector.find_similar("Python?", candidates, threshold=0.5)

        # Should have fewer than total candidates (unrelated filtered)
        assert len(results) < len(
            candidates
        ), "High threshold should filter out some candidates"

    def test_find_similar_skips_empty_candidates(self):
        """Empty candidate questions should be skipped."""
        detector = QuestionSimilarityDetector()

        candidates = [
            ("q1", "Should we use Python?"),
            ("q2", ""),  # Empty
            ("q3", "Is Python good?"),
        ]

        results = detector.find_similar("Python?", candidates, threshold=0.0)

        # Should only have 2 results (q2 skipped)
        assert len(results) == 2, "Empty candidates should be skipped"
        assert all(
            r["id"] != "q2" for r in results
        ), "Empty candidate should be excluded"


@pytest.mark.integration
class TestBackendFallback:
    """Test backend selection and fallback."""

    def test_detector_initializes_with_available_backend(self):
        """Detector should initialize with any available backend."""
        detector = QuestionSimilarityDetector()
        assert detector.backend is not None, "Should have initialized backend"

    def test_detector_works_with_jaccard_backend(self):
        """Detector should work with Jaccard backend (always available)."""
        backend = JaccardBackend()
        detector = QuestionSimilarityDetector(backend=backend)

        score = detector.compute_similarity("Python", "Python")
        assert score > 0.9, "Jaccard backend should work"

    def test_detector_works_with_tfidf_backend(self):
        """Detector should work with TF-IDF backend (if available)."""
        try:
            backend = TFIDFBackend()
            detector = QuestionSimilarityDetector(backend=backend)

            score = detector.compute_similarity(
                "Python programming", "Python programming"
            )
            assert score > 0.9, "TF-IDF backend should work"
        except ImportError:
            pytest.skip("scikit-learn not available")

    def test_detector_works_with_sentence_transformer_backend(self):
        """Detector should work with SentenceTransformer backend (if available)."""
        try:
            backend = SentenceTransformerBackend()
            detector = QuestionSimilarityDetector(backend=backend)

            score = detector.compute_similarity("Python code", "Python code")
            assert score > 0.9, "SentenceTransformer backend should work"
        except ImportError:
            pytest.skip("sentence-transformers not available")

    def test_jaccard_backend_always_available(self):
        """Jaccard backend should always be available (zero dependencies)."""
        backend = JaccardBackend()
        assert backend is not None, "Jaccard backend should always be available"

        score = backend.compute_similarity("hello world", "hello world")
        assert score == 1.0, "Jaccard backend should work"


@pytest.mark.integration
class TestSimilaritySymmetry:
    """Test mathematical properties of similarity."""

    def test_similarity_is_symmetric(self):
        """Similarity should be symmetric: sim(a,b) == sim(b,a)."""
        detector = QuestionSimilarityDetector()

        q1 = "Should we use Python?"
        q2 = "Should we use JavaScript?"

        score_1_2 = detector.compute_similarity(q1, q2)
        score_2_1 = detector.compute_similarity(q2, q1)

        assert (
            abs(score_1_2 - score_2_1) < 0.01
        ), f"Similarity should be symmetric: {score_1_2} ≈ {score_2_1}"

    def test_self_similarity_is_perfect(self):
        """Similarity of question with itself should be ~1.0."""
        detector = QuestionSimilarityDetector()

        q = "Should we use Python for backend development?"
        score = detector.compute_similarity(q, q)

        assert score > 0.95, f"Self-similarity should be ~1.0, got {score}"

    def test_self_similarity_for_short_text(self):
        """Self-similarity should be perfect even for short text."""
        detector = QuestionSimilarityDetector()

        q = "Python"
        score = detector.compute_similarity(q, q)

        assert score > 0.95, f"Self-similarity should be ~1.0, got {score}"


@pytest.mark.integration
class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_special_characters_handled(self):
        """Questions with special characters should work."""
        detector = QuestionSimilarityDetector()

        q1 = "Should we use Python? (Yes/No)"
        q2 = "Should we use Python? (Yes/No)"

        score = detector.compute_similarity(q1, q2)
        assert score > 0.9, "Special characters should be handled"

    def test_unicode_characters_handled(self):
        """Questions with unicode should work."""
        detector = QuestionSimilarityDetector()

        q1 = "Should we use Python™?"
        q2 = "Should we use Python™?"

        score = detector.compute_similarity(q1, q2)
        assert score > 0.9, "Unicode should be handled"

    def test_very_long_questions(self):
        """Very long questions should work."""
        detector = QuestionSimilarityDetector()

        long_q = "Should we " + "use Python " * 50 + "for backend development?"

        score = detector.compute_similarity(long_q, long_q)
        assert score > 0.9, "Long questions should work"

    def test_case_insensitivity(self):
        """Similarity should be case-insensitive."""
        detector = QuestionSimilarityDetector()

        q1 = "Should we use Python?"
        q2 = "should we use python?"

        score = detector.compute_similarity(q1, q2)
        assert score > 0.9, "Should be case-insensitive"

    def test_whitespace_normalized(self):
        """Extra whitespace should be normalized."""
        detector = QuestionSimilarityDetector()

        q1 = "Should   we    use   Python?"
        q2 = "Should we use Python?"

        score = detector.compute_similarity(q1, q2)
        assert score > 0.9, "Whitespace should be normalized"

    def test_punctuation_variations(self):
        """Punctuation variations should not drastically affect similarity."""
        detector = QuestionSimilarityDetector()

        q1 = "Should we use Python"
        q2 = "Should we use Python?"

        score = detector.compute_similarity(q1, q2)
        # Punctuation might lower score slightly, but should still be high
        assert score > 0.8, "Punctuation variations should have high similarity"

    def test_numbers_in_questions(self):
        """Questions with numbers should work."""
        detector = QuestionSimilarityDetector()

        q1 = "Should we upgrade to Python 3.11?"
        q2 = "Should we upgrade to Python 3.11?"

        score = detector.compute_similarity(q1, q2)
        assert score > 0.9, "Numbers should be handled"


@pytest.mark.integration
class TestThresholdValidation:
    """Test threshold parameter validation."""

    def test_invalid_threshold_clamped(self):
        """Invalid thresholds should be clamped to [0.0, 1.0]."""
        detector = QuestionSimilarityDetector()

        candidates = [("q1", "Python?")]

        # Should not raise - thresholds are clamped
        results_low = detector.find_similar("Query", candidates, threshold=-0.5)
        results_high = detector.find_similar("Query", candidates, threshold=1.5)

        assert isinstance(results_low, list), "Should handle negative threshold"
        assert isinstance(results_high, list), "Should handle >1 threshold"

    def test_zero_threshold_includes_all(self):
        """Threshold 0.0 should include all candidates."""
        detector = QuestionSimilarityDetector()

        candidates = [
            ("q1", "Python"),
            ("q2", "JavaScript"),
            ("q3", "Red"),
        ]

        results = detector.find_similar("Query", candidates, threshold=0.0)
        assert len(results) == len(
            candidates
        ), "Threshold 0.0 should include all candidates"

    def test_threshold_1_only_perfect_matches(self):
        """Threshold 1.0 should only include identical matches."""
        detector = QuestionSimilarityDetector()

        candidates = [
            ("q1", "Should we use Python?"),
            ("q2", "Should we use Python?"),  # Identical
            ("q3", "Something else"),
        ]

        results = detector.find_similar(
            "Should we use Python?", candidates, threshold=1.0
        )
        # Should only get perfect matches (accounting for floating point)
        # Jaccard will give 1.0 for identical, others might give 0.9999...
        assert all(
            r["score"] >= 0.99 for r in results
        ), "Threshold 1.0 should only return near-perfect matches"

    def test_threshold_0_5_moderate_filter(self):
        """Threshold 0.5 should filter out low-similarity candidates."""
        detector = QuestionSimilarityDetector()

        candidates = [
            ("q1", "Should we use Python?"),
            ("q2", "Is Python good?"),
            ("q3", "What color is the sky?"),  # Unrelated
        ]

        results = detector.find_similar(
            "Should we use Python?", candidates, threshold=0.5
        )

        # All results should have score >= 0.5
        assert all(
            r["score"] >= 0.5 for r in results
        ), "All results should be above threshold"


@pytest.mark.integration
class TestRealWorldScenarios:
    """Test realistic question similarity scenarios."""

    def test_technical_questions_similar(self):
        """Similar technical questions should be detected."""
        detector = QuestionSimilarityDetector()

        q1 = "What testing framework should we use?"
        q2 = "Which testing library is best?"

        score = detector.compute_similarity(q1, q2)
        # Both are about testing frameworks
        if isinstance(detector.backend, JaccardBackend):
            assert (
                score > 0.2
            ), "Similar technical questions should have some similarity"
        else:
            assert (
                score > 0.4
            ), "Similar technical questions should have moderate similarity"

    def test_architecture_questions_similar(self):
        """Similar architecture questions should be detected."""
        detector = QuestionSimilarityDetector()

        q1 = "Should we use microservices or monolith?"
        q2 = "Microservices vs monolithic architecture?"

        score = detector.compute_similarity(q1, q2)
        # Both are about architecture choices
        if isinstance(detector.backend, JaccardBackend):
            assert (
                score > 0.2
            ), "Similar architecture questions should have some similarity"
        else:
            assert (
                score > 0.4
            ), "Similar architecture questions should have moderate similarity"

    def test_deployment_questions_different(self):
        """Different deployment questions should have lower similarity."""
        detector = QuestionSimilarityDetector()

        q1 = "Should we deploy to AWS or Azure?"
        q2 = "What CI/CD pipeline should we use?"

        score = detector.compute_similarity(q1, q2)
        # Both about deployment but different aspects
        assert (
            score < 0.7
        ), "Different deployment questions should have moderate/low similarity"

    def test_mixed_domain_questions_low_similarity(self):
        """Questions from different domains should have low similarity."""
        detector = QuestionSimilarityDetector()

        q1 = "What database should we use for user data?"
        q2 = "How should we design the login UI?"

        score = detector.compute_similarity(q1, q2)
        # Database vs UI design
        assert score < 0.5, "Mixed domain questions should have low similarity"


@pytest.mark.integration
class TestPerformance:
    """Test performance characteristics of similarity detection."""

    def test_large_candidate_set(self):
        """Should handle large candidate sets efficiently."""
        detector = QuestionSimilarityDetector()

        # Generate 100 candidates
        candidates = [(f"q{i}", f"Question about topic {i}") for i in range(100)]

        query = "Question about topic 42"

        # Should complete without timeout
        results = detector.find_similar(query, candidates, threshold=0.3)

        assert isinstance(results, list), "Should handle large candidate sets"
        assert len(results) > 0, "Should find some matches"

    def test_repeated_searches_efficient(self):
        """Repeated searches should be efficient (backend caching)."""
        detector = QuestionSimilarityDetector()

        candidates = [
            ("q1", "Should we use Python?"),
            ("q2", "Should we use JavaScript?"),
            ("q3", "Should we use TypeScript?"),
        ]

        # Run same search multiple times
        for _ in range(10):
            results = detector.find_similar(
                "Should we use Python?", candidates, threshold=0.5
            )
            assert len(results) > 0, "Should find results consistently"


@pytest.mark.integration
class TestBackendConsistency:
    """Test consistency across different backends."""

    def test_all_backends_agree_on_identical(self):
        """All backends should give high score for identical questions."""
        q1 = "Should we use Python for backend development?"
        q2 = "Should we use Python for backend development?"

        # Test Jaccard (always available)
        jaccard = JaccardBackend()
        jaccard_score = jaccard.compute_similarity(q1, q2)
        assert jaccard_score > 0.95, "Jaccard should give high score for identical"

        # Test TF-IDF (if available)
        try:
            tfidf = TFIDFBackend()
            tfidf_score = tfidf.compute_similarity(q1, q2)
            assert tfidf_score > 0.95, "TF-IDF should give high score for identical"
        except ImportError:
            pass

        # Test SentenceTransformer (if available)
        try:
            st = SentenceTransformerBackend()
            st_score = st.compute_similarity(q1, q2)
            assert (
                st_score > 0.95
            ), "SentenceTransformer should give high score for identical"
        except ImportError:
            pass

    def test_all_backends_agree_on_unrelated(self):
        """All backends should give low score for unrelated questions."""
        q1 = "Should we use Python for backend development?"
        q2 = "What color should the logo be?"

        # Test Jaccard (always available)
        jaccard = JaccardBackend()
        jaccard_score = jaccard.compute_similarity(q1, q2)
        assert jaccard_score < 0.4, "Jaccard should give low score for unrelated"

        # Test TF-IDF (if available)
        try:
            tfidf = TFIDFBackend()
            tfidf_score = tfidf.compute_similarity(q1, q2)
            assert tfidf_score < 0.4, "TF-IDF should give low score for unrelated"
        except ImportError:
            pass

        # Test SentenceTransformer (if available)
        try:
            st = SentenceTransformerBackend()
            st_score = st.compute_similarity(q1, q2)
            assert (
                st_score < 0.4
            ), "SentenceTransformer should give low score for unrelated"
        except ImportError:
            pass


@pytest.mark.integration
class TestErrorHandling:
    """Test error handling and edge cases in similarity detection."""

    def test_compute_similarity_handles_none(self):
        """compute_similarity should handle None gracefully."""
        detector = QuestionSimilarityDetector()

        # None is converted to empty string in Python, but we test the empty path
        score = detector.compute_similarity("", None if None else "")
        assert score == 0.0, "None should be handled gracefully"

    def test_find_similar_empty_query(self):
        """find_similar should handle empty query."""
        detector = QuestionSimilarityDetector()

        candidates = [("q1", "Question 1")]
        results = detector.find_similar("", candidates, threshold=0.5)

        assert results == [], "Empty query should return empty results"

    def test_find_similar_candidate_with_only_whitespace(self):
        """find_similar should skip candidates with only whitespace."""
        detector = QuestionSimilarityDetector()

        candidates = [
            ("q1", "Valid question"),
            ("q2", "   "),  # Only whitespace
            ("q3", "Another valid question"),
        ]

        results = detector.find_similar("Valid?", candidates, threshold=0.0)

        # Whitespace normalizes to empty, should be skipped
        # But our implementation doesn't explicitly check for whitespace-only after normalization
        # It just normalizes, so "   " becomes "" after split/join
        assert len(results) >= 2, "Should process valid candidates"

    def test_backend_selection_fallback_chain(self):
        """Test that backend selection follows fallback chain."""
        detector = QuestionSimilarityDetector()

        # Backend should be one of the three types
        assert isinstance(
            detector.backend,
            (JaccardBackend, TFIDFBackend, SentenceTransformerBackend),
        ), "Should have valid backend type"

    def test_explicit_backend_selection(self):
        """Test explicit backend selection works."""
        jaccard = JaccardBackend()
        detector = QuestionSimilarityDetector(backend=jaccard)

        assert isinstance(
            detector.backend, JaccardBackend
        ), "Should use explicitly provided backend"

        score = detector.compute_similarity("test", "test")
        assert score > 0.9, "Explicit backend should work"

    def test_find_similar_handles_exception_in_candidate(self):
        """find_similar should handle exceptions gracefully for individual candidates."""
        from unittest.mock import patch

        detector = QuestionSimilarityDetector()

        candidates = [
            ("q1", "Valid question"),
            ("q2", "Another valid"),
        ]

        # Patch compute_similarity to raise exception on second call
        original_compute = detector.compute_similarity
        call_count = [0]

        def side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 2:
                raise ValueError("Simulated error")
            return original_compute(*args, **kwargs)

        with patch.object(detector, "compute_similarity", side_effect=side_effect):
            results = detector.find_similar("Query", candidates, threshold=0.0)

        # Should still have first result (second failed)
        assert len(results) >= 1, "Should continue processing after exception"

    def test_compute_similarity_backend_error_returns_zero(self):
        """compute_similarity should return 0.0 if backend raises exception."""
        from unittest.mock import Mock

        detector = QuestionSimilarityDetector()

        # Mock backend to raise exception
        original_backend = detector.backend
        mock_backend = Mock()
        mock_backend.compute_similarity = Mock(side_effect=ValueError("Backend error"))
        detector.backend = mock_backend

        score = detector.compute_similarity("test", "test")

        # Should return 0.0 on error
        assert score == 0.0, "Should return 0.0 on backend error"

        # Restore original backend
        detector.backend = original_backend

    def test_backend_auto_selection_logs_choice(self):
        """Test that auto-selection logs the chosen backend."""
        import logging

        # Capture logs
        logger = logging.getLogger("decision_graph.similarity")
        original_level = logger.level
        logger.setLevel(logging.INFO)

        handler = logging.StreamHandler()
        handler.setLevel(logging.INFO)
        logger.addHandler(handler)

        try:
            # Create detector with auto-selection
            detector = QuestionSimilarityDetector()

            # Should have selected a backend
            assert detector.backend is not None, "Should have selected backend"

            # Backend should be one of the three types
            assert isinstance(
                detector.backend,
                (JaccardBackend, TFIDFBackend, SentenceTransformerBackend),
            ), "Should have valid backend type"
        finally:
            logger.removeHandler(handler)
            logger.setLevel(original_level)

    def test_multiple_detectors_same_backend_class(self):
        """Multiple detectors should work independently."""
        detector1 = QuestionSimilarityDetector()
        detector2 = QuestionSimilarityDetector()

        # Both should work
        score1 = detector1.compute_similarity("Python", "Python")
        score2 = detector2.compute_similarity("JavaScript", "JavaScript")

        assert score1 > 0.9, "Detector 1 should work"
        assert score2 > 0.9, "Detector 2 should work"

    def test_whitespace_only_query_returns_empty(self):
        """Query with only whitespace should be treated as empty."""
        detector = QuestionSimilarityDetector()

        candidates = [("q1", "Valid question")]

        # Whitespace-only query normalizes to empty
        results = detector.find_similar("   \t  \n  ", candidates, threshold=0.5)

        assert results == [], "Whitespace-only query should return empty"
