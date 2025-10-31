"""
Prompt Optimization Module
Handles LLM-based prompt optimization for browser automation tasks
"""

from browser_use_interactive import CleanLogger
from browser_use.llm.messages import UserMessage


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


async def optimize_prompt(user_query: str, llm, logger: CleanLogger) -> str:
	"""
	Use LLM to optimize the user query into a specific, actionable prompt

	Args:
		user_query: User's original query
		llm: Language model instance
		logger: Logger for output

	Returns:
		Optimized prompt string
	"""
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


def add_task_anchoring(query: str) -> str:
	"""
	Add simple task anchoring to prevent hallucination
	Used when prompt optimization is disabled

	Args:
		query: Original user query

	Returns:
		Query with task anchoring added
	"""
	return f"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK: {query}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️  When you call done(), INCLUDE THE DATA YOU FOUND:

❌ NO: "Task completed"
✅ YES: "Chancellor is Dr. Paul Dhinakaran, MBA, PhD..."

Copy the extracted information into done(text="...").
Do NOT just say the task is complete."""
