#!/usr/bin/env python3
"""
Browser-Use Interactive REPL (Read-Eval-Print Loop)

A fully interactive CLI tool similar to Claude Code CLI that:
1. Provides a persistent chat-like session with the browser agent
2. Maintains browser and agent state across multiple queries
3. Uses Ollama with qwen2.5:7b by default (no API key required)
4. Shows all thinking and output for each step
5. Supports special commands for session management

Usage:
	uv run python browser_use_repl.py
	uv run python browser_use_repl.py --provider openai --model gpt-4o
	uv run python browser_use_repl.py --headless --no-vision
"""

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv

load_dotenv()

from browser_use import Agent
from browser_use.browser.profile import BrowserProfile
from browser_use.browser.session import BrowserSession

# Import CleanLogger and related utilities from browser_use_interactive
from browser_use_interactive import (
	CleanLogger,
	setup_logging,
)

# Official prompting guidelines from https://docs.browser-use.com/customize/agent/prompting-guide
PROMPT_OPTIMIZATION_TEMPLATE = """You are a browser automation prompt optimization expert.

Your task is to convert a user's natural query into an optimized, specific prompt for a browser automation agent.

OFFICIAL PROMPTING GUIDELINES (from browser-use docs):

1. **Be Specific, Not Vague**
   - Provide detailed, step-by-step instructions
   - Good: "Go to https://quotes.toscrape.com/, extract the first 3 quotes with authors, save to CSV"
   - Bad: "Go to web and get some quotes"

2. **Reference Actions by Name**
   - Use specific action names: navigate, click, scroll, extract, search, input_text, send_keys
   - Example: "use search action to find tutorials, click to open results, scroll action to view more"

3. **Include Keyboard Navigation for Troubleshooting**
   - When clicks fail, use keyboard: "send Tab to navigate, Enter to submit"
   - Example: "If button doesn't click, use send_keys Tab Tab Enter to submit form"

4. **Build Error Recovery Pathways**
   - Include fallback strategies
   - Example: "If page blocks access, use google search as alternative. If timeout occurs, use go_back and retry"

5. **Keep It Actionable**
   - Every instruction should be something the agent can execute
   - Avoid abstract goals like "understand the page" - instead "extract the main heading text"

USER QUERY: {user_query}

Generate an optimized prompt following these guidelines. Be specific but not overly complex. Focus on clear, actionable steps.

OPTIMIZED PROMPT:"""

# Try to import readline for command history support
try:
	import readline

	READLINE_AVAILABLE = True
except ImportError:
	READLINE_AVAILABLE = False


async def optimize_prompt_with_llm(user_query: str, llm, logger: CleanLogger) -> str:
	"""Use LLM to optimize the user query into a specific, actionable prompt"""
	logger.info(f"\nUser Query: {user_query}")
	logger.info("Generating optimized prompt using LLM...")

	# Create the optimization prompt
	optimization_prompt = PROMPT_OPTIMIZATION_TEMPLATE.format(user_query=user_query)

	try:
		# Handle different LLM types
		if hasattr(llm, 'chat') and hasattr(llm.chat, 'completions'):
			# OpenAI-style API
			response = await llm.chat.completions.create(
				model=llm.model if hasattr(llm, 'model') else "gpt-4o-mini",
				messages=[{"role": "user", "content": optimization_prompt}],
				temperature=0.3,
			)
			optimized_prompt = response.choices[0].message.content.strip()

		elif hasattr(llm, 'messages') and hasattr(llm.messages, 'create'):
			# Anthropic-style API
			response = await llm.messages.create(
				model=llm.model if hasattr(llm, 'model') else "claude-3-5-sonnet-20241022",
				max_tokens=1024,
				messages=[{"role": "user", "content": optimization_prompt}],
				temperature=0.3,
			)
			optimized_prompt = response.content[0].text.strip()

		elif hasattr(llm, 'generate_content_async'):
			# Google Gemini-style API
			response = await llm.generate_content_async(optimization_prompt)
			optimized_prompt = response.text.strip()

		elif hasattr(llm, 'ainvoke'):
			# LangChain-style interface (Ollama, etc.)
			from browser_use.llm.messages import UserMessage
			messages = [UserMessage(content=optimization_prompt)]
			response = await llm.ainvoke(messages)

			if hasattr(response, 'completion'):
				optimized_prompt = response.completion.strip()
			elif hasattr(response, 'content'):
				optimized_prompt = response.content.strip()
			else:
				optimized_prompt = str(response).strip()

		else:
			# Fallback: try direct call
			logger.info("Warning: Unknown LLM type, using simple optimization")
			optimized_prompt = f"{user_query}. Be direct and specific."

		logger.info(f"\nOptimized Prompt:\n{optimized_prompt}\n")
		return optimized_prompt

	except Exception as e:
		logger.error(f"Prompt optimization failed: {str(e)}")
		logger.info("Falling back to original query")
		return user_query


