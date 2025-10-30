#!/usr/bin/env python3
"""
Test email content generation
Run with: DEBUG_MCP_TOOL_SELECTION=1 python test_email_generation.py
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
from repl.session_manager import SessionManager


async def test_email_generation():
	"""Test if email content generation is working"""

	print("\n" + "="*70)
	print("Testing Email Content Generation".center(70))
	print("="*70 + "\n")

	logger = CleanLogger(verbose=True)

	# Initialize LLM
	print("Initializing LLM...")
	from browser_use.llm.ollama.chat import ChatOllama
	llm = ChatOllama(model='deepseek-r1:14b', host='http://localhost:11434')
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

	# Test cases
	test_cases = [
		("john@example.com", "our project was an absolute success"),
		("jane@company.com", "can we schedule a meeting tomorrow"),
		("support@service.com", "I need help with my account"),
	]

	print("Testing email content generation:\n")

	for recipient, user_intent in test_cases:
		print(f"Recipient: {recipient}")
		print(f"Message: {user_intent}")
		print("-" * 70)

		try:
			result = await session._generate_email_content(recipient, user_intent)

			print(f"✅ Email generation SUCCEEDED")
			print(f"   Subject: {result['subject']}")
			print(f"   Body (first 100 chars): {result['body'][:100]}...")

		except Exception as e:
			print(f"❌ Test failed with error: {type(e).__name__}: {str(e)}")

		print("\n")

	print("="*70)
	print("Test Complete".center(70))
	print("="*70)


if __name__ == '__main__':
	try:
		asyncio.run(test_email_generation())
	except KeyboardInterrupt:
		print("\n\nTest interrupted by user")
	except Exception as e:
		print(f"\nTest failed: {str(e)}")
		import traceback
		traceback.print_exc()
