"""
Tool Router for Browser-Use Agent
Intelligently routes user queries to appropriate tools (chat, browser, calendar, email)
"""

import json
import re
from enum import Enum
from typing import Optional, List
from dataclasses import dataclass

from browser_use.llm.base import BaseChatModel
from browser_use.llm.messages import UserMessage


class ToolType(Enum):
	"""Available tool types"""
	CHAT = "chat"
	BROWSER = "browser"
	CALENDAR = "calendar"
	EMAIL = "email"


@dataclass
class ToolDecision:
	"""Decision about which tool(s) to use"""
	primary_tool: ToolType
	secondary_tools: List[ToolType]
	reasoning: str
	specific_actions: List[str]
	original_query: str


# Tool routing prompt for LLM
TOOL_ROUTING_PROMPT = """You are an intelligent tool router for an AI assistant with multiple capabilities.

Analyze the user's request and determine which tool(s) to use.

Available tools:
1. **CHAT** - General conversation, answering questions, math, explanations, discussions
   - Use for: Questions, conversations, reasoning, calculations, general knowledge
   - Examples: "What's 2+2?", "Explain quantum physics", "Tell me a joke"

2. **BROWSER** - Web browsing, searching, extracting information from websites
   - Use for: Finding information online, checking prices, reading articles, web research
   - Examples: "Find flights to Tokyo", "What's the weather in Paris?", "Check Bitcoin price"

3. **CALENDAR** - View, create, update, delete calendar events, check availability
   - Use for: Scheduling, viewing schedule, calendar management
   - Examples: "Schedule meeting tomorrow", "What's on my calendar?", "Delete the 2pm event"

4. **EMAIL** - Read, send, search emails, manage labels
   - Use for: Email operations, checking inbox, sending messages
   - Examples: "Check unread emails", "Send email to John", "Find emails about project X"
   - IMPORTANT: Includes queries like "mail/email [person] saying [message]", "send message to [person]"

CRITICAL ROUTING RULES:
- **EMAIL** tool: ANY query with words "email", "mail", "send message", "inbox", "compose" is EMAIL
  - "email John saying hello" → EMAIL
  - "mail pranov about the project" → EMAIL
  - "send message to team" → EMAIL
  - "i want you to mail..." → EMAIL
- **BROWSER** tool: ONLY for web searches, online research, finding information on websites
  - "find flights" → BROWSER
  - "check weather" → BROWSER
  - "search for..." → BROWSER
- **CALENDAR** tool: ONLY for calendar/scheduling operations
- **CHAT** tool: ONLY for pure conversation without any external actions

If uncertain between EMAIL and BROWSER, and query mentions "email/mail/send/message", choose EMAIL.

Analyze this user request: "{user_query}"

Respond with ONLY valid JSON (no markdown, no extra text):
{{
	"primary_tool": "tool_name",
	"secondary_tools": ["tool1", "tool2"],
	"reasoning": "why these tools were chosen",
	"specific_actions": ["action1", "action2"]
}}"""


def parse_manual_override(query: str) -> Optional[ToolType]:
	"""
	Check if user explicitly specified a tool via command prefix

	Supports:
	- /browser <query> - Force browser automation
	- /calendar or /calender <query> - Force calendar MCP
	- /email or /mail <query> - Force email/Gmail MCP
	- /chat <query> - Force pure chat (no tools)

	Returns None if no override found
	"""
	query_lower = query.strip().lower()

	# Check for command prefix
	if query_lower.startswith('/browser '):
		return ToolType.BROWSER
	elif query_lower.startswith('/calendar ') or query_lower.startswith('/calender '):
		return ToolType.CALENDAR
	elif query_lower.startswith('/email ') or query_lower.startswith('/mail '):
		return ToolType.EMAIL
	elif query_lower.startswith('/chat '):
		return ToolType.CHAT

	return None


def strip_command_prefix(query: str) -> str:
	"""Remove command prefix from query if present"""
	query_lower = query.strip().lower()

	# Check all supported prefixes (including aliases)
	prefixes = [
		'/browser ',
		'/calendar ',
		'/calender ',  # Common misspelling
		'/email ',
		'/mail ',      # Shorter alias
		'/chat '
	]

	for prefix in prefixes:
		if query_lower.startswith(prefix):
			# Return original query with prefix removed (preserve case)
			return query[len(prefix):].strip()

	return query


def is_pure_chat_query(query: str) -> bool:
	"""
	Heuristic check if query is likely a pure chat interaction
	Returns True if query seems to be conversational without needing tools
	"""
	query_lower = query.strip().lower()

	# Chat indicators
	chat_patterns = [
		r'^(what|who|when|where|why|how|explain|tell me|can you)\s+(is|are|was|were|do|does)',
		r'^(calculate|compute|solve|what\'?s?\s+\d+)',  # Math questions
		r'^(hello|hi|hey|thanks|thank you|goodbye|bye)',  # Greetings
		r'^(tell me about|explain|describe|define)',  # Explanations
	]

	for pattern in chat_patterns:
		if re.search(pattern, query_lower):
			# Check if it's not asking for web search
			web_indicators = ['search', 'find online', 'look up', 'browse', 'website', 'google']
			if not any(indicator in query_lower for indicator in web_indicators):
				return True

	return False


