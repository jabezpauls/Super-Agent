# Understanding Agent Behavior in the REPL

## How the Agent Works

The browser agent operates in a loop:

1. **Receives Task** - Your query
2. **Observes Page** - Takes screenshot + reads DOM
3. **Thinks** - LLM decides what to do next
4. **Acts** - Executes browser actions (click, type, navigate, etc.)
5. **Evaluates** - Checks if goal is achieved
6. **Updates Memory** - Remembers what happened
7. **Repeats** - Goes to step 2 until task is done or max steps reached

## The Memory Field

### What It Should Look Like

```bash
Query: "go to youtube.com/@JabezTech and get subscriber count"

Step 1: Memory: "Navigated to JabezTech YouTube channel"
Step 2: Memory: "On channel page, searching for subscriber count"
Step 3: Memory: "Found subscriber count: 1.2M"
```

Memory should **always relate to your original query**.

### What's Going Wrong

```bash
Query: "go to youtube.com/@JabezTech and get subscriber count"

Step 1: Memory: "Navigated to JabezTech YouTube channel"
Step 2: Memory: "Analyzing YouTube comments and engagement"  ❌
Step 3: Memory: "Checking laptop prices across websites"  ❌❌
```

Memory has **drifted away** from your query. This is a hallucination.

## Why Memory Drift Happens

### 1. Training Data Contamination

The LLM was trained on examples like:
```
"Visit 5 websites and compare laptop prices"
"Analyze YouTube engagement metrics"
```

When it sees a YouTube page, it might recall these examples instead of your actual task.

### 2. Weak Context Window

Smaller models (qwen2.5:7b) have limited "working memory":
- **Step 1-3**: Remembers your task clearly
- **Step 4-7**: Task starts to fade
- **Step 8+**: May forget original task entirely

### 3. Ambiguous Observations

If the agent sees something that matches multiple patterns:
```
[Sees YouTube page with posts and comments]

Could be:
A) Channel page (your task: get subscriber count)
B) Community tab (unrelated to your task)  ← Agent might choose this
```

### 4. Action-Observation Mismatch

```
Action: Scroll down to find subscriber count
Observation: [Shows comments section]
Agent thinks: "Oh, I'm analyzing comments now"  ❌
```

The agent forgets WHY it scrolled and gets distracted by what it sees.

## How We're Preventing It

### 1. Task Anchoring (Built-in)

Every query gets wrapped:
```python
TASK: {your_query}

IMPORTANT: Focus ONLY on this task.
Do not switch to other tasks or examples.
```

### 2. System Prompt Reinforcement

The agent gets reminded:
```
- Your ONLY task is: {original_query}
- Do NOT switch to other tasks
- When complete, call 'done' immediately
```

### 3. Lower Default Max Steps

Changed from 20 → 10 steps:
- Less time to drift
- Forces quicker completion
- Encourages simpler queries

### 4. Stronger Task Phrasing

Your query is rephrased to be more explicit:
```
User: "get subscriber count"
→ "TASK: get subscriber count. Focus ONLY on this."
```

## What You Can Do

### Monitor the Memory Field

Watch for these patterns:

**✅ Good Memory Progression:**
```
Step 1: Memory: "Navigated to target page"
Step 2: Memory: "Searching for requested information"
Step 3: Memory: "Found and extracted the data"
```

**❌ Bad Memory Progression:**
```
Step 1: Memory: "Navigated to target page"
Step 2: Memory: "Analyzing different content"  ← DRIFT STARTING
Step 3: Memory: "Working on completely different task"  ← DRIFT COMPLETE
```

### Intervene Early

As soon as you see memory drift:

```bash
Ctrl+C  # Stop immediately
> /clear  # Reset browser
> [Try again with simpler/more specific query]
```

**Don't wait** for the agent to finish 10 steps of wrong work!

### Use Smaller Task Chunks

Instead of:
```
❌ "go to YouTube, find JabezTech, get subscriber count, video count, and latest video"
```

Do:
```
✅ "go to youtube.com/@JabezTech"
   [verify it worked]
✅ "get subscriber count"
   [verify it worked]
✅ "get video count"
```

This way, if memory drifts in one query, you only lose that one step.

### Be Ultra-Specific

Help the agent maintain focus:

**Vague (agent can drift):**
```
> check the channel information
```

**Specific (harder to drift):**
```
> extract the subscriber count number from this YouTube channel page
```

### Use Explicit Success Criteria

Tell the agent exactly what "done" looks like:

