#!/bin/bash
# Setup script for Droid CLI MCP servers
# Registers all 9 MCP servers using 'droid mcp add' commands

set -e

echo "🤖 Setting up Droid CLI MCP servers..."
echo ""

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
    echo "Please set these variables in your shell profile or .env file"
    exit 1
fi

echo "✅ All required environment variables found"
echo ""

# Remove existing MCP servers (if any) to avoid duplicates
echo "📝 Removing any existing MCP server configurations..."
for server in serena headless-terminal dataforseo chrome-bridge zen brave-search filesystem memory promos; do
    droid mcp remove "$server" 2>/dev/null || true
done
echo ""

# Add MCP servers
echo "➕ Adding MCP servers..."
echo ""

# 1. Serena - Code analysis and semantic tools
echo "1/9 Adding serena..."
droid mcp add serena --type stdio -- \
    uvx --from git+https://github.com/oraios/serena serena start-mcp-server --context ide-assistant

# 2. Headless Terminal - Terminal automation
echo "2/9 Adding headless-terminal..."
droid mcp add headless-terminal --type stdio -- \
    /usr/local/bin/ht-mcp

# 3. DataForSEO - SEO and search data
echo "3/9 Adding dataforseo..."
droid mcp add dataforseo --type stdio \
    --env "DATAFORSEO_USERNAME=$DATAFORSEO_USERNAME" \
    --env "DATAFORSEO_PASSWORD=$DATAFORSEO_PASSWORD" -- \
    node /Users/administrator/dev/tfwg/claude-config/mcp-servers/mcp-seo/build/main/main/cli.js

# 4. Chrome Bridge - Browser automation
echo "4/9 Adding chrome-bridge..."
droid mcp add chrome-bridge --type stdio -- \
    mcp-chrome-stdio

# 5. Zen - Multi-model chat and consensus
echo "5/9 Adding zen..."
droid mcp add zen --type stdio \
    --env "GEMINI_API_KEY=$GEMINI_API_KEY" \
    --env "OPENAI_API_KEY=$OPENAI_API_KEY" \
    --env "DEFAULT_MODEL=auto" \
    --env "DISABLED_TOOLS=analyze,refactor,testgen,secaudit,docgen,tracer" -- \
    uvx --from git+https://github.com/BeehiveInnovations/zen-mcp-server.git zen-mcp-server

# 6. Brave Search - Web search
echo "6/9 Adding brave-search..."
droid mcp add brave-search --type stdio \
    --env "BRAVE_API_KEY=$BRAVE_API_KEY" -- \
    npx -y @modelcontextprotocol/server-brave-search

# 7. Filesystem - File operations
echo "7/9 Adding filesystem..."
droid mcp add filesystem --type stdio -- \
    npx -y @modelcontextprotocol/server-filesystem /Users/administrator/dev

# 8. Memory - Knowledge graph
echo "8/9 Adding memory..."
droid mcp add memory --type stdio -- \
    npx -y @modelcontextprotocol/server-memory

# 9. Promos - Promo/offers data
echo "9/9 Adding promos..."
droid mcp add promos --type stdio -- \
    node /Users/administrator/dev/tfwg/promos/mcp-server.js

echo ""
echo "✅ All 9 MCP servers registered successfully!"
echo ""
echo "To verify, run: droid mcp"
echo ""
