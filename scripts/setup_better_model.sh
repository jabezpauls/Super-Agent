#!/bin/bash

# Script to help users upgrade to better models for browser-use REPL

set -e

echo "========================================="
echo "Browser-Use REPL - Model Setup Helper"
echo "========================================="
echo ""

echo "Current default model: qwen2.5:7b"
echo ""
echo "Recommended upgrades for better performance:"
echo "  1) DeepSeek-R1:7b     - Best local model (better reasoning, less drift)"
echo "  2) Qwen2.5:14b        - Larger, more capable (needs 16GB RAM)"
echo "  3) GPT-4o (OpenAI)    - Best overall (requires API key, costs money)"
echo "  4) Gemini Flash       - Fast & cheap cloud option (requires API key)"
echo "  5) Keep qwen2.5:7b    - Stay with default"
echo ""
read -p "Select an option (1-5): " choice

case $choice in
    1)
        echo ""
        echo "========================================="
        echo "Setting up DeepSeek-R1:7b"
        echo "========================================="
        echo ""
        echo "This model offers:"
        echo "  ✓ Better reasoning and focus"
        echo "  ✓ Less memory drift"
        echo "  ✓ Shows thinking process"
        echo "  ✓ Runs on most hardware (8GB+ RAM)"
        echo ""

        # Check if already installed
        if ollama list | grep -q "deepseek-r1:7b"; then
            echo "✓ DeepSeek-R1:7b already installed"
        else
            echo "Downloading DeepSeek-R1:7b (this may take a few minutes)..."
            ollama pull deepseek-r1:7b
            echo "✓ Download complete"
        fi

        echo ""
        echo "========================================="
        echo "Setup Complete!"
        echo "========================================="
        echo ""
        echo "To use DeepSeek-R1, run:"
        echo "  uv run python browser_use_repl.py --model deepseek-r1:7b --max-steps 8 --verbose"
        echo ""
        echo "Or add this alias to your shell config:"
        echo "  alias repl-deepseek='uv run python browser_use_repl.py --model deepseek-r1:7b --max-steps 8 --verbose'"
        echo ""

        read -p "Start REPL with DeepSeek-R1 now? (y/n): " start_now
        if [ "$start_now" = "y" ] || [ "$start_now" = "Y" ]; then
            echo "Starting..."
            uv run python browser_use_repl.py --model deepseek-r1:7b --max-steps 8 --verbose
        fi
        ;;

    2)
        echo ""
        echo "========================================="
        echo "Setting up Qwen2.5:14b"
        echo "========================================="
        echo ""
        echo "This model offers:"
        echo "  ✓ Better general knowledge"
        echo "  ✓ Multilingual support (29 languages)"
        echo "  ✓ Strong vision capabilities"
        echo "  ⚠ Requires 16GB+ RAM"
        echo ""

        # Check RAM
        total_ram=$(free -g | awk '/^Mem:/{print $2}')
        if [ "$total_ram" -lt 16 ]; then
            echo "⚠️  WARNING: Your system has less than 16GB RAM"
            echo "   Qwen2.5:14b may run slowly or fail to load"
            read -p "Continue anyway? (y/n): " continue_anyway
            if [ "$continue_anyway" != "y" ] && [ "$continue_anyway" != "Y" ]; then
                echo "Cancelled. Consider using DeepSeek-R1:7b instead."
                exit 0
            fi
        fi

        # Check if already installed
        if ollama list | grep -q "qwen2.5:14b"; then
            echo "✓ Qwen2.5:14b already installed"
        else
            echo "Downloading Qwen2.5:14b (this may take several minutes)..."
            ollama pull qwen2.5:14b
            echo "✓ Download complete"
        fi

        echo ""
        echo "========================================="
        echo "Setup Complete!"
        echo "========================================="
        echo ""
        echo "To use Qwen2.5:14b, run:"
        echo "  uv run python browser_use_repl.py --model qwen2.5:14b --max-steps 10 --verbose"
        echo ""

        read -p "Start REPL with Qwen2.5:14b now? (y/n): " start_now
        if [ "$start_now" = "y" ] || [ "$start_now" = "Y" ]; then
            echo "Starting..."
            uv run python browser_use_repl.py --model qwen2.5:14b --max-steps 10 --verbose
        fi
        ;;

    3)
        echo ""
        echo "========================================="
        echo "Setting up GPT-4o (OpenAI)"
        echo "========================================="
        echo ""
        echo "This model offers:"
        echo "  ✓ Best overall performance"
        echo "  ✓ Excellent context retention"
        echo "  ✓ Minimal memory drift"
        echo "  ✓ Handles complex tasks easily"
        echo "  ⚠ Requires API key and costs money (~$5-15 per 1M tokens)"
        echo ""

        # Check if API key exists
        if [ -f .env ] && grep -q "OPENAI_API_KEY" .env; then
            echo "✓ Found existing OPENAI_API_KEY in .env"
        else
            echo "You need an OpenAI API key."
            echo "Get one at: https://platform.openai.com/api-keys"
            echo ""
            read -p "Enter your OpenAI API key (or press Enter to skip): " api_key

            if [ -n "$api_key" ]; then
                if [ -f .env ]; then
                    echo "OPENAI_API_KEY=$api_key" >> .env
                else
                    echo "OPENAI_API_KEY=$api_key" > .env
                fi
                echo "✓ API key saved to .env"
            else
                echo "Skipped. You'll need to set OPENAI_API_KEY before using GPT-4o"
                exit 0
            fi
        fi

        echo ""
        echo "========================================="
        echo "Setup Complete!"
        echo "========================================="
        echo ""
        echo "To use GPT-4o, run:"
        echo "  uv run python browser_use_repl.py --provider openai --model gpt-4o --max-steps 20"
        echo ""

        read -p "Start REPL with GPT-4o now? (y/n): " start_now
        if [ "$start_now" = "y" ] || [ "$start_now" = "Y" ]; then
            echo "Starting..."
            uv run python browser_use_repl.py --provider openai --model gpt-4o --max-steps 20
        fi
        ;;

    4)
        echo ""
        echo "========================================="
        echo "Setting up Gemini 2.0 Flash (Google)"
        echo "========================================="
        echo ""
        echo "This model offers:"
        echo "  ✓ Fast response times"
        echo "  ✓ Low cost (free tier available)"
        echo "  ✓ Good balance of speed and accuracy"
        echo "  ⚠ Requires API key"
        echo ""

        # Check if API key exists
        if [ -f .env ] && grep -q "GOOGLE_API_KEY" .env; then
            echo "✓ Found existing GOOGLE_API_KEY in .env"
        else
            echo "You need a Google AI API key."
            echo "Get one at: https://aistudio.google.com/apikey"
            echo ""
            read -p "Enter your Google API key (or press Enter to skip): " api_key

            if [ -n "$api_key" ]; then
                if [ -f .env ]; then
                    echo "GOOGLE_API_KEY=$api_key" >> .env
                else
                    echo "GOOGLE_API_KEY=$api_key" > .env
                fi
                echo "✓ API key saved to .env"
            else
                echo "Skipped. You'll need to set GOOGLE_API_KEY before using Gemini"
                exit 0
            fi
        fi

        echo ""
        echo "========================================="
        echo "Setup Complete!"
        echo "========================================="
        echo ""
        echo "To use Gemini Flash, run:"
        echo "  uv run python browser_use_repl.py --provider google --model gemini-2.0-flash-exp --max-steps 15"
        echo ""

        read -p "Start REPL with Gemini Flash now? (y/n): " start_now
        if [ "$start_now" = "y" ] || [ "$start_now" = "Y" ]; then
            echo "Starting..."
            uv run python browser_use_repl.py --provider google --model gemini-2.0-flash-exp --max-steps 15
        fi
        ;;

    5)
        echo ""
        echo "Keeping default model: qwen2.5:7b"
        echo ""
        echo "Note: This model may experience memory drift on complex tasks."
        echo "Consider upgrading to DeepSeek-R1:7b for better performance."
        echo ""
        echo "To start the REPL with default settings:"
        echo "  uv run python browser_use_repl.py --verbose"
        echo ""

        read -p "Start REPL now? (y/n): " start_now
        if [ "$start_now" = "y" ] || [ "$start_now" = "Y" ]; then
            echo "Starting..."
            uv run python browser_use_repl.py --verbose
        fi
        ;;

    *)
        echo "Invalid choice. Exiting."
        exit 1
        ;;
esac

echo ""
echo "For more information, see MODEL_RECOMMENDATIONS.md"
echo "Happy automating! 🚀"
