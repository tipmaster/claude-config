#!/usr/bin/env bash
#
# generate-config.sh
# Generates ~/.claude/settings.json from templates + .env
#
# Usage: ./scripts/generate-config.sh [profile]
#   profile: laptop (default) or server
#

set -euo pipefail

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo -e "${GREEN}=== Claude Config Generator ===${NC}"
echo ""

# Detect profile if not provided
PROFILE="${1:-}"
if [ -z "$PROFILE" ]; then
    # Try to detect from .env
    if [ -f "${REPO_ROOT}/.env" ]; then
        source "${REPO_ROOT}/.env"
        PROFILE="${CLAUDE_PLATFORM:-laptop}"
    else
        PROFILE="laptop"
    fi
fi

echo "Profile: ${PROFILE}"
echo "Repository: ${REPO_ROOT}"
echo ""

# Check requirements
if ! command -v jq &> /dev/null; then
    echo -e "${RED}Error: jq is required but not installed${NC}"
    echo "Install with:"
    echo "  macOS: brew install jq"
    echo "  Linux: sudo apt-get install jq  or  sudo dnf install jq"
    exit 1
fi

# Check for .env file
if [ ! -f "${REPO_ROOT}/.env" ]; then
    echo -e "${RED}Error: .env file not found${NC}"
    echo "Create one from template:"
    echo "  cp .env.example .env"
    echo "  vim .env  # Add your API keys"
    exit 1
fi

# Load environment variables
echo "Loading .env..."
set -a  # Automatically export all variables
source "${REPO_ROOT}/.env"
set +a

# Set REPO_ROOT if not in .env
export REPO_ROOT="${REPO_ROOT}"
export HOME="${HOME}"

# Verify required API keys
MISSING_KEYS=()
if [ -z "${GEMINI_API_KEY:-}" ] || [ "${GEMINI_API_KEY}" = "your_gemini_api_key_here" ]; then
    MISSING_KEYS+=("GEMINI_API_KEY")
fi
if [ -z "${OPENAI_API_KEY:-}" ] || [ "${OPENAI_API_KEY}" = "your_openai_api_key_here" ]; then
    MISSING_KEYS+=("OPENAI_API_KEY")
fi

if [ ${#MISSING_KEYS[@]} -gt 0 ]; then
    echo -e "${YELLOW}Warning: The following API keys are not set:${NC}"
    for key in "${MISSING_KEYS[@]}"; do
        echo "  - $key"
    done
    echo ""
    echo "Edit .env and add your keys, then run this script again."
    echo ""
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Set default values for optional variables
export DISABLED_TOOLS="${DISABLED_TOOLS:-analyze,refactor,testgen,secaudit,docgen,tracer}"
export DEFAULT_MODEL="${DEFAULT_MODEL:-auto}"
export GOOGLE_API_KEY="${GOOGLE_API_KEY:-${GEMINI_API_KEY}}"
export OPENROUTER_API_KEY="${OPENROUTER_API_KEY:-}"
export ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-}"

# File paths
BASE_CONFIG="${REPO_ROOT}/config/base/settings.base.json"
PROFILE_CONFIG="${REPO_ROOT}/config/profiles/${PROFILE}.json"
OUTPUT_CONFIG="${HOME}/.claude/settings.json"

# Check if base config exists
if [ ! -f "$BASE_CONFIG" ]; then
    echo -e "${RED}Error: Base config not found: $BASE_CONFIG${NC}"
    exit 1
fi

# Check if profile config exists
if [ ! -f "$PROFILE_CONFIG" ]; then
    echo -e "${RED}Error: Profile config not found: $PROFILE_CONFIG${NC}"
    echo "Available profiles:"
    ls -1 "${REPO_ROOT}/config/profiles/" | sed 's/\.json$//' | sed 's/^/  - /'
    exit 1
fi

echo "Merging configs..."
echo "  Base: $BASE_CONFIG"
echo "  Profile: $PROFILE_CONFIG"
echo ""

# Merge base + profile using jq
# Strategy: deep merge where profile overwrites base
MERGED=$(jq -s '.[0] * .[1]' "$BASE_CONFIG" "$PROFILE_CONFIG")

# Perform environment variable substitution
echo "Substituting environment variables..."

# Export a function to do the substitution
substitute_vars() {
    local content="$1"
    # Replace ${VAR} with actual values
    # Handle all our known variables
    content="${content//\$\{REPO_ROOT\}/${REPO_ROOT}}"
    content="${content//\$\{HOME\}/${HOME}}"
    content="${content//\$\{GEMINI_API_KEY\}/${GEMINI_API_KEY}}"
    content="${content//\$\{GOOGLE_API_KEY\}/${GOOGLE_API_KEY}}"
    content="${content//\$\{OPENAI_API_KEY\}/${OPENAI_API_KEY}}"
    content="${content//\$\{ANTHROPIC_API_KEY\}/${ANTHROPIC_API_KEY:-}}"
    content="${content//\$\{OPENROUTER_API_KEY\}/${OPENROUTER_API_KEY:-}}"
    content="${content//\$\{DISABLED_TOOLS\}/${DISABLED_TOOLS}}"
    content="${content//\$\{DEFAULT_MODEL\}/${DEFAULT_MODEL}}"
    echo "$content"
}

# Perform substitution
FINAL_CONFIG=$(substitute_vars "$MERGED")

# Ensure output directory exists
mkdir -p "$(dirname "$OUTPUT_CONFIG")"

# Write output
echo "$FINAL_CONFIG" > "$OUTPUT_CONFIG"

echo -e "${GREEN}✅ Configuration generated successfully!${NC}"
echo ""
echo "Output: $OUTPUT_CONFIG"
echo ""

# Validate JSON
if jq empty "$OUTPUT_CONFIG" 2>/dev/null; then
    echo -e "${GREEN}✅ Output is valid JSON${NC}"
else
    echo -e "${RED}❌ Output is not valid JSON!${NC}"
    exit 1
fi

# Show MCP servers configured
echo ""
echo "MCP Servers configured:"
jq -r '.mcpServers | keys[]' "$OUTPUT_CONFIG" | sed 's/^/  - /'

echo ""
echo -e "${GREEN}Done!${NC}"
echo ""
echo "Next steps:"
echo "  1. Test Claude Code still works"
echo "  2. Run: claude --version"
echo "  3. Check MCP servers load correctly"
