# Browser-Use Interactive REPL

A fully interactive, persistent chat-like CLI for browser automation, similar to Claude Code CLI. Unlike the one-shot interactive tool, the REPL maintains a continuous session where you can have ongoing conversations with the browser agent.

## Features

- **Persistent Session**: Browser and agent state maintained across multiple queries
- **Local by Default**: Uses Ollama with qwen2.5:7b (no API key required!)
- **Chat-Like Interface**: Continuous conversation with the browser agent
- **Command History**: Navigate through previous commands with arrow keys
- **Special Commands**: Built-in commands for session management
- **Prompt Optimization**: Automatically converts vague queries into specific, actionable prompts
- **Step-by-Step Visibility**: See every action, thought, and result in real-time
- **Clean Output**: Professional logging without emojis
- **Multiple LLM Support**: Ollama (default), OpenAI, Anthropic, Google Gemini

## Installation

```bash
# 1. Install Ollama (if not already installed)
# Visit: https://ollama.com/
curl -fsSL https://ollama.com/install.sh | sh

# 2. Start Ollama server
ollama serve

# 3. Pull the default model (in a new terminal)
ollama pull qwen2.5:7b

# 4. Navigate to browser-use directory
cd /path/to/browser-use

# 5. Ensure dependencies are installed
uv sync
uvx playwright install chromium --with-deps
```

## Quick Start

### Basic Usage (No API Key Required!)

```bash
# Start the REPL with default settings (Ollama + qwen2.5:7b)
uv run python browser_use_repl.py

# Show detailed output including all thinking
uv run python browser_use_repl.py --verbose

# Run in headless mode
uv run python browser_use_repl.py --headless
```

### Example Session

```
======================================================================
  Browser-Use Interactive REPL
  Chat with the browser agent - Type your queries and press Enter
======================================================================

Special Commands:
  /help     - Show this help message
  /exit     - Exit the REPL
  /quit     - Exit the REPL
  /clear    - Clear browser session and start fresh
  /history  - Show command history
  /config   - Show current configuration

======================================================================

> find the latest Python version on python.org

======================================================================
  PROMPT OPTIMIZATION
======================================================================

  User Query: find the latest Python version on python.org

  Generating optimized prompt...

  Optimized Prompt:
  Navigate to python.org, locate the downloads section, identify and extract
  the latest stable Python version number with its release date.

======================================================================
  TASK EXECUTION
======================================================================

[Step 1] Processing...
----------------------------------------------------------------------

  Thinking:
    I need to navigate to python.org first...

  Action: NavigateAction
  Params: url=https://python.org

======================================================================
  EXECUTION COMPLETE
======================================================================

  SUCCESS: Task completed successfully

  Final Result:
  The latest stable Python version is 3.12.1, released on December 7, 2023.

> now check what version of pip comes with it

======================================================================
  PROMPT OPTIMIZATION
======================================================================

  User Query: now check what version of pip comes with it
  ...

> /exit

  Exiting REPL...
  Cleaning up...
  SUCCESS: Goodbye!
```

## Special Commands

The REPL supports several special commands (prefix with `/`):

| Command | Description |
|---------|-------------|
| `/help` | Show help message with available commands |
| `/exit` or `/quit` | Exit the REPL cleanly |
| `/clear` | Clear the current browser session and start fresh |
| `/history` | Display all commands from current session |
| `/config` | Show current configuration (LLM, browser settings, etc.) |

## Command-Line Options

| Option | Default | Description |
|--------|---------|-------------|
| `--provider` | `ollama` | LLM provider: openai, anthropic, google, ollama |
| `--model` | `qwen2.5:7b` | Model to use |
| `--host` | `http://localhost:11434` | Ollama server URL |
| `--headless` | `False` | Run browser in headless mode |
| `--max-steps` | `20` | Maximum number of steps per task |
| `--no-vision` | `False` | Disable screenshots/vision |
| `--no-optimize` | `False` | Skip prompt optimization |
| `--quiet` | `False` | Minimal output (only final results) |
| `--verbose` | `False` | Show detailed output including all thinking |

