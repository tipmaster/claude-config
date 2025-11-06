#!/usr/bin/env bash
#
# install-laptop.sh
# Installs Claude Code configuration for laptop/macOS
#
# This script:
# 1. Backs up current ~/.claude/
# 2. Creates symlinks from ~/.claude/ to this repo
# 3. Installs dependencies (npm, pip packages)
# 4. Generates settings.json from templates
#
# Usage: ./scripts/install-laptop.sh
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
CLAUDE_DIR="${HOME}/.claude"

echo -e "${BLUE}═══════════════════════════════════════════${NC}"
echo -e "${BLUE}  Claude Config - Laptop Installation${NC}"
echo -e "${BLUE}═══════════════════════════════════════════${NC}"
echo ""
echo "Repository: ${REPO_ROOT}"
echo "Claude Dir: ${CLAUDE_DIR}"
echo ""

# Platform check
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo -e "${YELLOW}Warning: This script is designed for macOS${NC}"
    echo "Current OS: $OSTYPE"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check if .env exists
if [ ! -f "${REPO_ROOT}/.env" ]; then
    echo -e "${YELLOW}⚠️  .env file not found${NC}"
    echo ""
    echo "You need to create .env with your API keys:"
    echo "  1. cp .env.example .env"
    echo "  2. vim .env  # Add your API keys"
    echo ""
    read -p "Create .env now? (Y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        cp "${REPO_ROOT}/.env.example" "${REPO_ROOT}/.env"
        echo ""
        echo -e "${GREEN}✅ Created .env from template${NC}"
        echo ""
        echo "Now edit it with your API keys:"
        echo "  vim ${REPO_ROOT}/.env"
        echo ""
        echo "Then run this script again."
        exit 0
    else
        echo ""
        echo "Installation cannot continue without .env file."
        exit 1
    fi
fi

# Load .env to set CLAUDE_PLATFORM
set -a
source "${REPO_ROOT}/.env"
set +a

# Ensure CLAUDE_PLATFORM is set to laptop
if [ "${CLAUDE_PLATFORM:-}" != "laptop" ]; then
    echo "Setting CLAUDE_PLATFORM=laptop in .env..."
    if grep -q "^CLAUDE_PLATFORM=" "${REPO_ROOT}/.env"; then
        sed -i.bak 's/^CLAUDE_PLATFORM=.*/CLAUDE_PLATFORM=laptop/' "${REPO_ROOT}/.env"
    else
        echo "CLAUDE_PLATFORM=laptop" >> "${REPO_ROOT}/.env"
    fi
fi

echo -e "${YELLOW}═══ Pre-Installation Checks ═══${NC}"
echo ""

# Check for required commands
MISSING_DEPS=()

if ! command -v jq &> /dev/null; then
    MISSING_DEPS+=("jq")
fi

if ! command -v node &> /dev/null; then
    echo -e "${YELLOW}Warning: node not found (needed for chrome-mcp)${NC}"
fi

if ! command -v python3 &> /dev/null; then
    echo -e "${YELLOW}Warning: python3 not found (needed for ai-counsel)${NC}"
fi