```
> go to youtube.com/@JabezTech and extract the text showing subscriber count (like "1.2M subscribers")
```

This makes it clear when the task is complete.

## Model-Specific Behavior

### qwen2.5:7b (Default, Ollama)

**Memory Characteristics:**
- Strong for 3-5 steps
- Starts to fade after 6-7 steps
- High drift risk after 8+ steps

**Best Practices:**
```bash
# Keep tasks SHORT
--max-steps 8

# Very simple queries
> go to [exact URL] and get [specific thing]

# Break complex tasks into multiple queries
```

**When Memory Drifts:**
- Usually happens at step 3-5
- Often triggered by scrolling or finding unexpected content
- Recovery: Ctrl+C → /clear → retry

### GPT-4/GPT-4o (OpenAI)

**Memory Characteristics:**
- Strong for 10-15 steps
- Rarely drifts
- Can handle complex multi-part tasks

**Best Practices:**
```bash
# Can use more steps
--max-steps 20

# Can chain goals
> go to YouTube and get subscriber count, video count, and channel description
```

### Gemini (Google)

**Memory Characteristics:**
- Strong for 7-12 steps
- Moderate drift risk
- Good with vision-based tasks

**Best Practices:**
```bash
--max-steps 12

# Balance between simple and complex
> go to youtube.com/@JabezTech and extract subscriber count and video count
```

## Real Example: Memory Drift in Action

### Your Query
```
> go to youtube.com/@JabezTech and get subscriber count
```

### What Happens (With Drift)

```
Step 1:
  Action: navigate to youtube.com/@JabezTech
  Observation: [YouTube channel page loads]
  Memory: "Navigated to JabezTech YouTube channel"
  ✅ GOOD - matches your task

Step 2:
  Action: scroll down
  Observation: [Sees community posts and comments]
  Memory: "On YouTube page with posts and engagement metrics"
  ⚠️ WARNING - getting generic, losing focus

Step 3:
  Action: extract post content
  Observation: [Extracts post text]
  Memory: "Analyzing YouTube community posts and interactions"
  ❌ BAD - completely forgot about subscriber count

Step 4:
  Action: navigate to ebay.com
  Memory: "Checking laptop prices on multiple websites"
  ❌❌ CATASTROPHIC - hallucinating a different task entirely
```

### How to Prevent This

#### Option 1: More Specific Query
```
> go to youtube.com/@JabezTech and extract the subscriber count text (format: "X subscribers")
```

Telling it the exact format helps maintain focus.

#### Option 2: Two-Step Approach
```
> go to youtube.com/@JabezTech
  [Wait for it to complete]

> extract subscriber count from this page
```

Split navigation from extraction.

#### Option 3: Lower Max Steps
```bash
uv run python browser_use_repl.py --max-steps 5
```

Force it to complete quickly before drift happens.

## Debugging Memory Issues

### Enable Verbose Mode
```bash
uv run python browser_use_repl.py --verbose
```

Watch these fields:
- **Memory** - Should always relate to your task
- **Next Goal** - Should be a step toward your task
- **Evaluation** - Should reference your task

### Look for Warning Signs

**Memory using wrong keywords:**
```
Your task: YouTube subscriber count
Memory: "laptop prices", "comparison shopping", "website navigation"
```

**Actions unrelated to task:**
```
Your task: Get subscriber count
Action: extract all post texts and interaction details
```

**Navigation to unexpected URLs:**
```
Your task: YouTube channel info
Action: navigate to ebay.com
```

### Recovery Strategy

```bash
# 1. Stop immediately when you notice drift
Ctrl+C

# 2. Check history to see what worked
> /history

# 3. Clear the session
> /clear

# 4. Retry with:
#    - More specific query
#    - Explicit URL
#    - Exact format description
> go to youtube.com/@JabezTech and extract the text that shows subscriber count

# 5. If still failing, reduce max steps
# Exit and restart with --max-steps 5
```

## Summary

**Memory drift is caused by:**
1. Model recalling training examples
2. Weak context retention in smaller models
3. Ambiguous observations triggering wrong associations
4. Too many steps allowing gradual drift

**Prevent it by:**
1. Keeping queries simple and specific
2. Using exact URLs
3. Setting low max-steps (5-10)
4. Breaking complex tasks into multiple queries
5. Monitoring memory field and intervening early

**When it happens:**
1. Ctrl+C immediately
2. /clear to reset
3. Retry with more specific query
4. Consider using stronger model if available

**Remember:** The agent is doing its best, but smaller models have limitations. Work WITH these limitations by keeping tasks short, simple, and focused!
