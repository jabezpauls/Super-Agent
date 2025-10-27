# Browser-Use REPL - Troubleshooting Guide

## Agent Memory Issues

### Problem: Memory Changes Between Steps

**Symptoms:**
```
[Step 2] Memory: Looking for YouTube subscriber count...
[Step 3] Memory: Checking laptop prices on multiple websites...  ❌ WRONG!
```

The agent suddenly switches to a completely different task mid-execution.

**Why This Happens:**

1. **Model Hallucination** - Smaller models (like qwen2.5:7b) can lose track of the original task
2. **Training Data Bleed** - The model recalls examples from training instead of focusing on your task
3. **Weak Task Anchoring** - The original goal isn't reinforced strongly enough

**Solutions:**

#### Solution 1: Use Shorter Max Steps (Default Now)
```bash
# Default is now 10 steps instead of 20
uv run python browser_use_repl.py --verbose

# For complex tasks, increase gradually
uv run python browser_use_repl.py --max-steps 15
```

**Why it helps:** Shorter tasks = less chance to drift

#### Solution 2: Make Queries More Specific
```bash
# ❌ Vague (agent can drift)
> find subscriber count for JabezTech

# ✅ Specific (harder to drift)
> go to youtube.com/@JabezTech and get the subscriber count from the page
```

#### Solution 3: Use /clear and Retry
```bash
> /clear
> [your query again, more specific]
```

**Why it helps:** Fresh browser session = fresh agent memory

#### Solution 4: Break Into Smaller Steps
Instead of one complex query, use multiple simple ones:

```bash
# ❌ One complex query
> go to youtube channel JabezTech, get subscriber count, then check latest video

# ✅ Multiple simple queries
> go to youtube.com/@JabezTech
> get subscriber count
> get latest video title
```

#### Solution 5: Try a Stronger Model (If Available)
```bash
# OpenAI GPT-4 (if you have API key)
uv run python browser_use_repl.py --provider openai --model gpt-4o

# Google Gemini
uv run python browser_use_repl.py --provider google --model gemini-2.0-flash-exp
```

**Why it helps:** Larger models maintain context better

### Problem: "Model returned empty action"

**Symptoms:**
```
WARNING  [Agent] Model returned empty action. Retrying...
```

**Why This Happens:**
- Model is confused about what to do next
- Previous step created unexpected state
- Task is too vague

**Solutions:**

1. **Interrupt and Simplify**
   ```bash
   Ctrl+C
   > /clear
   > [simpler, more direct query]
   ```

2. **Be More Explicit About the Goal**
   ```bash
   # ❌ Vague
   > check the page

   # ✅ Explicit
   > extract the subscriber count from this youtube page
   ```

3. **Reduce Max Steps**
   ```bash
   uv run python browser_use_repl.py --max-steps 5
   ```

### Problem: Agent Analyzes Wrong Content

**Symptoms:**
```
INFO [Agent] Memory: Analyzing YouTube comments and post interactions...
```

When you asked for subscriber count, not comments.

**Why This Happens:**
- Agent scrolled and found different content
- Model started analyzing whatever it sees instead of searching for the goal
- Vision mode captured screenshot of wrong area

**Solutions:**

1. **Use Explicit URLs**
   ```bash
   # ✅ Direct URL
   > go to youtube.com/@JabezTech and find the text that shows subscriber count
   ```

2. **Disable Vision for Text-Only Tasks**
   ```bash
   uv run python browser_use_repl.py --no-vision
   ```

   **Why it helps:** Without screenshots, agent focuses on text/DOM

3. **Use More Specific Extraction Queries**
   ```bash
   # ❌ Generic
   > get information about the channel

   # ✅ Specific
   > extract the subscriber count number (example: "1.2M subscribers")
   ```

4. **Limit Scrolling**
   The agent shouldn't need to scroll much for basic information. If it's scrolling excessively, use `/clear` and retry.

## Common Error Patterns

### Pattern 1: Task Switching

```
Original Task: Get subscriber count
Step 1: Navigate to YouTube ✓
Step 2: Scroll down ✓
Step 3: Suddenly checking laptop prices ❌
```

**Fix:**
- Reduce `--max-steps` to 5-10
- Make query more specific with exact URL
- Use `/clear` if it happens

### Pattern 2: Infinite Scrolling

```
Step 1: Scroll down
Step 2: Scroll down
Step 3: Scroll down
... (never finds what it's looking for)
```

**Fix:**
```bash
Ctrl+C
> /clear
> go to [exact URL] and extract [specific element by name]
```

