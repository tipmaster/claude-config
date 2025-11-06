"""Comprehensive benchmark suite for local models in AI Counsel."""

import asyncio
import time

import pytest

from models.schema import DeliberateRequest, Participant
from tests.benchmark.conftest import make_participants


pytestmark = [
    pytest.mark.benchmark,
    pytest.mark.local_model,
    pytest.mark.slow,
]


class TestLocalModelBenchmark:
    """Benchmark suite for local model performance."""

    @pytest.fixture
    def legal_questions(self):
        """Sample legal questions for testing."""
        return [
            {
                "question": """
                Should a small business LLC adopt an employee handbook for legal compliance?
                
                Consider:
                1. Legal liability protection
                2. Employment law compliance  
                3. Company culture establishment
                4. Administrative overhead
                """,
                "context": "Small tech startup with 5 employees, California jurisdiction",
                "expected_topics": ["employment law", "compliance", "liability"]
            },
            {
                "question": """
                What are the key considerations for drafting a remote work policy?
                
                Address:
                1. Tax implications across states
                2. Data security requirements
                3. Workers' classification
                4. Time zone coordination
                """,
                "context": "Software company transitioning to hybrid model",
                "expected_topics": ["remote work", "tax", "data security", "employment"]
            }
        ]

    @pytest.mark.asyncio
    async def test_ollama_performance_benchmark(self, engine, legal_questions):
        """Benchmark Ollama model performance metrics."""
        print("\n" + "="*60)
        print("OLLAMA PERFORMANCE BENCHMARK - xingyaow/codeact-agent-mistral")
        print("="*60)
        
        participants = make_participants("ollama", "xingyaow/codeact-agent-mistral")
        metrics = []
        
        for i, question_data in enumerate(legal_questions, 1):
            print(f"\n--- Test Case {i}: {question_data['context']} ---")
            
            request = DeliberateRequest(
                question=question_data["question"],
                participants=participants,
                rounds=1,  # Single round for performance testing
                context=question_data["context"],
                working_directory="/tmp",)
            
            # Measure performance
            start_time = time.time()
            result = await engine.execute(request)
            duration = time.time() - start_time
            
            # Collect metrics
            # Check if convergence reached (any of these statuses indicates consensus)
            convergence_statuses = {"converged", "unanimous_consensus", "majority_decision"}
            consensus_reached = (
                result.convergence_info and 
                result.convergence_info.status in convergence_statuses
            )
            metric = {
                "test_case": i,
                "duration": duration,
                "consensus_reached": consensus_reached,
                "response_length": len(result.summary.consensus) if result.summary and result.summary.consensus else 0,
                "transcript_words": len(" ".join([r.response for r in result.full_debate]).split()) if result.full_debate else 0
            }
            metrics.append(metric)
            
            print(f"✅ Duration: {duration:.2f}s")
            print(f"📝 Consensus length: {metric['response_length']} chars")
            print(f"🔄 Convergence: {result.convergence_info.status if result.convergence_info else 'N/A'}")
            print("💰 Cost: $0.00 (local inference)")
        
        # Performance analysis
        avg_duration = sum(m["duration"] for m in metrics) / len(metrics)
        convergence_rate = sum(m["consensus_reached"] for m in metrics) / len(metrics)
        
        print("\n📊 OLLAMA BENCHMARK RESULTS:")
        print(f"   • Average response time: {avg_duration:.2f}s")
        print(f"   • Convergence rate: {convergence_rate:.1%}")
        print("   • Total cost: $0.00")
        
        # Assertions for benchmark quality
        assert avg_duration < 120.0, f"Response too slow: {avg_duration:.2f}s"
        assert convergence_rate >= 0.5, f"Poor convergence: {convergence_rate:.1%}"
        
        return metrics

    @pytest.mark.asyncio 
    async def test_lm_studio_performance_benchmark(self, engine, legal_questions):
        """Benchmark LM Studio model performance metrics."""
        print("\n" + "="*60)
        print("LM STUDIO PERFORMANCE BENCHMARK")
        print("="*60)
        
        participants_template = make_participants("lmstudio", "llama-3-groq-8b-tool-use")
        metrics = []
        
        for i, question_data in enumerate(legal_questions, 1):
            print(f"\n--- Test Case {i}: {question_data['context']} ---")
            
            # Deliberation requires at least 2 participants
            participants = list(participants_template)
            request = DeliberateRequest(
                question=question_data["question"],
                participants=participants,
                rounds=1,
                context=question_data["context"],
                working_directory="/tmp",)
            
            start_time = time.time()
            result = await engine.execute(request)
            duration = time.time() - start_time
            
            # Check if convergence reached (any of these statuses indicates consensus)
            convergence_statuses = {"converged", "unanimous_consensus", "majority_decision"}
            consensus_reached = (
                result.convergence_info and 
                result.convergence_info.status in convergence_statuses
            )
            metric = {
                "test_case": i,
                "duration": duration,
                "consensus_reached": consensus_reached,
                "response_length": len(result.summary.consensus) if result.summary and result.summary.consensus else 0,
            }
            metrics.append(metric)
            
            print(f"✅ Duration: {duration:.2f}s")
            print(f"📝 Response length: {metric['response_length']} chars")
            print(f"🔄 Convergence: {result.convergence_info.status if result.convergence_info else 'N/A'}")
        
        avg_duration = sum(m["duration"] for m in metrics) / len(metrics)
        convergence_rate = sum(m["consensus_reached"] for m in metrics) / len(metrics)
        
        print("\n📊 LM STUDIO BENCHMARK RESULTS:")
        print(f"   • Average response time: {avg_duration:.2f}s")
        print(f"   • Convergence rate: {convergence_rate:.1%}")
        print("   • Total cost: $0.00")
        
        return metrics

    @pytest.mark.asyncio
    async def test_hybrid_local_deliberation_benchmark(self, engine, legal_questions):
        """Benchmark hybrid deliberation with multiple local models."""
        print("\n" + "="*60)
        print("HYBRID LOCAL DELIBERATION BENCHMARK")
        print("="*60)
        
        participants = [
            Participant(cli="ollama", model="xingyaow/codeact-agent-mistral"),
            Participant(cli="lmstudio", model="llama-3-groq-8b-tool-use"),
        ]
        
        metrics = []
        
        for i, question_data in enumerate(legal_questions[:1], 1):  # Test first question only
            print(f"\n--- Hybrid Test Case {i} ---")
            
            request = DeliberateRequest(
                question=question_data["question"],
                participants=participants,
                rounds=2,  # Multi-round deliberation
                context=question_data["context"],
                working_directory="/tmp",)
            
            start_time = time.time()
            result = await engine.execute(request)
            duration = time.time() - start_time
            convergence_status = result.convergence_info.status if result.convergence_info else "unknown"
            rounds_completed = (
                len(result.convergence_info.rounds)
                if result.convergence_info and hasattr(result.convergence_info, "rounds")
                else result.rounds_completed
            )
            
            metric = {
                "duration": duration,
                "convergence_status": convergence_status,
                "rounds_completed": rounds_completed,
                "response_quality_score": self._evaluate_response_quality(result, question_data),
            }
            metrics.append(metric)
            
            print(f"✅ Duration: {duration:.2f}s")
            print(f"🔄 Convergence: {convergence_status}")
            print(f"📊 Rounds: {rounds_completed}")
            print(f"⭐ Quality score: {metric['response_quality_score']}")
            print("💰 Total cost: $0.00 (100% local)")
        
        return metrics

    @pytest.mark.asyncio
    async def test_local_model_memory_usage(self, engine):
        """Test memory usage efficiency of local models."""
        print("\n" + "="*60)
        print("MEMORY USAGE BENCHMARK")
        print("="*60)
        
        baseline_memory = None
        peak_memory = None
        resource = None
        try:
            import resource  # type: ignore
            baseline_usage = resource.getrusage(resource.RUSAGE_SELF)
            baseline_memory = baseline_usage.ru_maxrss / 1024
        except (ImportError, AttributeError, OSError):
            print("⚠️  resource module not available on this platform")
        
        participants = make_participants("ollama", "xingyaow/codeact-agent-mistral")
        request = DeliberateRequest(
            question="What are the key legal considerations for Open Source licensing?",
            participants=participants,
            rounds=1,
            context="Software development context",
                working_directory="/tmp",)
        
        # Run deliberation
        await engine.execute(request)
        
        # Post-execution memory
        if baseline_memory is not None and resource is not None:
            try:
                peak_usage = resource.getrusage(resource.RUSAGE_SELF)
                peak_memory = peak_usage.ru_maxrss / 1024
                memory_increase = peak_memory - baseline_memory

                print("📊 MEMORY USAGE ANALYSIS:")
                print(f"   • Baseline: {baseline_memory:.1f} MB")
                print(f"   • Peak: {peak_memory:.1f} MB")
                print(f"   • Increase: {memory_increase:.1f} MB")

                assert baseline_memory > 0, "Invalid baseline memory measurement"
            except (AttributeError, OSError):
                print("⚠️  Could not measure post-execution memory")
        else:
            print("📊 MEMORY USAGE ANALYSIS:")
            print("   • Memory measurement not available on this platform")
            print("   • Test will proceed without detailed memory metrics")

    def _evaluate_response_quality(self, result, question_data):
        """Simple quality scoring based on content analysis."""
        if not result.summary or not result.summary.consensus:
            return 0.0
        
        score = 0.0
        response = result.summary.consensus.lower()
        
        # Check for expected legal topics
        for topic in question_data.get("expected_topics", []):
            if any(word in response for word in topic.split()):
                score += 0.3
        
        # Check for structured reasoning
        if any(indicator in response for indicator in ["consider", "therefore", "however", "additionally"]):
            score += 0.2
        
        # Check for actionable advice
        if any(action in response for action in ["should", "recommend", "avoid", "ensure"]):
            score += 0.2
        
        # Length quality (not too short, not too long)
        if 100 <= len(result.summary.consensus) <= 2000:
            score += 0.3
        
        return min(score, 1.0)

    @pytest.mark.asyncio
    async def test_concurrent_local_models(self, engine, legal_questions):
        """Test concurrent execution of multiple local model requests."""
        print("\n" + "="*60)
        print("CONCURRENT EXECUTION BENCHMARK")
        print("="*60)
        
        # Deliberation requires at least 2 participants
        participants = make_participants("ollama", "xingyaow/codeact-agent-mistral")
        
        # Create multiple requests
        requests = []
        for i, question_data in enumerate(legal_questions[:2], 1):
            request = DeliberateRequest(
                question=f"[Concurrent Test {i}] {question_data['question']}",
                participants=participants,
                rounds=1,
                context=f"Concurrent execution test {i}",
                working_directory="/tmp",)
            requests.append(request)
        
        # Execute concurrently
        start_time = time.time()
        results = await asyncio.gather(*[engine.execute(req) for req in requests])
        total_duration = time.time() - start_time
        
        print("📊 CONCURRENT EXECUTION RESULTS:")
        print(f"   • Total requests: {len(requests)}")
        print(f"   • Total duration: {total_duration:.2f}s")
        print(f"   • Average per request: {total_duration/len(requests):.2f}s")
        print(f"   • Success rate: {len([r for r in results if r.summary and r.summary.consensus])/len(results):.1%}")
        
        # Verify all requests succeeded
        assert all(result.summary and result.summary.consensus for result in results), "Some concurrent requests failed"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
