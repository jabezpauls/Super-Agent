#!/bin/bash
# Run browser_use_repl.py with vLLM backend

# Set vLLM endpoint
export OPENAI_API_KEY="dummy"
export OPENAI_BASE_URL="http://localhost:8000/v1"

# Choose model (must match what vLLM is running)
MODEL="openai/gpt-oss-20b"

echo "Using vLLM at http://localhost:8000/v1"
echo "Model: $MODEL"
echo "⚠️  Vision mode disabled (text-only model)"
echo ""

# Run REPL with any additional arguments passed to this script
# IMPORTANT: --no-vision flag is required for text-only models like GPT-OSS/Phi-4
python browser_use_repl.py \
  --provider openai \
  --model "$MODEL" \
  --no-vision \
  --verbose \
  "$@"
