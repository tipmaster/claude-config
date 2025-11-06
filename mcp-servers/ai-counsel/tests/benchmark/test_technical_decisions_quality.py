"""Technical decision benchmarks for local models."""

import pytest

from models.schema import DeliberateRequest
from tests.benchmark.conftest import make_participants


pytestmark = [
    pytest.mark.benchmark,
    pytest.mark.local_model,
    pytest.mark.technical_decisions,
]


class TestTechnicalDecisionsQuality:
    """Test technical reasoning and decision-making quality."""

    @pytest.fixture
    def technical_test_cases(self):
        """Comprehensive technical decision test cases."""
        return [
            {
                "name": "TypeScript vs JavaScript",
                "question": """
                Should our modern web application use TypeScript or JavaScript?
                
                Evaluate based on:
                1. Developer productivity and onboarding
                2. Code maintainability at scale
                3. Runtime performance implications
                4. Ecosystem and tooling support
                5. Team expertise and learning curve
                """,
                "context": "Startup building B2B SaaS platform, 5 developers",
                "required_topics": ["typescript", "javascript", "type safety", "productivity"],
                "technical_areas": ["web development", "tooling", "performance"],
            },
            {
                "name": "React vs Vue.js Framework Choice",
                "question": """
                For our new e-commerce platform, should we use React or Vue.js?
                
                Consider:
                1. Learning curve and developer experience
                2. Performance for product listings and checkout
                3. State management complexity
                4. Component ecosystem and third-party integrations
                5. Long-term maintainability
                """,
                "context": "E-commerce startup, team has mixed frontend experience",
                "required_topics": ["react", "vue", "frontend", "performance"],
                "technical_areas": ["frontend", "framework comparison", "ux"],
            },
            {
                "name": "Microservices vs Monolithic Architecture",
                "question": """
                Should our growing SaaS application move to microservices or stay monolithic?
                
                Assess:
                1. Development team coordination and deployment complexity
                2. Scaling characteristics and resource efficiency
                3. Data consistency and transaction management
                4. Monitoring and debugging overhead
                5. Migration costs and timeline
                """,
                "context": "Team of 8 developers, 50K active users, growing 20% monthly",
                "required_topics": ["microservices", "monolith", "architecture", "scaling"],
                "technical_areas": ["architecture", "scalability", "operations"],
            },
            {
                "name": "PostgreSQL vs MongoDB Database Choice",
                "question": """
                For our analytics platform, should we use PostgreSQL or MongoDB?
                
                Decision factors:
                1. Query complexity and reporting requirements
                2. Data consistency and transaction needs
                3. Schema flexibility vs structure requirements
                4. Integration with analytics tools and BI platforms
                5. Operational overhead and management complexity
                """,
                "context": "Analytics startup handling 1M events/day, complex reporting needs",
                "required_topics": ["postgresql", "mongodb", "database", "analytics"],
                "technical_areas": ["database", "analytics", "data modeling"],
            },
            {
                "name": "AWS vs Google Cloud Platform",
                "question": """
                Should our startup deploy on AWS or Google Cloud Platform?
                
                Compare across:
                1. Cost efficiency for our expected workload
                2. Developer experience and documentation quality
                3. Managed services and platform offerings
                4. Reliability and global infrastructure
                5. Vendor lock-in and migration flexibility
                """,
                "context": "Seed-stage startup, $50K annual cloud budget, global users",
                "required_topics": ["aws", "gcp", "cloud", "infrastructure"],
                "technical_areas": ["cloud computing", "devops", "cost optimization"],
            },
            {
                "name": "REST vs GraphQL API Design",
                "question": """
                For our mobile-first application, should we use REST or GraphQL APIs?
                
                Technical considerations:
                1. Mobile data usage and offline capabilities
                2. Frontend framework integration complexity
                3. API versioning and backward compatibility
                4. Caching strategies and performance optimization
                5. Team learning curve and development velocity
                """,
                "context": "React Native app with real-time features, iOS/Android deployment",
                "required_topics": ["rest", "graphql", "api", "mobile"],
                "technical_areas": ["api design", "mobile development", "performance"],
            }
        ]

    @pytest.mark.asyncio
    async def test_technical_reasoning_depth(self, engine, technical_test_cases):
        """Test depth of technical analysis and reasoning."""
        print("\n" + "="*60)
        print("TECHNICAL REASONING DEPTH ASSESSMENT")
        print("="*60)
        
        reasoning_scores = []
        
        for test_case in technical_test_cases:
            print(f"\n--- Technical Test: {test_case['name']} ---")
            
            participants = make_participants("ollama", "xingyaow/codeact-agent-mistral")
            request = DeliberateRequest(
                question=test_case["question"],
                participants=participants,
                rounds=2,  # Multi-round for thorough analysis
                context=test_case["context"],
                working_directory="/tmp",)
            
            result = await engine.execute(request)
            
            # Technical depth assessment
            depth_score = await self._assess_technical_depth(result, test_case)
            reasoning_scores.append({
                "test_name": test_case["name"],
                "depth_score": depth_score,
                "convergence": result.convergence_info.status,
                "response_length": len(result.summary.consensus) if result.summary and result.summary.consensus else 0
            })
            
            print(f"🔬 Technical Depth: {depth_score:.2f}/1.00")
            print(f"🔄 Convergence: {result.convergence_info.status}")
            print(f"📝 Response Length: {reasoning_scores[-1]['response_length']} chars")
        
        # Overall technical reasoning assessment
        avg_depth = sum(s["depth_score"] for s in reasoning_scores) / len(reasoning_scores)
        
        print("\n🧪 TECHNICAL REASONING SUMMARY:")
        print(f"   • Average Technical Depth: {avg_depth:.3f}")
        print(f"   • High-Quality Responses: {sum(1 for s in reasoning_scores if s['depth_score'] >= 0.7)}/{len(reasoning_scores)}")
        
        # Technical quality assertions (ensure metrics recorded)
        assert reasoning_scores, "No technical reasoning metrics recorded"
        
        return reasoning_scores

    @pytest.mark.asyncio
    async def test_context_awareness(self, engine, technical_test_cases):
        """Test context awareness and scenario adaptation."""
        print("\n" + "="*60)
        print("CONTEXT AWARENESS TEST")
        print("="*60)
        
        context_scores = []
        
        for test_case in technical_test_cases:
            # Create two versions with different contexts
            contexts = [
                f"{test_case['context']} - Budget-conscious early stage startup",
                f"{test_case['context']} - Well-funded enterprise with established team"
            ]
            
            for context_variant in contexts:
                participants = make_participants("ollama", "xingyaow/codeact-agent-mistral")
                request = DeliberateRequest(
                    question=test_case["question"],
                    participants=participants,
                    rounds=1,
                    context=context_variant,
                working_directory="/tmp",)
                
                result = await engine.execute(request)
                context_score = self._assess_context_relevance(result, test_case, context_variant)
                
                context_scores.append({
                    "test_name": f"{test_case['name']} - {context_variant.split('-')[-1].strip()}",
                    "context_score": context_score
                })
                
                print(f"--- {test_case['name']} ({context_variant.split('-')[-1].strip()}) ---")
                print(f"🎯 Context Relevance: {context_score:.2f}/1.00")
        
        avg_context = sum(s["context_score"] for s in context_scores) / len(context_scores)
        print("\n🎭 CONTEXT AWARENESS SUMMARY:")
        print(f"   • Average Context Relevance: {avg_context:.3f}")
        
        assert context_scores, "No context awareness metrics recorded"
        
        return context_scores

    @pytest.mark.asyncio
    async def test_practical_recommendations(self, engine, technical_test_cases):
        """Test for practical, actionable recommendations."""
        print("\n" + "="*60)
        print("PRACTICAL RECOMMENDATIONS TEST")
        print("="*60)
        
        practicality_scores = []
        
        for test_case in technical_test_cases:
            participants = make_participants("ollama", "xingyaow/codeact-agent-mistral")
            request = DeliberateRequest(
                question=test_case["question"],
                participants=participants,
                rounds=1,
                context=test_case["context"],
                working_directory="/tmp",)
            
            result = await engine.execute(request)
            practicality_score = self._assess_practicality(result, test_case)
            
            practicality_scores.append({
                "test_name": test_case["name"],
                "practicality_score": practicality_score
            })
            
            print(f"--- {test_case['name']} ---")
            print(f"🛠️ Practicality Score: {practicality_score:.2f}/1.00")
        
        avg_practicality = sum(s["practicality_score"] for s in practicality_scores) / len(practicality_scores)
        print("\n🔧 PRACTICALITY SUMMARY:")
        print(f"   • Average Practicality Score: {avg_practicality:.3f}")
        
        assert practicality_scores, "No practicality metrics recorded"
        
        return practicality_scores

    async def _assess_technical_depth(self, result, test_case):
        """Comprehensive technical depth assessment."""
        if not result.summary or not result.summary.consensus:
            return 0.0
        
        score = 0.0
        response = result.summary.consensus.lower()
        
        # Topic coverage (25%)
        topic_score = 0.0
        for topic in test_case["required_topics"]:
            if topic in response:
                topic_score += 1.0 / len(test_case["required_topics"])
        score += topic_score * 0.25
        
        # Technical terminology (25%)
        technical_terms = {
            "typescript": ["type safety", "static typing", "interface", "generics", "compilation"],
            "javascript": ["dynamic typing", "runtime", "prototype", "ecmascript", "npm"],
            "react": ["component", "state", "hooks", "jsx", "virtual dom"],
            "vue": ["template", "reactivity", "composition api", "directive", "component"],
            "microservices": ["service", "api gateway", "container", "orchestration", "decomposition"],
            "monolith": ["single application", "tight coupling", "deployment", "scaling", "maintenance"],
            "postgresql": ["relational", "sql", "acid", "indexing", "transaction"],
            "mongodb": ["nosql", "document", "schemaless", "aggregation", "scaling"],
            "aws": ["ec2", "s3", "lambda", "cloudformation", "vpc"],
            "gcp": ["compute engine", "cloud storage", "cloud functions", "deployment manager"],
            "rest": ["http", "endpoint", "resource", "status code", "restful"],
            "graphql": ["schema", "query", "mutation", "resolver", "subscription"]
        }
        
        tech_term_score = 0.0
        test_key = test_case["name"].lower().split(" vs ")[0]
        if test_key in technical_terms:
            term_list = technical_terms[test_key]
            found_terms = sum(1 for term in term_list if term in response)
            tech_term_score = min(found_terms / 3, 1.0)  # Require at least 3 technical terms
        score += tech_term_score * 0.25
        
        # Trade-off analysis (25%)
        tradeoff_indicators = ["advantage", "disadvantage", "pro", "con", "trade-off", "consideration", "versus", "compared to"]
        tradeoff_score = sum(1 for indicator in tradeoff_indicators if indicator in response)
        tradeoff_score = min(tradeoff_score / 3, 1.0)
        score += tradeoff_score * 0.25
        
        # Future-proofing considerations (25%)
        future_terms = ["scalability", "maintainability", "future-proof", "long-term", "growth", "evolution"]
        future_score = sum(1 for term in future_terms if term in response)
        future_score = min(future_score / 2, 1.0)
        score += future_score * 0.25
        
        return min(score, 1.0)

    def _assess_context_relevance(self, result, test_case, context):
        """Assess how well response matches specific context."""
        if not result.summary or not result.summary.consensus:
            return 0.0
        
        score = 0.0
        response = result.summary.consensus.lower()
        context_lower = context.lower()
        
        # Context keyword matching (40%)
        context_keywords = [
            "startup", "team", "budget", "scale", "enterprise",
            "small", "large", "early stage", "established", "funding"
        ]
        
        matched_context = sum(1 for kw in context_keywords if kw in context_lower and kw in response)
        context_score = min(matched_context / 2, 1.0)
        score += context_score * 0.4
        
        # Scale-appropriate recommendations (40%)
        if "startup" in context_lower or "early stage" in context_lower:
            startup_terms = ["simplicity", "cost-effective", "quick", "lean", "mvp"]
            startup_score = sum(1 for term in startup_terms if term in response)
            startup_score = min(startup_score / 2, 1.0)
            score += startup_score * 0.4
            
        elif "enterprise" in context_lower or "established" in context_lower:
            enterprise_terms = ["robust", "scalability", "maintenance", "governance", "enterprise-grade"]
            enterprise_score = sum(1 for term in enterprise_terms if term in response)
            enterprise_score = min(enterprise_score / 2, 1.0)
            score += enterprise_score * 0.4
        
        # Team size consideration (20%)
        if "5 developers" in context_lower or "small team" in context_lower:
            if any(term in response for term in ["learning curve", "simplicity", "onboarding"]):
                score += 0.2
        elif "8 developers" in context_lower or "growing team" in context_lower:
            if any(term in response for term in ["collaboration", "standards", "process"]):
                score += 0.2
        
        return min(score, 1.0)

    def _assess_practicality(self, result, test_case):
        """Assess practical, actionable recommendations."""
        if not result.summary or not result.summary.consensus:
            return 0.0
        
        score = 0.0
        response = result.summary.consensus.lower()
        
        # Action-oriented language (30%)
        action_indicators = ["recommend", "should", "consider", "implement", "choose", "adopt", "use", "select"]
        action_score = sum(1 for indicator in action_indicators if indicator in response)
        action_score = min(action_score / 3, 1.0)
        score += action_score * 0.3
        
        # Specific implementation guidance (30%)
        implementation_terms = ["steps", "approach", "strategy", "plan", "migration", "transition", "timeline"]
        impl_score = sum(1 for term in implementation_terms if term in response)
        impl_score = min(impl_score / 2, 1.0)
        score += impl_score * 0.3
        
        # Risk awareness and mitigation (40%)
        risk_terms = ["risk", "challenge", "drawback", "limitation", "mitigation", "careful", "caution"]
        if any(term in response for term in risk_terms):
            score += 0.2
        
        # Cost consideration
        if any(term in response for term in ["cost", "budget", "investment", "roi", "expensive"]):
            score += 0.1
        
        # Team impact consideration
        if any(term in response for term in ["team", "learning", "training", "hiring", "expertise"]):
            score += 0.1
        
        return min(score, 1.0)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
