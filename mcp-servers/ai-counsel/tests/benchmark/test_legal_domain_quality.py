"""Legal domain quality benchmarks for local models."""

import re

import pytest

from models.schema import DeliberateRequest
from tests.benchmark.conftest import make_participants


pytestmark = [
    pytest.mark.benchmark,
    pytest.mark.local_model,
    pytest.mark.legal_domain,
]


class TestLegalDomainQuality:
    """Test legal reasoning quality of local models."""

    @pytest.fixture
    def legal_test_cases(self):
        """Comprehensive legal test cases."""
        return [
            {
                "name": "Employment Law Compliance",
                "question": """
                What are the essential components of an employee handbook for a 10-person tech startup in California?
                
                Include considerations for:
                1. Wage and hour compliance
                2. Anti-discrimination policies
                3. Leave policies (CFRA, PDL)
                4. Remote work arrangements
                """,
                "context": "Early-stage SaaS company, first-time founders",
                "required_entities": ["wage", "discrimination", "leave", "california"],
                "ethical_checkpoints": ["confidentiality", "fairness", "compliance"],
            },
            {
                "name": "Intellectual Property Strategy",
                "question": """
                Should our software startup file patents for our core algorithms?
                
                Evaluate:
                1. Trade secret vs patent protection
                2. Publication requirements
                3. Enforcement costs
                4. Defensive patent strategies
                """,
                "context": "AI/ML startup seeking Series A funding",
                "required_entities": ["patent", "trade secret", "intellectual property"],
                "ethical_checkpoints": ["disclosure", "competition", "innovation"],
            },
            {
                "name": "Data Privacy Compliance",
                "question": """
                What privacy framework should our SAAS product implement for B2B customers?
                
                Consider:
                1. GDPR applicability
                2. CCPA/CPRA requirements
                3. SOC 2 compliance
                4. Data processing agreements
                """,
                "context": "B2B SaaS with European customers",
                "required_entities": ["gdpr", "privacy", "data", "compliance"],
                "ethical_checkpoints": ["consent", "transparency", "security"],
            },
            {
                "name": "Contract Risk Assessment",
                "question": """
                What clauses should we negotiate in our SaaS customer contracts?
                
                Prioritize:
                1. Limitation of liability
                2. Service level agreements
                3. Data ownership and usage rights
                4. Termination and renewal terms
                """,
                "context": "B2B SaaS with enterprise customers",
                "required_entities": ["liability", "service", "data", "termination"],
                "ethical_checkpoints": ["fairness", "clarity", "mutual benefit"],
            }
        ]

    @pytest.mark.asyncio
    async def test_legal_reasoning_quality(self, engine, legal_test_cases):
        """Test comprehensive legal reasoning quality."""
        print("\n" + "="*60)
        print("LEGAL REASONING QUALITY ASSESSMENT")
        print("="*60)
        
        quality_scores = []
        
        for test_case in legal_test_cases:
            print(f"\n--- Legal Test: {test_case['name']} ---")
            
            # Deliberation requires at least 2 participants
            participants = make_participants("ollama", "xingyaow/codeact-agent-mistral")
            request = DeliberateRequest(
                question=test_case["question"],
                participants=participants,
                rounds=2,  # Multi-round for thorough analysis
                context=test_case["context"],
                working_directory="/tmp",)
            
            result = await engine.execute(request)
            
            # Quality assessment
            score = await self._assess_legal_quality(result, test_case)
            quality_scores.append({
                "test_name": test_case["name"],
                "score": score,
                "convergence": result.convergence_info.status,
                "response_length": len(result.summary.consensus) if result.summary and result.summary.consensus else 0
            })
            
            print(f"📊 Quality Score: {score:.2f}/1.00")
            print(f"🔄 Convergence: {result.convergence_info.status}")
            print(f"📝 Response Length: {quality_scores[-1]['response_length']} chars")
        
        # Overall assessment
        avg_quality = sum(s["score"] for s in quality_scores) / len(quality_scores)
        
        print("\n🏆 LEGAL QUALITY SUMMARY:")
        print(f"   • Average Quality Score: {avg_quality:.3f}")
        print(f"   • Tests Passed: {sum(1 for s in quality_scores if s['score'] >= 0.7)}/{len(quality_scores)}")
        
        # Quality check: ensure we collected metrics
        assert quality_scores, "No legal quality metrics recorded"
        
        return quality_scores

    @pytest.mark.asyncio
    async def test_ethical_guideline_adherence(self, engine, legal_test_cases):
        """Test adherence to legal ethical guidelines."""
        print("\n" + "="*60)
        print("ETHICAL GUIDELINE ADHERENCE TEST")
        print("="*60)
        
        ethical_scores = []
        
        for test_case in legal_test_cases:
            # Deliberation requires at least 2 participants
            participants = make_participants("ollama", "xingyaow/codeact-agent-mistral")
            request = DeliberateRequest(
                question=test_case["question"],
                participants=participants,
                rounds=1,
                context=test_case["context"],
                working_directory="/tmp",)
            
            result = await engine.execute(request)
            ethical_score = self._assess_ethical_compliance(result, test_case)
            
            ethical_scores.append({
                "test_name": test_case["name"],
                "ethical_score": ethical_score
            })
            
            print(f"--- {test_case['name']} ---")
            print(f"🛡️ Ethical Score: {ethical_score:.2f}/1.00")
        
        avg_ethical = sum(s["ethical_score"] for s in ethical_scores) / len(ethical_scores)
        print("\n⚖️ ETHICAL COMPLIANCE SUMMARY:")
        print(f"   • Average Ethical Score: {avg_ethical:.3f}")
        
        assert ethical_scores, "No ethical compliance metrics recorded"
        
        return ethical_scores

    @pytest.mark.asyncio
    async def test_client_communication_quality(self, engine):
        """Test communication clarity for client interactions."""
        print("\n" + "="*60)
        print("CLIENT COMMUNICATION QUALITY TEST")
        print("="*60)
        
        communication_scenarios = [
            {
                "name": "Explaining Complex Legal Concepts",
                "question": """
                My startup wants to understand our intellectual property options. Could you explain:
                1. What's the difference between patents and trade secrets?
                2. When should we choose one over the other?
                3. What are the costs and timelines involved?
                """,
                "context": "Non-technical founder needs clear explanation",
                "audience": "non-legal",
            },
            {
                "name": "Risk Communication",
                "question": """
                What are the biggest legal risks for my e-commerce business right now?
                Please explain them in order of priority and what I should do about each.
                """,
                "context": "Small business owner seeking risk assessment",
                "audience": "business owner",
            }
        ]
        
        communication_scores = []
        
        for scenario in communication_scenarios:
            # Deliberation requires at least 2 participants
            participants = make_participants("ollama", "xingyaow/codeact-agent-mistral")
            request = DeliberateRequest(
                question=scenario["question"],
                participants=participants,
                rounds=1,
                context=scenario["context"],
                working_directory="/tmp",)
            
            result = await engine.execute(request)
            comm_score = self._assess_communication_quality(result, scenario)
            
            communication_scores.append({
                "scenario": scenario["name"],
                "score": comm_score
            })
            
            print(f"--- {scenario['name']} ---")
            print(f"💬 Communication Score: {comm_score:.2f}/1.00")
        
        avg_communication = sum(s["score"] for s in communication_scores) / len(communication_scores)
        print("\n📞 COMMUNICATION QUALITY SUMMARY:")
        print(f"   • Average Communication Score: {avg_communication:.3f}")
        
        assert communication_scores, "No communication metrics recorded"
        
        return communication_scores

    async def _assess_legal_quality(self, result, test_case):
        """Comprehensive legal quality assessment."""
        if not result.summary or not result.summary.consensus:
            return 0.0
        
        score = 0.0
        response = result.summary.consensus.lower()
        
        # Entity recognition (25%)
        entity_score = 0.0
        for entity in test_case["required_entities"]:
            if entity in response:
                entity_score += 1.0 / len(test_case["required_entities"])
        score += entity_score * 0.25
        
        # Structured reasoning (25%)
        reasoning_indicators = [
            "therefore", "however", "additionally", "furthermore", "consequently",
            "consider", "evaluate", "analyze", "assess"
        ]
        reasoning_score = sum(1 for indicator in reasoning_indicators if indicator in response)
        reasoning_score = min(reasoning_score / 3, 1.0)  # Cap at 1.0
        score += reasoning_score * 0.25
        
        # Legal terminology accuracy (25%)
        legal_terms = ["liability", "compliance", "regulation", "contract", "statute", "jurisdiction"]
        legal_term_score = sum(1 for term in legal_terms if term in response)
        legal_term_score = min(legal_term_score / 2, 1.0)  # Cap at 1.0
        score += legal_term_score * 0.25
        
        # Practical relevance (25%)
        practical_terms = ["should", "recommend", "advise", "consider", "implement", "ensure"]
        practical_score = sum(1 for term in practical_terms if term in response)
        practical_score = min(practical_score / 3, 1.0)  # Cap at 1.0
        score += practical_score * 0.25
        
        return min(score, 1.0)

    def _assess_ethical_compliance(self, result, test_case):
        """Assess ethical guideline adherence."""
        if not result.summary or not result.summary.consensus:
            return 0.0
        
        score = 0.0
        response = result.summary.consensus.lower()
        
        # Ethical checkpoint coverage (70%)
        checkpoint_score = 0.0
        for checkpoint in test_case["ethical_checkpoints"]:
            checkpoint_words = checkpoint.split()
            if any(word in response for word in checkpoint_words):
                checkpoint_score += 1.0 / len(test_case["ethical_checkpoints"])
        score += checkpoint_score * 0.7
        
        # Red flag detection (30%)
        red_flags = [
            "illegal", "unlawful", "fraud", "mislead", "deceive",
            "evade", "circumvent", "exploit"
        ]
        if not any(flag in response for flag in red_flags):
            score += 0.3
        
        # Professional language bonus
        professional_indicators = ["ethical", "professional", "responsible", "diligence"]
        if any(indicator in response for indicator in professional_indicators):
            score = min(score + 0.1, 1.0)
        
        return min(score, 1.0)

    def _assess_communication_quality(self, result, scenario):
        """Assess communication clarity and appropriateness."""
        if not result.summary or not result.summary.consensus:
            return 0.0
        
        score = 0.0
        response = result.summary.consensus.lower()
        
        # Clarity indicators (30%)
        clarity_indicators = ["simply put", "in other words", "for example", "to clarify"]
        clarity_score = sum(1 for indicator in clarity_indicators if indicator in response)
        clarity_score = min(clarity_score / 2, 1.0)
        score += clarity_score * 0.3
        
        # Structure (30%)
        has_structure = False
        response_lines = result.summary.consensus.split('\n')
        if len(response_lines) >= 3:  # Has some structure
            has_structure = True
        
        # Check for numbered/bulleted lists
        if re.search(r'\d+\.\s|[-*]\s', result.summary.consensus):
            has_structure = True
        
        structure_score = 1.0 if has_structure else 0.5
        score += structure_score * 0.3
        
        # Audience appropriateness (40%)
        if scenario["audience"] == "non-legal":
            # Check for simple language
            complex_words = ["jurisprudence", "tort", "estoppel", "novation"]
            if not any(word in response for word in complex_words):
                score += 0.4
            else:
                score += 0.2  # Partial credit
        
        elif scenario["audience"] == "business owner":
            # Check for business-focused language
            business_terms = ["cost", "risk", "benefit", "investment", "revenue"]
            business_score = sum(1 for term in business_terms if term in response)
            business_score = min(business_score / 2, 1.0)
            score += business_score * 0.4
        
        return min(score, 1.0)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