if [ ${#MISSING_DEPS[@]} -gt 0 ]; then
    echo -e "${RED}Error: Missing required dependencies:${NC}"
    for dep in "${MISSING_DEPS[@]}"; do
        echo "  - $dep"
    done
    echo ""
    echo "Install with:"
    echo "  brew install ${MISSING_DEPS[*]}"
    exit 1
fi

echo -e "${GREEN}✅ All required tools found${NC}"
echo ""

# Show what will be done
echo -e "${YELLOW}═══ Installation Plan ═══${NC}"
echo ""
echo "The following will be done:"
echo "  1. Backup ${CLAUDE_DIR} → ${CLAUDE_DIR}.backup.$(date +%Y%m%d_%H%M%S)"
echo "  2. Remove ${CLAUDE_DIR}/agents, commands, skills"
echo "  3. Create symlinks:"
echo "     ${CLAUDE_DIR}/agents → ${REPO_ROOT}/agents"
echo "     ${CLAUDE_DIR}/commands → ${REPO_ROOT}/commands"
echo "     ${CLAUDE_DIR}/skills → ${REPO_ROOT}/skills"
echo "  4. Install dependencies:"
echo "     - npm install in playwright-skill"
echo "     - pip install in ai-counsel"
echo "     - npm install in chrome-mcp"
echo "  5. Generate ${CLAUDE_DIR}/settings.json from templates"
echo ""

read -p "Proceed with installation? (y/N) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Installation cancelled."
    exit 0
fi

echo ""
echo -e "${YELLOW}═══ Step 1: Backup ═══${NC}"

BACKUP_DIR="${CLAUDE_DIR}.backup.$(date +%Y%m%d_%H%M%S)"
echo "Creating backup: ${BACKUP_DIR}"
cp -r "${CLAUDE_DIR}" "${BACKUP_DIR}"
echo -e "${GREEN}✅ Backup created${NC}"
echo ""

echo -e "${YELLOW}═══ Step 2: Remove Original Directories ═══${NC}"

for dir in agents commands skills; do
    if [ -d "${CLAUDE_DIR}/${dir}" ] && [ ! -L "${CLAUDE_DIR}/${dir}" ]; then
        echo "Removing ${CLAUDE_DIR}/${dir}"
        rm -rf "${CLAUDE_DIR}/${dir}"
    elif [ -L "${CLAUDE_DIR}/${dir}" ]; then
        echo "Removing existing symlink ${CLAUDE_DIR}/${dir}"
        rm "${CLAUDE_DIR}/${dir}"
    fi
done

echo -e "${GREEN}✅ Original directories removed${NC}"
echo ""

echo -e "${YELLOW}═══ Step 3: Create Symlinks ═══${NC}"

for dir in agents commands skills; do
    echo "Linking ${CLAUDE_DIR}/${dir} → ${REPO_ROOT}/${dir}"
    ln -s "${REPO_ROOT}/${dir}" "${CLAUDE_DIR}/${dir}"
done

echo -e "${GREEN}✅ Symlinks created${NC}"
echo ""

echo -e "${YELLOW}═══ Step 4: Install Dependencies ═══${NC}"
echo ""

# Install playwright-skill dependencies
if [ -f "${REPO_ROOT}/skills/playwright-skill/package.json" ]; then
    echo "Installing playwright-skill dependencies..."
    cd "${REPO_ROOT}/skills/playwright-skill"
    npm install --silent
    echo -e "${GREEN}✅ playwright-skill ready${NC}"
else
    echo -e "${YELLOW}⚠️  playwright-skill package.json not found${NC}"
fi

echo ""

# Install ai-counsel dependencies
if [ -f "${REPO_ROOT}/mcp-servers/ai-counsel/requirements.txt" ]; then
    echo "Installing ai-counsel dependencies..."
    cd "${REPO_ROOT}/mcp-servers/ai-counsel"

    # Create venv if doesn't exist
    if [ ! -d ".venv" ]; then
        python3 -m venv .venv
    fi

    # Install requirements
    .venv/bin/pip install --quiet -r requirements.txt
    echo -e "${GREEN}✅ ai-counsel ready${NC}"
else
    echo -e "${YELLOW}⚠️  ai-counsel requirements.txt not found${NC}"
fi

echo ""

# Install chrome-mcp dependencies
if [ -f "${REPO_ROOT}/mcp-servers/chrome-mcp/package.json" ]; then
    echo "Installing chrome-mcp dependencies..."
    cd "${REPO_ROOT}/mcp-servers/chrome-mcp"
    npm install --silent
    echo -e "${GREEN}✅ chrome-mcp ready${NC}"
else
    echo -e "${YELLOW}⚠️  chrome-mcp package.json not found${NC}"
fi

echo ""

echo -e "${YELLOW}═══ Step 5: Generate Configuration ═══${NC}"
echo ""

cd "${REPO_ROOT}"
"${REPO_ROOT}/scripts/generate-config.sh" laptop

echo ""
echo -e "${GREEN}═══════════════════════════════════════════${NC}"
echo -e "${GREEN}  ✅ Installation Complete!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════${NC}"
echo ""
echo "What was done:"
echo "  ✅ Backup created at: ${BACKUP_DIR}"
echo "  ✅ Symlinks created in ~/.claude/"
echo "  ✅ Dependencies installed"
echo "  ✅ Configuration generated"
echo ""
echo "Next steps:"
echo "  1. Test Claude Code: claude --version"
echo "  2. Start a session: claude"
echo "  3. Verify agents load: Type a message and check skills"
echo "  4. Check MCP servers: Use an MCP-powered command"
echo ""
echo "If anything goes wrong:"
echo "  - Restore backup: rm -rf ~/.claude && mv ${BACKUP_DIR} ~/.claude"
echo "  - Check logs: cat ~/.claude/debug/*.log"
echo ""
echo "Repository is now active. Any changes you make in:"
echo "  ${REPO_ROOT}"
echo "will be immediately reflected in Claude Code."
echo ""
