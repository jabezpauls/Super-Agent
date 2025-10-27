#!/usr/bin/env python3
"""
Browser-Use Interactive CLI

A clean, emoji-free CLI tool that:
1. Takes user queries
2. Uses LLM to generate optimized prompts following official guidelines
3. Executes browser automation tasks with full visibility
4. Shows all thinking and output for each step
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv

load_dotenv()

from browser_use import Agent
from browser_use.browser.profile import BrowserProfile


# Prompting guidelines from https://docs.browser-use.com/customize/agent/prompting-guide
PROMPT_OPTIMIZATION_TEMPLATE = """You are a prompt optimization expert for browser automation agents.

Your task is to convert a user's natural query into an optimized, specific prompt for a browser automation agent.

PROMPTING GUIDELINES:
1. Be extremely specific - avoid vague instructions
2. Reference specific actions by their exact names (navigate, click, scroll, extract, search, etc.)
3. Break down complex tasks into clear step-by-step instructions
4. Include keyboard navigation alternatives if needed (Tab, Enter, Arrow keys)
5. Build in error recovery strategies and fallback approaches
6. Use precise, actionable language

GOOD PROMPT EXAMPLE:
"Navigate to quotes.toscrape.com, extract the first 3 quotes with their authors, and save them to a CSV file named quotes.csv"

BAD PROMPT EXAMPLE:
"Go to website and get some quotes"

USER QUERY: {user_query}

Generate an optimized prompt following the guidelines above. Be specific, actionable, and include step-by-step instructions.