## Usage Examples

### Local with Ollama (Default)

```bash
# Default settings - no API key needed!
uv run python browser_use_repl.py

# Headless mode for background operation
uv run python browser_use_repl.py --headless

# Verbose mode to see all thinking
uv run python browser_use_repl.py --verbose

# Skip prompt optimization for direct control
uv run python browser_use_repl.py --no-optimize
```

### With Cloud LLMs

First, create a `.env` file with your API key:

```bash
# For OpenAI
OPENAI_API_KEY=your_key_here

# For Google Gemini
GOOGLE_API_KEY=your_key_here

# For Anthropic
ANTHROPIC_API_KEY=your_key_here
```

Then run with the desired provider:

```bash
# OpenAI GPT-4
uv run python browser_use_repl.py --provider openai --model gpt-4o

# Google Gemini
uv run python browser_use_repl.py --provider google --model gemini-2.0-flash-exp

# Anthropic Claude
uv run python browser_use_repl.py --provider anthropic --model claude-3-5-sonnet-20241022
```

## Interactive Features

### Command History

The REPL automatically saves your command history to `~/.browser_use_repl_history`. Navigate through previous commands using:

- **Up Arrow**: Previous command
- **Down Arrow**: Next command
- **Ctrl+R**: Search command history (if your terminal supports it)

### Session Persistence

Unlike the one-shot interactive tool, the REPL maintains:

- **Browser State**: Pages remain open between queries
- **Navigation History**: Agent knows where it's been
- **Conversation Context**: Follow-up queries understand previous context
- **Cookies & Authentication**: Login state persists across queries

Example of persistent session:

```
> login to github with my credentials

  [Agent completes login]

> now star the browser-use repository

  [Agent uses existing logged-in session to star the repo]

> show me my starred repositories

  [Agent navigates to starred repos page using same session]
```

### Clearing Session

If you want to start fresh without restarting the REPL:

```
> /clear

  Clearing browser session...
  SUCCESS: Session cleared

> [Next query will start with a fresh browser]
```

## Example Use Cases

### Web Research Session

```bash
uv run python browser_use_repl.py
```

```
> find the top 3 posts on hacker news today
> now get the first comment from each post
> summarize all the comments
```

### E-commerce Task Flow

```bash
uv run python browser_use_repl.py --verbose
```

```
> go to amazon.com and search for "wireless mouse"
> filter results to show only items under $30
> get the title and price of the top 3 results
> now check the reviews for the first one
```

### Form Filling Workflow

```bash
uv run python browser_use_repl.py
```

```
> navigate to the demo form at forms.example.com
> fill in the name field with "John Doe"
> now fill in the email with "john@example.com"
> select "Software Engineer" from the job dropdown
> submit the form
```

### Social Media Automation

```bash
uv run python browser_use_repl.py
```

```
> go to twitter.com and log in
> search for #browseruse tweets from today
> like the first 5 tweets
> now compose a tweet: "Loving the new Browser-Use REPL! 🚀"
```

## Keyboard Shortcuts

- **Ctrl+C** (once): Interrupt current task, return to prompt
- **Ctrl+C** (twice quickly): Force quit the REPL
- **Ctrl+D**: Exit the REPL gracefully
- **Up/Down Arrows**: Navigate command history
- **Ctrl+L**: Clear screen (terminal feature, history preserved)

## Configuration

### Display Settings

```bash
# Minimal output - only show final results
uv run python browser_use_repl.py --quiet

# Verbose output - show all LLM thinking
uv run python browser_use_repl.py --verbose
```

### Browser Settings

```bash
# Headless mode (no browser window)
uv run python browser_use_repl.py --headless

# Without vision/screenshots (faster, but less accurate)
uv run python browser_use_repl.py --no-vision

# Increase max steps for complex tasks
uv run python browser_use_repl.py --max-steps 50
```

### LLM Settings

