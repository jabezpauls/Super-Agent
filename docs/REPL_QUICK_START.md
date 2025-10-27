# Browser-Use REPL - Quick Start Guide

## Installation & Setup

```bash
# 1. Make sure Ollama is running
ollama serve

# 2. Check if qwen2.5:7b is available
ollama list

# 3. If not, pull it
ollama pull qwen2.5:7b

# 4. Start the REPL
uv run python browser_use_repl.py --verbose
```

## Your First Session

```
> go to youtube.com/@JabezTech and get subscriber count

  [Agent navigates and extracts subscriber count]

> now get the video count

  [Agent continues on same page to find video count]

> /exit
```

## Why Your Query Might Fail

### ❌ Problem: Agent Gets Distracted

**Your query:**
```
go to JabezTech YouTube channel and find the subscriber count by clicking
on About tab and scrolling until you see the number
```

**What happens:**
- Agent over-thinks the instructions
- Starts analyzing comments instead of finding subscriber count
- Gets lost in page content

### ✅ Solution: Keep It Simple

**Better query:**
```
go to youtube.com/@JabezTech and get subscriber count
```

**What happens:**
- Agent knows where to go directly
- Finds subscriber count efficiently
- Returns the result

## The Golden Rule

**Tell the agent WHAT you want, not HOW to do it.**

The agent is trained to:
- Navigate websites
- Find information
- Click buttons
- Extract content

You don't need to explain these steps!

## Common Patterns

### Pattern 1: Direct Navigation + Extraction
```
> go to [URL] and get [specific information]

Examples:
> go to python.org and get latest version
> go to github.com/browser-use/browser-use and get star count
> go to youtube.com/@channel and get subscriber count
```

### Pattern 2: Search + Extract
```
> search [site] for [query] and get [information]

Examples:
> search google for "best laptop 2024" and list top 5 results
> search amazon for wireless mouse under $30
> search github for browser automation tools
```

### Pattern 3: Multi-Step Workflow (Separate Queries)
```
> go to example.com
> click login button
> fill username with "test" and password with "pass123"
> click submit
```

## Special Commands

```
/help     - Show help
/exit     - Exit REPL
/clear    - Reset browser (use when agent gets confused)
/history  - See what you've tried
/config   - Check current settings
```

## When Things Go Wrong

### Agent is doing random things?
```
Ctrl+C (interrupt)
> /clear
> [Try simpler query]
```

### Not finding what you want?
```
> /clear
> go to [exact URL] and get [specific thing]
```

### Need to start over?
```
> /clear
> [Your query]
```

## Tips for Success

1. **Use explicit URLs** when possible
   - ✅ `go to youtube.com/@JabezTech`
   - ❌ `go to JabezTech's YouTube channel`

2. **One goal per query**
   - ✅ `get subscriber count` then `get video count`
   - ❌ `get subscriber count and video count and latest video title`

3. **Be specific about what to extract**
   - ✅ `get the star count`
   - ❌ `get some information about the repository`

4. **Avoid instructions on HOW**
   - ✅ `click subscribe button`
   - ❌ `find the subscribe button by scrolling, if not visible try the menu`

5. **Use /clear if stuck**
   - Browser state can get messy
   - /clear resets everything

## Example Session: Research Workflow

```
# Start REPL
uv run python browser_use_repl.py --verbose

# Session
> go to github.com/microsoft/vscode and get description
  [Result: VS Code is a code editor...]

> get the star count
  [Result: 175k stars]

> go to github.com/browser-use/browser-use
  [Navigates to new repo]

> get the description and star count
  [Result: Browser automation with LLMs. 15k stars]

> /history
  [Shows all your queries]

> /exit
```

## Configuration Options

```bash
# Verbose mode (see all thinking)
uv run python browser_use_repl.py --verbose

# Headless mode (no browser window)
uv run python browser_use_repl.py --headless --verbose

# Disable vision (faster, less accurate)
uv run python browser_use_repl.py --no-vision

# Increase max steps for complex tasks
uv run python browser_use_repl.py --max-steps 50

# Use LLM-based prompt optimization (experimental)
uv run python browser_use_repl.py --optimize
```

## Advanced: Using Other LLMs

### OpenAI
```bash
# Create .env file
echo "OPENAI_API_KEY=your_key" > .env

# Run with OpenAI
uv run python browser_use_repl.py --provider openai --model gpt-4o
```

### Google Gemini
```bash
# Create .env file
echo "GOOGLE_API_KEY=your_key" > .env

# Run with Google
uv run python browser_use_repl.py --provider google --model gemini-2.0-flash-exp
```

## Troubleshooting

### Ollama not running?
```bash
# Check if running
curl http://localhost:11434/api/tags

# If not, start it
ollama serve
```

### Model not found?
```bash
# Pull the model
ollama pull qwen2.5:7b

# Verify
ollama list
```

### Browser won't open?
```bash
# Install playwright
uvx playwright install chromium --with-deps
```

### Agent not understanding?
- Make query simpler
- Use explicit URLs
- Break into multiple queries
- Check /history to see what worked before

## Resources

- **Prompting Tips**: See `REPL_PROMPTING_TIPS.md`
- **Full Documentation**: See `REPL_CLI_README.md`
- **Demo Script**: Run `./demo_repl.sh`

## Quick Commands Reference

```bash
# Start REPL
uv run python browser_use_repl.py --verbose

# In REPL:
> your query here
> /clear          # Reset if confused
> /history        # See what you tried
> /config         # Check settings
> /exit           # Quit

# Interrupt stuck agent:
Ctrl+C
```

## Remember

**Keep queries simple, direct, and focused. Trust the agent to figure out HOW to accomplish WHAT you ask!**
