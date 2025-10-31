#!/usr/bin/env python3
"""
Browser-Use Interactive REPL (Read-Eval-Print Loop)
Multi-Tool AI Agent with Browser, Calendar, Email, and Chat capabilities

Features:
- Intelligent tool routing (automatic or manual)
- Browser automation (existing)
- Google Calendar integration via MCP
- Gmail integration via MCP
- Pure chat conversations
- Persistent sessions

Usage:
	python browser_use_repl.py                              # Default (Ollama)
	python browser_use_repl.py --provider openai --model gpt-4o
	python browser_use_repl.py --optimize --headless
"""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from browser_use_interactive import setup_logging, CleanLogger
from repl.cli import parse_arguments, create_llm_from_args, setup_mcp_environment
from repl.session_manager import SessionManager
from repl.commands import CommandHandler

# Readline for command history
try:
	import readline
	READLINE_AVAILABLE = True
except ImportError:
	READLINE_AVAILABLE = False


async def run_repl(llm, logger: CleanLogger, args) -> int:
	"""
	Run the interactive REPL loop

	Args:
		llm: Language model instance
		logger: Logger for output
		args: Parsed command-line arguments

	Returns:
		Exit code (0 for success)
	"""
	# Create session manager
	session = SessionManager(
		llm=llm,
		logger=logger,
		headless=args.headless,
		max_steps=args.max_steps,
		use_vision=not args.no_vision,
		optimize_prompts=args.optimize,
		user_data_dir=args.user_data_dir,
		profile_directory=args.profile_directory,
		cdp_url=args.cdp_url,
		enable_mcp=not args.disable_mcp,
		disable_chat=args.disable_chat,
	)

	# Create command handler
	cmd_handler = CommandHandler(session=session, logger=logger)

	# Setup readline history
	history_file = None
	if READLINE_AVAILABLE:
		history_file = Path.home() / '.browser_use_repl_history'
		try:
			readline.read_history_file(history_file)
		except FileNotFoundError:
			pass
		readline.set_history_length(1000)

	# Clear terminal and display ASCII art welcome message
	os.system('clear' if os.name != 'nt' else 'cls')

	# Bold neon cyan for cyberpunk aesthetic
	neon_cyan = '\033[1;96m'
	reset = '\033[0m'

	ascii_art = f"""{neon_cyan}
 ███████╗██╗   ██╗██████╗ ███████╗██████╗      █████╗  ██████╗ ███████╗███╗   ██╗████████╗
 ██╔════╝██║   ██║██╔══██╗██╔════╝██╔══██╗    ██╔══██╗██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝
 ███████╗██║   ██║██████╔╝█████╗  ██████╔╝    ███████║██║  ███╗█████╗  ██╔██╗ ██║   ██║
 ╚════██║██║   ██║██╔═══╝ ██╔══╝  ██╔══██╗    ██╔══██║██║   ██║██╔══╝  ██║╚██╗██║   ██║
 ███████║╚██████╔╝██║     ███████╗██║  ██║    ██║  ██║╚██████╔╝███████╗██║ ╚████║   ██║
 ╚══════╝ ╚═════╝ ╚═╝     ╚══════╝╚═╝  ╚═╝    ╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝
{reset}"""

	print(ascii_art)

	print("=" * 88)
	print()
	print("AVAILABLE TOOLS:")
	print("  Browser    │ Web automation and data extraction (always available)")
	print("  Chat       │ Natural language conversations" + (" (enabled)" if not args.disable_chat else " (disabled)"))
	print("  Calendar   │ Google Calendar management" + (" (MCP enabled)" if not args.disable_mcp else " (disabled)"))
	print("  Email      │ Gmail operations" + (" (MCP enabled)" if not args.disable_mcp else " (disabled)"))
	print("  Sheets     │ Google Sheets operations" + (" (MCP enabled)" if not args.disable_mcp else " (disabled)"))
	print()
	print("USAGE:")
	print("  • Type naturally - AI automatically selects the appropriate tool")
	print("  • Force specific tool: /browser, /email, /calendar, /sheets, /chat")
	print("  • Commands: /help (show all commands) | /exit (quit application)")
	print()
	print("CHROME CONNECTION:")
	print("  • Automatically connects to existing Chrome instance on port 9222")
	print("  • To use existing Chrome session, launch it first with:")
	print("    $ google-chrome --remote-debugging-port=9222 --user-data-dir=/tmp/chrome-debug")
	print("  • Verify connection: curl http://localhost:9222/json/version")
	print()
	print("=" * 88)
	print()

	try:
		while True:
			try:
				# Get user input
				query = input("> ").strip()

				if not query:
					continue

				# Add to history
				session.command_history.append(query)
				if READLINE_AVAILABLE and history_file:
					readline.write_history_file(history_file)

				# Handle special commands
				if query.startswith('/'):
					command_str = query[1:]
					should_continue = await cmd_handler.handle_command(command_str)

					if not should_continue:
						break  # Exit REPL

					continue

				# Process regular query
				result = await session.process_query(query)

				# Display result if not empty
				if result:
					print(f"\n{result}\n")

			except KeyboardInterrupt:
				print("\n\nUse /exit to quit, or Ctrl+C again to force quit")
				try:
					confirm = input("Press Ctrl+C again within 2 seconds to force quit: ")
				except KeyboardInterrupt:
					logger.info("\nForce quitting...")
					break
				continue

			except EOFError:
				logger.info("\nExiting REPL...")
				break

	finally:
		# Cleanup
		logger.info("Cleaning up...")
		await session.cleanup()
		logger.success("Goodbye!")

	return 0


async def main() -> int:
	"""Main entry point"""
	try:
		# Parse arguments
		args = parse_arguments()

		# Setup logging
		setup_logging(verbose=args.verbose)
		logger = CleanLogger(verbose=not args.quiet)

		# Set environment variables
		if args.verbose:
			os.environ['BROWSER_USE_LOGGING_LEVEL'] = 'info'
		else:
			os.environ['BROWSER_USE_LOGGING_LEVEL'] = 'error'

		# Setup MCP environment
		setup_mcp_environment(args)

		# Initialize LLM
		llm, exit_code = await create_llm_from_args(args, logger)
		if exit_code != 0:
			return exit_code

		# Run REPL
		return await run_repl(llm, logger, args)

	except KeyboardInterrupt:
		print("\n\nInterrupted by user")
		return 130

	except Exception as e:
		print(f"\nFatal error: {str(e)}")
		import traceback
		traceback.print_exc()
		return 1


if __name__ == '__main__':
	sys.exit(asyncio.run(main()))
