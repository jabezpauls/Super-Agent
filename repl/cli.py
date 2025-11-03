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


def validate_model_provider_match(model: str, provider: str, logger: CleanLogger) -> bool:
	"""
	Validate that model name matches the selected provider
	Returns True if validation passes, False otherwise (with warnings)
	"""
	# Known Groq models that users might confuse with Ollama syntax
	groq_models = {
		'gpt-oss-20b': 'openai/gpt-oss-20b',
		'gpt-oss-120b': 'openai/gpt-oss-120b',
		'gpt-oss:20b': 'openai/gpt-oss-20b',
		'gpt-oss:120b': 'openai/gpt-oss-120b',
	}

	# Check for Groq model with wrong provider
	if provider == 'ollama' and model in groq_models:
		logger.warning(f"⚠️  Model '{model}' is a Groq model, not Ollama!")
		logger.warning(f"   Correct usage: --provider groq --model {groq_models[model]}")
		logger.warning(f"   Continuing anyway, but this will likely fail...")
		return True  # Let it continue but with warning

	# Check for slash syntax with ollama (common mistake)
	if provider == 'ollama' and ('/' in model or model.startswith('openai/')):
		logger.warning(f"⚠️  Model '{model}' uses slash syntax which is typically for Groq/OpenAI")
		logger.warning(f"   Ollama models use colon syntax: model:tag (e.g., 'llama2:7b')")
		logger.warning(f"   If you meant to use Groq, add: --provider groq")
		return True  # Let it continue but with warning

	# Check for colon syntax with groq (common mistake)
	if provider == 'groq' and ':' in model and not model.startswith('openai/'):
		logger.warning(f"⚠️  Model '{model}' uses colon syntax which is for Ollama")
		logger.warning(f"   Groq models use slash syntax: provider/model (e.g., 'openai/gpt-oss-20b')")
		return True  # Let it continue but with warning

	return True


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

	# Validate model/provider match
	validate_model_provider_match(args.model, args.provider, logger)

	if args.provider == 'openai':
		from browser_use.llm.openai.chat import ChatOpenAI

		api_key = os.getenv('OPENAI_API_KEY')
		base_url = os.getenv('OPENAI_BASE_URL')

		# Allow dummy key for vLLM/local endpoints
		if not api_key and not base_url:
			logger.error("OPENAI_API_KEY not found in environment")
			logger.info("Please set it in your .env file or export it:")
			logger.info("  export OPENAI_API_KEY=your_key_here")
			logger.info("Or for vLLM/local endpoints, set OPENAI_BASE_URL")
			return None, 1

		# Use dummy key if base_url is provided (for vLLM compatibility)
		if base_url and not api_key:
			api_key = 'dummy'

		llm = ChatOpenAI(
			model=args.model,
			api_key=api_key,
			base_url=base_url
		)

		endpoint_info = f" (custom endpoint: {base_url})" if base_url else ""
		logger.info(f"OpenAI client initialized{endpoint_info}")
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
