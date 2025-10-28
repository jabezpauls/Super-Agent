"""
CLI Module
Command-line argument parsing and LLM initialization
"""

import argparse
import os
from typing import Tuple

from browser_use_interactive import CleanLogger


def parse_arguments() -> argparse.Namespace:
	"""Parse command-line arguments"""
	parser = argparse.ArgumentParser(
		description='Browser-Use Interactive REPL with Multi-Tool Support (Browser, Calendar, Email, Chat)',
		formatter_class=argparse.RawDescriptionHelpFormatter,
		epilog="""
Examples:
  %(prog)s                                    # Use Ollama (default, free)
  %(prog)s --provider openai --model gpt-4o  # Use OpenAI
  %(prog)s --headless --no-vision            # Headless mode
  %(prog)s --optimize                        # Enable prompt optimization
  %(prog)s --disable-mcp                     # Disable calendar/email tools
  %(prog)s --disable-chat                    # Disable pure chat mode

Multi-Tool Usage:
  > What's 2+2?                              # Chat (auto-routed)
  > Find flights to Tokyo                    # Browser (auto-routed)
  > Check my calendar tomorrow               # Calendar (auto-connects)
  > Send email to john@example.com           # Email (auto-connects)
  > /browser search for hotels               # Force browser tool
  > /calendar schedule meeting 2pm           # Force calendar tool

Prerequisites (for Ollama):
  1. Install Ollama: https://ollama.com/
  2. Start server: ollama serve
  3. Pull model: ollama pull qwen2.5:7b

Prerequisites (for MCP - Google Calendar/Gmail):
  See docs/MCP_SETUP_GUIDE.md for OAuth setup
		""",
	)

	# LLM Configuration
	llm_group = parser.add_argument_group('LLM Configuration')

	llm_group.add_argument(
		'--model',
		type=str,
		default='qwen2.5:7b',
		help='LLM model to use (default: qwen2.5:7b)',
	)

	llm_group.add_argument(
		'--provider',
		type=str,
		choices=['openai', 'anthropic', 'google', 'ollama'],
		default='ollama',
		help='LLM provider (default: ollama)',
	)

	llm_group.add_argument(
		'--host',
		type=str,
		default='http://localhost:11434',
		help='Ollama server URL (default: http://localhost:11434)',
	)

	# Browser Configuration
	browser_group = parser.add_argument_group('Browser Configuration')

	browser_group.add_argument(
		'--headless',
		action='store_true',
		help='Run browser in headless mode',
	)

	browser_group.add_argument(
		'--max-steps',
		type=int,
		default=10,
		help='Maximum steps per task (default: 10)',
	)

	browser_group.add_argument(
		'--no-vision',
		action='store_true',
		help='Disable vision/screenshots',
	)

	browser_group.add_argument(
		'--user-data-dir',
		type=str,
		help='Chrome user data directory (e.g., ~/.config/google-chrome)',
	)

	browser_group.add_argument(
		'--profile-directory',
		type=str,
		help='Chrome profile name (e.g., "Default")',
	)

	browser_group.add_argument(
		'--cdp-url',
		type=str,
		help='Connect to existing Chrome via CDP (e.g., http://localhost:9222)',
	)

	# Tool Configuration
	tool_group = parser.add_argument_group('Tool Configuration')

	tool_group.add_argument(
		'--optimize',
		action='store_true',
		help='Enable LLM-based prompt optimization (recommended)',
	)

	tool_group.add_argument(
		'--disable-mcp',
		action='store_true',
		help='Disable MCP tools (Calendar, Email)',
	)

	tool_group.add_argument(
		'--disable-chat',
		action='store_true',
		help='Disable pure chat mode (always use tools)',
	)

	tool_group.add_argument(
		'--google-credentials',
		type=str,
		default='credentials.json',
		help='Path to Google OAuth credentials (default: credentials.json)',
	)

	# Output Configuration
	output_group = parser.add_argument_group('Output Configuration')

	output_group.add_argument(
		'--quiet',
		action='store_true',
		help='Minimal output (only final results)',
	)

	output_group.add_argument(
		'--verbose',
		'-v',
		action='store_true',
		help='Detailed output including thinking and actions',
	)

	return parser.parse_args()