async def route_query(
	llm: BaseChatModel,
	user_query: str,
	force_tool: Optional[ToolType] = None
) -> ToolDecision:
	"""
	Route user query to appropriate tool(s) using LLM

	Args:
		llm: Language model for routing decision
		user_query: User's input query
		force_tool: If provided, override LLM decision with this tool

	Returns:
		ToolDecision with primary and secondary tools
	"""
	# If tool is forced, return immediately
	if force_tool:
		return ToolDecision(
			primary_tool=force_tool,
			secondary_tools=[],
			reasoning=f"User explicitly requested {force_tool.value} tool",
			specific_actions=[user_query],
			original_query=user_query
		)

	# Quick heuristic for pure chat
	if is_pure_chat_query(user_query):
		# Still use LLM for confirmation but bias towards chat
		pass  # Continue to LLM routing

	try:
		# Prepare routing prompt
		prompt = TOOL_ROUTING_PROMPT.format(user_query=user_query)

		# Call LLM for routing decision
		response = await llm.ainvoke([UserMessage(content=prompt)])

		# Extract text from response
		if hasattr(response, 'content'):
			response_text = response.content
		else:
			response_text = str(response)

		# Debug: Check if response is empty
		if not response_text or not response_text.strip():
			raise ValueError(f"LLM returned empty response. Full response object: {response}")

		# Parse JSON response
		# Remove markdown code blocks if present
		response_text = re.sub(r'```json\s*', '', response_text)
		response_text = re.sub(r'```\s*', '', response_text)
		response_text = response_text.strip()

		# Debug: Check if cleaned response is valid
		if not response_text:
			raise ValueError("Response became empty after cleaning markdown")

		decision_data = json.loads(response_text)

		# Parse tool types
		primary = ToolType(decision_data["primary_tool"].lower())
		secondary = [ToolType(t.lower()) for t in decision_data.get("secondary_tools", [])]

		return ToolDecision(
			primary_tool=primary,
			secondary_tools=secondary,
			reasoning=decision_data.get("reasoning", ""),
			specific_actions=decision_data.get("specific_actions", [user_query]),
			original_query=user_query
		)

	except (json.JSONDecodeError, KeyError, ValueError) as e:
		# Fallback: Use heuristic routing
		return fallback_routing(user_query, error=str(e))


def fallback_routing(query: str, error: str = "") -> ToolDecision:
	"""
	Fallback routing using keyword-based heuristics
	Used when LLM routing fails
	"""
	query_lower = query.lower()

	# Email keywords
	if any(word in query_lower for word in ['email', 'mail', 'inbox', 'send message', 'unread']):
		return ToolDecision(
			primary_tool=ToolType.EMAIL,
			secondary_tools=[],
			reasoning=f"Fallback routing detected email keywords (LLM error: {error})",
			specific_actions=[query],
			original_query=query
		)

	# Calendar keywords (including common misspellings)
	if any(word in query_lower for word in ['calendar', 'calender', 'schedule', 'meeting', 'appointment', 'event', 'planned', 'tomorrow', 'today']):
		return ToolDecision(
			primary_tool=ToolType.CALENDAR,
			secondary_tools=[],
			reasoning=f"Fallback routing detected calendar keywords (LLM error: {error})",
			specific_actions=[query],
			original_query=query
		)

	# Browser keywords
	if any(word in query_lower for word in ['search', 'find', 'look up', 'browse', 'website', 'google', 'price', 'weather', 'news']):
		return ToolDecision(
			primary_tool=ToolType.BROWSER,
			secondary_tools=[],
			reasoning=f"Fallback routing detected browser keywords (LLM error: {error})",
			specific_actions=[query],
			original_query=query
		)

	# Default to chat
	return ToolDecision(
		primary_tool=ToolType.CHAT,
		secondary_tools=[],
		reasoning=f"Fallback routing defaulted to chat (LLM error: {error})",
		specific_actions=[query],
		original_query=query
	)


def detect_multi_tool_query(query: str) -> List[ToolType]:
	"""
	Detect if query requires multiple tools in sequence

	Examples:
	- "Check my calendar and email John" → [CALENDAR, EMAIL]
	- "Find flight prices and schedule them in calendar" → [BROWSER, CALENDAR]

	Returns list of tool types in order they should be executed
	"""
	query_lower = query.lower()
	tools = []

	# Pattern matching for multi-tool queries
	if 'calendar' in query_lower or 'schedule' in query_lower or 'meeting' in query_lower:
		tools.append(ToolType.CALENDAR)

	if 'email' in query_lower or 'send' in query_lower and 'message' in query_lower:
		tools.append(ToolType.EMAIL)

	if any(word in query_lower for word in ['search', 'find', 'look up', 'browse', 'check online']):
		tools.append(ToolType.BROWSER)

	# Look for conjunctions indicating sequence
	has_conjunction = any(conj in query_lower for conj in [' and ', ' then ', ' after ', ' followed by'])

	if has_conjunction and len(tools) > 1:
		return tools

	return []


def format_routing_decision_log(decision: ToolDecision) -> str:
	"""Format routing decision for display to user"""
	lines = []
	lines.append(f"🎯 **Tool Routing:**")
	lines.append(f"   Primary: {decision.primary_tool.value.upper()}")

	if decision.secondary_tools:
		tools_str = ", ".join([t.value.upper() for t in decision.secondary_tools])
		lines.append(f"   Secondary: {tools_str}")

	lines.append(f"   Reasoning: {decision.reasoning}")

	return "\n".join(lines)
