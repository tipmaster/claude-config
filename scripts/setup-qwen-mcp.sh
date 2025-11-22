#!/bin/bash
# Setup script for Qwen CLI MCP servers
# Registers all 9 MCP servers using 'qwen mcp add' commands

set -e

echo "🤖 Setting up Qwen CLI MCP servers..."
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
    qwen mcp remove "$server" 2>/dev/null || true
done
echo ""

# Add MCP servers
echo "➕ Adding MCP servers..."
echo ""

# 1. Serena - Code analysis and semantic tools
echo "1/9 Adding serena..."
qwen mcp add serena uvx \
    -t stdio \
    -- --from git+https://github.com/oraios/serena serena start-mcp-server --context ide-assistant

# 2. Headless Terminal - Terminal automation
echo "2/9 Adding headless-terminal..."
qwen mcp add headless-terminal /usr/local/bin/ht-mcp \
    -t stdio

# 3. DataForSEO - SEO and search data
echo "3/9 Adding dataforseo..."
qwen mcp add dataforseo node \
    -t stdio \
    -e "DATAFORSEO_USERNAME=$DATAFORSEO_USERNAME" \
    -e "DATAFORSEO_PASSWORD=$DATAFORSEO_PASSWORD" \
    -- /Users/administrator/dev/tfwg/claude-config/mcp-servers/mcp-seo/build/main/main/cli.js

# 4. Chrome Bridge - Browser automation
echo "4/9 Adding chrome-bridge..."
qwen mcp add chrome-bridge mcp-chrome-stdio \
    -t stdio

# 5. Zen - Multi-model chat and consensus
echo "5/9 Adding zen..."
qwen mcp add zen uvx \
    -t stdio \
    -e "GEMINI_API_KEY=$GEMINI_API_KEY" \
    -e "OPENAI_API_KEY=$OPENAI_API_KEY" \
    -e "DEFAULT_MODEL=auto" \
    -e "DISABLED_TOOLS=analyze,refactor,testgen,secaudit,docgen,tracer" \
    -- --from git+https://github.com/BeehiveInnovations/zen-mcp-server.git zen-mcp-server

# 6. Brave Search - Web search
echo "6/9 Adding brave-search..."
qwen mcp add brave-search npx \
    -t stdio \
    -e "BRAVE_API_KEY=$BRAVE_API_KEY" \
    -- -y @modelcontextprotocol/server-brave-search

# 7. Filesystem - File operations
echo "7/9 Adding filesystem..."
qwen mcp add filesystem npx \
    -t stdio \
    -- -y @modelcontextprotocol/server-filesystem /Users/administrator/dev

# 8. Memory - Knowledge graph
echo "8/9 Adding memory..."
qwen mcp add memory npx \
    -t stdio \
    -- -y @modelcontextprotocol/server-memory

# 9. Promos - Promo/offers data
echo "9/9 Adding promos..."
qwen mcp add promos node \
    -t stdio \
    -- /Users/administrator/dev/tfwg/promos/mcp-server.js

echo ""
echo "✅ All 9 MCP servers registered successfully!"
echo ""
echo "To verify, run: qwen mcp list"
echo ""