async def create_llm_from_args(args: argparse.Namespace, logger: CleanLogger) -> Tuple[object, int]:
	"""
	Create LLM instance from command-line arguments

	Args:
		args: Parsed arguments
		logger: Logger for output

	Returns:
		Tuple of (llm instance, exit code). Exit code is 0 on success, 1 on error.
	"""
	logger.header("INITIALIZATION")
	logger.info(f"Provider: {args.provider}")
	logger.info(f"Model: {args.model}")

	if args.provider == 'openai':
		from openai import AsyncOpenAI

		api_key = os.getenv('OPENAI_API_KEY')
		if not api_key:
			logger.error("OPENAI_API_KEY not found in environment")
			logger.info("Please set it in your .env file or export it:")
			logger.info("  export OPENAI_API_KEY=your_key_here")
			return None, 1

		llm = AsyncOpenAI(api_key=api_key)
		llm.model = args.model
		logger.info("OpenAI client initialized")
		return llm, 0

	elif args.provider == 'anthropic':
		from anthropic import AsyncAnthropic

		api_key = os.getenv('ANTHROPIC_API_KEY')
		if not api_key:
			logger.error("ANTHROPIC_API_KEY not found in environment")
			logger.info("Please set it in your .env file or export it:")
			logger.info("  export ANTHROPIC_API_KEY=your_key_here")
			return None, 1

		llm = AsyncAnthropic(api_key=api_key)
		llm.model = args.model
		logger.info("Anthropic client initialized")
		return llm, 0

	elif args.provider == 'google':
		from browser_use.llm.google import ChatGoogle

		api_key = os.getenv('GOOGLE_API_KEY')
		if not api_key:
			logger.error("GOOGLE_API_KEY not found in environment")
			logger.info("Please set it in your .env file or export it:")
			logger.info("  export GOOGLE_API_KEY=your_key_here")
			return None, 1

		llm = ChatGoogle(model=args.model, api_key=api_key)
		logger.info("Google client initialized")
		return llm, 0

	elif args.provider == 'ollama':
		from browser_use.llm.ollama.chat import ChatOllama
		from ollama import AsyncClient

		# Test connection first
		logger.info(f"Testing connection to Ollama at {args.host}...")
		try:
			client = AsyncClient(host=args.host)
			await client.list()
			logger.info("Connected to Ollama server")
		except Exception as e:
			logger.error(f"Failed to connect to Ollama at {args.host}")
			logger.error(f"Error: {str(e)}")
			logger.info("\nMake sure Ollama is running:")
			logger.info("  ollama serve")
			logger.info(f"\nAnd the model is available:")
			logger.info(f"  ollama pull {args.model}")
			return None, 1

		llm = ChatOllama(model=args.model, host=args.host)
		logger.info(f"Ollama client initialized with model: {args.model}")
		return llm, 0

	else:
		logger.error(f"Unknown provider: {args.provider}")
		return None, 1


def setup_mcp_environment(args: argparse.Namespace):
	"""
	Setup MCP-related environment variables

	Args:
		args: Parsed arguments
	"""
	if not args.disable_mcp:
		# Set Google credentials path if specified
		if args.google_credentials:
			os.environ['GOOGLE_CREDENTIALS_PATH'] = args.google_credentials

		# Use default token paths if not already set
		if 'GOOGLE_TOKEN_PATH' not in os.environ:
			os.environ['GOOGLE_TOKEN_PATH'] = 'token.pickle'

		# Set MCP server ports if not already set
		if 'MCP_CALENDAR_PORT' not in os.environ:
			os.environ['MCP_CALENDAR_PORT'] = '8002'

		if 'MCP_GMAIL_PORT' not in os.environ:
			os.environ['MCP_GMAIL_PORT'] = '8001'
