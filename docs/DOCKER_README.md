# Docker Setup - Quick Reference

## ✅ YES! You can run this WITHOUT sudo access!

The entire Browser Automation REPL runs inside Docker as a **non-root user** (browseruser, UID 1000).

---

## Quick Commands

```bash
# Interactive quick start
./docker-quick-start.sh

# Or manually:
docker-compose run --rm repl-ollama    # Free, local LLM
docker-compose run --rm repl-openai    # Cloud LLM (requires API key)
docker-compose run --rm repl-gemini    # Cloud LLM (requires API key)
```

---

## What's Included

| File | Purpose |
|------|---------|
| `Dockerfile.repl` | Specialized container for REPL with Chrome + Python 3.11 |
| `docker-compose.yml` | Pre-configured services for different LLM providers |
| `DOCKER_SETUP.md` | Complete documentation (15KB, read this!) |
| `docker-quick-start.sh` | Interactive setup script |
| `.dockerignore` | Keeps image small |

---

## System Without Sudo Access

If you can't use sudo on your new system, you have **3 options**:

### Option 1: Docker already installed + you're in docker group
```bash
# Just use it! No sudo needed
docker-compose run --rm repl-ollama
```

### Option 2: Install Rootless Docker (no sudo required!)
```bash
curl -fsSL https://get.docker.com/rootless | sh
export PATH=$HOME/bin:$PATH
systemctl --user start docker
docker-compose run --rm repl-ollama
```

### Option 3: Skip Docker, use UV locally
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv --python 3.11
source .venv/bin/activate
uv sync
python browser_use_repl.py --model deepseek-r1:14b
```

---

## Container Architecture

```
Dockerfile.repl
├── Base: Python 3.11 slim
├── Google Chrome stable
├── Xvfb (virtual display)
├── Non-root user (browseruser, UID 1000) ← NO SUDO!
├── UV package manager
└── Browser-use library + REPL

Size: ~2.5GB
Memory: ~2GB with DeepSeek-R1:14b
CPU: 1-2 cores recommended
```

---

## Environment Variables

Create a `.env` file:

```bash
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=AIza...
ANTHROPIC_API_KEY=sk-ant-...
OLLAMA_HOST=http://host.docker.internal:11434
```

Or export them:

```bash
export OPENAI_API_KEY="sk-..."
docker-compose run --rm repl-openai
```

---

## Common Issues

### "Cannot connect to Docker daemon"
```bash
# Add yourself to docker group (requires sudo ONCE)
sudo usermod -aG docker $USER
# Then log out and back in
```

### "Cannot connect to Ollama"
```bash
# Make sure Ollama is running on host
curl http://localhost:11434/api/tags

# Or run Ollama in Docker
docker-compose up -d ollama
docker exec ollama ollama pull deepseek-r1:14b
```

### "Chrome failed to start"
```bash
# Ensure --headless flag is set
docker-compose run --rm repl-ollama \
  browser_use_repl.py --headless --model deepseek-r1:14b
```

---

## Testing

```bash
# 1. Build
docker-compose build repl-ollama

# 2. Run
docker-compose run --rm repl-ollama

# 3. Inside REPL, try:
> /help
> get current date and time
> /exit

# 4. Success! 🎉
```

---

## Production Deployment

```bash
# Build and tag
docker build -f Dockerfile.repl -t myregistry/browser-repl:v1 .

# Push to registry
docker push myregistry/browser-repl:v1

# Run on server
docker run -d --name browser-repl \
  -e OPENAI_API_KEY="sk-..." \
  myregistry/browser-repl:v1
```

---

## Documentation

- **Full guide**: `DOCKER_SETUP.md` (15KB, comprehensive)
- **This file**: Quick reference
- **Interactive**: Run `./docker-quick-start.sh`

---

## Next Steps

1. ✅ Read `DOCKER_SETUP.md` for full details
2. ✅ Run `./docker-quick-start.sh` to get started
3. ✅ Choose your LLM provider
4. ✅ Start automating!

When you move to a system without sudo:
- Copy these files
- Run `docker-compose`
- Everything just works! ✨

---

**Generated**: January 2025
**Docker Version**: 20.10+
**Tested On**: Ubuntu 22.04, macOS Sonoma, Windows 11 with WSL2