class InteractiveSession:
	"""Manages the persistent interactive session with browser agent"""

	def __init__(
		self,
		llm,
		logger: CleanLogger,
		headless: bool = False,
		max_steps: int = 20,
		use_vision: bool = True,
		optimize_prompts: bool = True,
		user_data_dir: Optional[str] = None,
		profile_directory: Optional[str] = None,
		cdp_url: Optional[str] = None,
	):
		self.llm = llm
		self.logger = logger
		self.headless = headless
		self.max_steps = max_steps
		self.use_vision = use_vision
		self.optimize_prompts = optimize_prompts
		self.user_data_dir = user_data_dir
		self.profile_directory = profile_directory
		self.cdp_url = cdp_url

		self.browser_session: Optional[BrowserSession] = None
		self.agent: Optional[Agent] = None
		self.command_history: list[str] = []
		self.running = False

	async def initialize_browser(self):
		"""Initialize the browser session (called once at startup)"""
		if self.browser_session is not None:
			return

		self.logger.header("INITIALIZING BROWSER SESSION")
		self.logger.info("Starting browser...")

		try:
			# Configure browser profile with user options
			browser_profile_args = {
				'headless': self.headless,
				'keep_alive': True,  # Keep browser alive between tasks
				'enable_default_extensions': True,
				'highlight_elements': True,
			}

			# Add user data directory if specified
			if self.user_data_dir:
				browser_profile_args['user_data_dir'] = self.user_data_dir
				self.logger.info(f"Using Chrome profile: {self.user_data_dir}")

			# Add profile directory if specified
			if self.profile_directory:
				browser_profile_args['profile_directory'] = self.profile_directory
				self.logger.info(f"Using profile directory: {self.profile_directory}")

			browser_profile = BrowserProfile(**browser_profile_args)

			# Create browser session with CDP URL if specified
			browser_session_args = {'browser_profile': browser_profile}
			if self.cdp_url:
				browser_session_args['cdp_url'] = self.cdp_url
				self.logger.info(f"Connecting to existing Chrome at: {self.cdp_url}")

			self.browser_session = BrowserSession(**browser_session_args)
			self.logger.info("Browser initialized successfully")

		except Exception as e:
			self.logger.error(f"Failed to initialize browser: {str(e)}")
			raise

	async def process_query(self, query: str) -> str:
		"""Process a user query through the browser agent"""
		# Ensure browser is initialized
		if self.browser_session is None:
			await self.initialize_browser()

		# Optimize prompt if enabled
		if self.optimize_prompts:
			self.logger.header("PROMPT OPTIMIZATION")
			# Use LLM to optimize the prompt with official guidelines
			optimized_prompt = await optimize_prompt_with_llm(query, self.llm, self.logger)
		else:
			# Add simple task anchoring to prevent hallucination
			optimized_prompt = f"""TASK: {query}

IMPORTANT: Focus ONLY on this task. Do not switch to other tasks or examples. Complete this specific goal and nothing else."""

		# Execute the task
		self.logger.header("TASK EXECUTION")
		self.logger.info(f"Task: {optimized_prompt}")
		self.logger.info(f"Max Steps: {self.max_steps}")
		self.logger.info(f"Vision: {'Enabled' if self.use_vision else 'Disabled'}")
		self.logger.info(f"Browser Mode: {'Headless' if self.headless else 'Visible'}")

		try:
			if self.agent is None:
				# Create new agent with custom system prompt for better focus
				from browser_use.agent.views import AgentSettings

				agent_settings = AgentSettings(
					use_vision=self.use_vision,
					use_thinking=True,
					max_actions_per_step=10,
					# Add a custom system prompt suffix to prevent task drift
					system_prompt_suffix=f"\n\nIMPORTANT REMINDERS:\n- Your ONLY task is: {query}\n- Do NOT switch to other tasks or examples\n- Stay focused on this specific goal\n- When you complete this task, call the 'done' action immediately\n- Do not continue to other unrelated tasks",
				)

				self.agent = Agent(
					task=optimized_prompt,
					llm=self.llm,
					browser_session=self.browser_session,
					**agent_settings.model_dump(),
				)

				# Hook into agent to display step-by-step output
				original_step = self.agent.step
				step_counter = [0]

				async def verbose_step(*args, **kwargs):
					"""Wrapper to log each step"""
					step_counter[0] += 1
					self.logger.step(step_counter[0], "Processing...")

					result = await original_step(*args, **kwargs)

					# Display thinking
					if result and hasattr(result, 'model_output') and result.model_output:
						output = result.model_output

						if hasattr(output, 'current_state'):
							state = output.current_state

							# Show thinking
							if hasattr(state, 'thinking') and state.thinking:
								self.logger.thinking(state.thinking)

							# Show evaluation
							if hasattr(state, 'evaluation_previous_goal') and state.evaluation_previous_goal:
								self.logger.info(f"\nEvaluation: {state.evaluation_previous_goal}")

							# Show next goal
							if hasattr(state, 'next_goal') and state.next_goal:
								self.logger.info(f"Next Goal: {state.next_goal}")

						# Show actions
						if hasattr(output, 'actions') and output.actions:
							for action in output.actions:
								action_name = action.__class__.__name__ if hasattr(action, '__class__') else str(action)

								# Get action parameters
								params = []
								if hasattr(action, 'model_dump'):
									action_dict = action.model_dump()
									for key, value in action_dict.items():
										if key not in ['index'] and value is not None:
											params.append(f"{key}={value}")

								self.logger.action(action_name, ", ".join(params) if params else "")

					# Show results
					if result and hasattr(result, 'result'):
						for action_result in result.result:
							if hasattr(action_result, 'extracted_content') and action_result.extracted_content:
								self.logger.result(action_result.extracted_content)

							if hasattr(action_result, 'error') and action_result.error:
								self.logger.error(action_result.error)

					return result

				# Replace step method
				self.agent.step = verbose_step

				# Run the agent
				result = await self.agent.run(max_steps=self.max_steps)
			else:
				# Add new task to existing agent
				self.agent.add_new_task(optimized_prompt)
				result = await self.agent.run(max_steps=self.max_steps)

			# Display final results
			self.logger.header("EXECUTION COMPLETE")

			if result and hasattr(result, 'final_result'):
				final_result = result.final_result()
				if final_result:
					self.logger.success("Task completed successfully")
					self.logger.info("\nFinal Result:")
					self.logger.info(f"{final_result}")
					return final_result
				else:
					self.logger.info("Task completed but no final result returned")
					return "Task completed"
			else:
				self.logger.info("Task completed")
				return "Task completed"

		except KeyboardInterrupt:
			self.logger.error("Task interrupted by user")
			return "Interrupted"

		except Exception as e:
			self.logger.error(f"Task failed: {str(e)}")
			import traceback

			if self.logger.verbose:
				traceback.print_exc()
			return f"Failed: {str(e)}"

	async def clear_session(self):
		"""Clear the current browser session and agent"""
		self.logger.info("Clearing browser session...")

		if self.agent:
			self.agent = None

		if self.browser_session:
			try:
				await self.browser_session.close()
			except Exception as e:
				self.logger.error(f"Error closing browser: {str(e)}")
			finally:
				self.browser_session = None

		self.logger.success("Session cleared")

	async def cleanup(self):
		"""Cleanup resources on exit"""
		if self.browser_session:
			try:
				await self.browser_session.close()
			except Exception:
				pass


