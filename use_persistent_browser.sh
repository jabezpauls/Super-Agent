#!/bin/bash
# Use browser_use_repl.py with persistent Chrome (keeps you logged in)

CDP_PORT=9222
CDP_URL="http://localhost:$CDP_PORT"

# Check if Chrome is running
if ! curl -s $CDP_URL/json/version >/dev/null 2>&1; then
    echo "❌ Chrome is not running with remote debugging on port $CDP_PORT"
    echo ""
    echo "Start it first with:"
    echo "  ./setup_persistent_browser.sh"
    echo ""
    echo "Or manually:"
    echo "  google-chrome --remote-debugging-port=$CDP_PORT --user-data-dir=~/.browser-use-profile &"
    echo ""
    exit 1
fi

echo "✅ Connected to Chrome at $CDP_URL"
echo ""

# Get Chrome info
curl -s $CDP_URL/json/version | python3 -c "
import json, sys
data = json.load(sys.stdin)
print(f\"Browser: {data.get('Browser', 'Unknown')}\")
print(f\"User Agent: {data.get('User-Agent', 'Unknown')}\")
print()
"

# Run REPL with persistent browser connection
python browser_use_repl.py \
  --cdp-url "$CDP_URL" \
  "$@"
