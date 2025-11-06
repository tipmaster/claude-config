"""Pytest fixtures and helpers for benchmark tests."""
from typing import Optional

import pytest

from adapters.base import BaseCLIAdapter
from deliberation.engine import DeliberationEngine
from models.config import load_config
from models.schema import Participant


class MockBenchmarkAdapter(BaseCLIAdapter):
    """Mock adapter for benchmark testing without external dependencies."""

    def __init__(self, name: str, timeout: int = 60):
        """Initialize mock adapter."""
        super().__init__(command=f"mock-{name}", args=[], timeout=timeout)
        self.name = name
        self.invoke_count = 0

    async def invoke(
        self, prompt: str, model: str, context: Optional[str] = None, is_deliberation: bool = True
    ) -> str:
        """Mock invoke method - returns realistic deliberation responses."""
        self.invoke_count += 1
        
        # Detect question context to tailor responses
        prompt_lower = prompt.lower()
        
        # Technical domain responses (check first to avoid substring collisions like "ip" in "typescript")
        if any(word in prompt_lower for word in ["typescript", "javascript", "react", "vue", "framework", "architecture", "microservice", "monolith", "database", "postgres", "mongodb"]):
            responses = [
                "After careful technical analysis, I believe we should prioritize robustness and type safety. TypeScript provides excellent tooling support and catches errors at compile time, which significantly reduces production issues. However, the learning curve might be steep initially.",
                "From a technical perspective, I see benefits in both approaches. TypeScript offers long-term maintainability benefits through strong typing, while JavaScript allows faster iteration and simpler development velocity. Consider team expertise and project timeline.",
                "Both arguments have merit. TypeScript offers excellent developer experience and compile-time safety guarantees. JavaScript provides faster development velocity. I recommend evaluating your team's capabilities and project requirements before deciding.",
                "The key technical consideration is scalability and maintainability. Strong typing systems help catch bugs early in development. I advise adopting a technology stack that balances developer productivity with long-term code quality and system reliability.",
            ]
        # Legal domain responses
        elif any(word in prompt_lower for word in ["legal", "compliance", "liability", "employment", "gdpr", "contract", "patent", "intellectual property"]):
            responses = [
                "After careful legal analysis, I recommend prioritizing compliance and liability protection. Consider implementing comprehensive policies covering wage and hour compliance, anti-discrimination measures, and data protection. These should be documented in your employee handbook and reviewed annually.",
                "From a legal perspective, the liability concerns are significant. We should consider both regulatory compliance and contractual protections. Documentation and clear policies are essential for demonstrating due diligence and mitigating legal exposure.",
                "Both regulatory compliance and operational efficiency matter here. I advise implementing structured compliance procedures with clear documentation. Additionally, ensure all policies are reviewed by qualified legal counsel and communicated consistently to stakeholders.",
                "The risk assessment reveals multiple compliance considerations. Evaluate liability implications carefully. I recommend a phased approach: first establish core compliance framework, then enhance with additional protections based on jurisdiction-specific requirements.",
            ]
        # Default responses
        else:
            responses = [
                "After careful consideration, I believe we should evaluate this decision thoroughly. There are important considerations on both sides. Let me analyze the key factors: feasibility, resource requirements, and potential outcomes.",
                "I see valid points in this discussion. Additionally, we should consider the broader implications and stakeholder requirements. A thorough evaluation reveals several important factors to address.",
                "Both perspectives offer value. Furthermore, I recommend considering risk mitigation strategies and implementation timelines. We should therefore ensure clear communication and documentation of our decision rationale.",
                "The analysis suggests we should prioritize risk management and stakeholder alignment. I recommend implementing a structured evaluation process and documenting our reasoning for future reference and accountability.",
            ]
        
        response = responses[self.invoke_count % len(responses)]
        
        # Include optional VOTE marker if this is a deliberation round
        if is_deliberation and self.invoke_count >= 2:
            vote_json = '{"option": "Option A", "confidence": 0.75, "rationale": "Balanced analysis supports this approach", "continue_debate": false}' if self.invoke_count % 2 == 0 else '{"option": "Option B", "confidence": 0.65, "rationale": "Additional considerations warrant discussion", "continue_debate": true}'
            response += f"\n\nVOTE: {vote_json}"
        
        return response

    def parse_output(self, raw_output: str) -> str:
        """Mock parse_output method."""
        return raw_output.strip()

@pytest.fixture
def mock_benchmark_adapters():
    """Provide mock adapters for all benchmarked CLIs."""

    adapters = {
        "ollama": MockBenchmarkAdapter("ollama"),
        "lmstudio": MockBenchmarkAdapter("lmstudio"),
        "claude": MockBenchmarkAdapter("claude"),
        "codex": MockBenchmarkAdapter("codex"),
        "droid": MockBenchmarkAdapter("droid"),
        "gemini": MockBenchmarkAdapter("gemini"),
    }

    return adapters


@pytest.fixture
async def engine(mock_benchmark_adapters):
    """Shared deliberation engine backed by mock adapters."""

    config = load_config("config.yaml")
    engine = DeliberationEngine(adapters=dict(mock_benchmark_adapters), config=config)
    yield engine


def make_participants(primary_cli: str, primary_model: str, *, peer_cli: Optional[str] = None, peer_model: Optional[str] = None) -> list[Participant]:
    """Create a valid participant pair for benchmark requests."""

    peer_cli = peer_cli or primary_cli
    peer_model = peer_model or primary_model
    return [
        Participant(cli=primary_cli, model=primary_model),
        Participant(cli=peer_cli, model=peer_model),
    ]
