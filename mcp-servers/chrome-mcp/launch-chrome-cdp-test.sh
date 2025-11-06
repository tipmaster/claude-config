#!/bin/bash

# Launch Chrome with CDP in a test profile (separate from your main profile)
# Useful for testing without affecting your main Chrome profile

echo "Launching Chrome with CDP enabled (Test Profile)..."
echo "This will create a separate Chrome profile for testing."
echo ""

# Create a test profile directory
TEST_PROFILE_DIR="$HOME/.chrome-mcp-test-profile"
mkdir -p "$TEST_PROFILE_DIR"

# Launch Chrome with remote debugging enabled on port 9222
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
        --remote-debugging-port=9222 \
        --user-data-dir="$TEST_PROFILE_DIR" \
        --enable-automation \
        --no-first-run &
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    google-chrome \
        --remote-debugging-port=9222 \
        --user-data-dir="$TEST_PROFILE_DIR" \
        --enable-automation \
        --no-first-run &
else
    echo "Unsupported OS: $OSTYPE"
    exit 1
fi

echo ""
echo "Chrome launched with CDP on port 9222 (Test Profile)"
echo "Profile location: $TEST_PROFILE_DIR"
echo "You can verify the connection at: http://localhost:9222/json/version"