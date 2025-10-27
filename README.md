# Browser Agent - AI-Powered Browser Automation REPL

This directory contains a **complete, standalone** Browser Automation REPL application with all dependencies and documentation needed to run it.

---

## 📦 What's Included

This is a **portable, self-contained** package with everything you need:

```
browser_agent/
├── browser_use_repl.py              # Main REPL application
├── browser_use_interactive.py       # Alternative interactive CLI
├── browser_use/                     # Browser automation library
├── pyproject.toml                   # Python dependencies
├── uv.lock                          # Locked dependencies
│
├── Dockerfile.repl                  # Docker container definition
├── docker-compose.yml               # Multi-service Docker setup
│
├── docs/                            # Documentation directory
│   ├── REPL_CLI_README.md          # Main REPL documentation
│   ├── REPL_QUICK_START.md         # Quick start guide
│   ├── REPL_TROUBLESHOOTING.md     # Troubleshooting guide
│   ├── REPL_PROMPTING_TIPS.md      # Prompting best practices
│   ├── UNDERSTANDING_AGENT_BEHAVIOR.md # How the agent works
│   ├── MODEL_RECOMMENDATIONS.md     # LLM model comparison
│   ├── MODELS_QUICK_GUIDE.md       # Quick model selection guide
│   ├── DOCKER_SETUP.md             # Complete Docker guide
│   └── DOCKER_README.md            # Docker quick reference
│
├── scripts/                         # Utility scripts
│   ├── demo_repl.sh                # Demo script
│   ├── docker-quick-start.sh       # Interactive Docker setup
│   ├── setup_better_model.sh       # Model setup helper
│   └── verify_setup.sh             # Setup verification
│
└── README.md                       # This file
```

---

## 🚀 Quick Start

### Option 1: Local Installation (Recommended for Development)

```bash
# 1. Navigate to this directory
cd browser_agent

# 2. Install UV (fast Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 3. Create virtual environment and install dependencies
uv venv --python 3.11
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv sync

# 4. Install Ollama (for free local LLM)
curl -fsSL https://ollama.com/install.sh | sh
ollama pull deepseek-r1:14b

# 5. Run the REPL
python browser_use_repl.py --model deepseek-r1:14b
```

### Option 2: Docker (Recommended for Production)

```bash
# 1. Navigate to this directory
cd browser_agent

# 2. Run the interactive setup script
./scripts/docker-quick-start.sh

# Or manually:
docker-compose build repl-ollama
docker-compose run --rm repl-ollama
```

### Option 3: Cloud LLM (OpenAI, Gemini, etc.)

```bash
# Set your API key
export OPENAI_API_KEY="sk-..."
# OR
export GOOGLE_API_KEY="AIza..."

# Run with cloud LLM
python browser_use_repl.py --provider openai --model gpt-4o-mini
# OR
python browser_use_repl.py --provider google --model gemini-2.0-flash-exp
```

---

## 📚 Documentation

### Essential Reading (Start Here!)

1. **[REPL_QUICK_START.md](docs/REPL_QUICK_START.md)** - Get started in 5 minutes
2. **[REPL_CLI_README.md](docs/REPL_CLI_README.md)** - Complete REPL documentation
3. **[MODEL_RECOMMENDATIONS.md](docs/MODEL_RECOMMENDATIONS.md)** - Which LLM to use?

### When You Need Help

4. **[REPL_TROUBLESHOOTING.md](docs/REPL_TROUBLESHOOTING.md)** - Common issues & fixes
5. **[UNDERSTANDING_AGENT_BEHAVIOR.md](docs/UNDERSTANDING_AGENT_BEHAVIOR.md)** - How the agent thinks
6. **[REPL_PROMPTING_TIPS.md](docs/REPL_PROMPTING_TIPS.md)** - Write better prompts

### Docker Deployment

7. **[DOCKER_README.md](docs/DOCKER_README.md)** - Quick Docker reference
8. **[DOCKER_SETUP.md](docs/DOCKER_SETUP.md)** - Complete Docker guide (15KB)

---

## 💡 Usage Examples

### Basic Usage

```bash
# Start the REPL
python browser_use_repl.py --model deepseek-r1:14b

# Inside the REPL:
> get the subscriber count for youtube channel @mkbhd
> search google for "python tutorials" and give me top 3 results
> go to amazon.com and find the price of "laptop under $1000"
> /history
> /exit
```

### With Prompt Optimization

```bash
# Enable LLM-based prompt optimization
python browser_use_repl.py --model deepseek-r1:14b --optimize

# Now your casual queries get optimized automatically!
> check youtube subscribers
# Optimized to: "Navigate to youtube.com, use search action..."
```