OPTIMIZED PROMPT:"""


def setup_logging(verbose: bool = False) -> None:
	"""Configure logging for the CLI tool"""
	if verbose:
		# Show all browser-use activity
		logging.basicConfig(
			level=logging.INFO,
			format='%(message)s',  # Cleaner format for verbose mode
		)
		# Only silence really noisy libraries
		for logger_name in ['httpx', 'httpcore', 'urllib3', 'ollama']:
			logging.getLogger(logger_name).setLevel(logging.WARNING)
	else:
		# Quiet mode - minimal output
		logging.basicConfig(
			level=logging.INFO,
			format='%(asctime)s - %(levelname)s - %(message)s',
			datefmt='%H:%M:%S',
		)
		# Silence verbose loggers
		for logger_name in [
			'httpx',
			'httpcore',
			'urllib3',
			'ollama',
			'browser_use',
		]:
			logging.getLogger(logger_name).setLevel(logging.WARNING)

		logging.getLogger('browser_use.agent').setLevel(logging.WARNING)
		logging.getLogger('browser_use.tools').setLevel(logging.WARNING)


class CleanLogger:
	"""Clean logging without emojis"""

	def __init__(self, verbose: bool = True):
		self.verbose = verbose

	def header(self, text: str):
		"""Print section header"""
		if self.verbose:
			print(f"\n{'=' * 70}")
			print(f"  {text}")
			print(f"{'=' * 70}\n")

	def step(self, step_num: int, text: str):
		"""Print step information"""
		if self.verbose:
			print(f"\n[Step {step_num}] {text}")
			print(f"{'-' * 70}")

	def info(self, text: str):
		"""Print info message"""
		if self.verbose:
			print(f"  {text}")

	def thinking(self, text: str):
		"""Print thinking/reasoning"""
		if self.verbose:
			print(f"\n  Thinking:")
			for line in text.split('\n'):
				if line.strip():
					print(f"    {line}")

	def action(self, action_name: str, params: str):
		"""Print action being taken"""
		if self.verbose:
			print(f"\n  Action: {action_name}")
			if params:
				print(f"  Params: {params}")

	def result(self, text: str):
		"""Print action result"""
		if self.verbose:
			if text and text.strip():
				print(f"\n  Result:")
				for line in text.split('\n')[:10]:  # Limit output
					if line.strip():
						print(f"    {line}")
				if len(text.split('\n')) > 10:
					print(f"    ... (output truncated)")

	def error(self, text: str):
		"""Print error message"""
		print(f"\n  ERROR: {text}", file=sys.stderr)

	def success(self, text: str):
		"""Print success message"""
		print(f"\n  SUCCESS: {text}")


async def optimize_prompt_with_llm(user_query: str, llm, logger: CleanLogger) -> str:
	"""Use LLM to optimize the user query into a specific, actionable prompt"""
	logger.header("PROMPT OPTIMIZATION")
	logger.info(f"User Query: {user_query}")

	# Create the optimization prompt
	optimization_prompt = PROMPT_OPTIMIZATION_TEMPLATE.format(user_query=user_query)

	try:
		# Call LLM to optimize the prompt
		logger.info("\nGenerating optimized prompt...")

		# For OpenAI
		if hasattr(llm, 'chat'):
			response = await llm.chat.completions.create(
				model=llm.model if hasattr(llm, 'model') else "gpt-4o-mini",
				messages=[{"role": "user", "content": optimization_prompt}],
				temperature=0.3,
			)
			optimized_prompt = response.choices[0].message.content.strip()

		# For other LLM types (Anthropic, Google, etc.)
		else:
			from browser_use.llm.messages import UserMessage

			messages = [UserMessage(content=optimization_prompt)]
			response = await llm.ainvoke(messages)

			if hasattr(response, 'completion'):
				optimized_prompt = response.completion
			else:
				optimized_prompt = str(response)

		logger.info("\nOptimized Prompt:")
		logger.info(f"{optimized_prompt}")

		return optimized_prompt

	except Exception as e:
		logger.error(f"Failed to optimize prompt: {str(e)}")
		logger.info(f"\nFalling back to original query: {user_query}")
		return user_query


async def run_browser_task(
	prompt: str,
	llm,
	logger: CleanLogger,
	headless: bool = False,
	max_steps: int = 20,
	use_vision: bool = True,
) -> str:
	"""Execute the browser automation task with detailed output"""

	logger.header("TASK EXECUTION")
	logger.info(f"Task: {prompt}")
	logger.info(f"Max Steps: {max_steps}")
	logger.info(f"Vision: {'Enabled' if use_vision else 'Disabled'}")
	logger.info(f"Browser Mode: {'Headless' if headless else 'Visible'}")

	try:
		# Configure browser profile
		browser_profile = BrowserProfile(
			headless=headless,
			keep_alive=False,
			enable_default_extensions=True,
			highlight_elements=True,
		)

		# Create agent
		agent = Agent(
			task=prompt,
			llm=llm,
			use_vision=use_vision,
			browser_profile=browser_profile,
			use_thinking=True,
			max_actions_per_step=10,
		)

		# Hook into agent to display step-by-step output
		original_step = agent.step
		step_counter = [0]  # Use list for mutable counter

		async def verbose_step(*args, **kwargs):
			"""Wrapper to log each step"""
			step_counter[0] += 1
			logger.step(step_counter[0], "Processing...")

			result = await original_step(*args, **kwargs)

			# Display thinking
			if result and hasattr(result, 'model_output') and result.model_output:
				output = result.model_output

				if hasattr(output, 'current_state'):
					state = output.current_state

					# Show thinking
					if hasattr(state, 'thinking') and state.thinking:
						logger.thinking(state.thinking)

					# Show evaluation
					if hasattr(state, 'evaluation_previous_goal') and state.evaluation_previous_goal:
						logger.info(f"\nEvaluation: {state.evaluation_previous_goal}")

					# Show next goal
					if hasattr(state, 'next_goal') and state.next_goal:
						logger.info(f"Next Goal: {state.next_goal}")

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

						logger.action(action_name, ", ".join(params) if params else "")

			# Show results
			if result and hasattr(result, 'result'):
				for action_result in result.result:
					if hasattr(action_result, 'extracted_content') and action_result.extracted_content:
						logger.result(action_result.extracted_content)

					if hasattr(action_result, 'error') and action_result.error:
						logger.error(action_result.error)

			return result

		# Replace step method
		agent.step = verbose_step

		# Run the agent
		result = await agent.run(max_steps=max_steps)

		# Display final results
		logger.header("EXECUTION COMPLETE")

		if result and hasattr(result, 'final_result'):
			final_result = result.final_result()
			if final_result:
				logger.success("Task completed successfully")
				logger.info("\nFinal Result:")
				logger.info(f"{final_result}")
				return final_result
			else:
				logger.info("Task completed but no final result returned")
				return "Task completed"
		else:
			logger.info("Task completed")
			return "Task completed"

	except KeyboardInterrupt:
		logger.error("Task interrupted by user")
		return "Interrupted"

	except Exception as e:
		logger.error(f"Task failed: {str(e)}")
		import traceback
		if logger.verbose:
			traceback.print_exc()
		return f"Failed: {str(e)}"


def parse_arguments() -> argparse.Namespace:
	"""Parse command-line arguments"""
	parser = argparse.ArgumentParser(
		description='Interactive Browser-Use CLI - Clean, emoji-free browser automation with Ollama',
		formatter_class=argparse.RawDescriptionHelpFormatter,
		epilog="""
