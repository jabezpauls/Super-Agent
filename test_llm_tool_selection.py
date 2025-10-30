#!/usr/bin/env python3
"""
Quick test to check if LLM tool selection is working
Run with: DEBUG_MCP_TOOL_SELECTION=1 python test_llm_tool_selection.py
"""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

# Enable debug mode
os.environ['DEBUG_MCP_TOOL_SELECTION'] = '1'
os.environ['BROWSER_USE_LOGGING_LEVEL'] = 'error'

from browser_use_interactive import CleanLogger
from repl.cli import create_llm_from_args, parse_arguments
from repl.session_manager import SessionManager


async def test_llm_tool_selection():
	"""Test if LLM tool selection is working"""

	print("\n" + "="*70)
	print("Testing LLM Tool Selection".center(70))
	print("="*70 + "\n")

	# Create minimal args
	class Args:
		model = 'deepseek-r1:14b'
		provider = 'ollama'
		host = 'http://localhost:11434'
		headless = True
		max_steps = 5
		no_vision = True
		optimize = False
		user_data_dir = None
		profile_directory = None
		cdp_url = None
		disable_mcp = False
		disable_chat = False
		quiet = False
		verbose = False
		google_credentials = 'credentials.json'

	args = Args()
	logger = CleanLogger(verbose=True)

	# Initialize LLM
	print("Initializing LLM...")
	from browser_use.llm.ollama.chat import ChatOllama
	llm = ChatOllama(model=args.model, host=args.host)
	print("✅ LLM initialized\n")

	# Create session manager
	session = SessionManager(
		llm=llm,
		logger=logger,
		headless=True,
		max_steps=5,
		use_vision=False,
		optimize_prompts=False,
		enable_mcp=True,
		disable_chat=False,
	)

	# Test queries
	test_queries = [
		("summerize my mails", "gmail"),
		("send email to john@example.com saying hello", "gmail"),
		("check my calendar tomorrow", "calendar"),
	]

	print("Testing LLM tool selection with various queries:\n")

	for query, server_type in test_queries:
		print(f"Query: '{query}'")
		print(f"Server: {server_type}")
		print("-" * 70)

		try:
			# Try connecting to MCP (will fail gracefully if not set up)
			try:
				await session.ensure_mcp_connected(server_type)
			except Exception as e:
				print(f"⚠️  MCP connection failed (expected if not configured): {e}")
				print("   Continuing with LLM tool selection test...\n")

			# Test LLM tool selection
			result = await session._llm_select_mcp_tool(server_type, query)

			if result:
				print(f"✅ LLM tool selection SUCCEEDED")
				print(f"   Operation: {result.get('operation', 'N/A')}")
				print(f"   Parameters: {list(result.keys())}")
			else:
				print(f"❌ LLM tool selection FAILED (returned None)")
				print(f"   Will fall back to regex parsing")

		except Exception as e:
			print(f"❌ Test failed with error: {type(e).__name__}: {str(e)}")

		print("\n")

	print("="*70)
	print("Test Complete".center(70))
	print("="*70)


if __name__ == '__main__':
	try:
		asyncio.run(test_llm_tool_selection())
	except KeyboardInterrupt:
		print("\n\nTest interrupted by user")
	except Exception as e:
		print(f"\nTest failed: {str(e)}")
		import traceback
		traceback.print_exc()
