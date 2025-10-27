# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Browser Agent is a self-contained distribution package of the browser-use library with additional REPL/CLI applications for interactive browser automation. This directory contains everything needed to run browser automation with local (Ollama) or cloud LLMs through an interactive command-line interface.

## Repository Structure

This is a **portable, standalone package** within the larger browser-use repository:

- **REPL Applications**: `browser_use_repl.py` (main REPL) and `browser_use_interactive.py` (alternative CLI)
- **Browser-Use Library**: `browser_use/` directory contains the full browser automation library
- **Docker Setup**: Complete containerized deployment with `Dockerfile.repl`, `docker-compose.yml`, and setup scripts
- **Documentation**: Comprehensive guides for REPL usage, troubleshooting, model selection, and Docker deployment

## High-Level Architecture

### REPL Layer (This Directory)

The REPL applications provide an interactive wrapper around the browser-use library:

- **browser_use_repl.py**: Main REPL with persistent sessions, command history, and prompt optimization
- **browser_use_interactive.py**: Alternative CLI with clean logging and step-by-step execution display
- **Prompt Optimization**: Optional LLM-based query enhancement following browser-use prompting guidelines

### Browser-Use Library (browser_use/)

The underlying library follows an event-driven architecture documented in the parent CLAUDE.md. Key components:

- **Agent** (`browser_use/agent/service.py`): LLM-driven action loop orchestrator
- **BrowserSession** (`browser_use/browser/session.py`): Browser lifecycle and CDP connection management
- **Tools** (`browser_use/tools/service.py`): Action registry mapping LLM decisions to browser operations
- **DomService** (`browser_use/dom/service.py`): DOM extraction and processing
- **LLM Integration** (`browser_use/llm/`): Support for OpenAI, Anthropic, Google, Groq, Ollama

## Development Commands

**Setup:**
```bash
uv venv --python 3.11
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv sync
```

**Run REPL:**
```bash
# With local Ollama (free, no API key)
python browser_use_repl.py --model deepseek-r1:14b

# With cloud LLM
python browser_use_repl.py --provider openai --model gpt-4o-mini
python browser_use_repl.py --provider google --model gemini-2.0-flash-exp

# With prompt optimization
python browser_use_repl.py --model deepseek-r1:14b --optimize

# Headless mode (no browser window)
python browser_use_repl.py --model deepseek-r1:14b --headless
```

**Docker Deployment:**
```bash
# Interactive setup script
./scripts/docker-quick-start.sh

# Or manually
docker-compose build repl-ollama
docker-compose run --rm repl-ollama

# With cloud LLM
export OPENAI_API_KEY="sk-..."
docker-compose run --rm repl-openai
```

**Testing (Library Tests):**
```bash
# Run CI tests
uv run pytest -vxs tests/ci

# Run all tests
uv run pytest -vxs tests/

# Run single test
uv run pytest -vxs tests/ci/test_specific_test.py
```

**Quality Checks:**
```bash
# Type checking
uv run pyright

# Linting and formatting
uv run ruff check --fix
uv run ruff format

# Pre-commit hooks
uv run pre-commit run --all-files
```

## Code Style

Follow the same conventions as the main browser-use library (see parent CLAUDE.md for details):

- Use async python (Python >= 3.11)
- Use tabs for indentation, not spaces
- Modern python typing: `str | None` instead of `Optional[str]`
- Pydantic v2 models with strict validation
- Service pattern: main logic in `service.py`, models in `views.py`
- Runtime assertions for constraints
- Console logging in `_log_*` prefixed methods

### REPL-Specific Patterns

- **Clean Output**: Use `CleanLogger` from `browser_use_interactive.py` for user-facing output
- **Session Management**: Maintain browser and agent state across queries in persistent REPL loop
- **Command Handling**: Special commands (e.g., `/history`, `/exit`) handled separately from browser automation queries
- **Error Recovery**: Graceful handling of LLM failures, browser crashes, and user interrupts (Ctrl+C)

## REPL Applications

### browser_use_repl.py (Main REPL)

Full-featured REPL with:
- Persistent browser sessions across multiple queries
- Command history with `/history` command
- Optional prompt optimization with `--optimize`
- Support for all LLM providers (Ollama, OpenAI, Google, Anthropic, Groq)
- Configurable max steps, timeouts, and browser options
- Clean logging with rich terminal formatting

### browser_use_interactive.py (Alternative CLI)

Simpler interactive CLI focusing on:
- Step-by-step action display
- Detailed logging of each agent action
- Single-query execution mode
- Minimal dependencies

## Key Configuration Options

**Environment Variables:**
```bash
OPENAI_API_KEY=sk-...           # OpenAI API key
ANTHROPIC_API_KEY=sk-ant-...    # Anthropic API key
GOOGLE_API_KEY=AIza...          # Google API key
OLLAMA_HOST=http://localhost:11434  # Ollama server URL
HEADLESS=true                   # Run browser in headless mode
MAX_STEPS=10                    # Maximum actions per query
OPTIMIZE_PROMPTS=false          # Enable prompt optimization
```

**Command-Line Arguments:**
```bash
--model              # LLM model name (e.g., deepseek-r1:14b, gpt-4o-mini)
--provider           # LLM provider (ollama, openai, google, anthropic, groq)
--headless           # Run without browser GUI
--max-steps          # Max actions per query (default: 10)
--optimize           # Enable LLM-based prompt optimization
--verbose            # Show detailed logs
--user-data-dir      # Chrome profile directory
--profile-directory  # Chrome profile name (e.g., "Default")
--env-file           # Load environment variables from file
```

