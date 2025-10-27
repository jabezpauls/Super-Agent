# Running Browser Automation REPL in Docker

This guide explains how to run the Browser Automation REPL inside Docker containers **without needing sudo access** on your host machine.

---

## Why Docker?

✅ **No sudo required** - Runs as non-root user inside container
✅ **Consistent environment** - Works across different systems
✅ **Isolated** - Doesn't interfere with host system packages
✅ **Portable** - Same setup on dev, staging, production
✅ **Easy LLM switching** - Different containers for different providers

---

## Quick Start

### Option 1: Using Docker Compose (Recommended)

```bash
# 1. Build the container
docker-compose build repl-ollama

# 2. Run with local Ollama (free, requires Ollama on host)
docker-compose run --rm repl-ollama

# OR run with OpenAI (requires API key)
export OPENAI_API_KEY="your-key-here"
docker-compose run --rm repl-openai

# OR run with Google Gemini (requires API key)
export GOOGLE_API_KEY="your-key-here"
docker-compose run --rm repl-gemini
```

### Option 2: Using Docker Directly

```bash
# Build the container
docker build -f Dockerfile.repl -t browser-repl:latest .

# Run interactively
docker run -it --rm \
  -e OPENAI_API_KEY="your-key-here" \
  browser-repl:latest \
  browser_use_repl.py --provider openai --model gpt-4o-mini --headless
```

---

## Prerequisites

### On Your Host Machine:

1. **Docker installed** (does NOT require sudo if you're in docker group)
   ```bash
   # Check Docker version
   docker --version

   # Check if you can run Docker without sudo
   docker ps

   # If you get permission denied, add yourself to docker group (requires sudo ONCE)
   # sudo usermod -aG docker $USER
   # Then log out and back in
   ```

2. **For Ollama mode** (optional, free):
   ```bash
   # Install Ollama on host machine
   curl -fsSL https://ollama.com/install.sh | sh

   # Pull DeepSeek-R1 model
   ollama pull deepseek-r1:14b

   # Start Ollama server (runs in background)
   ollama serve
   ```

3. **For cloud LLM modes** (optional, paid):
   - OpenAI API key: https://platform.openai.com/api-keys
   - Google API key: https://ai.google.dev/
   - Anthropic API key: https://console.anthropic.com/

---

## Container Architecture

The Docker setup includes:

```
Dockerfile.repl
├── Base: Python 3.11 slim
├── Google Chrome (stable)
├── Xvfb (virtual display for headless mode)
├── Non-root user (browseruser, uid=1000)
├── UV package manager
└── Browser-use library + REPL

Runs without ANY sudo/root access after build!
```

---

## Usage Examples

### 1. Interactive REPL with Ollama (Free, Local)

```bash
# Start the container
docker-compose run --rm repl-ollama

# Inside container, you can now use the REPL:
> get the subscriber count for youtube channel @mkbhd
> search google for "python tutorials" and give me top 3 results
> /history
> /exit
```

### 2. One-Shot Task with OpenAI

```bash
# Run a single task and exit
docker run -it --rm \
  -e OPENAI_API_KEY="sk-..." \
  browser-repl:latest \
  browser_use_repl.py \
  --provider openai \
  --model gpt-4o-mini \
  --headless \
  --query "get current bitcoin price from coinbase"
```

### 3. Headful Mode (See Browser GUI)

```bash
# Requires X11 forwarding on host
docker run -it --rm \
  -e DISPLAY=$DISPLAY \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  -e OPENAI_API_KEY="sk-..." \
  browser-repl:latest \
  browser_use_repl.py --model gpt-4o-mini
```

### 4. With Prompt Optimization

```bash
docker-compose run --rm repl-ollama \
  browser_use_repl.py \
  --model deepseek-r1:14b \
  --headless \
  --optimize \
  --max-steps 10
```

### 5. Custom Chrome Profile

```bash
# Mount your Chrome profile from host
docker run -it --rm \
  -v ~/.config/google-chrome:/home/browseruser/chrome-profile:ro \
  -e OPENAI_API_KEY="sk-..." \
  browser-repl:latest \
  browser_use_repl.py \
  --user-data-dir /home/browseruser/chrome-profile \
  --model gpt-4o-mini
```

---

## Environment Variables

Configure via `.env` file or export:

```bash
# LLM API Keys
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=AIza...

# Ollama connection (if running on host)
OLLAMA_HOST=http://host.docker.internal:11434

# Display for headless mode
DISPLAY=:99
```

Create `.env` file:

```bash
cat > .env << 'EOF'
OPENAI_API_KEY=your-key-here
GOOGLE_API_KEY=your-key-here
ANTHROPIC_API_KEY=your-key-here
EOF
```

Then use with docker-compose:

```bash
docker-compose --env-file .env run --rm repl-openai
```

---

## Docker Compose Services

The `docker-compose.yml` defines 4 services:

### 1. `repl-ollama` (Free, Local LLM)
```bash
docker-compose run --rm repl-ollama
```
- Uses Ollama on host machine (via `host.docker.internal`)
- Default model: `deepseek-r1:14b`
- Zero cost, full privacy

### 2. `repl-openai` (Cloud LLM)
```bash
export OPENAI_API_KEY="sk-..."
docker-compose run --rm repl-openai
```
- Uses OpenAI GPT-4o-mini
- Requires API key
- Fast, reliable

### 3. `repl-gemini` (Cloud LLM)
```bash
export GOOGLE_API_KEY="AIza..."
docker-compose run --rm repl-gemini
```
- Uses Google Gemini 2.0 Flash
- Requires API key
- Cost-effective

### 4. `ollama` (Optional Ollama Server)
```bash
docker-compose up -d ollama
```
- Run Ollama inside Docker instead of host
- Useful if you can't install Ollama on host
- Requires `--gpus all` for GPU support

---

## Building the Container

### Build with Docker Compose:
```bash
docker-compose build repl-ollama
```

### Build with Docker directly:
```bash
docker build -f Dockerfile.repl -t browser-repl:latest .
```

### Build for specific platform:
```bash
# For Linux AMD64
docker build --platform linux/amd64 -f Dockerfile.repl -t browser-repl:latest .

# For ARM64 (Apple Silicon)
docker build --platform linux/arm64 -f Dockerfile.repl -t browser-repl:latest .
```

---

## Troubleshooting

### Problem: "permission denied while trying to connect to Docker daemon"

**Solution**: Add yourself to docker group (requires sudo ONCE):

```bash
sudo usermod -aG docker $USER
# Log out and log back in
newgrp docker
```

### Problem: "Cannot connect to Ollama at http://host.docker.internal:11434"

**Solutions**:

1. **Check Ollama is running on host**:
   ```bash
   curl http://localhost:11434/api/tags
   ```

2. **Use host network mode** (Linux only):
   ```bash
   docker run --network host -it --rm browser-repl:latest
   # Now use http://localhost:11434 instead
   ```

3. **Run Ollama in Docker**:
   ```bash
   docker-compose up -d ollama
   # Wait for it to start
   docker exec ollama ollama pull deepseek-r1:14b
   # Update docker-compose.yml to use http://ollama:11434
   ```

### Problem: "Chrome crashed or failed to start"

**Solution**: Ensure `--headless` flag is set:

```bash
docker run -it --rm browser-repl:latest \
  browser_use_repl.py --headless --model gpt-4o-mini
```

### Problem: "No space left on device"

**Solution**: Clean up Docker:

```bash
# Remove unused containers, images, networks
docker system prune -a

# Remove unused volumes
docker volume prune
```

### Problem: Container runs but REPL doesn't accept input

**Solution**: Ensure `-it` flags are set:

```bash
# Correct (interactive + tty)
docker run -it --rm browser-repl:latest

# Wrong (missing -it)
docker run --rm browser-repl:latest
```

---

## Running Without Docker Group (Rootless Docker)

If you can't join the docker group, use rootless Docker:

```bash
# Install rootless Docker (no sudo needed!)
curl -fsSL https://get.docker.com/rootless | sh

# Add to PATH
export PATH=/home/$USER/bin:$PATH

# Configure Docker context
systemctl --user start docker

# Now use docker normally
docker run -it --rm browser-repl:latest
```

---

## Production Deployment

### Deploy to Cloud (AWS, GCP, Azure)

1. **Build and push to registry**:
   ```bash
   docker build -f Dockerfile.repl -t myregistry/browser-repl:v1 .
   docker push myregistry/browser-repl:v1
   ```

2. **Run on cloud VM**:
   ```bash
   docker run -d \
     --name browser-repl \
     --restart unless-stopped \
     -e OPENAI_API_KEY="sk-..." \
     myregistry/browser-repl:v1 \
     browser_use_repl.py --headless --model gpt-4o-mini
   ```

3. **Attach to running container**:
   ```bash
   docker exec -it browser-repl /bin/bash
   ```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: browser-repl
spec:
  replicas: 1
  selector:
    matchLabels:
      app: browser-repl
  template:
    metadata:
      labels:
        app: browser-repl
    spec:
      containers:
      - name: repl
        image: myregistry/browser-repl:v1
        env:
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: llm-secrets
              key: openai-key
        args: ["browser_use_repl.py", "--headless", "--model", "gpt-4o-mini"]
        resources:
          limits:
            memory: "2Gi"
            cpu: "1000m"
```

---

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Browser Automation Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Build Docker image
        run: docker build -f Dockerfile.repl -t browser-repl:test .

      - name: Run automation tests
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          docker run --rm \
            -e OPENAI_API_KEY=$OPENAI_API_KEY \
            browser-repl:test \
            browser_use_repl.py --headless --query "test query"
```

---

## Performance Considerations

### Container Resource Limits

```bash
# Limit memory and CPU
docker run -it --rm \
  --memory="2g" \
  --cpus="2" \
  browser-repl:latest
```

### Chrome Optimization for Containers

The Dockerfile already includes:
- Headless mode (no GUI overhead)
- Xvfb for virtual display
- Disabled GPU acceleration (not needed in container)
- Minimal Chrome flags for low memory usage

### LLM Performance

| LLM Provider | Response Time | Memory Usage | Cost |
|-------------|---------------|--------------|------|
| Ollama (DeepSeek-R1:14b) | 3-5s | ~4GB | Free |
| OpenAI (GPT-4o-mini) | 1-2s | ~500MB | $0.15-0.60/1M tokens |
| Google (Gemini 2.0 Flash) | 1-3s | ~500MB | $0.075/1M tokens |

---

## Security Best Practices

1. **Don't hardcode API keys** - Use environment variables or secrets
2. **Use non-root user** - Already configured in Dockerfile.repl
3. **Limit container capabilities**:
   ```bash
   docker run --cap-drop=ALL --cap-add=NET_BIND_SERVICE ...
   ```
4. **Use read-only filesystem**:
   ```bash
   docker run --read-only --tmpfs /tmp ...
   ```
5. **Scan images for vulnerabilities**:
   ```bash
   docker scan browser-repl:latest
   ```

---

## FAQ

### Q: Can I run this without Docker at all?

**A:** Yes! Use the native setup:
```bash
uv venv --python 3.11
uv sync
source .venv/bin/activate
python browser_use_repl.py --model deepseek-r1:14b
```

### Q: How do I update the REPL code without rebuilding?

**A:** Use volume mounts:
```bash
docker run -it --rm \
  -v $(pwd)/browser_use_repl.py:/home/browseruser/app/browser_use_repl.py \
  browser-repl:latest
```

### Q: Can I use this on Windows?

**A:** Yes! Install Docker Desktop for Windows, then:
```bash
docker-compose run --rm repl-ollama
```

### Q: How much disk space does the container need?

**A:** ~2.5GB total:
- Base Python image: ~150MB
- Chrome: ~300MB
- Python dependencies: ~500MB
- UV + packages: ~200MB
- System dependencies: ~1.3GB

### Q: Can I run multiple REPL sessions simultaneously?

**A:** Yes!
```bash
# Terminal 1
docker-compose run --rm --name repl1 repl-ollama

# Terminal 2
docker-compose run --rm --name repl2 repl-ollama
```

---

## Next Steps

1. ✅ Build the container: `docker-compose build repl-ollama`
2. ✅ Test with Ollama: `docker-compose run --rm repl-ollama`
3. ✅ Set API keys: Create `.env` file with your keys
4. ✅ Try different LLMs: Use `repl-openai`, `repl-gemini`
5. ✅ Deploy to production: Push to cloud registry

---

**Generated**: January 2025
**Docker Version**: 20.10+
**Tested On**: Ubuntu 22.04, macOS Sonoma, Windows 11 with WSL2