Examples:
  %(prog)s "find latest python version"
  %(prog)s --headless "search github for browser-use stars"
  %(prog)s --verbose "get weather in San Francisco"  # Show all thinking
  %(prog)s --no-optimize "navigate to example.com"  # Skip prompt optimization
  %(prog)s --provider openai --model gpt-4o "your task"  # Use OpenAI instead

Prerequisites:
  1. Install Ollama: https://ollama.com/
  2. Start Ollama: ollama serve
  3. Pull model: ollama pull qwen2.5:7b
		""",
	)

	parser.add_argument(
		'query',
		type=str,
		nargs='?',
		help='Your natural language query (e.g., "find the top post on Hacker News")',
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
		default=20,
		help='Maximum number of steps (default: 20)',
	)

	parser.add_argument(
		'--no-vision',
		action='store_true',
		help='Disable vision/screenshots',
	)

	parser.add_argument(
		'--no-optimize',
		action='store_true',
		help='Skip prompt optimization step',
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
		help='Show live progress updates including LLM thinking and all actions',
	)

	return parser.parse_args()


async def main() -> int:
	"""Main entry point"""
	args = parse_arguments()

	# Get query
	query = args.query
	if not query:
		query = input("Enter your task: ").strip()
		if not query:
			print("Error: No task provided")
			return 1

	# Setup logging first
	setup_logging(verbose=args.verbose)

	# Setup logger - show output unless quiet mode
	logger = CleanLogger(verbose=not args.quiet)

	# Print banner
	if not args.quiet:
		print("\n" + "=" * 70)
		print("  Browser-Use Interactive CLI")
		print("  Clean, emoji-free browser automation")
		print("=" * 70)

	try:
		# Set environment variable based on verbose mode
		import os
		if args.verbose:
			# Show all logs in verbose mode
			os.environ['BROWSER_USE_LOGGING_LEVEL'] = 'info'
		else:
			# Only show errors in quiet mode
			os.environ['BROWSER_USE_LOGGING_LEVEL'] = 'error'

		# Initialize LLM
		logger.header("INITIALIZATION")
		logger.info(f"Provider: {args.provider}")
		logger.info(f"Model: {args.model}")

		if args.provider == 'openai':
			from openai import AsyncOpenAI
			import os

			api_key = os.getenv('OPENAI_API_KEY')
			if not api_key:
				logger.error("OPENAI_API_KEY not found in environment")
				logger.info("Please set it in your .env file or export it:")
				logger.info("  export OPENAI_API_KEY=your_key_here")
				return 1

			llm = AsyncOpenAI(api_key=api_key)
			# Store model name for later use
			llm.model = args.model
			logger.info("OpenAI client initialized")

		elif args.provider == 'anthropic':
			from anthropic import AsyncAnthropic
			import os

			api_key = os.getenv('ANTHROPIC_API_KEY')
			if not api_key:
				logger.error("ANTHROPIC_API_KEY not found in environment")
				logger.info("Please set it in your .env file or export it:")
				logger.info("  export ANTHROPIC_API_KEY=your_key_here")
				return 1

			llm = AsyncAnthropic(api_key=api_key)
			# Store model name for later use
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

		# Optimize prompt (unless disabled)
		if not args.no_optimize:
			optimized_prompt = await optimize_prompt_with_llm(query, llm, logger)
		else:
			optimized_prompt = query
			logger.info(f"Using query as-is: {query}")

		# Execute task
		result = await run_browser_task(
			prompt=optimized_prompt,
			llm=llm,
			logger=logger,
			headless=args.headless,
			max_steps=args.max_steps,
			use_vision=not args.no_vision,
		)

		# Print final result for quiet mode
		if args.quiet:
			print(result)

		return 0

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