### With Existing Chrome Profile

```bash
# Use your logged-in Chrome profile
python browser_use_repl.py \
  --model deepseek-r1:14b \
  --user-data-dir ~/.config/google-chrome \
  --profile-directory "Default"
```

### Headless Mode (No Browser Window)

```bash
# Run without GUI (for servers)
python browser_use_repl.py --model deepseek-r1:14b --headless
```

---

## 🔧 System Requirements

### Minimum Requirements

- **OS**: Ubuntu 22.04, macOS 12+, or Windows 10/11 with WSL2
- **RAM**: 8GB (16GB recommended for local LLMs)
- **Disk**: 1GB (9GB if using local LLM like DeepSeek-R1:14b)
- **Python**: 3.11+
- **Internet**: Required for cloud LLMs and web browsing

### For Local LLM (Ollama)

| Model | RAM Required | Speed | Quality |
|-------|-------------|-------|---------|
| DeepSeek-R1:7b | 8GB | Fast | Good |
| DeepSeek-R1:14b | 16GB | Medium | Excellent |
| DeepSeek-R1:32b | 32GB + GPU | Slow | Best |

### For Cloud LLM

- API key from OpenAI, Anthropic, or Google
- ~₹100-500/month for moderate usage

---

## 🐳 Docker Deployment

### Why Docker?

✅ **No sudo required** - Runs as non-root user (UID 1000)
✅ **Consistent environment** - Works across different systems
✅ **Isolated** - Doesn't interfere with host packages
✅ **Portable** - Same setup everywhere

### Docker Quick Commands

```bash
# With local Ollama (free)
docker-compose run --rm repl-ollama

# With OpenAI
export OPENAI_API_KEY="sk-..."
docker-compose run --rm repl-openai

# With Google Gemini
export GOOGLE_API_KEY="AIza..."
docker-compose run --rm repl-gemini

# Interactive setup
./scripts/docker-quick-start.sh
```

See [DOCKER_SETUP.md](docs/DOCKER_SETUP.md) for complete Docker documentation.

---

## 🎯 Use Cases

### 1. Data Extraction
```
> go to quotes.toscrape.com and extract the first 5 quotes with authors
```

### 2. Price Monitoring
```
> find the current price of bitcoin on coinbase
```

### 3. Research Automation
```
> search google scholar for "machine learning in healthcare" and get top 3 paper titles
```

### 4. Form Filling
```
> go to example.com/contact and fill the form with name "John Doe" and email "john@example.com"
```

### 5. Content Discovery
```
> find the top 5 trending repositories on github for python
```

---

## 🆘 Troubleshooting

### "Agent keeps switching tasks (memory drift)"

**Solution**: Use smaller max-steps and enable optimization
```bash
python browser_use_repl.py --model deepseek-r1:14b --max-steps 5 --optimize
```

See [REPL_TROUBLESHOOTING.md](docs/REPL_TROUBLESHOOTING.md) for more issues.

### "Cannot connect to Ollama"

**Solution**: Make sure Ollama is running
```bash
# Start Ollama server
ollama serve

# Test connection
curl http://localhost:11434/api/tags
```

### "Chrome failed to start"

**Solution**: Use headless mode
```bash
python browser_use_repl.py --model deepseek-r1:14b --headless
```

### "Permission denied (Docker)"

**Solution**: Add yourself to docker group (one-time sudo)
```bash
sudo usermod -aG docker $USER
# Log out and back in
```

---

## 📊 Performance & Costs

### Local LLM (Ollama) - Recommended

- **Cost**: ₹0/month
- **Privacy**: 100% local, no data leaves your machine
- **Speed**: 3-5 seconds per action
- **Requires**: 16GB RAM for DeepSeek-R1:14b

### Cloud LLM (OpenAI, Gemini)

| Provider | Model | Cost/1M tokens | Speed | Quality |
|----------|-------|----------------|-------|---------|
| **Google Gemini** | 2.0 Flash | ₹5-10 | 1-2s | Excellent |
| **OpenAI** | GPT-4o-mini | ₹100-200 | 1-2s | Excellent |
| **Anthropic** | Claude Sonnet | ₹200-500 | 2-3s | Best |

**Moderate usage** (100 queries/day): ₹100-500/month

---

## 🔒 Security & Privacy

### Local Mode (Ollama)
- ✅ **100% private** - No data sent to cloud
- ✅ **Offline capable** - Works without internet (for automation, not browsing)
- ✅ **No API keys** - No risk of key leakage

### Cloud Mode (OpenAI, Gemini)
- ⚠️ **Prompts sent to cloud** - LLM provider sees your queries
- ⚠️ **API key required** - Keep secure, don't commit to git
- ✅ **No browsing data sent** - Only automation instructions