```bash
# Use a different Ollama model
uv run python browser_use_repl.py --model llama3.1:8b

# Connect to remote Ollama server
uv run python browser_use_repl.py --host http://remote-server:11434

# Disable prompt optimization
uv run python browser_use_repl.py --no-optimize
```

## Comparison with Other CLIs

| Feature | REPL CLI | Interactive CLI | Main CLI (TUI) |
|---------|----------|-----------------|----------------|
| **Session Type** | Persistent | One-shot | Persistent |
| **Interface** | Command prompt | Command line | Full TUI |
| **Conversation** | Multi-turn | Single task | Multi-turn |
| **Command History** | Yes | Limited | Yes |
| **Special Commands** | Yes | No | No |
| **Browser Persistence** | Yes | No | Yes |
| **Best For** | Interactive exploration | Quick automation | Visual debugging |

## Troubleshooting

### Ollama Connection Issues

```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# If not running, start it
ollama serve

# Verify the model is available
ollama list
```

### Browser Not Opening

```bash
# Install/reinstall Chromium
uvx playwright install chromium --with-deps

# Try headless mode
uv run python browser_use_repl.py --headless
```

### Prompt Optimization Fails

```bash
# Skip optimization to use queries directly
uv run python browser_use_repl.py --no-optimize
```

### Agent Gets Stuck

In the REPL, press `Ctrl+C` once to interrupt the current task, then:

```
> /clear
> [Try a more specific query]
```

### History Not Working

The REPL saves history to `~/.browser_use_repl_history`. If arrow keys don't work:

1. Check if the file exists and has write permissions
2. Try installing `readline` package: `pip install readline`
3. On Windows, consider using WSL or Git Bash for better readline support

## Advanced Usage

### Combining Multiple Queries

The REPL is perfect for complex workflows that build on each other:

```
> search google for "browser automation python"
> click on the first result
> scroll down to the examples section
> extract all the example code snippets
> save them to a file called examples.txt
```

### Session Management

```bash
# View current configuration
> /config

Current Configuration:
  LLM: ChatOllama
  Model: qwen2.5:7b
  Browser Mode: Visible
  Vision: Enabled
  Max Steps: 20
  Prompt Optimization: Enabled

# Check what you've done
> /history

Command History:
  1. find the latest Python version on python.org
  2. now check what version of pip comes with it
  3. /config
```

### Error Recovery

If a task fails, you can:

1. Refine your query and try again (session persists)
2. Use `/clear` to start with a fresh browser
3. Press Ctrl+C to interrupt and try a different approach

## Performance Tips

1. **Use `--no-vision` for text-only tasks**: Faster execution, saves on LLM tokens
2. **Set appropriate `--max-steps`**: Lower for simple tasks, higher for complex workflows
3. **Use `--headless` for production**: Saves resources when visual feedback isn't needed
4. **Enable `--verbose` for debugging**: See exactly what the agent is thinking
5. **Use local Ollama for unlimited queries**: No API costs or rate limits

## Security Notes

- The browser session persists, including cookies and login state
- Use `/clear` to wipe session data between different workflows
- Be cautious when entering sensitive information (passwords, API keys)
- Consider using `--headless` for server deployments

## Integration with Scripts

While the REPL is interactive, you can also pipe commands to it:

```bash
# Run a sequence of commands
echo -e "find top HN post\n/exit" | uv run python browser_use_repl.py
```

For non-interactive automation, use the one-shot `browser_use_interactive.py` instead.

## License

Same as browser-use: MIT License

## Related Documentation

- **Official Docs**: https://docs.browser-use.com/
- **Prompting Guide**: https://docs.browser-use.com/customize/agent/prompting-guide
- **Architecture**: See `ARCHITECTURE.md`
- **One-Shot CLI**: See `INTERACTIVE_CLI_README.md`
- **Main TUI**: See browser-use CLI documentation

## Support

- **Discord**: https://discord.gg/ESAUZAdxXY
- **GitHub Issues**: https://github.com/browser-use/browser-use/issues
- **Awesome Prompts**: https://github.com/browser-use/awesome-prompts