async def run_repl(
	llm,
	logger: CleanLogger,
	headless: bool = False,
	max_steps: int = 20,
	use_vision: bool = True,
	optimize_prompts: bool = True,
	user_data_dir: Optional[str] = None,
	profile_directory: Optional[str] = None,
	cdp_url: Optional[str] = None,
) -> int:
	"""Run the interactive REPL loop"""

	# Print banner
	print("\n" + "=" * 70)
	print("  Browser-Use Interactive REPL")
	print("  Chat with the browser agent - Type your queries and press Enter")
	print("=" * 70)
	print("\nSpecial Commands:")
	print("  /help     - Show this help message")
	print("  /exit     - Exit the REPL")
	print("  /quit     - Exit the REPL")
	print("  /clear    - Clear browser session and start fresh")
	print("  /history  - Show command history")
	print("  /config   - Show current configuration")
	print("\nTips for Better Results:")
	print("  - Be specific and direct in your queries")
	print("  - Example: 'go to youtube.com/@JabezTech and get subscriber count'")
	print("  - Keep queries simple - ONE goal at a time")
	print("  - Use /clear if the agent gets confused or memory changes")
	print("  - Watch the 'Memory:' field - it should match your task")
	print("\n" + "=" * 70 + "\n")

	# Initialize session
	session = InteractiveSession(
		llm=llm,
		logger=logger,
		headless=headless,
		max_steps=max_steps,
		use_vision=use_vision,
		optimize_prompts=optimize_prompts,
		user_data_dir=user_data_dir,
		profile_directory=profile_directory,
		cdp_url=cdp_url,
	)

	# Setup readline history if available
	if READLINE_AVAILABLE:
		history_file = Path.home() / '.browser_use_repl_history'
		try:
			readline.read_history_file(history_file)
		except FileNotFoundError:
			pass

		# Set maximum history length
		readline.set_history_length(1000)

	try:
		while True:
			try:
				# Get user input
				query = input("\n> ").strip()

				if not query:
					continue

				# Add to history
				session.command_history.append(query)
				if READLINE_AVAILABLE:
					readline.write_history_file(history_file)

				# Handle special commands
				if query.startswith('/'):
					command = query[1:].lower()

					if command in ['exit', 'quit']:
						logger.info("Exiting REPL...")
						break

					elif command == 'help':
						print("\nAvailable Commands:")
						print("  /help     - Show this help message")
						print("  /exit     - Exit the REPL")
						print("  /quit     - Exit the REPL")
						print("  /clear    - Clear browser session and start fresh")
						print("  /history  - Show command history")
						print("  /config   - Show current configuration")
						print("\nJust type your query to interact with the browser agent.")
						continue

					elif command == 'clear':
						await session.clear_session()
						continue

					elif command == 'history':
						print("\nCommand History:")
						for i, cmd in enumerate(session.command_history, 1):
							print(f"  {i}. {cmd}")
						continue

					elif command == 'config':
						print("\nCurrent Configuration:")
						print(f"  LLM: {llm.__class__.__name__}")
						if hasattr(llm, 'model'):
							print(f"  Model: {llm.model}")
						print(f"  Browser Mode: {'Headless' if headless else 'Visible'}")
						print(f"  Vision: {'Enabled' if use_vision else 'Disabled'}")
						print(f"  Max Steps: {max_steps}")
						print(f"  Prompt Optimization: {'Enabled' if optimize_prompts else 'Disabled'}")
						continue

					else:
						logger.error(f"Unknown command: /{command}")
						logger.info("Type /help to see available commands")
						continue

				# Process the query
				await session.process_query(query)

			except KeyboardInterrupt:
				print("\n\nUse /exit or /quit to exit the REPL, or Ctrl+C again to force quit")
				try:
					# Wait for confirmation
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


