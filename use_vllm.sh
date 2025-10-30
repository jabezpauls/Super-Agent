#!/bin/bash
# Run browser_use_repl.py with vLLM backend

# Set vLLM endpoint
export OPENAI_API_KEY="dummy"
export OPENAI_BASE_URL="http://localhost:8000/v1"

# Choose model (must match what vLLM is running)
MODEL="Qwen/Qwen2.5-14B-Instruct"

echo "Using vLLM at http://localhost:8000/v1"
echo "Model: $MODEL"
echo ""

# Run REPL with any additional arguments passed to this script
python browser_use_repl.py \
  --provider openai \
  --model "$MODEL" \
  "$@"
