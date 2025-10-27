# REPL Prompting Tips

## The Problem with Over-Optimization

The agent can get distracted when prompts are too complex or have too many steps. This happens because:

1. **Too many instructions** confuse the agent's focus
2. **Multi-step plans** cause the agent to improvise when steps don't match reality
3. **Generic instructions** (like "scroll to find...") lead to exploration instead of direct action

## Best Practices for Queries

### ✅ GOOD Queries (Direct & Specific)

```
go to youtube.com/@JabezTech and get the subscriber count

navigate to python.org and find the latest version

go to github.com/browser-use/browser-use and get the star count

search google for "best laptop 2024" and get top 3 results

go to amazon.com and search for wireless mouse under $30
```

### ❌ BAD Queries (Too Complex)

```
Navigate to YouTube by entering the URL in the browser, then search for JabezTech,
click on the channel, find the About tab, scroll down until you see the subscriber
count, extract it, and save it to a variable

Go to Python's website, look around for download information, try to find version
details, and if that doesn't work, try searching the page, then extract whatever
version number you can find
```

## Key Principles

### 1. Be Direct
Don't tell the agent HOW to do it, just tell it WHAT you want:

❌ "Navigate to the URL bar, type youtube.com, press Enter, then..."
✅ "go to youtube.com"

### 2. One Clear Goal Per Query
Don't chain multiple tasks in one query:

❌ "go to YouTube, search for channels, find JabezTech, get subscribers, then go to Twitter and search for the same person"
✅ Query 1: "go to youtube.com/@JabezTech and get subscriber count"
✅ Query 2: "now go to twitter.com and search for JabezTech"

### 3. Avoid Conditional Logic
Don't add "if this then that" instructions:

❌ "If you can't find the button, try scrolling. If that doesn't work, use search. Otherwise, click the menu."
✅ "find and click the subscribe button"

### 4. Trust the Agent's Capabilities
The agent knows how to:
- Navigate to URLs
- Click elements
- Extract text
- Search on pages
- Scroll when needed

You don't need to micromanage these actions.

### 5. Use Natural Language
Write like you're talking to a human assistant:

❌ "Execute navigation action to URL https://example.com then perform click action on element with selector #button"
✅ "go to example.com and click the login button"

## Common Scenarios

### Getting Information from a Page

```
✅ "go to youtube.com/@JabezTech and get subscriber count"
✅ "navigate to python.org and find latest version"
✅ "go to github.com/microsoft/vscode and get the description"
```

### Searching and Extracting

```
✅ "search google for 'best laptop 2024' and list top 3 results with prices"
✅ "go to amazon and search for 'wireless mouse' under $30"
✅ "search github for 'browser automation' and get top 5 repos"
```

### Multi-Step Workflows (Use Multiple Queries)

Instead of one complex query, break it down:

```
Query 1: "go to twitter.com and login"
Query 2: "search for #browseruse"
Query 3: "like the first 3 tweets"
Query 4: "compose a tweet: 'Great tool!'"
```

### Form Filling

```
✅ "go to example.com/contact and fill name='John Doe' email='john@example.com'"
✅ "fill the search box with 'laptop' and submit"
```

## When the Agent Gets Distracted

If the agent starts doing random things:

1. **Press Ctrl+C** to interrupt
2. **Use `/clear`** to reset the browser session
3. **Simplify your query** - make it more direct
4. **Try again** with a clearer goal

Example:
```
> go to youtube and get subscriber count for JabezTech channel and also check video views

[Agent gets confused, starts analyzing comments]

Ctrl+C to stop

> /clear

> go to youtube.com/@JabezTech and get subscriber count

[Agent succeeds]
```

## Debugging Your Queries

If a query isn't working:

1. **Make it shorter** - Remove extra words
2. **Be more specific** - Include exact URLs or names
3. **Remove explanations** - Just state what you want
4. **Test simpler version first** - Build up complexity gradually

### Example Refinement Process

```
❌ Original: "Can you please navigate to the YouTube website and try to find the
    channel called JabezTech, and once you're there, if possible, extract the
    subscriber count from wherever it might be displayed"

🔄 Better: "go to YouTube and find JabezTech channel's subscriber count"

✅ Best: "go to youtube.com/@JabezTech and get subscriber count"
```

## Using the REPL Effectively

### Starting Fresh
```
> /clear
  [Clears browser and agent state]
> your new query here
```

### Building on Previous Context
```
> go to github.com/microsoft/vscode
  [Agent navigates]

> get the description
  [Agent uses existing page to extract description]

> now get the star count
  [Agent continues on same page]
```

### Checking Configuration
```
> /config
  [Shows current settings]

> /history
  [Shows what you've tried]
```

## Model-Specific Tips

### Ollama (qwen2.5:7b)
- Keep queries very simple and direct
- Use explicit URLs when possible
- Break complex tasks into multiple queries
- Be patient - local models are slower but work well with clear instructions

### OpenAI (GPT-4)
- Can handle slightly more complex queries
- Better at understanding context
- Still benefits from direct, specific instructions

### Claude / Gemini
- Good at understanding intent
- Can handle some conditional logic
- Best results still come from simple, direct queries

## Quick Reference

| Situation | Do This | Not This |
|-----------|---------|----------|
| Getting data | "get subscriber count" | "find the number of subscribers by looking for..." |
| Navigation | "go to youtube.com" | "open a new tab, type youtube.com in the address bar, press enter" |
| Clicking | "click subscribe button" | "locate the subscribe button which might be red or in the menu..." |
| Extracting | "get top 3 product names" | "scroll through products, read each name, compile a list..." |
| Searching | "search google for X" | "go to google, find search box, type X, press enter, wait for results..." |

## Remember

The agent is smart enough to figure out HOW to accomplish tasks. Your job is to clearly communicate WHAT you want, not how to do it. Keep it simple, direct, and focused!
