"""AI Counsel MCP Server.

This MCP server exposes 2 primary tools via the Model Context Protocol:
1. deliberate - Multi-round AI model deliberation
2. query_decisions - Query the decision graph memory (when enabled)

Additionally, during deliberation, AI models can invoke 4 internal tools via
TOOL_REQUEST markers (not directly exposed via MCP):
- read_file: Read file contents
- search_code: Search codebase with regex
- list_files: List files matching glob pattern
- run_command: Execute read-only commands

The internal tools are executed by the DeliberationEngine, not the MCP client.
"""
import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Optional

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from adapters import create_adapter
from decision_graph.storage import DecisionGraphStorage
from deliberation.engine import DeliberationEngine
from deliberation.query_engine import QueryEngine
from models.config import AdapterConfig, CLIToolConfig, load_config
from models.model_registry import ModelRegistry
from models.schema import DeliberateRequest

# Project directory (where server.py is located) - for config and logs
PROJECT_DIR = Path(__file__).parent.absolute()
# Working directory (where server was started from) - for transcripts
WORK_DIR = Path.cwd()

# Configure logging to file in project directory
log_file = PROJECT_DIR / "mcp_server.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stderr),  # Explicitly use stderr
    ],
)
logger = logging.getLogger(__name__)


# Initialize server
app = Server("ai-counsel")


# Load configuration from project directory
try:
    config_path = PROJECT_DIR / "config.yaml"
    logger.info(f"Loading config from: {config_path}")
    config = load_config(str(config_path))
    logger.info("Configuration loaded successfully")
except Exception as e:
    logger.error(f"Failed to load config: {e}", exc_info=True)
    raise


model_registry = ModelRegistry(config)
session_defaults: dict[str, str] = {}


# Create adapters - prefer new 'adapters' section, fallback to legacy 'cli_tools'
adapters = {}
adapter_sources: list[tuple[str, dict[str, CLIToolConfig | AdapterConfig]]] = []

# Try new adapters section first (preferred)
if hasattr(config, "adapters") and config.adapters:
    adapter_sources.append(("adapters", config.adapters))  # type: ignore[arg-type]

# Fallback to legacy cli_tools for backward compatibility
if hasattr(config, "cli_tools") and config.cli_tools:
    adapter_sources.append(("cli_tools", config.cli_tools))  # type: ignore[arg-type]

for source_name, adapter_configs in adapter_sources:
    for cli_name, cli_config in adapter_configs.items():
        # Skip if already loaded from preferred source
        if cli_name in adapters:
            logger.debug(
                f"Adapter '{cli_name}' already loaded from preferred source, skipping {source_name}"
            )
            continue

        try:
            adapters[cli_name] = create_adapter(cli_name, cli_config)
            logger.info(f"Initialized adapter: {cli_name} (from {source_name})")
        except Exception as e:
            logger.error(f"Failed to create adapter for {cli_name}: {e}")


# Create engine with config for convergence detection
engine = DeliberationEngine(adapters=adapters, config=config, server_dir=WORK_DIR)


CLI_TITLES = {
    "claude": "Claude (Anthropic)",
    "codex": "Codex (OpenAI)",
    "droid": "Droid Adapter",
    "gemini": "Gemini (Google)",
    "llamacpp": "llama.cpp",
    "ollama": "Ollama",
    "lmstudio": "LM Studio",
    "openrouter": "OpenRouter",
}


def _build_participant_variants() -> list[dict]:
    """Construct JSON schema variants for participants per adapter."""

    variants: list[dict] = []
    all_clis = [
        "claude",
        "codex",
        "droid",
        "gemini",
        "llamacpp",
        "ollama",
        "lmstudio",
        "openrouter",
    ]

    for cli in all_clis:
        model_entries = model_registry.list_for_adapter(cli)
        model_schema: dict

        if model_entries:
            any_of: list[dict] = []
            default_id: Optional[str] = None
            for entry in model_entries:
                title = entry.label
                if entry.tier:
                    title = f"{title} ({entry.tier})"
                option = {"const": entry.id, "title": title}
                if entry.note:
                    option["description"] = entry.note
                any_of.append(option)
                if entry.default and default_id is None:
                    default_id = entry.id

            any_of.append(
                {
                    "type": "null",
                    "title": "Use session default",
                    "description": "Leave blank or select null to use the session or recommended default",
                }
            )

            model_schema = {
                "type": ["string", "null"],
                "anyOf": any_of,
                "description": "Model identifier for this adapter",
            }
            if default_id:
                model_schema["default"] = default_id
        else:
            model_schema = {
                "type": ["string", "null"],
                "description": "Model identifier (free-form for this adapter)",
            }

        variant = {
            "type": "object",
            "properties": {
                "cli": {
                    "type": "string",
                    "const": cli,
                    "title": CLI_TITLES.get(cli, cli.title()),
                    "description": "Adapter to use (CLI tools or HTTP services)",
                },
                "model": model_schema,
            },
            "required": ["cli"],
            "additionalProperties": False,
        }
        variants.append(variant)

    return variants


