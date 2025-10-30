# Knowledge Directory

This directory contains your personal context and information that the AI agent uses to personalize tasks.

## Files:

- **profile.txt** - Your personal information (name, email, address, etc.)
- **contacts.txt** - Your contact list with email addresses
- **preferences.txt** - Your preferences and common task defaults

## Usage:

All `.txt` files in this directory are automatically loaded and injected into the agent's context. The agent will use this information for:

- **Email sending** - Lookup contact emails by name
- **Form filling** - Auto-fill with your personal info
- **Scheduling** - Use your timezone and preferences
- **General tasks** - Context-aware automation

## How to Update:

1. Edit any `.txt` file in this directory
2. Restart the REPL to reload the context
3. That's it! The agent will use the updated information

## Security:

⚠️ **Important:** These files contain personal information!

- Keep this directory private (already in `.gitignore`)
- Don't share these files publicly
- Use environment variables for sensitive secrets
- Consider encrypting if needed

## Examples:

### Sending Email:
```
> send email to jabez saying hello
```
Agent will lookup "jabez" in contacts.txt and find `jabezpaul8@gmail.com`

### Filling Forms:
```
> fill this form with my information
```
Agent will use data from profile.txt

### Scheduling:
```
> schedule meeting with team tomorrow
```
Agent will use your default meeting preferences