### Docker Security
- ✅ **Non-root user** - Runs as UID 1000 (browseruser)
- ✅ **Isolated** - Container can't access host files (except mounted volumes)
- ✅ **No sudo needed** - Safe for restricted environments

---

## 🛠️ Advanced Configuration

### Environment Variables

Create a `.env` file:

```bash
# LLM API Keys
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=AIza...

# Ollama Configuration
OLLAMA_HOST=http://localhost:11434

# Browser Settings
HEADLESS=true
MAX_STEPS=10
OPTIMIZE_PROMPTS=false
```

Load with:
```bash
python browser_use_repl.py --env-file .env
```

### Command-Line Arguments

```bash
python browser_use_repl.py \
  --model deepseek-r1:14b \          # LLM model
  --provider ollama \                 # LLM provider (ollama/openai/google/anthropic)
  --headless \                        # Run without GUI
  --max-steps 10 \                    # Max actions per query
  --optimize \                        # Enable prompt optimization
  --verbose \                         # Show detailed logs
  --user-data-dir ~/.config/chrome \  # Chrome profile
  --profile-directory "Default"       # Chrome profile name
```

Run `python browser_use_repl.py --help` for all options.

---

## 📈 Monitoring & Logging

### View Agent Actions

Enable verbose mode:
```bash
python browser_use_repl.py --model deepseek-r1:14b --verbose
```

You'll see:
- Each step the agent takes
- DOM elements it finds
- Actions it executes
- LLM reasoning (if available)

### Debug Memory Drift

Watch the "Memory:" field in verbose output:
```
Memory: Original task - get YouTube subscribers
Step 1: Navigate to youtube.com ✓
Step 2: Search for channel ✓
Step 3: DRIFT DETECTED! Now searching for laptops ✗
```

See [UNDERSTANDING_AGENT_BEHAVIOR.md](docs/UNDERSTANDING_AGENT_BEHAVIOR.md) for details.

---

## 🚢 Deployment Options

### 1. Local Development
```bash
uv venv && uv sync
python browser_use_repl.py --model deepseek-r1:14b
```

### 2. Server (Headless)
```bash
docker run -d --name browser-repl \
  -e OPENAI_API_KEY="sk-..." \
  browser-repl:latest \
  browser_use_repl.py --headless --model gpt-4o-mini
```

### 3. CI/CD Pipeline
```yaml
# GitHub Actions example
- name: Run browser automation
  run: |
    docker-compose run --rm repl-ollama \
      browser_use_repl.py --headless --query "test query"
```

### 4. Cloud VM (AWS, GCP, Azure)
```bash
# Deploy to cloud
docker build -f Dockerfile.repl -t myregistry/browser-repl:v1 .
docker push myregistry/browser-repl:v1

# Run on cloud VM
docker run -d -e OPENAI_API_KEY="sk-..." myregistry/browser-repl:v1
```

---

## 🤝 Contributing

This is part of the browser-use open-source project.

**Main repository**: https://github.com/browser-use/browser-use
**Documentation**: https://docs.browser-use.com/

---

## 📝 License

This project uses the **browser-use** library, which is licensed under the MIT License.

All additional REPL code and documentation in this directory is also MIT licensed.

---

## 🆘 Getting Help

### Documentation
1. Read [REPL_QUICK_START.md](docs/REPL_QUICK_START.md)
2. Check [REPL_TROUBLESHOOTING.md](docs/REPL_TROUBLESHOOTING.md)
3. Review [REPL_CLI_README.md](docs/REPL_CLI_README.md)

### Common Issues
- **Memory drift**: See [UNDERSTANDING_AGENT_BEHAVIOR.md](docs/UNDERSTANDING_AGENT_BEHAVIOR.md)
- **Prompt writing**: See [REPL_PROMPTING_TIPS.md](docs/REPL_PROMPTING_TIPS.md)
- **Model selection**: See [MODEL_RECOMMENDATIONS.md](docs/MODEL_RECOMMENDATIONS.md)
- **Docker issues**: See [DOCKER_SETUP.md](docs/DOCKER_SETUP.md)

### Still Stuck?
- Check browser-use docs: https://docs.browser-use.com/
- GitHub issues: https://github.com/browser-use/browser-use/issues

---

## 🎓 Credits

**Browser-Use Library**: https://github.com/browser-use/browser-use
**REPL Implementation**: Custom interactive CLI wrapper
**Docker Setup**: Containerized deployment for portability

---

**Last Updated**: January 2025
**Version**: 1.0
**Tested On**: Ubuntu 22.04, macOS Sonoma, Windows 11 with WSL2