def _build_set_session_schema() -> dict:
    """Construct schema for the set_session_models tool."""

    properties: dict[str, dict] = {}
    for cli, entries in model_registry.list().items():
        any_of = []
        default_id = None
        for entry in entries:
            title = entry.get("label", entry.get("id", ""))
            tier = entry.get("tier")
            if tier:
                title = f"{title} ({tier})"
            option = {"const": entry["id"], "title": title}
            note = entry.get("note")
            if note:
                option["description"] = note
            any_of.append(option)
            if entry.get("default") and default_id is None:
                default_id = entry["id"]

        any_of.append(
            {
                "type": "null",
                "title": "Clear session default",
                "description": "Remove the session override for this adapter",
            }
        )

        schema: dict = {
            "type": ["string", "null"],
            "anyOf": any_of,
            "description": f"Override the default model used for the {cli} adapter",
        }
        if default_id:
            schema["default"] = default_id

        properties[cli] = schema

    return {
        "type": "object",
        "properties": properties,
        "additionalProperties": False,
        "description": "Set or clear session-scoped model overrides by adapter",
    }


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available MCP tools."""

    participant_variants = _build_participant_variants()

    deliberate_tool = Tool(
        name="deliberate",
        description=(
            "Initiate deliberative consensus where AI models debate across multiple rounds. "
            "Models see each other's responses and adapt their reasoning. Supports CLI tools "
            "(claude, codex, droid, gemini, llamacpp) and HTTP services (ollama, lmstudio, openrouter)."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "The question or proposal for the models to deliberate on",
                    "minLength": 10,
                },
                "participants": {
                    "type": "array",
                    "items": {"oneOf": participant_variants},
                    "minItems": 2,
                    "description": "List of AI participants (minimum 2)",
                },
                "rounds": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 5,
                    "default": 2,
                    "description": "Number of deliberation rounds (1-5)",
                },
                "mode": {
                    "type": "string",
                    "enum": ["quick", "conference"],
                    "default": "quick",
                    "description": "quick = single round opinions, conference = multi-round deliberation",
                },
                "context": {
                    "type": "string",
                    "description": "Optional additional context (code snippets, requirements, etc.)",
                },
                "working_directory": {
                    "type": "string",
                    "description": "Working directory for tool execution (tools resolve relative paths from here). Should be the client's current working directory.",
                },
            },
            "required": ["question", "participants", "working_directory"],
        },
    )

    tools: list[Tool] = [deliberate_tool]

    tools.append(
        Tool(
            name="list_models",
            description="Return the allowlisted model options for each adapter.",
            inputSchema={
                "type": "object",
                "properties": {
                    "adapter": {
                        "type": "string",
                        "description": "Optional adapter name to filter the response",
                    }
                },
                "additionalProperties": False,
            },
        )
    )

    tools.append(
        Tool(
            name="set_session_models",
            description=(
                "Set session-scoped default models by adapter. Pass null to clear an override."
            ),
            inputSchema=_build_set_session_schema(),
        )
    )

    if (
        hasattr(config, "decision_graph")
        and config.decision_graph
        and config.decision_graph.enabled
    ):
        tools.append(
            Tool(
                name="query_decisions",
                description=(
                    "Search and analyze past deliberations in the decision graph memory. "
                    "Find similar decisions, identify contradictions, or trace decision evolution."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query_text": {
                            "type": "string",
                            "description": "Query text to search for similar decisions",
                        },
                        "find_contradictions": {
                            "type": "boolean",
                            "default": False,
                            "description": "Find contradictions in decision history instead of searching",
                        },
                        "decision_id": {
                            "type": "string",
                            "description": "Trace evolution of a specific decision by ID",
                        },
                        "limit": {
                            "type": "integer",
                            "default": 5,
                            "minimum": 1,
                            "maximum": 20,
                            "description": "Maximum number of results to return",
                        },
                        "format": {
                            "type": "string",
                            "enum": ["summary", "detailed", "json"],
                            "default": "summary",
                            "description": "Output format",
                        },
                    },
                },
            )
        )

    return tools


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """
    Handle tool calls from MCP client.

    Args:
        name: Tool name ("deliberate", "list_models", "set_session_models", "query_decisions")
        arguments: Tool arguments as dict

    Returns:
        List of TextContent with JSON response
    """
    logger.info(f"Tool call received: {name} with arguments: {arguments}")

    if name == "list_models":
        return await handle_list_models(arguments)
    if name == "set_session_models":
        return await handle_set_session_models(arguments)
    if name == "query_decisions":
        return await handle_query_decisions(arguments)
    elif name != "deliberate":
        error_msg = f"Unknown tool: {name}"
        logger.error(error_msg)
        raise ValueError(error_msg)

    try:
        # Validate and parse request
        logger.info("Validating request parameters...")
        request = DeliberateRequest(**arguments)
        logger.info(
            f"Request validated. Starting deliberation: {request.question[:50]}..."
        )
        logger.info(f"Working directory: {request.working_directory}")

        # Apply session defaults and allowlist validation
        for participant in request.participants:
            cli = participant.cli
            provided_model = participant.model

            if not provided_model:
                default_model = session_defaults.get(cli) or model_registry.get_default(cli)
                if not default_model:
                    raise ValueError(
                        f"No model provided for adapter '{cli}', and no default is configured."
                    )
                participant.model = default_model
                logger.info(
                    f"Using default model '{default_model}' for adapter '{cli}'."
                )
            elif not model_registry.is_allowed(cli, provided_model):
                allowed = sorted(model_registry.allowed_ids(cli))
                if allowed:
                    raise ValueError(
                        f"Model '{provided_model}' is not allowlisted for adapter '{cli}'. "
                        f"Allowed models: {', '.join(allowed)}."
                    )
            # Ensure session default remains valid (e.g., config change)
            if participant.model and not model_registry.is_allowed(cli, participant.model):
                allowed = sorted(model_registry.allowed_ids(cli))
                if allowed:
                    raise ValueError(
                        f"Model '{participant.model}' is no longer allowlisted for adapter '{cli}'. "
                        f"Allowed models: {', '.join(allowed)}."
                    )

        # Execute deliberation
        result = await engine.execute(request)
        logger.info(
            f"Deliberation complete: {result.rounds_completed} rounds, status: {result.status}"
        )

        # Truncate full_debate for MCP response if needed (to avoid token limit)
        max_rounds = getattr(config, "mcp", {}).get("max_rounds_in_response", 3)
        result_dict = result.model_dump()

        if len(result.full_debate) > max_rounds:
            total_rounds = len(result.full_debate)
            # Convert RoundResponse objects to dicts for the truncated slice
            result_dict["full_debate"] = [
                r.model_dump() if hasattr(r, "model_dump") else r
                for r in result.full_debate[-max_rounds:]
            ]
            result_dict["full_debate_truncated"] = True
            result_dict["total_rounds"] = total_rounds
            logger.info(
                f"Truncated full_debate from {total_rounds} to last {max_rounds} rounds for MCP response"
            )
        else:
            result_dict["full_debate_truncated"] = False

        # Summarize tool_executions for MCP response (full detail is in transcript)
        if result_dict.get("tool_executions"):
            tool_summary = {
                "total_tools_executed": len(result_dict["tool_executions"]),
                "tools_by_round": {},
                "tools_by_type": {},
            }

            for execution in result_dict["tool_executions"]:
                # Count by round
                round_num = execution.get("round_number", 0)
                tool_summary["tools_by_round"][round_num] = tool_summary["tools_by_round"].get(round_num, 0) + 1

                # Count by tool type
                tool_name = execution.get("request", {}).get("name", "unknown")
                tool_summary["tools_by_type"][tool_name] = tool_summary["tools_by_type"].get(tool_name, 0) + 1

            # Replace massive tool_executions array with compact summary
            result_dict["tool_executions"] = tool_summary
            result_dict["tool_executions_note"] = "Tool execution details available in transcript file"
            logger.info(f"Summarized {tool_summary['total_tools_executed']} tool executions for MCP response")

        # Serialize result
        result_json = json.dumps(result_dict, indent=2)
        logger.info(f"Result serialized, length: {len(result_json)} chars")

        # Return result as TextContent
        response = [TextContent(type="text", text=result_json)]
        logger.info("Response prepared successfully")
        return response

    except Exception as e:
        logger.error(f"Error in deliberation: {type(e).__name__}: {e}", exc_info=True)
        error_response = {
            "error": str(e),
            "error_type": type(e).__name__,
            "status": "failed",
        }
        return [TextContent(type="text", text=json.dumps(error_response, indent=2))]


async def handle_list_models(arguments: dict) -> list[TextContent]:
    """Return allowlisted models, optionally filtered by adapter."""

    adapter = arguments.get("adapter")
    catalog = model_registry.list()
    response: dict

    if adapter:
        models = catalog.get(adapter, [])
        response = {
            "adapter": adapter,
            "models": models,
            "recommended_default": model_registry.get_default(adapter),
            "session_default": session_defaults.get(adapter),
        }
    else:
        recommended_defaults = {
            cli: model_registry.get_default(cli) for cli in catalog.keys()
        }
        response = {
            "models": catalog,
            "recommended_defaults": recommended_defaults,
            "session_defaults": dict(session_defaults),
        }

    return [TextContent(type="text", text=json.dumps(response, indent=2))]


async def handle_set_session_models(arguments: dict) -> list[TextContent]:
    """Set or clear session-scoped default models."""

    updates: dict[str, Optional[str]] = {}

    if not arguments:
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "status": "no-op",
                        "message": "No adapters provided; session defaults unchanged.",
                        "session_defaults": session_defaults,
                    },
                    indent=2,
                ),
            )
        ]

    for cli, value in arguments.items():
        if cli not in model_registry.adapters():
            raise ValueError(
                f"Adapter '{cli}' is not managed by the model registry and cannot be overridden."
            )
        if value is None:
            session_defaults.pop(cli, None)
            updates[cli] = None
            continue

        if not model_registry.is_allowed(cli, value):
            allowed = sorted(model_registry.allowed_ids(cli))
            raise ValueError(
                f"Model '{value}' is not allowlisted for adapter '{cli}'. "
                f"Allowed models: {', '.join(allowed)}."
            )

        session_defaults[cli] = value
        updates[cli] = value

    response = {
        "status": "updated",
        "updates": updates,
        "session_defaults": dict(session_defaults),
    }
    return [TextContent(type="text", text=json.dumps(response, indent=2))]


async def handle_query_decisions(arguments: dict) -> list[TextContent]:
    """Handle query_decisions tool call."""
    try:
        db_path = Path(getattr(config.decision_graph, "db_path", "decision_graph.db"))
        # Make db_path absolute - if relative, resolve from project directory
        if not db_path.is_absolute():
            db_path = PROJECT_DIR / db_path
        storage = DecisionGraphStorage(str(db_path))
        engine = QueryEngine(storage, config=config.decision_graph)

        query_text = arguments.get("query_text")
        find_contradictions = arguments.get("find_contradictions", False)
        decision_id = arguments.get("decision_id")
        limit = arguments.get("limit", 5)
        format_type = arguments.get("format", "summary")

        # Validate mutual exclusivity
        provided_params = sum([
            bool(query_text),
            bool(find_contradictions),
            bool(decision_id)
        ])

        if provided_params == 0:
            return [TextContent(
                type="text",
                text=json.dumps({
                    "error": "Must provide one of: query_text, find_contradictions, or decision_id",
                    "status": "failed"
                }, indent=2)
            )]

        if provided_params > 1:
            return [TextContent(
                type="text",
                text=json.dumps({
                    "error": "Only one of query_text, find_contradictions, or decision_id can be provided",
                    "status": "failed",
                    "provided": {
                        "query_text": bool(query_text),
                        "find_contradictions": bool(find_contradictions),
                        "decision_id": bool(decision_id)
                    }
                }, indent=2)
            )]

        # Helper function to format decision results based on format type
        def format_decision(decision, score=None):
            """Format a decision based on the requested format type."""
            if format_type == "detailed":
                # Detailed format includes all available fields
                formatted = {
                    "id": decision.id,
                    "question": decision.question,
                    "consensus": decision.consensus,
                    "participants": decision.participants,
                    "timestamp": decision.timestamp,
                }
                if score is not None:
                    formatted["score"] = score
                # Include stances if available
                if hasattr(decision, "stances") and decision.stances:
                    formatted["stances"] = [
                        {
                            "participant": s.participant,
                            "position": s.position,
                            "confidence": getattr(s, "confidence", None),
                            "rationale": getattr(s, "rationale", None),
                        }
                        for s in decision.stances
                    ]
                return formatted
            elif format_type == "json":
                # JSON format returns full object representation
                formatted = {
                    "id": decision.id,
                    "question": decision.question,
                    "consensus": decision.consensus,
                    "participants": decision.participants,
                    "timestamp": decision.timestamp,
                }
                if score is not None:
                    formatted["score"] = score
                if hasattr(decision, "stances") and decision.stances:
                    formatted["stances"] = [
                        {
                            "participant": s.participant,
                            "position": s.position,
                            "confidence": getattr(s, "confidence", None),
                            "rationale": getattr(s, "rationale", None),
                        }
                        for s in decision.stances
                    ]
                return formatted
            else:
                # Summary format (default) - minimal fields
                formatted = {
                    "id": decision.id,
                    "question": decision.question,
                    "consensus": decision.consensus,
                    "participants": decision.participants,
                }
                if score is not None:
                    formatted["score"] = score
                return formatted

        result = None

        if query_text:
            # Search similar decisions
            results = await engine.search_similar(query_text, limit=limit)
            result = {
                "type": "similar_decisions",
                "count": len(results),
                "results": [
                    format_decision(r.decision, r.score)
                    for r in results
                ],
            }

        elif find_contradictions:
            # Find contradictions
            contradictions = await engine.find_contradictions()
            # Format contradictions based on format type
            if format_type == "detailed":
                result = {
                    "type": "contradictions",
                    "count": len(contradictions),
                    "results": [
                        {
                            "decision_id_1": c.decision_id_1,
                            "decision_id_2": c.decision_id_2,
                            "question_1": c.question_1,
                            "question_2": c.question_2,
                            "severity": c.severity,
                            "description": c.description,
                            "similarity_score": getattr(c, "similarity_score", None),
                        }
                        for c in contradictions
                    ],
                }
            else:
                result = {
                    "type": "contradictions",
                    "count": len(contradictions),
                    "results": [
                        {
                            "decision_id_1": c.decision_id_1,
                            "decision_id_2": c.decision_id_2,
                            "question_1": c.question_1,
                            "question_2": c.question_2,
                            "severity": c.severity,
                            "description": c.description,
                        }
                        for c in contradictions
                    ],
                }

        elif decision_id:
            # Trace evolution
            timeline = await engine.trace_evolution(decision_id, include_related=True)
            if format_type == "detailed":
                result = {
                    "type": "evolution",
                    "decision_id": timeline.decision_id,
                    "question": timeline.question,
                    "consensus": timeline.consensus,
                    "status": timeline.status,
                    "participants": timeline.participants,
                    "timestamp": getattr(timeline, "timestamp", None),
                    "rounds": len(timeline.rounds),
                    "related_decisions": timeline.related_decisions[:3],
                }
            else:
                result = {
                    "type": "evolution",
                    "decision_id": timeline.decision_id,
                    "question": timeline.question,
                    "consensus": timeline.consensus,
                    "status": timeline.status,
                    "participants": timeline.participants,
                    "rounds": len(timeline.rounds),
                    "related_decisions": timeline.related_decisions[:3],
                }

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        logger.error(
            f"Error in query_decisions: {type(e).__name__}: {e}", exc_info=True
        )
        error_response = {
            "error": str(e),
            "error_type": type(e).__name__,
            "status": "failed",
        }
        return [TextContent(type="text", text=json.dumps(error_response, indent=2))]


async def main():
    """Run the MCP server."""
    logger.info("Starting AI Counsel MCP Server...")
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