def parse_arguments() -> argparse.Namespace:
	"""Parse command-line arguments"""
	parser = argparse.ArgumentParser(
		description='Browser-Use Interactive REPL - Persistent chat-like session with browser agent',
		formatter_class=argparse.RawDescriptionHelpFormatter,
		epilog="""
Examples:
  %(prog)s                                    # Use Ollama with qwen2.5:7b (default)
  %(prog)s --provider openai --model gpt-4o  # Use OpenAI
  %(prog)s --headless --no-vision            # Headless mode without vision
  %(prog)s --verbose                         # Show detailed output
  %(prog)s --no-optimize                     # Skip prompt optimization

Prerequisites (for default Ollama):
  1. Install Ollama: https://ollama.com/
  2. Start Ollama: ollama serve
  3. Pull model: ollama pull qwen2.5:7b
		""",
	)

	parser.add_argument(
		'--model',
		type=str,
		default='qwen2.5:7b',
		help='LLM model to use (default: qwen2.5:7b for ollama)',
	)

	parser.add_argument(
		'--provider',
		type=str,
		choices=['openai', 'anthropic', 'google', 'ollama'],
		default='ollama',
		help='LLM provider to use (default: ollama)',
	)

	parser.add_argument(
		'--host',
		type=str,
		default='http://localhost:11434',
		help='Ollama server URL (default: http://localhost:11434)',
	)

	parser.add_argument(
		'--headless',
		action='store_true',
		help='Run browser in headless mode',
	)

	parser.add_argument(
		'--max-steps',
		type=int,
		default=10,
		help='Maximum number of steps per task (default: 10, increase for complex tasks)',
	)

	parser.add_argument(
		'--no-vision',
		action='store_true',
		help='Disable vision/screenshots',
	)

	parser.add_argument(
		'--optimize',
		action='store_true',
		help='Enable LLM-based prompt optimization using official browser-use guidelines (recommended for complex queries)',
	)

	parser.add_argument(
		'--quiet',
		action='store_true',
		help='Minimal output (only final result)',
	)

	parser.add_argument(
		'--verbose',
		'-v',
		action='store_true',
		help='Show detailed output including all thinking and actions',
	)

	parser.add_argument(
		'--user-data-dir',
		type=str,
		help='Chrome user data directory path (e.g., ~/.config/google-chrome)',
	)

	parser.add_argument(
		'--profile-directory',
		type=str,
		help='Chrome profile directory name (e.g., "Default", "Profile 1")',
	)

	parser.add_argument(
		'--cdp-url',
		type=str,
		help='Connect to existing Chrome via CDP URL (e.g., http://localhost:9222)',
	)

	return parser.parse_args()


