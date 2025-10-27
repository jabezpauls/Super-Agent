#!/bin/bash

# Demo script for Browser-Use Interactive REPL
# This script helps you quickly test the REPL with different configurations

set -e

echo "========================================="
echo "Browser-Use Interactive REPL Demo"
echo "========================================="
echo ""

# Check if Ollama is running
echo "Checking Ollama server..."
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "❌ Ollama server is not running!"
    echo "   Please start it with: ollama serve"
    exit 1
fi
echo "✓ Ollama server is running"
echo ""

# Check if the model is available
echo "Checking for qwen2.5:7b model..."
if ! ollama list | grep -q "qwen2.5:7b"; then
    echo "❌ qwen2.5:7b model not found!"
    echo "   Pulling model (this may take a few minutes)..."
    ollama pull qwen2.5:7b
fi
echo "✓ qwen2.5:7b model is available"
echo ""

# Ask user which mode to run
echo "Select a mode to run:"
echo "  1) Default (verbose, visible browser)"
echo "  2) Quiet mode (minimal output)"
echo "  3) Headless mode (no browser window)"
echo "  4) Custom (specify your own options)"
echo ""
read -p "Enter your choice (1-4): " choice

case $choice in
    1)
        echo ""
        echo "Starting REPL in verbose mode with visible browser..."
        echo "Type your queries and press Enter. Use /help for commands."
        echo ""
        uv run python browser_use_repl.py --verbose
        ;;
    2)
        echo ""
        echo "Starting REPL in quiet mode..."
        echo "Only final results will be shown."
        echo ""
        uv run python browser_use_repl.py --quiet
        ;;
    3)
        echo ""
        echo "Starting REPL in headless mode..."
        echo "Browser will run in the background (no window)."
        echo ""
        uv run python browser_use_repl.py --headless --verbose
        ;;
    4)
        echo ""
        echo "Enter custom options (e.g., --headless --no-vision):"
        read -p "Options: " custom_opts
        echo ""
        echo "Starting REPL with custom options: $custom_opts"
        echo ""
        uv run python browser_use_repl.py $custom_opts
        ;;
    *)
        echo "Invalid choice. Running default mode."
        uv run python browser_use_repl.py --verbose
        ;;
esac
