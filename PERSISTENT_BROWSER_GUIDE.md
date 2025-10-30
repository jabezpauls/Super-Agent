# Using Persistent Browser Sessions with Browser-Use

This guide shows you how to use browser-use with an already signed-in browser, keeping your sessions across runs.

## Quick Start (Recommended)

### 1. Setup (First Time Only)

```bash
# Start Chrome with persistent profile
./setup_persistent_browser.sh
```

This will:
- Launch Chrome with a dedicated profile
- Enable remote debugging
- Keep running in the background

**Now sign in to your accounts in Chrome:**
- Gmail
- Google Calendar
- Any other sites you need

### 2. Use REPL (Every Time)

```bash
# Connect to the persistent browser
./use_persistent_browser.sh --model gpt-oss:20b
```

**That's it!** Browser-use will use your logged-in Chrome session.

---

## Method Comparison

| Method | Pros | Cons | Best For |
|--------|------|------|----------|
| **CDP Connection** | Fast, uses existing sessions | Chrome must stay open | Interactive use |
| **Profile Directory** | Automatic persistence | Launches new window each time | Automation scripts |
| **Dedicated Profile** | Clean separation from personal | Need manual setup | Production/testing |

---

## Method 1: CDP Connection (Fastest)

### Setup:
```bash
# Terminal 1: Start Chrome with debugging
google-chrome \
  --remote-debugging-port=9222 \
  --user-data-dir=~/.browser-use-profile &

# Sign in to your accounts in Chrome
```

### Usage:
```bash
# Terminal 2: Run REPL
python browser_use_repl.py \
  --model gpt-oss:20b \
  --cdp-url http://localhost:9222
```

### Verify Connection:
```bash
# Check if Chrome is ready
curl http://localhost:9222/json/version
```

---

## Method 2: Chrome Profile (Simplest)

### Find Your Profile:
```bash
# Linux
ls ~/.config/google-chrome/
# Look for: Default, Profile 1, Profile 2, etc.

# Mac
ls ~/Library/Application\ Support/Google/Chrome/
```

### Usage:
```bash
python browser_use_repl.py \
  --model gpt-oss:20b \
  --user-data-dir ~/.config/google-chrome \
  --profile-directory "Default"
```

**Note:** This will launch a new Chrome window using your profile.

---

## Method 3: Dedicated Profile (Production)

### Create Profile:
```bash
# Create dedicated profile directory
mkdir -p ~/.browser-use-profile

# Launch Chrome to set it up
google-chrome --user-data-dir=~/.browser-use-profile

# Sign in to your accounts, then close Chrome
```

### Usage:
```bash
python browser_use_repl.py \
  --model gpt-oss:20b \
  --user-data-dir ~/.browser-use-profile
```

---

## Advanced: Multiple Profiles

### Create Multiple Profiles:
```bash
# Work profile
google-chrome --user-data-dir=~/.browser-use-work &

# Personal profile
google-chrome --user-data-dir=~/.browser-use-personal \
  --remote-debugging-port=9223 &
```

### Use Specific Profile:
```bash
# Use work profile
python browser_use_repl.py \
  --model gpt-oss:20b \
  --cdp-url http://localhost:9222

# Use personal profile
python browser_use_repl.py \
  --model gpt-oss:20b \
  --cdp-url http://localhost:9223
```

---

## Troubleshooting

### Chrome Won't Connect

**Check if Chrome is running:**
```bash
curl http://localhost:9222/json/version
```

**If not running, start it:**
```bash
google-chrome --remote-debugging-port=9222 \
  --user-data-dir=~/.browser-use-profile &
```

### Port Already in Use

**Kill existing Chrome on that port:**
```bash
# Find the process
lsof -ti:9222

# Kill it
pkill -f "chrome.*remote-debugging-port=9222"

# Or use different port
google-chrome --remote-debugging-port=9223 \
  --user-data-dir=~/.browser-use-profile &
```

### Sessions Not Persisting

**Make sure you're using the same profile directory:**
```bash
# Check what profile you're using
ps aux | grep chrome | grep user-data-dir

# Always use the same directory
--user-data-dir=~/.browser-use-profile
```

---

## Best Practices

1. **Use Dedicated Profile** - Don't mix automation with personal browsing
2. **Keep Chrome Open** - For CDP connections, Chrome must stay running
3. **Use Scripts** - Use `setup_persistent_browser.sh` for consistency
4. **Backup Profile** - Backup `~/.browser-use-profile` periodically

---

## Security Notes

⚠️ **Never expose remote debugging port (9222) to the internet!**

- Only bind to localhost (default)
- Don't forward this port through SSH
- Use firewall rules to block external access

✅ **Safe:**
```bash
--remote-debugging-port=9222  # Binds to 127.0.0.1 only
```

❌ **Dangerous:**
```bash
--remote-debugging-address=0.0.0.0  # DON'T DO THIS!
```

---

## Examples

### Example 1: Email Automation
```bash
# Setup
./setup_persistent_browser.sh
# Sign in to Gmail in Chrome

# Use
./use_persistent_browser.sh --model gpt-oss:20b
> send email to john@example.com saying hello
```

### Example 2: Calendar Management
```bash
# Chrome stays logged into Google Calendar
./use_persistent_browser.sh
> check my calendar tomorrow
> schedule meeting with team at 2pm
```

### Example 3: Research Tasks
```bash
# Logged in to research databases/journals
./use_persistent_browser.sh
> search for papers about AI agents
> summarize the top 3 results
```

---

## Scripts Summary

| Script | Purpose |
|--------|---------|
| `setup_persistent_browser.sh` | One-time setup, launches Chrome |
| `use_persistent_browser.sh` | Connect REPL to persistent Chrome |
| `start_vllm_docker.sh` | Start vLLM for faster inference |
| `use_vllm.sh` | Use REPL with vLLM backend |

---

## Next Steps

1. Run `./setup_persistent_browser.sh`
2. Sign in to your accounts
3. Run `./use_persistent_browser.sh --model gpt-oss:20b`
4. Start automating! 🚀

For faster performance, combine with vLLM:
```bash
# Terminal 1: Start vLLM
./start_vllm_docker.sh

# Terminal 2: Start Chrome
./setup_persistent_browser.sh

# Terminal 3: Use both together
export OPENAI_API_KEY="dummy"
export OPENAI_BASE_URL="http://localhost:8000/v1"
python browser_use_repl.py \
  --provider openai \
  --model Qwen/Qwen2.5-14B-Instruct \
  --cdp-url http://localhost:9222
```