async def main() -> int:
	"""Main entry point"""
	args = parse_arguments()

	# Setup logging first
	setup_logging(verbose=args.verbose)

	# Setup logger - show output unless quiet mode
	logger = CleanLogger(verbose=not args.quiet)

	try:
		# Set environment variable based on verbose mode
		if args.verbose:
			os.environ['BROWSER_USE_LOGGING_LEVEL'] = 'info'
		else:
			os.environ['BROWSER_USE_LOGGING_LEVEL'] = 'error'

		# Initialize LLM
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
				return 1

			llm = AsyncOpenAI(api_key=api_key)
			llm.model = args.model
			logger.info("OpenAI client initialized")

		elif args.provider == 'anthropic':
			from anthropic import AsyncAnthropic

			api_key = os.getenv('ANTHROPIC_API_KEY')
			if not api_key:
				logger.error("ANTHROPIC_API_KEY not found in environment")
				logger.info("Please set it in your .env file or export it:")
				logger.info("  export ANTHROPIC_API_KEY=your_key_here")
				return 1

			llm = AsyncAnthropic(api_key=api_key)
			llm.model = args.model
			logger.info("Anthropic client initialized")

		elif args.provider == 'google':
			from browser_use.llm.google import ChatGoogle

			api_key = os.getenv('GOOGLE_API_KEY')
			if not api_key:
				logger.error("GOOGLE_API_KEY not found in environment")
				logger.info("Please set it in your .env file or export it:")
				logger.info("  export GOOGLE_API_KEY=your_key_here")
				return 1

			llm = ChatGoogle(model=args.model, api_key=api_key)
			logger.info("Google client initialized")

		elif args.provider == 'ollama':
			from browser_use.llm.ollama.chat import ChatOllama
			from ollama import AsyncClient

			# Test connection to Ollama first
			logger.info(f"Testing connection to Ollama server at {args.host}...")
			try:
				client = AsyncClient(host=args.host)
				await client.list()
				logger.info("Connected to Ollama server")
			except Exception as e:
				logger.error(f"Failed to connect to Ollama server at {args.host}")
				logger.error(f"Error: {str(e)}")
				logger.info("\nMake sure Ollama is running:")
				logger.info("  ollama serve")
				logger.info(f"\nAnd the model is available:")
				logger.info(f"  ollama pull {args.model}")
				return 1

			llm = ChatOllama(model=args.model, host=args.host)
			logger.info(f"Ollama client initialized with model: {args.model}")

		else:
			logger.error(f"Unknown provider: {args.provider}")
			return 1

		# Run the REPL
		return await run_repl(
			llm=llm,
			logger=logger,
			headless=args.headless,
			max_steps=args.max_steps,
			use_vision=not args.no_vision,
			optimize_prompts=args.optimize,
			user_data_dir=args.user_data_dir,
			profile_directory=args.profile_directory,
			cdp_url=args.cdp_url,
		)

	except KeyboardInterrupt:
		logger.error("\nInterrupted by user")
		return 130

	except Exception as e:
		logger.error(f"Fatal error: {str(e)}")
		import traceback

		if not args.quiet:
			traceback.print_exc()
		return 1


if __name__ == '__main__':
	try:
		exit_code = asyncio.run(main())
		sys.exit(exit_code)
	except KeyboardInterrupt:
		print("\nInterrupted by user")
		sys.exit(130)
