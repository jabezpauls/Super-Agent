#!/bin/bash
# Setup persistent browser profile for browser-use
# This keeps you logged in across sessions

set -e

PROFILE_DIR="$HOME/.browser-use-profile"
CDP_PORT=9222

echo "Setting up persistent browser profile..."
echo "Profile location: $PROFILE_DIR"
echo ""

# Check if Chrome is already running on this port
if curl -s http://localhost:$CDP_PORT/json/version >/dev/null 2>&1; then
    echo "⚠️  Chrome is already running on port $CDP_PORT"
    echo ""
    echo "Options:"
    echo "  1. Kill existing Chrome: pkill -f 'chrome.*remote-debugging-port=$CDP_PORT'"
    echo "  2. Use different port: Change CDP_PORT in this script"
    echo ""
    exit 1
fi

# Create profile directory if it doesn't exist
mkdir -p "$PROFILE_DIR"

echo "Starting Chrome with persistent profile..."
google-chrome \
  --remote-debugging-port=$CDP_PORT \
  --user-data-dir="$PROFILE_DIR" \
  --no-first-run \
  --no-default-browser-check &

CHROME_PID=$!

echo ""
echo "✅ Chrome started with PID: $CHROME_PID"
echo ""
echo "📋 SETUP INSTRUCTIONS:"
echo ""
echo "1. Chrome should have opened in a new window"
echo "2. Sign in to your accounts (Gmail, Google Calendar, etc.)"
echo "3. Browse to any sites you need to be logged into"
echo "4. Leave Chrome OPEN"
echo ""
echo "Once signed in, run the REPL in a new terminal:"
echo ""
echo "  python browser_use_repl.py --model gpt-oss:20b --cdp-url http://localhost:$CDP_PORT"
echo ""
echo "Or use the helper script:"
echo "  ./use_persistent_browser.sh"
echo ""
echo "Press Ctrl+C to stop this script (Chrome will keep running)"
echo ""

# Wait and show connection info
sleep 3
if curl -s http://localhost:$CDP_PORT/json/version >/dev/null 2>&1; then
    echo "✅ Chrome is ready for connections!"
    echo ""
    curl -s http://localhost:$CDP_PORT/json/version | python3 -c "
import json, sys
data = json.load(sys.stdin)
print(f\"Browser: {data.get('Browser', 'Unknown')}\")
print(f\"WebSocket: {data.get('webSocketDebuggerUrl', 'Unknown')}\")
"
else
    echo "⚠️  Chrome may still be starting up..."
fi

# Keep script running
echo ""
echo "Chrome is running. Press Ctrl+C to exit (Chrome will continue running)"
wait $CHROME_PID
