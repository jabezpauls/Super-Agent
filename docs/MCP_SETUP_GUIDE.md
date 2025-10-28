# MCP Setup Guide - Google Calendar & Gmail Integration

This guide will help you set up Google Calendar and Gmail MCP servers for use with the browser-use REPL.

## Overview

The MCP (Model Context Protocol) servers allow the browser-use agent to interact with Google Calendar and Gmail APIs, enabling the agent to:
- **Calendar**: View, create, update, and delete calendar events
- **Gmail**: Read, send, search emails, and modify labels

## Prerequisites

- Python 3.11+
- Google Account
- Google Cloud Project with APIs enabled

## Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click "Select a project" → "New Project"
3. Enter project name (e.g., "Browser Use MCP")
4. Click "Create"

## Step 2: Enable Required APIs

1. In Google Cloud Console, go to "APIs & Services" → "Library"
2. Search for and enable:
   - **Google Calendar API**
   - **Gmail API**

Click "Enable" for each API.

## Step 3: Create OAuth 2.0 Credentials

### 3.1 Configure OAuth Consent Screen

1. Go to "APIs & Services" → "OAuth consent screen"
2. Select "External" user type (unless you have Google Workspace)
3. Click "Create"
4. Fill in required fields:
   - **App name**: Browser Use MCP
   - **User support email**: Your email
   - **Developer contact**: Your email
5. Click "Save and Continue"
6. **Scopes**: Click "Add or Remove Scopes"
   - Add: `https://www.googleapis.com/auth/calendar`
   - Add: `https://www.googleapis.com/auth/gmail.modify`
7. Click "Save and Continue"
8. **Test users**: Add your email address (while app is in testing)
9. Click "Save and Continue"

### 3.2 Create OAuth Client ID

1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "OAuth client ID"
3. Application type: **Desktop app**
4. Name: "Browser Use Desktop"
5. Click "Create"
6. Click "Download JSON" to download the credentials file
7. Save as `credentials.json` in your `browser_agent` directory

## Step 4: Install Required Dependencies

The dependencies should already be installed from `pyproject.toml`, but verify:

```bash
cd browser_agent
uv sync

# Or manually install if needed:
pip install fastmcp google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
```

## Step 5: Set Up Environment Variables

Create or update your `.env` file in the `browser_agent` directory:

```bash
# Google OAuth credentials
GOOGLE_CREDENTIALS_PATH=./credentials.json
GOOGLE_TOKEN_PATH=./token.pickle

# MCP Server ports
MCP_CALENDAR_PORT=8002
MCP_GMAIL_PORT=8001

# Your LLM API keys (if using cloud models)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=AIza...
```

## Step 6: First-Time Authentication

When you first use the MCP servers, you'll need to authenticate:

### Option A: Authenticate via REPL

1. Start the REPL:
   ```bash
   python browser_use_repl.py --model deepseek-r1:14b
   ```

2. Use a calendar or email command:
   ```
   > check my calendar tomorrow
   ```

3. A browser window will open for OAuth authentication:
   - Select your Google account
   - Click "Continue" to allow access
   - Grant permissions for Calendar and Gmail
   - Close the browser when it says "authentication successful"

### Option B: Authenticate Manually

Run the MCP servers directly to authenticate:

```bash
# Authenticate Calendar
python scripts/mcp_calendar_server.py

# Authenticate Gmail (in a new terminal)
python scripts/mcp_gmail_server.py
```

After authentication, tokens will be saved to:
- `token.pickle` (Calendar)
- `gmail_token.pickle` (Gmail)

## Step 7: Verify Setup

Test that everything works:

```bash
python browser_use_repl.py --model deepseek-r1:14b
```

Try these commands:
```
> list my calendar events for today
> check my unread emails
> schedule a test meeting tomorrow at 2pm
```

## Troubleshooting

### Issue: "FileNotFoundError: credentials.json"

**Solution**: Make sure `credentials.json` is in the `browser_agent` directory and `GOOGLE_CREDENTIALS_PATH` is set correctly.

```bash
# Check if file exists
ls credentials.json

# Verify environment variable
echo $GOOGLE_CREDENTIALS_PATH
```

