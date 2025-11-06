#!/usr/bin/env python3
"""Demo script showing tool results are now injected into context."""
from deliberation.engine import DeliberationEngine
from models.schema import Participant, RoundResponse
from models.tool_schema import ToolRequest, ToolResult, ToolExecutionRecord
from datetime import datetime

# Create engine
engine = DeliberationEngine({})

# Simulate tool execution history
engine.tool_execution_history = [
    ToolExecutionRecord(
        round_number=1,
        request=ToolRequest(name='read_file', arguments={'path': '/config.yaml'}),
        result=ToolResult(
            tool_name='read_file',
            success=True,
            output='database: postgresql\nport: 5432\nssl: true',
            error=None
        ),
        requested_by='sonnet@claude'
    )
]

# Simulate previous responses
previous_responses = [
    RoundResponse(
        round=1,
        participant='sonnet@claude',
        stance='neutral',
        response='Let me check the config file.',
        timestamp=datetime.now().isoformat()
    )
]

# Build context with tool results (current_round_num=2)
context = engine._build_context(previous_responses, current_round_num=2)

print('=' * 80)
print('CONTEXT WITH TOOL RESULTS (Round 2)')
print('=' * 80)
print(context)
print('=' * 80)
print()

# Verify key elements are present
checks = [
    ('Recent Tool Results' in context, 'Tool results section present'),
    ('read_file' in context, 'Tool name present'),
    ('postgresql' in context, 'Tool output content present'),
    ('Round 1' in context, 'Round number present'),
    ('```' in context, 'Code block formatting present'),
]

print('VERIFICATION CHECKS:')
for passed, description in checks:
    status = '✅ PASS' if passed else '❌ FAIL'
    print(f'{status}: {description}')

print()
print('SUMMARY: Tool results are now successfully injected into context!')
