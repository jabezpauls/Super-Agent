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

The REPL applications provide an interactive wrapper around the browser-use library with **modular architecture**:

**Main Applications:**
- **browser_use_repl.py**: Main REPL with multi-tool support (browser, chat, calendar, email), intelligent tool routing, persistent sessions, and command history
- **browser_use_interactive.py**: Alternative CLI with clean logging and step-by-step execution display

**Modular Components (repl/):**
- **cli.py**: Command-line argument parsing, LLM initialization, MCP environment setup
- **session_manager.py**: Core session management with intelligent tool routing, lazy browser initialization, MCP connection management
- **commands.py**: Special command handling (/help, /exit, /browser, /calendar, /email, /connect, /status)
- **prompt_optimizer.py**: Optional LLM-based query enhancement following browser-use prompting guidelines

**Integration Modules:**
- **browser_use/agent/tool_router.py**: Intelligent LLM-based tool routing (chat vs browser vs calendar vs email)
- **browser_use/mcp/manager.py**: MCP server lifecycle management with lazy-loading

**MCP Servers (scripts/):**
- **scripts/mcp_calendar_server.py**: Google Calendar MCP server (list/create/update/delete events, check availability)
- **scripts/mcp_gmail_server.py**: Gmail MCP server (list/read/send emails, search, modify labels)

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

# With MCP tools (Calendar, Email)
python browser_use_repl.py --model deepseek-r1:14b --google-credentials credentials.json

# Disable specific features
python browser_use_repl.py --disable-mcp  # No calendar/email
python browser_use_repl.py --disable-chat # No pure chat mode
```

**MCP Setup (Optional - for Calendar/Email):**
```bash
# Install MCP dependencies
pip install fastmcp google-auth-oauthlib google-api-python-client

# Setup Google OAuth (see docs/MCP_SETUP_GUIDE.md)
# 1. Create Google Cloud project
# 2. Enable Calendar and Gmail APIs
# 3. Download credentials.json
# 4. Run REPL - OAuth flow will open browser for authorization

# Run REPL with MCP
python browser_use_repl.py --google-credentials credentials.json
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

### Modular Architecture (repl/)

The REPL is organized into focused, single-responsibility modules:

- **repl/cli.py** (~260 lines): Argument parsing and LLM initialization
  - `parse_arguments()`: Define all CLI arguments with help text
  - `create_llm_from_args()`: Create provider-specific LLM instances
  - `setup_mcp_environment()`: Configure MCP-related environment variables

- **repl/session_manager.py** (~450 lines): Core session and routing logic
  - `SessionManager`: Main class coordinating browser, agent, and MCP
  - `initialize_browser()`: Lazy browser initialization on first use
  - `ensure_mcp_connected()`: Lazy MCP server connection
  - `chat_response()`: Pure chat without tools
  - `execute_browser_task()`: Browser automation with prompt optimization
  - `execute_mcp_task()`: MCP tool execution (calendar, email)
  - `process_query()`: Main routing logic with manual override support

- **repl/commands.py** (~300 lines): Special command handlers
  - `CommandHandler.handle_command()`: Dispatch commands to appropriate handlers
  - Commands: `/help`, `/exit`, `/clear`, `/history`, `/config`
  - Tool forcing: `/browser`, `/calendar`, `/email`, `/chat`
  - MCP management: `/connect`, `/disconnect`, `/status`, `/tools`

- **repl/prompt_optimizer.py** (~130 lines): Prompt enhancement
  - `optimize_prompt()`: LLM-based optimization using official guidelines
  - `add_task_anchoring()`: Simple anchoring for non-optimized mode
  - Supports multiple LLM providers (OpenAI, Anthropic, Google, Ollama)

**Design Principles:**
- Each module has a single, clear responsibility
- Lazy-loading for expensive resources (browser, MCP servers)
- Clean separation between CLI, business logic, and I/O
- Easy to test individual components
- Main file (browser_use_repl.py) is minimal orchestrator (~144 lines)

## REPL Applications

### browser_use_repl.py (Main REPL)

Full-featured multi-tool REPL with:

**Multi-Tool Support:**
- **Browser Tool**: Web automation (always available)
- **Chat Tool**: Natural conversations without external tools
- **Calendar Tool**: Google Calendar via MCP (list/create/update/delete events, check availability)
- **Email Tool**: Gmail via MCP (list/read/send emails, search, modify labels)

**Intelligent Routing:**
- Automatic LLM-based tool selection based on user query
- Manual tool forcing with `/browser`, `/calendar`, `/email`, `/chat` commands
- Hybrid approach: smart defaults with manual override capability

**Session Management:**
- Persistent browser sessions across multiple queries
- Lazy-loading: browser and MCP servers connect only when first needed
- Clean session cleanup with `/clear` command

**Features:**
- Command history with `/history` command
- Optional prompt optimization with `--optimize`
- Support for all LLM providers (Ollama, OpenAI, Google, Anthropic, Groq)
- Configurable max steps, timeouts, and browser options
- Clean logging with rich terminal formatting
- MCP server management (`/connect`, `/disconnect`, `/status`, `/tools`)

**Special Commands:**
- `/help` - Show available commands
- `/exit` or `/quit` - Exit REPL
- `/clear` - Clear browser session
- `/history` - Show command history
- `/config` - Show current configuration
- `/browser <query>` - Force browser tool
- `/calendar <query>` - Force calendar tool
- `/email <query>` - Force email tool
- `/chat <message>` - Force pure chat response
- `/connect <server>` - Connect to MCP server (calendar, gmail)
- `/disconnect <server>` - Disconnect from MCP server
- `/status` - Show MCP connection status
- `/tools` - List available tools

### browser_use_interactive.py (Alternative CLI)

