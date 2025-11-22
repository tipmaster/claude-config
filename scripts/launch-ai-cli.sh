#!/bin/bash
# Convenience launcher for AI CLIs with autonomous execution modes
# Usage: ./launch-ai-cli.sh [claude|gemini|codex|copilot|droid|qwen|opencode] [mode]

set -e

TOOL="${1:-}"
MODE="${2:-interactive}"

usage() {
    cat <<EOF
🤖 AI CLI Launcher - Launch with optimal autonomous settings

USAGE:
    ./launch-ai-cli.sh <tool> [mode]

TOOLS:
    claude      - Claude Code (Anthropic)
    gemini      - Gemini CLI (Google)
    codex       - Codex CLI (OpenAI)
    copilot     - GitHub Copilot CLI
    droid       - Droid CLI (Qwen)
    opencode    - OpenCode (Multi-model)

MODES:
    interactive - Default interactive mode (asks for confirmations)
    auto-edit   - Auto-approve file edits (recommended)
    auto-tool   - (Copilot only) Auto-approve all tool executions
    low         - (Droid only) Basic file operations
    medium      - (Droid only) Development operations (git, builds, etc.)
    high        - (Droid only) Production changes and deployments
    yolo        - Auto-approve everything (DANGEROUS - use with caution)
    full-auto   - (Codex only) Low-friction sandboxed auto-execution

EXAMPLES:
    # Claude Code (always interactive)
    ./launch-ai-cli.sh claude

    # Gemini with auto-edit (auto-approve edits only)
    ./launch-ai-cli.sh gemini auto-edit

    # Gemini YOLO mode (auto-approve everything)
    ./launch-ai-cli.sh gemini yolo

    # Codex with full-auto (model decides when to ask)
    ./launch-ai-cli.sh codex full-auto

    # Codex YOLO (DANGEROUS - no sandbox, no approvals)
    ./launch-ai-cli.sh codex yolo

    # Copilot with auto-tool (auto-approve all tools)
    ./launch-ai-cli.sh copilot auto-tool

    # Copilot YOLO (DANGEROUS - auto-approve all + unrestricted paths)
    ./launch-ai-cli.sh copilot yolo

    # Droid with low autonomy (file editing)
    ./launch-ai-cli.sh droid low

    # Droid with medium autonomy (development work)
    ./launch-ai-cli.sh droid medium

    # Droid with high autonomy (production deployments)
    ./launch-ai-cli.sh droid high

    # Droid YOLO (DANGEROUS - bypass all permissions)
    ./launch-ai-cli.sh droid yolo

RECOMMENDED SETTINGS:
    ✅ Daily work:         auto-edit mode (safe, productive)
    ⚠️  Trusted projects:  full-auto (Codex) or yolo (Gemini)
    🚫 Production:         interactive mode only

EOF
}

if [ -z "$TOOL" ]; then
    usage
    exit 1
fi

