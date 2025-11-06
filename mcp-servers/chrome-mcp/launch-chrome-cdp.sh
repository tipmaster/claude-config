#!/bin/bash

# Launch Chrome with CDP (Chrome DevTools Protocol) enabled
# This allows the chrome-mcp server to connect to your existing Chrome browser

echo "Launching Chrome with CDP enabled..."
echo "This will allow MCP servers to connect to your browser."
echo ""
echo "IMPORTANT: This will open a new Chrome window. Your existing Chrome windows will remain open."
echo "To use your logged-in sessions, navigate to the sites you want in this new window."
echo ""

# Kill any existing Chrome instances with remote debugging (optional)
# Uncomment the next line if you want to ensure only one CDP-enabled Chrome is running
# pkill -f "chrome.*remote-debugging-port"

# Launch Chrome with remote debugging enabled on port 9222
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
        --remote-debugging-port=9222 \
        --user-data-dir="$HOME/Library/Application Support/Google/Chrome" \
        --profile-directory="Default" \
        --enable-automation \
        --no-first-run &
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    google-chrome \
        --remote-debugging-port=9222 \
        --user-data-dir="$HOME/.config/google-chrome" \
        --profile-directory="Default" \
        --enable-automation \
        --no-first-run &
else
    echo "Unsupported OS: $OSTYPE"
    exit 1
fi

echo ""
echo "Chrome launched with CDP on port 9222"
echo "You can verify the connection at: http://localhost:9222/json/version"
echo ""
echo "The chrome-mcp server can now connect to this Chrome instance."
echo "Use your existing logged-in sessions by navigating to the desired sites."