### Issue: "Access blocked: App is in testing mode"

**Solution**:
1. Go to OAuth consent screen in Google Cloud Console
2. Add your email to "Test users"
3. Or publish the app (requires verification for production use)

### Issue: "Token has been expired or revoked"

**Solution**: Delete old tokens and re-authenticate:

```bash
rm token.pickle gmail_token.pickle
python browser_use_repl.py --model deepseek-r1:14b
# Follow authentication prompts again
```

### Issue: "Port already in use"

**Solution**: Change MCP server ports in `.env`:

```bash
MCP_CALENDAR_PORT=8003
MCP_GMAIL_PORT=8004
```

### Issue: "Invalid grant" error

**Solution**: Token refresh failed. Delete and re-generate:

```bash
rm token.pickle gmail_token.pickle
# Re-authenticate
```

### Issue: MCP servers not starting

**Solution**: Check if required dependencies are installed:

```bash
pip list | grep -E "fastmcp|google-auth|google-api"

# If missing:
pip install fastmcp google-auth google-auth-oauthlib google-api-python-client
```

## Security Best Practices

### 1. Protect Your Credentials

**Never commit these files to git:**
- `credentials.json`
- `token.pickle`
- `gmail_token.pickle`
- `.env`

Add to `.gitignore`:
```
credentials.json
*.pickle
token*.pickle
.env
```

### 2. Token Storage

Tokens are stored locally as pickle files. For production:
- Use encrypted storage
- Implement token rotation
- Consider using service accounts instead of user OAuth

### 3. Scope Limitations

The MCP servers request minimal scopes:
- Calendar: `https://www.googleapis.com/auth/calendar` (full access)
- Gmail: `https://www.googleapis.com/auth/gmail.modify` (read/send/modify)

For read-only use cases, consider more restrictive scopes:
- Calendar read-only: `https://www.googleapis.com/auth/calendar.readonly`
- Gmail read-only: `https://www.googleapis.com/auth/gmail.readonly`

Edit the `SCOPES` in `mcp_calendar_server.py` and `mcp_gmail_server.py` to change permissions.

### 4. Rate Limits

Google APIs have usage quotas:
- **Calendar API**: 1,000,000 queries/day
- **Gmail API**: 1,000,000,000 quota units/day

The MCP servers don't implement rate limiting. For heavy usage, add rate limiting logic.

## API Quota Management

### Check Your Quota Usage

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Navigate to "APIs & Services" → "Dashboard"
3. Click on "Google Calendar API" or "Gmail API"
4. View "Quotas & System Limits"

### Increase Quotas

Default quotas are sufficient for personal use. For higher limits:
1. Go to "IAM & Admin" → "Quotas"
2. Filter by service (Calendar or Gmail)
3. Select quota and click "Edit Quotas"
4. Request increase (requires justification)

## Using with Multiple Google Accounts

To use different Google accounts:

1. **Switch accounts**: Delete token files and re-authenticate
   ```bash
   rm token.pickle gmail_token.pickle
   python browser_use_repl.py --model deepseek-r1:14b
   # Select different account during OAuth flow
   ```

2. **Use separate token files**: Set different paths in `.env`
   ```bash
   GOOGLE_TOKEN_PATH=./tokens/account1_token.pickle
   ```

## Advanced: Service Account Authentication

For server/production deployments, use service accounts instead of OAuth:

1. Create service account in Google Cloud Console
2. Download service account key JSON
3. Grant calendar/email access to service account email
4. Modify MCP servers to use service account credentials

See [Google's Service Account documentation](https://cloud.google.com/iam/docs/service-accounts) for details.

## Next Steps

- Read [REPL_CLI_README.md](REPL_CLI_README.md) for REPL usage
- Read [REPL_PROMPTING_TIPS.md](REPL_PROMPTING_TIPS.md) for effective prompts
- Explore multi-tool queries combining browser, calendar, and email

## Support

If you encounter issues not covered here:
1. Check browser-use docs: https://docs.browser-use.com/
2. GitHub issues: https://github.com/browser-use/browser-use/issues
3. Google API docs:
   - [Calendar API](https://developers.google.com/calendar)
   - [Gmail API](https://developers.google.com/gmail)