case "$TOOL" in
    claude)
        echo "🟢 Launching Claude Code (interactive mode)"
        echo "   Note: Claude Code doesn't support autonomous modes via CLI flags"
        echo "   Configure trust_level in ~/.claude/settings.json for trusted projects"
        echo ""
        claude
        ;;

    gemini)
        case "$MODE" in
            auto-edit)
                echo "🟡 Launching Gemini CLI (auto-edit mode)"
                echo "   ✅ Auto-approves: File edits"
                echo "   ❌ Requires approval: Tool executions, MCP calls"
                echo ""
                gemini --approval-mode auto_edit
                ;;
            yolo)
                echo "🔴 Launching Gemini CLI (YOLO mode - auto-approve ALL)"
                echo "   ⚠️  WARNING: Auto-approves EVERYTHING without asking"
                echo "   Use only in trusted projects!"
                echo ""
                gemini --yolo
                ;;
            interactive|*)
                echo "🟢 Launching Gemini CLI (interactive mode)"
                echo "   Default config: auto_edit (from gemini-settings.json)"
                echo "   All MCP servers whitelisted"
                echo ""
                gemini
                ;;
        esac
        ;;

    codex)
        case "$MODE" in
            full-auto)
                echo "🟡 Launching Codex CLI (full-auto mode)"
                echo "   ✅ Model decides when to ask for approval"
                echo "   ✅ Sandboxed workspace-write access"
                echo "   ✅ Network access enabled"
                echo ""
                codex --full-auto
                ;;
            yolo)
                echo "🔴 Launching Codex CLI (YOLO mode - EXTREMELY DANGEROUS)"
                echo "   ⚠️  WARNING: NO SANDBOX, NO APPROVALS"
                echo "   ⚠️  Can execute ANY command without asking"
                echo "   ⚠️  Use ONLY in externally sandboxed environments"
                echo ""
                read -p "Type 'YES I UNDERSTAND THE RISKS' to continue: " confirm
                if [ "$confirm" = "YES I UNDERSTAND THE RISKS" ]; then
                    codex --dangerously-bypass-approvals-and-sandbox
                else
                    echo "Aborted."
                    exit 1
                fi
                ;;
            auto-edit)
                echo "🟡 Launching Codex CLI (auto-edit equivalent)"
                echo "   Note: Codex uses trust_level + approval_mode"
                echo "   Current config: approval_mode=on-request, trust_level=trusted"
                echo ""
                codex
                ;;
            interactive|*)
                echo "🟢 Launching Codex CLI (default configured mode)"
                echo "   approval_mode: on-request (model decides)"
                echo "   sandbox: workspace-write"
                echo "   trust_level: trusted for known projects"
                echo ""
                codex
                ;;
        esac
        ;;

    copilot)
        case "$MODE" in
            auto-tool)
                echo "🟡 Launching Copilot CLI (auto-tool mode)"
                echo "   ✅ Auto-approves: All tool executions"
                echo "   ❌ Requires approval: File path access (restricted to trusted_folders)"
                echo ""
                copilot --allow-all-tools
                ;;
            yolo)
                echo "🔴 Launching Copilot CLI (YOLO mode - auto-approve ALL + unrestricted paths)"
                echo "   ⚠️  WARNING: Auto-approves ALL tools + unrestricted file access"
                echo "   Use only in trusted projects or dev containers!"
                echo ""
                copilot --allow-all-tools --allow-all-paths
                ;;
            interactive|*)
                echo "🟢 Launching Copilot CLI (interactive mode)"
                echo "   Default config: gpt-5.1 model"
                echo "   MCP servers: 9 total (serena, chrome-bridge, zen, etc.)"
                echo ""
                copilot
                ;;
        esac
        ;;

    droid)
        case "$MODE" in
            low)
                echo "🟡 Launching Droid CLI (low autonomy)"
                echo "   ✅ Auto-approves: Basic file operations (create, edit, delete)"
                echo "   ❌ Requires approval: Git operations, package managers, builds"
                echo ""
                droid --auto low
                ;;
            medium)
                echo "🟡 Launching Droid CLI (medium autonomy)"
                echo "   ✅ Auto-approves: File ops + git + package managers + builds"
                echo "   ❌ Requires approval: Production deployments, system configs"
                echo ""
                droid --auto medium
                ;;
            high)
                echo "🟠 Launching Droid CLI (high autonomy)"
                echo "   ✅ Auto-approves: All development + production operations"
                echo "   ⚠️  WARNING: Can make production changes"
                echo "   Use only in trusted projects!"
                echo ""
                droid --auto high
                ;;
            yolo)
                echo "🔴 Launching Droid CLI (YOLO mode - EXTREMELY DANGEROUS)"
                echo "   ⚠️  WARNING: BYPASSES ALL PERMISSION CHECKS"
                echo "   ⚠️  Can execute ANY operation without asking"
                echo "   ⚠️  Use ONLY in externally sandboxed environments"
                echo ""
                read -p "Type 'YES I UNDERSTAND THE RISKS' to continue: " confirm
                if [ "$confirm" = "YES I UNDERSTAND THE RISKS" ]; then
                    droid --skip-permissions-unsafe
                else
                    echo "Aborted."
                    exit 1
                fi
                ;;
            interactive|*)
                echo "🟢 Launching Droid CLI (read-only mode)"
                echo "   Default safe mode: Can read files but no modifications"
                echo "   MCP servers: 9 total (serena, chrome-bridge, zen, etc.)"
                echo "   Use --auto low/medium/high for autonomous operations"
                echo ""
                droid
                ;;
        esac
        ;;

    qwen)
        case "$MODE" in
            auto-edit)
                echo "🟡 Launching Qwen CLI (auto-edit mode)"
                echo "   ✅ Auto-approves: File edits"
                echo "   ❌ Requires approval: Tool executions, MCP calls"
                echo ""
                qwen --approval-mode auto-edit
                ;;
            yolo)
                echo "🔴 Launching Qwen CLI (YOLO mode - auto-approve ALL)"
                echo "   ⚠️  WARNING: Auto-approves EVERYTHING without asking"
                echo "   Use only in trusted projects!"
                echo ""
                qwen --yolo
                ;;
            plan)
                echo "🟡 Launching Qwen CLI (plan mode)"
                echo "   📋 Planning mode: Generates plans without executing"
                echo "   ✅ Safe for reviewing proposed changes"
                echo "   ❌ Does not execute any operations"
                echo ""
                qwen --approval-mode plan
                ;;
            interactive|*)
                echo "🟢 Launching Qwen CLI (interactive mode)"
                echo "   Default config: auto-edit (from qwen settings.json)"
                echo "   All MCP servers registered via setup script"
                echo ""
                qwen
                ;;
        esac
        ;;

    opencode)
        echo "🟢 Launching OpenCode"
        echo "   Note: OpenCode autonomous settings via config.json"
        echo "   See ~/.config/opencode/opencode.json"
        echo ""
        opencode
        ;;

    *)
        echo "❌ Unknown tool: $TOOL"
        usage
        exit 1
        ;;
esac
