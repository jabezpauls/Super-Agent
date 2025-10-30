#!/bin/bash
# Start vLLM in Docker with GPU support
# Choose your model by uncommenting one of the MODEL lines below

set -e

# Stop and remove existing container
echo "Stopping existing vLLM container..."
docker stop vllm 2>/dev/null || true
docker rm vllm 2>/dev/null || true

# Choose your model (uncomment one):

# RECOMMENDED: Qwen2.5-14B (Best balance)
MODEL="Qwen/Qwen2.5-14B-Instruct"

# Alternative 1: DeepSeek R1 14B (Best reasoning)
# MODEL="deepseek-ai/DeepSeek-R1-Distill-Qwen-14B"

# Alternative 2: Qwen2.5-7B (Fastest, less VRAM)
# MODEL="Qwen/Qwen2.5-7B-Instruct"

# Alternative 3: Qwen2.5-32B (Best quality, needs 24GB VRAM)
# MODEL="Qwen/Qwen2.5-32B-Instruct"

echo "Starting vLLM with model: $MODEL"

docker run -d \
  --gpus all \
  --name vllm \
  -p 8000:8000 \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  --shm-size 8g \
  --restart unless-stopped \
  vllm/vllm-openai:latest \
  --model "$MODEL" \
  --dtype auto \
  --gpu-memory-utilization 0.9 \
  --max-model-len 8192 \
  --trust-remote-code

echo ""
echo "✅ vLLM container started!"
echo ""
echo "Waiting for model to load (this may take 2-5 minutes)..."
echo "You can check progress with: docker logs -f vllm"
echo ""

# Wait for vLLM to be ready
echo "Testing vLLM endpoint..."
for i in {1..60}; do
  if curl -s http://localhost:8000/v1/models >/dev/null 2>&1; then
    echo ""
    echo "✅ vLLM is ready!"
    echo ""
    echo "Model info:"
    curl -s http://localhost:8000/v1/models | python3 -m json.tool
    echo ""
    echo "Usage:"
    echo "  export OPENAI_API_KEY='dummy'"
    echo "  export OPENAI_BASE_URL='http://localhost:8000/v1'"
    echo "  python browser_use_repl.py --provider openai --model $MODEL"
    echo ""
    exit 0
  fi
  echo -n "."
  sleep 5
done

echo ""
echo "⚠️  vLLM is taking longer than expected to start."
echo "Check logs with: docker logs -f vllm"
