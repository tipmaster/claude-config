"""Simple benchmark suite for local models."""

import time

import pytest

from models.schema import DeliberateRequest
from tests.benchmark.conftest import make_participants


pytestmark = [
    pytest.mark.benchmark,
    pytest.mark.local_model,
    pytest.mark.slow,
]


class TestSimpleLocalModelBenchmark:
    """Simple benchmark for local models with working tests."""

    @pytest.mark.asyncio
    async def test_ollama_basic_performance(self, engine):
        """Test basic performance of Ollama model."""
        print("\n" + "="*50)
        print("OLLAMA BASIC PERFORMANCE TEST")
        print("="*50)
        
        participants = make_participants("ollama", "xingyaow/codeact-agent-mistral")
        
        question = """
        Should our software company adopt TypeScript or JavaScript for frontend development?
        
        Consider:
        1. Developer productivity and maintainability
        2. Performance implications
        3. Learning curve for the team
        4. Tooling and ecosystem support
        """
        
        request = DeliberateRequest(
            question=question,
            participants=participants,
            rounds=2,
            context="Startup with 5 developers, building SaaS platform",
                working_directory="/tmp",)
        
        print("🔄 Running deliberation with 2 Ollama models...")
        start_time = time.time()
        
        try:
            result = await engine.execute(request)
            duration = time.time() - start_time
            
            print("\n✅ Ollama Performance Results:")
            print(f"   • Duration: {duration:.2f} seconds")
            print(f"   • Convergence: {result.convergence_info.status}")
            consensus_text = result.summary.consensus if result.summary else ""
            print(f"   • Response length: {len(consensus_text) if consensus_text else 0} chars")
            print("   • Cost: $0.00 (local inference)")
            
            # Basic assertions
            assert result.summary is not None, "No summary generated"
            assert consensus_text is not None, "Missing consensus text"
            assert duration < 180.0, f"Response too slow: {duration:.2f}s"
            
            return {
                "duration": duration,
                "convergence": result.convergence_info.status,
                "response_length": len(consensus_text)
            }
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            raise

    @pytest.mark.asyncio
    async def test_simple_quality_assessment(self, engine):
        """Test quality of local model responses."""
        print("\n" + "="*50)
        print("SIMPLE QUALITY ASSESSMENT")
        print("="*50)
        
        participants = make_participants("ollama", "xingyaow/codeact-agent-mistral")
        
        test_cases = [
            {
                "name": "Technical Decision",
                "question": "Should we use React.js or Vue.js for our new web application?",
                "context": "Building a customer-facing dashboard with complex data visualization",
                "expected_keywords": ["react", "vue", "framework", "component", "performance"]
            },
            {
                "name": "Legal Compliance", 
                "question": "What are the key privacy considerations for a user authentication system?",
                "context": "B2B SaaS product handling sensitive customer data",
                "expected_keywords": ["privacy", "security", "data", "compliance", "encryption"]
            }
        ]
        
        quality_scores = []
        
        for test_case in test_cases:
            print(f"\n--- {test_case['name']} ---")
            
            request = DeliberateRequest(
                question=test_case["question"],
                participants=participants,
                rounds=1,
                context=test_case["context"],
                working_directory="/tmp",)
            
            start_time = time.time()
            result = await engine.execute(request)
            duration = time.time() - start_time
            
            # Simple quality assessment
            score = self._assess_simple_quality(result, test_case)
            quality_scores.append(score)
            
            consensus_text = result.summary.consensus if result.summary else ""
            print(f"   ✅ Duration: {duration:.2f}s")
            print(f"   📏 Response length: {len(consensus_text) if consensus_text else 0} chars")
            print(f"   ⭐ Quality score: {score:.2f}/1.00")
            print(f"   🔄 Convergence: {result.convergence_info.status}")
            
            # Basic quality assertions - more lenient for local models
            assert score >= 0.1, f"Poor quality score: {score:.2f}"
            assert result.summary is not None, "No summary generated"
            
            # Debug: print the actual content
            if result.summary and result.summary.consensus:
                print(f"   📄 Consensus: '{result.summary.consensus[:100]}...'")
            else:
                print("   ❌ No summary consensus available")
            
            if hasattr(result, 'full_debate') and result.full_debate:
                print(f"   💬 Debate rounds: {len(result.full_debate)}")
                full_text = " ".join([r.response for r in result.full_debate])
                print(f"   💬 Full text length: {len(full_text)} chars")
                print(f"   💬 Preview: {full_text[:150]}...")
                print(f"   🗳️  Voting result: {'Available' if result.voting_result else 'None'}")
            else:
                print("   ❌ No debate data available")
        
        avg_quality = sum(quality_scores) / len(quality_scores)
        print(f"\n📊 AVERAGE QUALITY: {avg_quality:.3f}")
        
        assert avg_quality >= 0.2, f"Poor average quality: {avg_quality:.3f}"
        
        return quality_scores

    @pytest.mark.asyncio
    async def testCostComparisonDemonstration(self, engine):
        """Demonstrate cost comparison benefits (conceptual)."""
        print("\n" + "="*50)
        print("COST COMPARISON DEMONSTRATION")
        print("="*50)

        participants = make_participants("ollama", "xingyaow/codeact-agent-mistral")
        
        cost_scenarios = [
            {
                "name": "Technical Architecture Decision",
                "question": "Should we choose PostgreSQL or MongoDB for our analytics platform?",
                "context": "High-volume data processing, need complex queries",
                "cloud_estimated_cost": 0.15  # Estimated cost per request for cloud models
            },
            {
                "name": "Legal Compliance Review", 
                "question": "What data protection measures are required for EU customers?",
                "context": "Expanding SaaS product to European market",
                "cloud_estimated_cost": 0.12
            }
        ]
        
        total_savings = 0.0
        
        for scenario in cost_scenarios:
            request = DeliberateRequest(
                question=scenario["question"],
                participants=participants,
                rounds=1,
                context=scenario["context"],
                working_directory="/tmp",)
            
            start_time = time.time()
            result = await engine.execute(request)
            duration = time.time() - start_time
            
            actual_cost = 0.0  # Local models are free
            savings = scenario["cloud_estimated_cost"] - actual_cost
            total_savings += savings
            
            print(f"\n--- {scenario['name']} ---")
            print(f"   ⏱️  Duration: {duration:.2f}s")
            consensus_text = result.summary.consensus if result.summary else ""
            print(f"   💰 Local model cost: ${actual_cost:.2f}")
            print(f"   💸 Cloud model estimate: ${scenario['cloud_estimated_cost']:.2f}")
            print(f"   💵 Savings: ${savings:.2f}")
            print(f"   📝 Response: {len(consensus_text) if consensus_text else 0} chars")
            
            assert result.summary is not None, "No summary generated"
        
        print(f"\n💰 TOTAL SAVINGS FOR {len(cost_scenarios)} REQUESTS: ${total_savings:.2f}")
        print(f"📈 PROJECTED ANNUAL SAVINGS (100 requests/mo): ${total_savings * 12 * 100:.2f}")
        
        return total_savings

    def _assess_simple_quality(self, result, test_case):
        """Simple quality scoring for responses."""
        score = 0.0
        
        # Check if we have actual model responses (most important)
        if hasattr(result, 'full_debate') and result.full_debate:
            full_debate_text = " ".join([round_response.response for round_response in result.full_debate]).lower()
            
            # Check for expected keywords (50%)
            keyword_score = 0.0
            for keyword in test_case["expected_keywords"]:
                if keyword in full_debate_text:
                    keyword_score += 1.0 / len(test_case["expected_keywords"])
            score += keyword_score * 0.5
            
            # Check for reasonable length (25%)
            if len(full_debate_text) > 200:
                score += 0.25
            
            # Check for structured reasoning (25%)
            reasoning_indicators = ["consider", "therefore", "however", "additionally", "recommend", "雅思"]
            if any(indicator in full_debate_text for indicator in reasoning_indicators):
                score += 0.25
        
        # Bonus points for voting data
        elif hasattr(result, 'voting_result') and result.voting_result:
            score += 0.2
        
        # Fallback: check summary if available
        elif result.summary and result.summary.consensus:
            response = result.summary.consensus.lower()
            keyword_score = 0.0
            for keyword in test_case["expected_keywords"]:
                if keyword in response:
                    keyword_score += 1.0 / len(test_case["expected_keywords"])
            score += keyword_score * 0.3
            
            if len(response) > 50:
                score += 0.2
        
        return min(score, 1.0)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
