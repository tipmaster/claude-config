#!/usr/bin/env bash
#
# init-project.sh
# Initialize a new project with agent-os framework
#
# This script copies the agent-os development standards and project
# instructions into a project directory. This is SEPARATE from the
# Claude Code configuration (which is global).
#
# Usage: ./scripts/init-project.sh /path/to/your-project
#

set -euo pipefail

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Get directories
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
CONTEXT_DIR="${REPO_ROOT}/context-engineering"

echo -e "${BLUE}═══════════════════════════════════════════${NC}"
echo -e "${BLUE}  Agent-OS Framework - Project Init${NC}"
echo -e "${BLUE}═══════════════════════════════════════════${NC}"
echo ""

# Check argument
if [ $# -eq 0 ]; then
    echo -e "${RED}Error: No project directory specified${NC}"
    echo ""
    echo "Usage: $0 /path/to/your-project"
    echo ""
    echo "Example:"
    echo "  $0 ~/dev/my-new-project"
    echo ""
    exit 1
fi

PROJECT_DIR="$1"

# Expand ~ if present
PROJECT_DIR="${PROJECT_DIR/#\~/$HOME}"

# Create project directory if doesn't exist
if [ ! -d "$PROJECT_DIR" ]; then
    echo -e "${YELLOW}Project directory doesn't exist. Creating...${NC}"
    mkdir -p "$PROJECT_DIR"
fi

# Resolve to absolute path
PROJECT_DIR="$(cd "$PROJECT_DIR" && pwd)"

echo "Project directory: ${PROJECT_DIR}"
echo "Source: ${CONTEXT_DIR}"
echo ""

# Check if files already exist
EXISTING_FILES=()
for file in CLAUDE.MD AGENTS.MD GEMINI.MD SHARED_INSTRUCTIONS.MD; do
    if [ -e "${PROJECT_DIR}/${file}" ]; then
        EXISTING_FILES+=("$file")
    fi
done

if [ ${#EXISTING_FILES[@]} -gt 0 ]; then
    echo -e "${YELLOW}⚠️  The following files already exist:${NC}"
    for file in "${EXISTING_FILES[@]}"; do
        echo "  - $file"
    done
    echo ""
    read -p "Overwrite? (y/N) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Cancelled."
        exit 0
    fi
fi

echo -e "${YELLOW}═══ Creating Symlinks ═══${NC}"
echo ""

# Create symlinks to context-engineering files
cd "$PROJECT_DIR"

ln -sf "${CONTEXT_DIR}/CLAUDE.MD" CLAUDE.MD
echo "✓ CLAUDE.MD → ${CONTEXT_DIR}/CLAUDE.MD"

ln -sf "${CONTEXT_DIR}/AGENTS.MD" AGENTS.MD
echo "✓ AGENTS.MD → ${CONTEXT_DIR}/AGENTS.MD"

ln -sf "${CONTEXT_DIR}/GEMINI.MD" GEMINI.MD
echo "✓ GEMINI.MD → ${CONTEXT_DIR}/GEMINI.MD"

ln -sf "${CONTEXT_DIR}/SHARED_INSTRUCTIONS.MD" SHARED_INSTRUCTIONS.MD
echo "✓ SHARED_INSTRUCTIONS.MD → ${CONTEXT_DIR}/SHARED_INSTRUCTIONS.MD"

echo ""
echo -e "${GREEN}✅ Project initialized with agent-os framework!${NC}"
echo ""
echo "Files created in ${PROJECT_DIR}:"
ls -lh "${PROJECT_DIR}"/CLAUDE.MD "${PROJECT_DIR}"/SHARED_INSTRUCTIONS.MD 2>/dev/null | awk '{print "  " $9 " → " $11 " " $12}'
echo ""
echo "What this means:"
echo "  - CLAUDE.MD: Project-specific instructions for Claude"
echo "  - SHARED_INSTRUCTIONS.MD: Common development standards"
echo "  - These are symlinks, so updates in claude-config propagate automatically"
echo ""
echo "Next steps:"
echo "  1. cd ${PROJECT_DIR}"
echo "  2. Edit project-specific settings (if needed)"
echo "  3. Start working: claude"
echo ""