### Pattern 3: Hallucinated Actions

```
INFO [Agent] Memory: Visited 3 of 5 comparison websites...
```

When you only asked to visit 1 website.

**Fix:**
- This is the model recalling training examples
- Use stronger task anchoring (already built into REPL)
- Try a stronger model if available
- Use more explicit, shorter queries

## Model-Specific Issues

### Ollama qwen2.5:7b (Default)

**Strengths:**
- Runs locally (no API costs)
- Fast for simple tasks
- Good for basic navigation and extraction

**Weaknesses:**
- Can drift on complex tasks
- Memory less reliable after 5-7 steps
- May hallucinate task details

**Best Practices:**
```bash
# Keep max steps low
uv run python browser_use_repl.py --max-steps 8

# Use very simple, direct queries
> go to youtube.com/@JabezTech
> get subscriber count

# Don't chain multiple goals
❌ get subscriber count, video count, and latest video
✅ get subscriber count
```

### OpenAI GPT-4/GPT-4o

**Strengths:**
- Excellent context retention
- Handles complex multi-step tasks
- Less likely to hallucinate

**Weaknesses:**
- Requires API key and costs money
- Slower than local models

**Best Practices:**
```bash
# Can handle longer tasks
uv run python browser_use_repl.py --provider openai --model gpt-4o --max-steps 20

# Can chain goals
> go to youtube.com/@JabezTech and get subscriber count, video count, and description
```

### Google Gemini

**Strengths:**
- Good balance of speed and capability
- Free tier available
- Handles vision well

**Weaknesses:**
- May need API key
- Rate limits on free tier

**Best Practices:**
```bash
# Good for moderate complexity
uv run python browser_use_repl.py --provider google --model gemini-2.0-flash-exp --max-steps 15
```

## Emergency Recovery Commands

### Agent is Completely Stuck
```bash
Ctrl+C (twice if needed)
> /clear
> /config  # verify settings
> [try again with simpler query]
```

### Agent Keeps Failing Same Task
```bash
> /clear
> /history  # see what you tried
> [try completely different approach]
```

### Browser State is Corrupted
```bash
> /exit
# Restart REPL
uv run python browser_use_repl.py --verbose
```

## Prevention Best Practices

### 1. Start Simple, Build Up
```bash
# First run
> go to youtube.com/@JabezTech

# If that works
> get subscriber count

# If that works
> get video count
```

### 2. Use Checkpoints
After each successful query, note what worked:
```bash
> /history
# Review what queries succeeded
```

### 3. Clear Between Major Tasks
```bash
> go to youtube.com/@JabezTech and get subscriber count
> /clear  # Start fresh for next task
> go to github.com/browser-use and get stars
```

### 4. Monitor Memory Changes
Watch the `Memory:` field in verbose mode:
```
INFO [Agent] 🧠 Memory: [should relate to your task]
```

If memory changes to something unrelated → Ctrl+C and `/clear`

### 5. Set Realistic Max Steps
```bash
# Simple info extraction: 5-8 steps
uv run python browser_use_repl.py --max-steps 8

# Form filling: 10-15 steps
uv run python browser_use_repl.py --max-steps 15

# Complex workflows: Use multiple queries instead
```

## Debug Mode

For deep debugging, enable verbose mode:
```bash
uv run python browser_use_repl.py --verbose
```

Watch for these warning signs:
- Memory changing topics
- Actions unrelated to your task
- Scrolling more than 2-3 times
- Navigating to unexpected URLs
- Empty actions or evaluation failures

When you see these → Ctrl+C → /clear → Retry

## Performance Optimization

### Faster Execution
```bash
# Disable vision for text-only tasks
uv run python browser_use_repl.py --no-vision --max-steps 8

# Use headless mode
uv run python browser_use_repl.py --headless --no-vision
```

### Better Accuracy
```bash
# Enable vision for complex pages
uv run python browser_use_repl.py --verbose

# Use stronger model
uv run python browser_use_repl.py --provider openai --model gpt-4o
```

## Getting Help

If you're still having issues:

1. Check `/history` to see what worked before
2. Try `/clear` and use a more specific query
3. Reduce `--max-steps` to force quicker completion
4. Try a different model if available
5. Break complex tasks into multiple simple queries

## Remember

The REPL is designed to work best with:
- **Simple, direct queries**
- **Explicit URLs**
- **One goal at a time**
- **Low max steps (5-10)**
- **Fresh sessions (`/clear`) between different tasks**

When in doubt: **Keep it simple, keep it focused, keep it short!**
