#!/bin/bash
# Quick start script for Browser Automation REPL in Docker
# Run this to get started immediately!

set -e

echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║     Browser Automation REPL - Docker Quick Start                ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""

# Check Docker is installed
if ! command -v docker &> /dev/null; then
	echo "❌ Error: Docker is not installed!"
	echo "   Install from: https://docs.docker.com/get-docker/"
	exit 1
fi

# Check Docker is accessible without sudo
if ! docker ps &> /dev/null; then
	echo "❌ Error: Cannot access Docker daemon!"
	echo "   You may need to add yourself to the docker group:"
	echo "   sudo usermod -aG docker \$USER"
	echo "   Then log out and back in."
	exit 1
fi

echo "✓ Docker is installed and accessible"
echo ""

# Ask user which LLM to use
echo "Which LLM provider do you want to use?"
echo ""
echo "1) Ollama (Free, Local) - requires Ollama running on host"
echo "2) OpenAI (Paid, Cloud) - requires API key"
echo "3) Google Gemini (Paid, Cloud) - requires API key"
echo "4) Build container only (no run)"
echo ""
read -p "Enter choice [1-4]: " choice

case $choice in
	1)
		echo ""
		echo "[→] Selected: Ollama (Local, Free)"
		echo ""

		# Check if Ollama is running
		if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
			echo "⚠️  Warning: Ollama doesn't seem to be running on localhost:11434"
			echo ""
			echo "To install and start Ollama:"
			echo "  curl -fsSL https://ollama.com/install.sh | sh"
			echo "  ollama serve &"
			echo "  ollama pull deepseek-r1:14b"
			echo ""
			read -p "Continue anyway? [y/N]: " continue_choice
			if [[ ! $continue_choice =~ ^[Yy]$ ]]; then
				exit 1
			fi
		else
			echo "✓ Ollama is running on localhost:11434"
		fi

		echo ""
		echo "[→] Building Docker container..."
		docker-compose build repl-ollama

		echo ""
		echo "[→] Starting REPL with Ollama + DeepSeek-R1:14b..."
		echo ""
		docker-compose run --rm repl-ollama
		;;

	2)
		echo ""
		echo "[→] Selected: OpenAI (Cloud, Paid)"
		echo ""

		if [ -z "$OPENAI_API_KEY" ]; then
			echo "Enter your OpenAI API key:"
			read -s OPENAI_API_KEY
			export OPENAI_API_KEY
		else
			echo "✓ Using OPENAI_API_KEY from environment"
		fi

		echo ""
		echo "[→] Building Docker container..."
		docker-compose build repl-openai

		echo ""
		echo "[→] Starting REPL with OpenAI GPT-4o-mini..."
		echo ""
		docker-compose run --rm repl-openai
		;;

	3)
		echo ""
		echo "[→] Selected: Google Gemini (Cloud, Paid)"
		echo ""

		if [ -z "$GOOGLE_API_KEY" ]; then
			echo "Enter your Google API key:"
			read -s GOOGLE_API_KEY
			export GOOGLE_API_KEY
		else
			echo "✓ Using GOOGLE_API_KEY from environment"
		fi

		echo ""
		echo "[→] Building Docker container..."
		docker-compose build repl-gemini

		echo ""
		echo "[→] Starting REPL with Google Gemini 2.0 Flash..."
		echo ""
		docker-compose run --rm repl-gemini
		;;

	4)
		echo ""
		echo "[→] Building all containers..."
		docker-compose build
		echo ""
		echo "✓ Containers built successfully!"
		echo ""
		echo "To run:"
		echo "  docker-compose run --rm repl-ollama"
		echo "  docker-compose run --rm repl-openai"
		echo "  docker-compose run --rm repl-gemini"
		;;

	*)
		echo "Invalid choice!"
		exit 1
		;;
esac

echo ""
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║                       Session Ended                              ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
