#!/bin/bash
# Generate Codex config.toml from template with environment variable substitution

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TEMPLATE="$REPO_ROOT/config/codex-settings.toml"
OUTPUT="$HOME/.codex/config.toml"

echo "🔧 Generating Codex config from template..."

# Check if template exists
if [ ! -f "$TEMPLATE" ]; then
    echo "❌ Template not found: $TEMPLATE"
    exit 1
fi

# Check for required environment variables
required_vars=(
    "GEMINI_API_KEY"
    "OPENAI_API_KEY"
    "BRAVE_API_KEY"
    "DATAFORSEO_USERNAME"
    "DATAFORSEO_PASSWORD"
)

missing_vars=()
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        missing_vars+=("$var")
    fi
done

if [ ${#missing_vars[@]} -gt 0 ]; then
    echo "❌ Missing required environment variables:"
    printf '   - %s\n' "${missing_vars[@]}"
    echo ""
    echo "Please set these variables in your .env file or export them:"
    echo "  source ~/.env"
    echo "  or"
    echo "  export GEMINI_API_KEY=\"your-key-here\""
    exit 1
fi

# Create backup if config exists
if [ -f "$OUTPUT" ]; then
    backup="$OUTPUT.backup.$(date +%Y%m%d_%H%M%S)"
    echo "📦 Backing up existing config to: $backup"
    cp "$OUTPUT" "$backup"
fi

# Generate config by substituting environment variables
echo "📝 Substituting environment variables..."
envsubst < "$TEMPLATE" > "$OUTPUT"

# Set restrictive permissions
chmod 600 "$OUTPUT"

echo "✅ Codex config generated successfully!"
echo "   Location: $OUTPUT"
echo ""
echo "🔍 Verify the config:"
echo "   cat $OUTPUT | grep -v 'API_KEY\\|PASSWORD' | head -30"
echo ""
echo "🚀 Launch Codex:"
echo "   codex"