Simpler interactive CLI focusing on:
- Step-by-step action display
- Detailed logging of each agent action
- Single-query execution mode
- Minimal dependencies
- Browser-only (no MCP integration)

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
# LLM Configuration
--model              # LLM model name (e.g., deepseek-r1:14b, gpt-4o-mini)
--provider           # LLM provider (ollama, openai, google, anthropic, groq)
--host               # Ollama server URL (default: http://localhost:11434)

# Browser Configuration
--headless           # Run without browser GUI
--max-steps          # Max actions per query (default: 10)
--no-vision          # Disable vision/screenshots
--user-data-dir      # Chrome profile directory
--profile-directory  # Chrome profile name (e.g., "Default")
--cdp-url            # Connect to existing Chrome via CDP

# Tool Configuration
--optimize           # Enable LLM-based prompt optimization
--disable-mcp        # Disable MCP tools (Calendar, Email)
--disable-chat       # Disable pure chat mode (always use tools)
--google-credentials # Path to Google OAuth credentials (default: credentials.json)

# Output Configuration
--quiet              # Minimal output (only final results)
--verbose            # Show detailed logs including thinking and actions
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
5. **docs/MCP_SETUP_GUIDE.md**: Google Calendar and Gmail MCP integration (optional)
6. **docs/REPL_TROUBLESHOOTING.md**: Common issues and solutions
7. **docs/UNDERSTANDING_AGENT_BEHAVIOR.md**: How the agent makes decisions
8. **docs/REPL_PROMPTING_TIPS.md**: Writing effective browser automation prompts
9. **docs/DOCKER_SETUP.md**: Complete Docker deployment guide
10. **docs/DOCKER_README.md**: Quick Docker reference

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

## Tool Routing System

The REPL uses intelligent LLM-based routing to automatically select the appropriate tool:

### Available Tool Types
- **CHAT**: Natural conversation without external tools (e.g., "What's 2+2?", "Explain quantum physics")
- **BROWSER**: Web automation and data extraction (e.g., "Find flights to Tokyo", "Search for Python tutorials")
- **CALENDAR**: Google Calendar operations (e.g., "Check my calendar tomorrow", "Schedule meeting 2pm")
- **EMAIL**: Gmail operations (e.g., "Read latest email", "Send email to john@example.com")

### Routing Decision Process

1. **Manual Override Detection**: Check for `/browser`, `/calendar`, `/email`, `/chat` prefixes
2. **LLM-Based Routing**: If no manual override, query LLM to analyze intent:
   ```python
   decision = await route_query(llm, user_query)
   # Returns: ToolDecision(primary_tool, reasoning, specific_actions)
   ```
3. **Fallback Heuristics**: If LLM routing fails, use pattern matching:
   - Calendar keywords: "calendar", "schedule", "meeting", "event"
   - Email keywords: "email", "gmail", "send message", "inbox"
   - Browser keywords: "search", "find", "website", "open"
   - Chat: Default for general questions

4. **Tool Execution**: Execute appropriate handler based on decision

### Routing Examples

```bash
# Automatic routing
> What's the capital of France?           # → CHAT
> Find cheap flights to Tokyo             # → BROWSER
> Check my calendar for tomorrow          # → CALENDAR (auto-connects MCP)
> Send email to john@example.com          # → EMAIL (auto-connects MCP)

# Manual override
> /browser What's 2+2?                    # → BROWSER (forced)
> /chat search for Python tutorials       # → CHAT (forced)
> /calendar list events                   # → CALENDAR (forced)
> /email check inbox                      # → EMAIL (forced)
```

## MCP Integration

### Architecture

The REPL integrates with MCP (Model Context Protocol) servers to extend agent capabilities:

- **MCPManager** (`browser_use/mcp/manager.py`): Server lifecycle management
- **Lazy Loading**: MCP servers connect only when first needed
- **Server Configs**: Defined in `MCP_SERVER_CONFIGS` dict with command, args, ports
- **Tool Registration**: MCP tools automatically registered to agent's tool registry

### MCP Servers

**Calendar Server** (`scripts/mcp_calendar_server.py`):
- `list_calendar_events`: Query events with filters, search, time ranges
- `create_calendar_event`: Create events with attendees, notifications
- `update_calendar_event`: Modify existing events
- `delete_calendar_event`: Delete events with cancellation emails
- `check_availability`: Check free/busy status

**Gmail Server** (`scripts/mcp_gmail_server.py`):
- `list_emails`: List emails with Gmail search syntax
- `read_email`: Read specific email with full content
- `send_email`: Send emails with CC/BCC, HTML support
- `modify_email_labels`: Add/remove labels (INBOX, UNREAD, etc.)
- `search_emails`: Quick email search

### MCP Setup

See `docs/MCP_SETUP_GUIDE.md` for complete setup instructions:

1. **Install Dependencies**: `pip install fastmcp google-auth-oauthlib google-api-python-client`
2. **Google Cloud Setup**: Create project, enable APIs, create OAuth credentials
3. **Download credentials.json**: OAuth 2.0 client credentials
4. **Run REPL**: `python browser_use_repl.py --google-credentials credentials.json`
5. **OAuth Flow**: Browser opens for authorization, token saved to token.pickle

### MCP Management Commands

```bash
/connect calendar      # Connect to Calendar MCP server
/connect gmail         # Connect to Gmail MCP server
/disconnect calendar   # Disconnect from Calendar
/status                # Show all MCP connection status
/tools                 # List available tools
```

## important-instruction-reminders

Do what has been asked; nothing more, nothing less.
NEVER create files unless they're absolutely necessary for achieving your goal.
ALWAYS prefer editing an existing file to creating a new one.
NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User.