Run `python browser_use_repl.py --help` for complete options.

## Docker Architecture

The Docker setup supports multiple configurations:

### Services in docker-compose.yml

1. **repl-ollama**: REPL with local Ollama LLM (no API key required)
2. **repl-openai**: REPL with OpenAI GPT models
3. **repl-gemini**: REPL with Google Gemini models
4. **repl-anthropic**: REPL with Anthropic Claude models

### Security Features

- **Non-root execution**: Runs as UID 1000 (browseruser), no sudo required
- **Isolated environment**: Container can't access host files except mounted volumes
- **No privileged mode**: Standard Docker security model

### Dockerfile.repl Structure

- Base: Ubuntu 22.04 with Python 3.11
- Browser: Chromium via Playwright with all dependencies
- LLM: Ollama pre-installed and configured
- User: Non-root user (browseruser) for security
- Entry: Interactive shell with REPL available

## Documentation Structure

Essential reading order:

1. **README.md**: Overview, quick start, and deployment options
2. **docs/REPL_QUICK_START.md**: 5-minute getting started guide
3. **docs/REPL_CLI_README.md**: Complete REPL documentation with all features
4. **docs/MODEL_RECOMMENDATIONS.md**: LLM model selection guide
5. **docs/REPL_TROUBLESHOOTING.md**: Common issues and solutions
6. **docs/UNDERSTANDING_AGENT_BEHAVIOR.md**: How the agent makes decisions
7. **docs/REPL_PROMPTING_TIPS.md**: Writing effective browser automation prompts
8. **docs/DOCKER_SETUP.md**: Complete Docker deployment guide
9. **docs/DOCKER_README.md**: Quick Docker reference

## Important Development Constraints

- **Always use `uv`** instead of `pip` for dependency management
- **Test REPL changes with multiple LLM providers** (Ollama, OpenAI, Google)
- **Maintain Docker compatibility** - test containerized deployments
- **Update relevant documentation** when changing REPL features or commands
- **Keep REPL responsive** - use async operations, avoid blocking calls
- **Handle interrupts gracefully** - Ctrl+C should cleanup browser and exit cleanly
- **Preserve session state** - browser and agent should persist across queries in same session

## Testing Strategy

### REPL Testing

Since REPL applications are interactive, testing focuses on:
1. **Manual testing** with various queries and LLM providers
2. **Integration testing** of underlying browser-use library (see `tests/ci/`)
3. **Docker testing** to verify containerized deployments work
4. **Edge case handling**: interrupt handling, browser crashes, LLM failures

### Library Testing

The underlying browser-use library has comprehensive tests:
- Run with `uv run pytest -vxs tests/ci`
- Never mock anything except the LLM
- Use pytest-httpserver for browser scenarios
- Follow modern pytest-asyncio patterns (see parent CLAUDE.md)

## Common REPL Issues

### Memory Drift
Agent loses track of original task and starts doing unrelated actions.

**Solutions:**
- Use smaller `--max-steps` (e.g., 5 instead of 10)
- Enable `--optimize` for clearer prompts
- Write specific, step-by-step queries (see docs/REPL_PROMPTING_TIPS.md)

### Ollama Connection Errors
Cannot connect to Ollama server.

**Solutions:**
- Verify Ollama is running: `ollama serve`
- Test connection: `curl http://localhost:11434/api/tags`
- Check OLLAMA_HOST environment variable

### Chrome Launch Failures
Browser fails to start or crashes immediately.

**Solutions:**
- Use `--headless` mode on servers without display
- Check Chrome dependencies: `uvx playwright install chromium --with-deps`
- Verify Docker has enough memory (8GB+ for local LLM)

## Deployment Options

### Local Development
Best for: Testing, development, custom configurations
```bash
uv venv && uv sync
python browser_use_repl.py --model deepseek-r1:14b
```

### Docker Local
Best for: Consistent environment, easy setup, avoiding dependency issues
```bash
./docker-quick-start.sh
# or
docker-compose run --rm repl-ollama
```

### Cloud VM
Best for: Production, long-running tasks, centralized automation
```bash
# Build and push
docker build -f Dockerfile.repl -t myregistry/browser-repl:v1 .
docker push myregistry/browser-repl:v1

# Deploy on cloud VM (AWS, GCP, Azure)
docker run -d -e OPENAI_API_KEY="sk-..." myregistry/browser-repl:v1
```

## LLM Provider Configuration

### Ollama (Local, Free)
```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull model
ollama pull deepseek-r1:14b

# Run REPL
python browser_use_repl.py --model deepseek-r1:14b
```

### OpenAI
```bash
export OPENAI_API_KEY="sk-..."
python browser_use_repl.py --provider openai --model gpt-4o-mini
```

### Google Gemini
```bash
export GOOGLE_API_KEY="AIza..."
python browser_use_repl.py --provider google --model gemini-2.0-flash-exp
```

### Anthropic Claude
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
python browser_use_repl.py --provider anthropic --model claude-3-5-sonnet-20241022
```

## Prompt Optimization

When `--optimize` is enabled, user queries are enhanced using the official browser-use prompting guidelines:

1. **Be Specific**: Detailed step-by-step instructions
2. **Explicit Actions**: Use exact action names (click, type, scroll, etc.)
3. **Clear Goals**: Define success criteria
4. **Context**: Provide relevant information

The optimization uses a separate LLM call to transform casual queries into structured prompts before execution.

## important-instruction-reminders

Do what has been asked; nothing more, nothing less.
NEVER create files unless they're absolutely necessary for achieving your goal.
ALWAYS prefer editing an existing file to creating a new one.
NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User.
