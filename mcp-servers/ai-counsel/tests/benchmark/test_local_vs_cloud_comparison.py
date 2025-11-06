"""Local vs Cloud Model Performance Comparison Tests."""

import time

import pytest

from models.schema import DeliberateRequest
from tests.benchmark.conftest import make_participants


pytestmark = [
    pytest.mark.benchmark,
    pytest.mark.local_model,
    pytest.mark.comparison,
    pytest.mark.slow,
]


class TestLocalVsCloudComparison:
    """Compare local model performance against cloud alternatives."""

    @pytest.fixture
    def comparison_scenarios(self):
        """Scenarios for local vs cloud comparison."""
        return [
            {
                "name": "Legal Compliance Analysis",
                "question": """
                What are the key compliance requirements for a B2B SaaS product serving healthcare customers?
                
                Analyze:
                1. HIPAA compliance obligations
                2. Data storage and encryption requirements
                3. Business Associate Agreement (BAA) necessities
                4. Employee training and documentation needs
                """,
                "context": "SaaS startup expanding into healthcare market",
                "priority": "high_confidence",
                "privacy_sensitive": True,
            },
            {
                "name": "Technical Architecture Decision",
                "question": """
                Should our microservices architecture use event-driven communication or direct API calls?
                
                Evaluate:
                1. System reliability and fault tolerance
                2. Development complexity and debugging
                3. Performance characteristics
                4. Scalability implications
                """,
                "context": "High-traffic e-commerce platform, 100K daily active users",
                "priority": "performance_critical",
                "privacy_sensitive": False,
            },
            {
                "name": "Business Strategy Advisory",
                "question": """
                Should our SaaS company offer a free tier or focus on paid plans exclusively?
                
                Consider:
                1. Customer acquisition cost implications
                2. Conversion rates and funnel analysis
                3. Support overhead and resource requirements
                4. Competitive positioning challenges
                """,
                "context": "Series A stage SaaS with $1M ARR, 500 paying customers",
                "priority": "strategic",
                "privacy_sensitive": True,
            }
        ]

    @pytest.mark.asyncio
    async def test_speed_comparison(self, engine, comparison_scenarios):
        """Compare response times between local and cloud models."""
        print("\n" + "="*60)
        print("SPEED COMPARISON: Local vs Cloud Models")
        print("="*60)
        
        model_participants = [
            {"name": "Ollama Local", "participants": make_participants("ollama", "xingyaow/codeact-agent-mistral")},
            {"name": "LM Studio Local", "participants": make_participants("lmstudio", "llama-3-groq-8b-tool-use")},
            {"name": "Claude Cloud", "participants": make_participants("claude", "sonnet")},
        ]
        
        speed_results = {}
        
        for scenario in comparison_scenarios[:2]:  # Limit to 2 scenarios for time
            print(f"\n--- Speed Test: {scenario['name']} ---")
            speed_results[scenario["name"]] = {}
            
            for model_info in model_participants:
                try:
                    request = DeliberateRequest(
                        question=scenario["question"],
                        participants=model_info["participants"],
                        rounds=1,
                        context=scenario["context"],
                working_directory="/tmp",)
                    
                    start_time = time.time()
                    result = await engine.execute(request)
                    duration = time.time() - start_time
                    
                    speed_results[scenario["name"]][model_info["name"]] = {
                        "duration": duration,
                        "success": True,
                        "response_length": len(result.summary.consensus) if result.summary and result.summary.consensus else 0
                    }
                    
                    print(f"✅ {model_info['name']}: {duration:.2f}s ({speed_results[scenario['name']][model_info['name']]['response_length']} chars)")
                    
                except Exception as e:
                    speed_results[scenario["name"]][model_info["name"]] = {
                        "duration": float('inf'),
                        "success": False,
                        "error": str(e)
                    }
                    print(f"❌ {model_info['name']}: Failed - {e}")
        
        # Speed analysis
        print("\n⚡ SPEED ANALYSIS:")
        for scenario_name, results in speed_results.items():
            successful_models = {k: v for k, v in results.items() if v["success"]}
            if successful_models:
                fastest = min(successful_models.items(), key=lambda x: x[1]["duration"])
                slowest = max(successful_models.items(), key=lambda x: x[1]["duration"])
                print(f"   {scenario_name}:")
                print(f"     • Fastest: {fastest[0]} ({fastest[1]['duration']:.2f}s)")
                print(f"     • Slowest: {slowest[0]} ({slowest[1]['duration']:.2f}s)")
                print(f"     • Speedup: {slowest[1]['duration']/fastest[1]['duration']:.1f}x")
        
        # Assertions
        local_speeds = []
        cloud_speeds = []
        
        for scenario_results in speed_results.values():
            local_speeds.extend([r["duration"] for name, r in scenario_results.items() 
                               if r["success"] and "Local" in name])
            cloud_speeds.extend([r["duration"] for name, r in scenario_results.items() 
                                if r["success"] and "Cloud" in name])
        
        if local_speeds and cloud_speeds:
            avg_local = sum(local_speeds) / len(local_speeds)
            avg_cloud = sum(cloud_speeds) / len(cloud_speeds)
            print("\n📊 AVERAGE SPEED COMPARISON:")
            print(f"   • Local Models: {avg_local:.2f}s")
            print(f"   • Cloud Models: {avg_cloud:.2f}s")
            print(f"   • Local Speed Advantage: {avg_cloud/avg_local:.1f}x")
        
        return speed_results

    @pytest.mark.asyncio
    async def test_cost_analysis(self, engine, comparison_scenarios):
        """Analyze cost differences between local and cloud models."""
        print("\n" + "="*60)
        print("COST ANALYSIS: Local vs Cloud Models")
        print("="*60)
        
        cost_estimates = {
            "Ollama Local": {"per_request": 0.0, "monthly_fixed": 0.0, "compute_cost": 10.0},  # Minimal electricity
            "LM Studio Local": {"per_request": 0.0, "monthly_fixed": 0.0, "compute_cost": 15.0},
            "Claude Cloud": {"per_request": 0.15, "monthly_fixed": 0.0, "compute_cost": 0.0},
            "GPT-4 Cloud": {"per_request": 0.12, "monthly_fixed": 0.0, "compute_cost": 0.0},
        }
        
        # Simulate usage scenarios
        usage_scenarios = [
            {"name": "Light Usage", "requests_per_month": 100},
            {"name": "Medium Usage", "requests_per_month": 1000},
            {"name": "Heavy Usage", "requests_per_month": 10000},
        ]
        
        print("\n💰 COST PROJECTIONS:")
        for usage in usage_scenarios:
            print(f"\n--- {usage['name']} ({usage['requests_per_month']} requests/month) ---")
            
            for model_name, cost_info in cost_estimates.items():
                total_monthly = (
                    cost_info["per_request"] * usage["requests_per_month"] +
                    cost_info["monthly_fixed"] +
                    cost_info["compute_cost"]
                )
                
                cost_per_request = total_monthly / usage["requests_per_month"] if usage["requests_per_month"] > 0 else 0
                
                print(f"   {model_name}: ${total_monthly:.2f}/month (${cost_per_request:.4f}/request)")
        
        # Calculate savings
        print("\n💸 POTENTIAL SAVINGS:")
        for usage in usage_scenarios:
            monthly_requests = usage["requests_per_month"]
            
            local_monthly = (
                cost_estimates["Ollama Local"]["per_request"] * monthly_requests +
                cost_estimates["Ollama Local"]["monthly_fixed"] +
                cost_estimates["Ollama Local"]["compute_cost"]
            )
            
            cloud_monthly = (
                cost_estimates["Claude Cloud"]["per_request"] * monthly_requests +
                cost_estimates["Claude Cloud"]["monthly_fixed"] +
                cost_estimates["Claude Cloud"]["compute_cost"]
            )
            
            savings = cloud_monthly - local_monthly
            savings_percentage = (savings / cloud_monthly) * 100 if cloud_monthly > 0 else 0
            
            print(f"   {usage['name']}: ${savings:.2f} saved monthly ({savings_percentage:.1f}% reduction)")
        
        return cost_estimates

    @pytest.mark.asyncio
    async def test_quality_comparison(self, engine, comparison_scenarios):
        """Compare response quality between local and cloud models."""
        print("\n" + "="*60)
        print("QUALITY COMPARISON: Local vs Cloud Models")
        print("="*60)
        
        model_participants = [
            {"name": "Ollama Local", "participants": make_participants("ollama", "xingyaow/codeact-agent-mistral")},
            {"name": "LM Studio Local", "participants": make_participants("lmstudio", "llama-3-groq-8b-tool-use")},
        ]
        
        quality_results = {}
        
        for scenario in comparison_scenarios[:1]:  # Limit to 1 scenario for cost/time
            print(f"\n--- Quality Test: {scenario['name']} ---")
            quality_results[scenario["name"]] = {}
            
            for model_info in model_participants:
                try:
                    request = DeliberateRequest(
                        question=scenario["question"],
                        participants=model_info["participants"],
                        rounds=2,  # Multi-round for better quality
                        context=scenario["context"],
                working_directory="/tmp",)
                    
                    result = await engine.execute(request)
                    quality_score = self._assess_response_quality(result, scenario)
                    
                    quality_results[scenario["name"]][model_info["name"]] = {
                        "quality_score": quality_score,
                        "convergence_status": result.convergence_info.status,
                        "response_length": len(result.summary.consensus) if result.summary and result.summary.consensus else 0,
                        "success": True
                    }
                    
                    print(f"🎯 {model_info['name']}: {quality_score:.3f} quality score")
                    
                except Exception as e:
                    quality_results[scenario["name"]][model_info["name"]] = {
                        "quality_score": 0.0,
                        "success": False,
                        "error": str(e)
                    }
                    print(f"❌ {model_info['name']}: Failed - {e}")
        
        # Quality analysis
        print("\n📈 QUALITY ANALYSIS:")
        for scenario_name, results in quality_results.items():
            successful_models = {k: v for k, v in results.items() if v["success"]}
            if successful_models:
                best_quality = max(successful_models.items(), key=lambda x: x[1]["quality_score"])
                avg_quality = sum(r["quality_score"] for r in successful_models.values()) / len(successful_models)
                
                print(f"   {scenario_name}:")
                print(f"     • Best Quality: {best_quality[0]} ({best_quality[1]['quality_score']:.3f})")
                print(f"     • Average Quality: {avg_quality:.3f}")
                
                # Quality categories
                high_quality = [name for name, result in successful_models.items() if result["quality_score"] >= 0.8]
                medium_quality = [name for name, result in successful_models.items() if 0.6 <= result["quality_score"] < 0.8]
                
                if high_quality:
                    print(f"     • High Quality (≥0.8): {', '.join(high_quality)}")
                if medium_quality:
                    print(f"     • Medium Quality (0.6-0.79): {', '.join(medium_quality)}")
        
        return quality_results

    @pytest.mark.asyncio
    async def test_privacy_security_comparison(self, engine, comparison_scenarios):
        """Compare privacy and security aspects."""
        print("\n" + "="*60)
        print("PRIVACY & SECURITY COMPARISON")
        print("="*60)
        
        privacy_features = {
            "Ollama Local": {
                "data_leaves_premises": False,
                "third_party_access": False,
                "audit_trail": True,
                "encryption_in_transit": False,  # Local only
                "encryption_at_rest": True,
                "compliance_friendly": True,
                "data_retention_control": True
            },
            "LM Studio Local": {
                "data_leaves_premises": False,
                "third_party_access": False,
                "audit_trail": True,
                "encryption_in_transit": False,
                "encryption_at_rest": True,
                "compliance_friendly": True,
                "data_retention_control": True
            },
            "Claude Cloud": {
                "data_leaves_premises": True,
                "third_party_access": True,  # Anthropic API
                "audit_trail": True,
                "encryption_in_transit": True,
                "encryption_at_rest": True,
                "compliance_friendly": True,  # SOC 2, etc.
                "data_retention_control": False
            }
        }
        
        # Test with privacy-sensitive scenario
        privacy_scenario = [s for s in comparison_scenarios if s.get("privacy_sensitive", False)][0]
        print(f"\n--- Privacy Analysis: {privacy_scenario['name']} ---")
        
        for model_name, features in privacy_features.items():
            print(f"\n🔒 {model_name}:")
            
            privacy_score = 0
            total_features = len(features)
            
            for feature_name, feature_value in features.items():
                status = "✅" if feature_value else "❌"
                print(f"   {status} {feature_name.replace('_', ' ').title()}: {feature_value}")
                if feature_value:
                    privacy_score += 1
            
            privacy_percentage = (privacy_score / total_features) * 100
            print(f"   📊 Privacy Score: {privacy_percentage:.1f}%")
            
            # Recommendations based on sensitivity
            if privacy_scenario.get("privacy_sensitive", False) and features["data_leaves_premises"]:
                print("   ⚠️  WARNING: Data leaves premises - not ideal for sensitive content")
            elif not features["data_leaves_premises"]:
                print("   ✅ RECOMMENDED: Data stays on-premises for sensitive content")
        
        return privacy_features

    async def test_hybrid_approach_benefits(self, engine, comparison_scenarios):
        """Test hybrid local+cloud approach for optimal balance."""
        print("\n" + "="*60)
        print("HYBRID APPROACH: Local + Cloud Benefits")
        print("="*60)
        
        # Define hybrid strategy
        hybrid_strategies = [
            {
                "name": "Privacy-First Hybrid",
                "description": "Local for sensitive data, Cloud for general tasks",
                "rule": "privacy_sensitive ? local : cloud"
            },
            {
                "name": "Cost-Optimized Hybrid", 
                "description": "Local for high-volume, Cloud for complex tasks",
                "rule": "high_volume ? local : cloud"
            },
            {
                "name": "Quality-First Hybrid",
                "description": "Cloud for critical decisions, Local for routine tasks",
                "rule": "high_confidence ? cloud : local"
            }
        ]
        
        print("\n🔄 HYBRID STRATEGY ANALYSIS:")
        
        for strategy in hybrid_strategies:
            print(f"\n--- {strategy['name']} ---")
            print(f"   Strategy: {strategy['description']}")
            print(f"   Rule: {strategy['rule']}")
            
            scenario_distribution = {"local": 0, "cloud": 0, "hybrid": 0}
            
            for scenario in comparison_scenarios:
                decision = self._apply_hybrid_rule(strategy["rule"], scenario)
                scenario_distribution[decision] += 1
                
                print(f"   • {scenario['name']}: {decision.upper()}")
            
            # Calculate cost savings estimate
            total_scenarios = len(comparison_scenarios)
            local_percentage = (scenario_distribution["local"] / total_scenarios) * 100
            cloud_percentage = (scenario_distribution["cloud"] / total_scenarios) * 100
            hybrid_percentage = (scenario_distribution["hybrid"] / total_scenarios) * 100
            
            estimated_cost_saving = (local_percentage / 100) * 0.8  # 80% of typical cost when using local
            print(f"   📊 Distribution: Local {local_percentage:.0f}%, Cloud {cloud_percentage:.0f}%, Hybrid {hybrid_percentage:.0f}%")
            print(f"   💰 Estimated Cost Savings: {estimated_cost_saving:.0%} vs all-cloud approach")
        
        return hybrid_strategies

    def _apply_hybrid_rule(self, rule, scenario):
        """Apply hybrid strategy rule to determine model choice."""
        if rule == "privacy_sensitive ? local : cloud":
            return "local" if scenario.get("privacy_sensitive", False) else "cloud"
        elif rule == "high_volume ? local : cloud":
            return "local" if scenario.get("priority") == "performance_critical" else "cloud"
        elif rule == "high_confidence ? cloud : local":
            return "cloud" if scenario.get("priority") == "high_confidence" else "local"
        else:
            return "hybrid"

    def _assess_response_quality(self, result, scenario):
        """Assess quality of model response."""
        if not result.summary or not result.summary.consensus:
            return 0.0
        
        score = 0.0
        response = result.summary.consensus.lower()
        
        # Content completeness (30%)
        content_indicators = ["consider", "evaluate", "analyze", "assess", "review"]
        content_score = sum(1 for indicator in content_indicators if indicator in response)
        content_score = min(content_score / 3, 1.0)
        score += content_score * 0.3
        
        # Structure and organization (25%)
        structure_indicators = ["first", "second", "third", "additionally", "furthermore", "conclusion"]
        structure_score = sum(1 for indicator in structure_indicators if indicator in response)
        structure_score = min(structure_score / 3, 1.0)
        score += structure_score * 0.25
        
        # Specificity and detail (25%)
        if len(result.summary.consensus) > 500:
            score += 0.15
        if len(result.summary.consensus) > 1000:
            score += 0.1
        
        # Context relevance (20%)
        context_lower = scenario["context"].lower()
        context_match = sum(1 for word in context_lower.split() if len(word) > 4 and word in response)
        context_score = min(context_match / 3, 1.0)
        score += context_score * 0.2
        
        return min(score, 1.0)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
