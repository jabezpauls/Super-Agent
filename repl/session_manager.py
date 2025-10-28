"""
Session Manager Module
Manages browser sessions, agent state, MCP connections, and intelligent tool routing
"""

import asyncio
import re
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

from browser_use import Agent
from browser_use.browser.profile import BrowserProfile
from browser_use.browser.session import BrowserSession
from browser_use.agent.views import AgentSettings
from browser_use.agent.tool_router import (
	ToolType,
	ToolDecision,
	route_query,
	parse_manual_override,
	strip_command_prefix,
	format_routing_decision_log,
)
from browser_use.mcp.manager import MCPManager
from browser_use.llm.messages import UserMessage

from repl.prompt_optimizer import optimize_prompt, add_task_anchoring


class SessionManager:
	"""
	Manages the interactive session with intelligent tool routing

	Coordinates between:
	- Browser automation (existing)
	- Pure chat responses (new)
	- MCP tools (calendar, email) (new)
	- Tool routing logic (new)
	"""

	def __init__(
		self,
		llm,
		logger,
		headless: bool = False,
		max_steps: int = 20,
		use_vision: bool = True,
		optimize_prompts: bool = True,
		user_data_dir: Optional[str] = None,
		profile_directory: Optional[str] = None,
		cdp_url: Optional[str] = None,
		enable_mcp: bool = True,
		disable_chat: bool = False,
	):
		"""
		Initialize session manager

		Args:
			llm: Language model instance
			logger: Logger for output
			headless: Run browser in headless mode
			max_steps: Maximum steps per task
			use_vision: Enable vision capabilities
			optimize_prompts: Use LLM to optimize prompts
			user_data_dir: Chrome user data directory
			profile_directory: Chrome profile directory
			cdp_url: Connect to existing Chrome via CDP
			enable_mcp: Enable MCP server support
			disable_chat: Disable pure chat mode
		"""
		self.llm = llm
		self.logger = logger
		self.headless = headless
		self.max_steps = max_steps
		self.use_vision = use_vision
		self.optimize_prompts = optimize_prompts
		self.user_data_dir = user_data_dir
		self.profile_directory = profile_directory
		self.cdp_url = cdp_url
		self.enable_mcp = enable_mcp
		self.disable_chat = disable_chat

		# Browser and agent state
		self.browser_session: Optional[BrowserSession] = None
		self.agent: Optional[Agent] = None
		self.command_history: list[str] = []
		self.running = False

		# MCP integration
		self.mcp_manager = MCPManager() if enable_mcp else None
		self.active_mcp_servers: set[str] = set()

		# Conversation history for pure chat
		self.conversation_history: list[tuple[str, str]] = []

		# Tool forcing (for manual overrides like /browser, /calendar, etc.)
		self.force_tool: Optional[str] = None

	async def initialize_browser(self):
		"""Initialize the browser session (lazy-loaded on first browser use)"""
		if self.browser_session is not None:
			return

		self.logger.header("INITIALIZING BROWSER SESSION")

		try:
			# Configure browser profile
			browser_profile_args = {
				'headless': self.headless,
				'keep_alive': True,
				'enable_default_extensions': True,
				'highlight_elements': True,
			}

			if self.user_data_dir:
				browser_profile_args['user_data_dir'] = self.user_data_dir
				self.logger.info(f"Using Chrome profile: {self.user_data_dir}")

			if self.profile_directory:
				browser_profile_args['profile_directory'] = self.profile_directory
				self.logger.info(f"Using profile directory: {self.profile_directory}")

			browser_profile = BrowserProfile(**browser_profile_args)

			# Try to connect to existing Chrome first (if no cdp_url specified, try default)
			cdp_url_to_try = self.cdp_url or "http://localhost:9222"

			if not self.cdp_url:  # Only try auto-connect if user didn't specify cdp_url
				self.logger.info(f"🔍 Checking for existing Chrome instance at {cdp_url_to_try}...")

				# Try to connect to existing Chrome
				try:
					import httpx
					async with httpx.AsyncClient() as client:
						response = await client.get(f"{cdp_url_to_try}/json/version", timeout=2.0)
						if response.status_code == 200:
							version_data = response.json()
							self.logger.success(f"✅ Found existing Chrome instance!")
							self.logger.info(f"   Browser: {version_data.get('Browser', 'Unknown')}")
							self.logger.info(f"   WebSocket: {version_data.get('webSocketDebuggerUrl', 'Unknown')}")
							self.logger.info(f"🔗 Connecting to: {cdp_url_to_try}")

							# Set cdp_url so it will be used below
							self.cdp_url = cdp_url_to_try
				except Exception as e:
					# No existing Chrome found, will launch new one
					self.logger.info(f"No existing Chrome found at {cdp_url_to_try}")
					self.logger.info(f"Debug: {type(e).__name__}: {str(e)}")
					self.logger.info("Launching new Chrome instance...")
					pass

			# Create browser session (launch new Chrome or connect to specified cdp_url)
			browser_session_args = {'browser_profile': browser_profile}
			if self.cdp_url:
				browser_session_args['cdp_url'] = self.cdp_url
				self.logger.info(f"🔗 Using CDP URL: {self.cdp_url}")

			self.logger.info("Creating BrowserSession...")
			self.browser_session = BrowserSession(**browser_session_args)

			if self.cdp_url:
				self.logger.success("✅ Connected to existing Chrome successfully!")
			else:
				self.logger.success("✅ New Chrome instance launched successfully!")

		except Exception as e:
			self.logger.error(f"Failed to initialize browser: {str(e)}")
			raise

	async def ensure_mcp_connected(self, server_type: str):
		"""
		Lazy-load MCP server if not already connected

		Args:
			server_type: Type of server ('calendar', 'gmail')
		"""
		if not self.enable_mcp or not self.mcp_manager:
			raise RuntimeError("MCP is disabled. Start REPL with MCP enabled.")

		if server_type not in self.active_mcp_servers:
			self.logger.info(f"🔌 Connecting to {server_type} MCP server...")

			try:
				# Connect to MCP server
				await self.mcp_manager.connect(server_type)

				# Register MCP tools if we have an agent with browser session
				# Note: MCP tools will be registered when agent is created
				self.active_mcp_servers.add(server_type)
				self.logger.success(f"✅ Connected to {server_type} MCP server")

			except Exception as e:
				self.logger.error(f"Failed to connect to {server_type} MCP server: {str(e)}")
				raise

	async def chat_response(self, query: str) -> str:
		"""
		Generate a pure chat response without using tools

		Args:
			query: User's question or message

		Returns:
			Chat response string
		"""
		# Build context from recent conversation
		context_messages = []
		for user_msg, assistant_msg in self.conversation_history[-3:]:
			context_messages.append(f"User: {user_msg}")
			context_messages.append(f"Assistant: {assistant_msg}")

		context = "\n".join(context_messages) if context_messages else "No previous conversation"

		# Create chat prompt
		prompt = f"""You are a helpful AI assistant having a natural conversation.

Previous conversation:
{context}

User: {query}

Respond naturally and helpfully."""

		try:
			# Use LLM for chat response
			messages = [UserMessage(content=prompt)]
			response = await self.llm.ainvoke(messages)

			if hasattr(response, 'content'):
				response_text = response.content
			else:
				response_text = str(response)

			# Add to conversation history
			self.conversation_history.append((query, response_text))

			return response_text

		except Exception as e:
			self.logger.error(f"Chat response failed: {str(e)}")
			return f"I apologize, but I encountered an error: {str(e)}"

	async def execute_browser_task(self, query: str) -> str:
		"""
		Execute a browser automation task

		Args:
			query: Task description

		Returns:
			Task result string
		"""
		# Ensure browser is initialized
		if self.browser_session is None:
			await self.initialize_browser()

		# Optimize prompt if enabled
		if self.optimize_prompts:
			self.logger.header("PROMPT OPTIMIZATION")
			optimized_prompt = await optimize_prompt(query, self.llm, self.logger)
		else:
			optimized_prompt = add_task_anchoring(query)

		# Execute the task
		self.logger.header("TASK EXECUTION")
		self.logger.info(f"Task: {optimized_prompt}")
		self.logger.info(f"Max Steps: {self.max_steps}")
		self.logger.info(f"Vision: {'Enabled' if self.use_vision else 'Disabled'}")
		self.logger.info(f"Browser Mode: {'Headless' if self.headless else 'Visible'}")

		try:
			if self.agent is None:
				# Create new agent
				agent_settings = AgentSettings(
					use_vision=self.use_vision,
					use_thinking=True,
					max_actions_per_step=10,
					system_prompt_suffix=f"\n\nIMPORTANT REMINDERS:\n- Your ONLY task is: {query}\n- Do NOT switch to other tasks or examples\n- Stay focused on this specific goal\n- When you complete this task, call the 'done' action immediately\n- Do not continue to other unrelated tasks",
				)

				self.agent = Agent(
					task=optimized_prompt,
					llm=self.llm,
					browser_session=self.browser_session,
					**agent_settings.model_dump(),
				)

				# Register MCP tools to agent if connected
				if self.mcp_manager and hasattr(self.agent, 'tools'):
					for server_type in self.active_mcp_servers:
						await self.mcp_manager.register_tools(server_type, self.agent.tools)

				# Add verbose logging
				self._setup_verbose_logging()

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
			if hasattr(self.logger, 'verbose') and self.logger.verbose:
				traceback.print_exc()
			return f"Failed: {str(e)}"

	def _parse_calendar_query(self, query: str) -> Optional[Dict[str, Any]]:
		"""
		Parse simple calendar queries to extract operation and parameters

		Args:
			query: User's calendar query

		Returns:
			Dict with operation and parameters, or None if can't parse
		"""
		query_lower = query.lower().strip()

		# List/check calendar operations
		if any(keyword in query_lower for keyword in ['list', 'show', 'check', 'what', 'view']):
			# Use local timezone
			now = datetime.now().astimezone()

			# Check for time references
			if 'tomorrow' in query_lower:
				return {
					'operation': 'list_events',
					'time_min': (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0).isoformat(),
					'time_max': (now + timedelta(days=1)).replace(hour=23, minute=59, second=59, microsecond=0).isoformat()
				}
			elif 'today' in query_lower:
				return {
					'operation': 'list_events',
					'time_min': now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat(),
					'time_max': now.replace(hour=23, minute=59, second=59, microsecond=0).isoformat()
				}
			else:
				# Default to next 7 days
				return {
					'operation': 'list_events',
					'time_min': now.isoformat(),
					'time_max': (now + timedelta(days=7)).isoformat(),
					'max_results': 10
				}

		# Add/create event operations
		if any(keyword in query_lower for keyword in ['add', 'create', 'schedule', 'book']):
			# Extract time (e.g., "6pm", "18:00", "6:00 pm")
			time_match = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)?', query_lower)

			# Extract event description (everything except time-related words)
			description = re.sub(r'\b(add|create|schedule|book|to|my|calendar|calender|at|tomorrow|today)\b', '', query_lower)
			description = re.sub(r'\d{1,2}(?::\d{2})?\s*(?:am|pm)?', '', description)
			# Clean up multiple spaces and strip
			description = re.sub(r'\s+', ' ', description).strip()

			if time_match:
				hour = int(time_match.group(1))
				minute = int(time_match.group(2)) if time_match.group(2) else 0
				am_pm = time_match.group(3)

				# Convert to 24-hour format
				if am_pm == 'pm' and hour != 12:
					hour += 12
				elif am_pm == 'am' and hour == 12:
					hour = 0

				# Determine date (tomorrow or today) - use LOCAL timezone
				now = datetime.now().astimezone()
				if 'tomorrow' in query_lower:
					event_date = now + timedelta(days=1)
				else:
					event_date = now

				# Create timezone-aware datetime in local timezone
				start_time = event_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
				end_time = start_time + timedelta(hours=1)  # Default 1 hour duration

				return {
					'operation': 'create_event',
					'summary': description.title() if description else 'Event',
					'start_time': start_time.isoformat(),
					'end_time': end_time.isoformat()
				}

		return None

	async def _llm_select_mcp_tool(self, server_type: str, query: str) -> Optional[Dict[str, Any]]:
		"""
		Use LLM to intelligently select MCP tool and extract parameters

		Args:
			server_type: 'calendar' or 'gmail'
			query: User's natural language query

		Returns:
			Dict with 'operation' and parameters, or None if LLM fails
		"""
		client = self.mcp_manager.clients.get(server_type)
		if not client:
			return None

		# Get available tools from MCP server
		tools_info = []
		if server_type == 'calendar':
			tools_info = [
				{"name": "list_calendar_events", "params": ["time_min", "time_max", "max_results", "query"], "description": "List calendar events with optional filtering by time range or search query"},
				{"name": "create_calendar_event", "params": ["summary", "start_time", "end_time", "description", "location", "attendees"], "description": "Create a new calendar event with specified details"},
				{"name": "update_calendar_event", "params": ["event_id", "summary", "start_time", "end_time", "description", "location"], "description": "Update an existing calendar event"},
				{"name": "delete_calendar_event", "params": ["event_id"], "description": "Delete a calendar event by ID"},
				{"name": "check_availability", "params": ["time_min", "time_max"], "description": "Check free/busy calendar availability"}
			]
		elif server_type == 'gmail':
			tools_info = [
				{"name": "list_emails", "params": ["query", "max_results"], "description": "List emails with Gmail search query (e.g., 'from:user@example.com', 'is:unread')"},
				{"name": "read_email", "params": ["email_id"], "description": "Read a specific email by its ID"},
				{"name": "send_email", "params": ["to", "subject", "body", "cc", "bcc"], "description": "Send a new email to recipients"},
				{"name": "modify_email_labels", "params": ["email_id", "add_labels", "remove_labels"], "description": "Add or remove labels from an email"},
				{"name": "search_emails", "params": ["query", "max_results"], "description": "Search emails using Gmail syntax"}
			]

		# Build LLM prompt
		tools_str = "\n".join([f"- **{t['name']}**: {t['description']}\n  Parameters: {', '.join(t['params'])}" for t in tools_info])

		# Get current date/time for context
		now = datetime.now().astimezone()
		current_time_str = now.strftime("%Y-%m-%d %H:%M:%S %Z")
		timezone_str = now.strftime("%z")  # e.g., +0530 for IST

		prompt = f"""You are an MCP tool selector for {server_type.upper()} operations.

Current date/time: {current_time_str} (timezone: {timezone_str})

User query: "{query}"

Available tools:
{tools_str}

Analyze the query and select the most appropriate tool with parameters.

IMPORTANT rules:
- For "list", "show", "check", "do i have", "from" queries → use list_emails or list_calendar_events
- For "send", "email to", "mail to" queries → use send_email
- For "add", "create", "schedule" event queries → use create_calendar_event
- For time expressions: convert to ISO format with timezone (e.g., "tomorrow at 6pm" → "2025-10-29T18:00:00{timezone_str}")
- For email "from" queries: use Gmail search syntax "from:email@example.com"
- For list emails: use "max_results": 10 by default

Respond with ONLY valid JSON (no markdown, no extra text):
{{
	"tool": "tool_name_here",
	"parameters": {{
		"param1": "value1",
		"param2": "value2"
	}},
	"reasoning": "why this tool was chosen"
}}"""

		try:
			# Call LLM - try different methods based on what's available
			content = None

			# Try browser_use's message format first
			try:
				from browser_use.llm.messages import UserMessage
				response = await self.llm.ainvoke([UserMessage(content=prompt)])
				if hasattr(response, 'content'):
					content = response.content.strip()
				else:
					content = str(response).strip()
			except (ImportError, AttributeError):
				pass

			# Fallback: try langchain format
			if not content:
				try:
					from langchain_core.messages import HumanMessage
					response = await self.llm.ainvoke([HumanMessage(content=prompt)])
					content = response.content.strip()
				except (ImportError, AttributeError):
					pass

			# Fallback: try direct methods
			if not content:
				if hasattr(self.llm, 'acomplete'):
					response = await self.llm.acomplete(prompt)
					content = response.text.strip() if hasattr(response, 'text') else str(response).strip()
				elif hasattr(self.llm, 'complete'):
					response = self.llm.complete(prompt)
					content = response.text.strip() if hasattr(response, 'text') else str(response).strip()

			if not content:
				raise ValueError("Could not get response from LLM")

			# Debug: log raw response
			self.logger.info(f"📄 Raw LLM response (first 200 chars): {content[:200]}")

			# Extract JSON
			if '```json' in content:
				content = content.split('```json')[1].split('```')[0].strip()
			elif '```' in content:
				content = content.split('```')[1].split('```')[0].strip()

			# Debug: log cleaned JSON
			self.logger.info(f"🔍 Cleaned JSON (first 200 chars): {content[:200]}")

			import json
			tool_data = json.loads(content)

			# Map tool names to operations
			tool_name_map = {
				'list_calendar_events': 'list_events',
				'create_calendar_event': 'create_event',
				'update_calendar_event': 'update_event',
				'delete_calendar_event': 'delete_event',
				'check_availability': 'check_availability',
				'list_emails': 'list_emails',
				'read_email': 'read_email',
				'send_email': 'send_email',
				'modify_email_labels': 'modify_labels',
				'search_emails': 'search_emails'
			}

			operation = tool_name_map.get(tool_data['tool'], tool_data['tool'])

			self.logger.success(f"🤖 LLM selected tool: {tool_data['tool']}")
			self.logger.info(f"💭 Reasoning: {tool_data.get('reasoning', 'N/A')}")

			params = tool_data['parameters']

			# Special handling for send_email: generate professional content if needed
			if operation == 'send_email' and server_type == 'gmail':
				# Ensure 'to' is a list
				if 'to' in params and not isinstance(params['to'], list):
					params['to'] = [params['to']]

				# Check if subject/body are too brief - if so, enhance them
				if 'to' in params and ('subject' not in params or 'body' not in params or len(params.get('body', '')) < 10):
					self.logger.info(f"📧 Generating professional email content...")
					user_intent = params.get('body', query)
					recipient = params['to'][0] if isinstance(params['to'], list) else params['to']
					email_content = await self._generate_email_content(recipient, user_intent)
					params['subject'] = email_content['subject']
					params['body'] = email_content['body']
					self.logger.success(f"✉️ Email content generated")

			return {
				'operation': operation,
				**params
			}

		except Exception as e:
			self.logger.error(f"LLM tool selection failed: {e}")
			return None

	async def _generate_email_content(self, recipient: str, user_intent: str) -> Dict[str, str]:
		"""Use LLM to generate email subject and body from user intent"""
		prompt = f"""Generate a professional email based on this request:

User wants to send email to: {recipient}
User's intent/message: {user_intent}

Generate ONLY a JSON response with this exact format (no other text):
{{
	"subject": "appropriate subject line here",
	"body": "well-formatted email body here"
}}

The body should be professional but match the tone of the user's intent. Keep it concise."""

		try:
			# Call LLM to generate email content - try different methods
			content = None

			# Try browser_use's message format first
			try:
				from browser_use.llm.messages import UserMessage
				response = await self.llm.ainvoke([UserMessage(content=prompt)])
				if hasattr(response, 'content'):
					content = response.content.strip()
				else:
					content = str(response).strip()
			except (ImportError, AttributeError):
				pass

			# Fallback: try langchain format
			if not content:
				try:
					from langchain_core.messages import HumanMessage
					response = await self.llm.ainvoke([HumanMessage(content=prompt)])
					content = response.content.strip()
				except (ImportError, AttributeError):
					pass

			# Fallback: try direct methods
			if not content:
				if hasattr(self.llm, 'acomplete'):
					response = await self.llm.acomplete(prompt)
					content = response.text.strip() if hasattr(response, 'text') else str(response).strip()
				elif hasattr(self.llm, 'complete'):
					response = self.llm.complete(prompt)
					content = response.text.strip() if hasattr(response, 'text') else str(response).strip()

			if not content:
				raise ValueError("Could not get response from LLM")

			# Extract JSON from response (handle markdown code blocks)
			if '```json' in content:
				content = content.split('```json')[1].split('```')[0].strip()
			elif '```' in content:
				content = content.split('```')[1].split('```')[0].strip()

			import json
			email_data = json.loads(content)

			return {
				'subject': email_data.get('subject', 'Message from Browser-Use REPL'),
				'body': email_data.get('body', user_intent)
			}
		except Exception as e:
			self.logger.error(f"LLM email generation failed: {e}, using fallback")
			# Fallback to simple extraction
			return {
				'subject': user_intent[:50] + ('...' if len(user_intent) > 50 else ''),
				'body': user_intent
			}

	async def _parse_gmail_query(self, query: str) -> Optional[Dict[str, Any]]:
		"""
		Parse simple Gmail queries to extract operation and parameters

		Args:
			query: User's Gmail query

		Returns:
			Dict with operation and parameters, or None if can't parse
		"""
		query_lower = query.lower().strip()

		# List/read email operations (CHECK THESE FIRST before send operations)
		if any(keyword in query_lower for keyword in ['list', 'show', 'check', 'read', 'do i have', 'any mail from', 'from']):
			# Check for "from" with email address
			if 'from' in query_lower:
				email_match = re.search(r'from\s+([\w\.-]+@[\w\.-]+\.\w+)', query_lower)
				if email_match:
					from_email = email_match.group(1)
					return {
						'operation': 'list_emails',
						'query': f'from:{from_email}',
						'max_results': 10
					}

			if 'unread' in query_lower:
				return {
					'operation': 'list_emails',
					'query': 'is:unread',
					'max_results': 10
				}
			elif 'inbox' in query_lower:
				return {
					'operation': 'list_emails',
					'query': 'in:inbox',
					'max_results': 10
				}
			else:
				# Default to recent emails
				return {
					'operation': 'list_emails',
					'max_results': 10
				}

		# Search email operations
		if 'search' in query_lower or 'find' in query_lower:
			# Extract search query (everything after "for" or "search")
			search_query = ""
			if 'for' in query_lower:
				search_query = query[query_lower.index('for') + 3:].strip()
			elif 'search' in query_lower:
				search_query = query[query_lower.index('search') + 6:].strip()

			if search_query:
				return {
					'operation': 'search_emails',
					'query': search_query,
					'max_results': 10
				}

		# Send email operations (CHECKED LAST to avoid false positives)
		if any(keyword in query_lower for keyword in ['send', 'email to', 'mail to']):
			# Extract email address
			email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', query)

			if email_match:
				to_email = email_match.group(0)

				# Extract user intent - everything after "saying" or "that", or the whole query
				user_intent = ""
				if 'saying' in query_lower:
					user_intent = query[query_lower.index('saying') + 7:].strip()
				elif 'that' in query_lower:
					user_intent = query[query_lower.index('that') + 4:].strip()
				else:
					# Use whole query minus send/email keywords and email address
					user_intent = query_lower
					for keyword in ['send', 'email', 'mail', 'to']:
						user_intent = user_intent.replace(keyword, '')
					user_intent = user_intent.replace(to_email.lower(), '').strip()

				# Use LLM to generate professional email subject and body
				self.logger.info(f"🤖 Using LLM to generate email content...")
				email_content = await self._generate_email_content(to_email, user_intent)
				self.logger.success(f"📧 Generated - Subject: {email_content['subject']}")

				return {
					'operation': 'send_email',
					'to': [to_email],  # Gmail expects a list
					'subject': email_content['subject'],
					'body': email_content['body']
				}

		return None

	async def _handle_email_summarization(self, query: str) -> str:
		"""
		Handle email summarization tasks that require multiple MCP calls

		Args:
			query: User query like "summarize my mails today"

		Returns:
			Summary of emails
		"""
		try:
			# Parse time filter from query
			query_lower = query.lower()
			now = datetime.now().astimezone()

			time_filter = {}
			if 'today' in query_lower:
				time_filter = {
					'query': f'after:{now.strftime("%Y/%m/%d")}',
					'max_results': 20
				}
			elif 'yesterday' in query_lower:
				yesterday = now - timedelta(days=1)
				time_filter = {
					'query': f'after:{yesterday.strftime("%Y/%m/%d")} before:{now.strftime("%Y/%m/%d")}',
					'max_results': 20
				}
			elif 'week' in query_lower or 'last 7 days' in query_lower:
				week_ago = now - timedelta(days=7)
				time_filter = {
					'query': f'after:{week_ago.strftime("%Y/%m/%d")}',
					'max_results': 50
				}
			else:
				# Default to recent emails
				time_filter = {'max_results': 10}

			self.logger.info(f"📧 Fetching emails with filter: {time_filter}")

			# List emails
			email_list = await self._execute_mcp_tool_direct('gmail', 'list_emails', time_filter)

			# Extract email IDs from response (parse markdown)
			import re
			email_ids = re.findall(r'\*\*ID:\*\*\s+(\w+)', email_list)

			if not email_ids:
				return "No emails found for the specified time period."

			# Limit to 20 emails max
			emails_to_read = min(len(email_ids), 20)
			self.logger.info(f"📨 Found {len(email_ids)} emails. Reading up to {emails_to_read} for summarization...")

			# Read emails for summarization
			email_contents = []
			for i, email_id in enumerate(email_ids[:emails_to_read], 1):
				try:
					self.logger.info(f"  📧 Reading email {i}/{emails_to_read}...")
					email_content = await self._execute_mcp_tool_direct('gmail', 'read_email', {'email_id': email_id, 'include_attachments': False})
					email_contents.append(email_content)
				except Exception as e:
					self.logger.error(f"Failed to read email {email_id}: {e}")
					continue

			if not email_contents:
				return "Could not read any emails."

			# Combine all email contents
			combined_emails = "\n\n---\n\n".join(email_contents)

			# Ask LLM to summarize
			self.logger.info(f"🤖 Asking LLM to generate comprehensive summary of {len(email_contents)} emails...")

			summary_prompt = f"""You are an expert email analyst. Analyze and summarize the following {len(email_contents)} emails in detail:

{combined_emails[:30000]}

Provide a comprehensive, well-structured summary with:

## 📊 Email Statistics
- Total emails analyzed: {len(email_contents)}
- Time period: {time_filter.get('query', 'recent')}

## 👥 Key Senders
List the most frequent senders and what they typically sent about

## 📋 Main Topics & Categories
Categorize emails by topic/theme (work, personal, newsletters, notifications, etc.)

## ⚠️ Important/Urgent Items
Highlight any emails that require immediate attention or action

## 📌 Action Items
List specific tasks or actions mentioned in the emails

## 💡 Key Insights
Any patterns, trends, or notable observations

Be specific and detailed. Include sender names, subject lines, and key points from individual emails where relevant."""

			# Call LLM for summarization
			content = None
			try:
				from browser_use.llm.messages import UserMessage
				response = await self.llm.ainvoke([UserMessage(content=summary_prompt)])
				if hasattr(response, 'content'):
					content = response.content.strip()
				else:
					content = str(response).strip()
			except Exception as e:
				self.logger.error(f"LLM summarization failed: {e}")
				return f"Found {len(email_contents)} emails but could not generate summary. Please check manually."

			self.logger.success(f"✅ Summary generated successfully")
			return content

		except Exception as e:
			self.logger.error(f"Email summarization failed: {str(e)}")
			return f"Failed to summarize emails: {str(e)}"

	async def _execute_mcp_tool_direct(self, server_type: str, operation: str, params: Dict[str, Any]) -> str:
		"""
		Execute an MCP tool directly without using the browser agent

		Args:
			server_type: Type of MCP server ('calendar', 'gmail')
			operation: Tool operation name (e.g., 'list_events', 'create_event')
			params: Parameters for the tool

		Returns:
			Result string from the MCP tool
		"""
		client = self.mcp_manager.clients.get(server_type)
		if not client:
			raise RuntimeError(f"MCP server {server_type} not connected")

		# Map operation to MCP tool name
		tool_name_map = {
			# Calendar tools
			'list_events': 'list_calendar_events',
			'create_event': 'create_calendar_event',
			'update_event': 'update_calendar_event',
			'delete_event': 'delete_calendar_event',
			'check_availability': 'check_availability',
			# Gmail tools
			'list_emails': 'list_emails',
			'read_email': 'read_email',
			'send_email': 'send_email',
			'modify_labels': 'modify_email_labels',
			'search_emails': 'search_emails'
		}

		tool_name = tool_name_map.get(operation, operation)

		# FastMCP tools expect parameters wrapped in 'input_data'
		wrapped_params = {'input_data': params}

		# Call the MCP tool
		self.logger.info(f"📞 Calling MCP tool: {tool_name}")
		self.logger.info(f"📋 Parameters: {params}")

		try:
			result = await client.call_tool(tool_name, wrapped_params)
			self.logger.success(f"✅ MCP tool completed successfully")
			return str(result)
		except Exception as e:
			self.logger.error(f"Failed to call MCP tool {tool_name}: {str(e)}")
			raise

	async def execute_mcp_task(self, server_type: str, query: str) -> str:
		"""
		Execute an MCP tool task (calendar or email)

		Args:
			server_type: 'calendar' or 'gmail'
			query: Task description

		Returns:
			Task result string
		"""
		# Ensure MCP server is connected
		await self.ensure_mcp_connected(server_type)

		# Try LLM-based tool selection first
		self.logger.header("LLM-BASED MCP TOOL SELECTION")
		self.logger.info(f"🤖 Asking LLM to select appropriate {server_type} tool...")

		parsed = await self._llm_select_mcp_tool(server_type, query)

		# Fallback to regex-based parsing if LLM fails
		if not parsed:
			self.logger.error(f"LLM tool selection failed, falling back to regex parsing...")
			if server_type == 'calendar':
				parsed = self._parse_calendar_query(query)
			elif server_type == 'gmail':
				parsed = await self._parse_gmail_query(query)

		if parsed:
			self.logger.header("DIRECT MCP EXECUTION")
			self.logger.info(f"✨ Using direct MCP call (no browser needed)")

			operation = parsed.pop('operation')
			try:
				result = await self._execute_mcp_tool_direct(server_type, operation, parsed)
				return result
			except Exception as e:
				self.logger.error(f"Direct MCP execution failed: {str(e)}")
				self.logger.info("Falling back to agent reasoning...")
				# Fall through to agent execution

		# Check if this is a summarization/complex task that needs multiple MCP calls
		if any(keyword in query.lower() for keyword in ['summarize', 'summary', 'summerize']):
			self.logger.header("COMPLEX MCP TASK - SUMMARIZATION")
			self.logger.info(f"📊 Handling summarization without browser...")
			return await self._handle_email_summarization(query)

		# For other complex queries, use agent with MCP tools
		self.logger.info(f"📦 Using {server_type} MCP tools (via agent reasoning)")
		return await self.execute_browser_task(query)

	async def process_query(self, query: str) -> str:
		"""
		Main query processing with intelligent tool routing

		Args:
			query: User's query

		Returns:
			Response string
		"""
		# Check for manual tool override
		manual_tool = parse_manual_override(query) if not self.force_tool else ToolType(self.force_tool)

		if manual_tool or self.force_tool:
			# Strip command prefix if present
			clean_query = strip_command_prefix(query)
			tool_type = manual_tool or ToolType(self.force_tool)

			self.logger.info(f"🎯 Manual override: using {tool_type.value.upper()} tool")

			# Execute based on forced tool
			if tool_type == ToolType.CHAT:
				if self.disable_chat:
					self.logger.error("Pure chat mode is disabled")
					return "Chat mode disabled"
				self.logger.header("CHAT RESPONSE")
				return await self.chat_response(clean_query)

			elif tool_type == ToolType.BROWSER:
				return await self.execute_browser_task(clean_query)

			elif tool_type == ToolType.CALENDAR:
				return await self.execute_mcp_task('calendar', clean_query)

			elif tool_type == ToolType.EMAIL:
				return await self.execute_mcp_task('gmail', clean_query)

		# Automatic tool routing
		self.logger.header("TOOL ROUTING")

		decision = await route_query(self.llm, query, force_tool=manual_tool)

		# Log routing decision
		self.logger.info(format_routing_decision_log(decision))

		# Execute primary tool
		if decision.primary_tool == ToolType.CHAT:
			if self.disable_chat:
				self.logger.warning("Pure chat mode is disabled, using browser instead")
				return await self.execute_browser_task(query)

			self.logger.header("CHAT RESPONSE")
			return await self.chat_response(query)

		elif decision.primary_tool == ToolType.BROWSER:
			return await self.execute_browser_task(query)

		elif decision.primary_tool == ToolType.CALENDAR:
			return await self.execute_mcp_task('calendar', query)

		elif decision.primary_tool == ToolType.EMAIL:
			return await self.execute_mcp_task('gmail', query)

		# Fallback to browser if unknown tool
		else:
			self.logger.warning(f"Unknown tool type: {decision.primary_tool}, falling back to browser")
			return await self.execute_browser_task(query)

	def _setup_verbose_logging(self):
		"""Setup verbose step-by-step logging for agent"""
		if not self.agent:
			return

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

					if hasattr(state, 'thinking') and state.thinking:
						self.logger.thinking(state.thinking)

					if hasattr(state, 'evaluation_previous_goal') and state.evaluation_previous_goal:
						self.logger.info(f"\nEvaluation: {state.evaluation_previous_goal}")

					if hasattr(state, 'next_goal') and state.next_goal:
						self.logger.info(f"Next Goal: {state.next_goal}")

				# Show actions
				if hasattr(output, 'actions') and output.actions:
					for action in output.actions:
						action_name = action.__class__.__name__ if hasattr(action, '__class__') else str(action)

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

		self.agent.step = verbose_step

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
		# Close browser
		if self.browser_session:
			try:
				await self.browser_session.close()
			except Exception:
				pass

		# Disconnect MCP servers
		if self.mcp_manager:
			try:
				await self.mcp_manager.disconnect_all()
			except Exception:
				pass
