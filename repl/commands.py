"""
Command Handler Module
Handles special commands in the REPL (commands starting with /)
"""

from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
	from repl.session_manager import SessionManager


class CommandHandler:
	"""Handles REPL special commands"""

	def __init__(self, session: 'SessionManager', logger):
		"""
		Initialize command handler

		Args:
			session: SessionManager instance
			logger: Logger for output
		"""
		self.session = session
		self.logger = logger

	async def handle_command(self, command_str: str) -> bool:
		"""
		Handle a special command

		Args:
			command_str: Command string (without the leading /)

		Returns:
			True if command was handled, False if should exit REPL
		"""
		# Parse command and arguments
		parts = command_str.lower().split(maxsplit=1)
		command = parts[0]
		args = parts[1] if len(parts) > 1 else ""

		# Exit commands
		if command in ['exit', 'quit']:
			self.logger.info("Exiting REPL...")
			return False

		# Help command
		elif command == 'help':
			self._show_help()
			return True

		# Clear session
		elif command == 'clear':
			await self.session.clear_session()
			return True

		# Show history
		elif command == 'history':
			self._show_history()
			return True

		# Show config
		elif command == 'config':
			self._show_config()
			return True

		# Tool forcing commands (new)
		elif command == 'browser':
			if not args:
				self.logger.error("Usage: /browser <query>")
				return True
			self.session.force_tool = 'browser'
			await self.session.process_query(args)
			self.session.force_tool = None
			return True

		elif command in ['calendar', 'calender']:  # Support common misspelling
			if not args:
				self.logger.error("Usage: /calendar <query>")
				return True
			self.session.force_tool = 'calendar'
			await self.session.process_query(args)
			self.session.force_tool = None
			return True

		elif command in ['email', 'mail']:  # Support shorter alias
			if not args:
				self.logger.error("Usage: /email or /mail <query>")
				return True
			self.session.force_tool = 'email'
			await self.session.process_query(args)
			self.session.force_tool = None
			return True

		elif command == 'chat':
			if not args:
				self.logger.error("Usage: /chat <message>")
				return True
			self.session.force_tool = 'chat'
			await self.session.process_query(args)
			self.session.force_tool = None
			return True

		# MCP management commands (new)
		elif command == 'connect':
			if not args:
				self.logger.error("Usage: /connect <calendar|gmail>")
				return True
			await self._connect_mcp(args)
			return True

		elif command == 'disconnect':
			if not args:
				self.logger.error("Usage: /disconnect <calendar|gmail>")
				return True
			await self._disconnect_mcp(args)
			return True

		elif command == 'status':
			self._show_status()
			return True

		elif command == 'tools':
			self._show_tools()
			return True

		# Unknown command
		else:
			self.logger.error(f"Unknown command: /{command}")
			self.logger.info("Type /help to see available commands")
			return True

	def _show_help(self):
		"""Display help message"""
		print("\n" + "="*60)
		print("Browser-Use REPL - Available Commands")
		print("="*60)

		print("\n📋 Basic Commands:")
		print("  /help     - Show this help message")
		print("  /exit     - Exit the REPL")
		print("  /quit     - Exit the REPL")
		print("  /clear    - Clear browser session and start fresh")
		print("  /history  - Show command history")
		print("  /config   - Show current configuration")

		print("\n🎯 Tool Forcing (override automatic routing):")
		print("  /browser <query>         - Force use of browser tool")
		print("  /calendar <query>        - Force use of calendar tool")
		print("  /calender <query>        - Alias for /calendar")
		print("  /email <query>           - Force use of email/Gmail tool")
		print("  /mail <query>            - Alias for /email")
		print("  /chat <message>          - Force pure chat response")

		print("\n🔌 MCP Server Management:")
		print("  /connect <server>    - Connect to MCP server (calendar, gmail)")
		print("  /disconnect <server> - Disconnect from MCP server")
		print("  /status              - Show MCP connection status")
		print("  /tools               - List available tools")

		print("\n💡 Tips:")
		print("  - Just type naturally - the AI will choose the right tool automatically")
		print("  - Calendar and email tools auto-connect on first use")
		print("  - Use /browser, /mail, /calendar, /chat to force specific tools")
		print("  - Example: '/browser remember to meet dentist at 6pm' forces browser use")

		print("\n🌐 Using Existing Chrome:")
		print("  - Auto-connects to Chrome on port 9222 if available")
		print("  - Launch Chrome with:")
		print("    google-chrome --remote-debugging-port=9222 --user-data-dir=/tmp/chrome-debug")
		print("  - Verify with: curl http://localhost:9222/json/version")
		print("  - Or specify custom port: python browser_use_repl.py --cdp-url http://localhost:PORT")

		print("="*60 + "\n")

	def _show_history(self):
		"""Display command history"""
		print("\nCommand History:")
		if not self.session.command_history:
			print("  (empty)")
		else:
			for i, cmd in enumerate(self.session.command_history, 1):
				print(f"  {i}. {cmd}")

	def _show_config(self):
		"""Display current configuration"""
		print("\nCurrent Configuration:")
		print(f"  LLM: {self.session.llm.__class__.__name__}")
		if hasattr(self.session.llm, 'model'):
			print(f"  Model: {self.session.llm.model}")
		print(f"  Browser Mode: {'Headless' if self.session.headless else 'Visible'}")
		print(f"  Vision: {'Enabled' if self.session.use_vision else 'Disabled'}")
		print(f"  Max Steps: {self.session.max_steps}")
		print(f"  Prompt Optimization: {'Enabled' if self.session.optimize_prompts else 'Disabled'}")
		print(f"  MCP Enabled: {'Yes' if self.session.enable_mcp else 'No'}")
		print(f"  Pure Chat Mode: {'Disabled' if self.session.disable_chat else 'Enabled'}")

	async def _connect_mcp(self, server_type: str):
		"""Connect to an MCP server"""
		server_type = server_type.strip().lower()

		if not self.session.enable_mcp:
			self.logger.error("MCP is disabled. Restart REPL with MCP enabled.")
			return

		valid_servers = ['calendar', 'gmail']
		if server_type not in valid_servers:
			self.logger.error(f"Unknown server: {server_type}. Valid: {', '.join(valid_servers)}")
			return

		try:
			await self.session.ensure_mcp_connected(server_type)
			self.logger.success(f"✅ Connected to {server_type} MCP server")
		except Exception as e:
			self.logger.error(f"Failed to connect: {str(e)}")

	async def _disconnect_mcp(self, server_type: str):
		"""Disconnect from an MCP server"""
		server_type = server_type.strip().lower()

		if not self.session.enable_mcp or not self.session.mcp_manager:
			self.logger.error("MCP is disabled")
			return

		try:
			await self.session.mcp_manager.disconnect(server_type)
			self.session.active_mcp_servers.discard(server_type)
			self.logger.success(f"🔌 Disconnected from {server_type} MCP server")
		except Exception as e:
			self.logger.error(f"Failed to disconnect: {str(e)}")

	def _show_status(self):
		"""Show MCP connection status"""
		print("\n" + "="*60)
		print("MCP Server Status")
		print("="*60)

		if not self.session.enable_mcp:
			print("MCP is disabled")
			print("="*60 + "\n")
			return

		print(f"\nMCP Manager: {'Initialized' if self.session.mcp_manager else 'Not initialized'}")

		if self.session.mcp_manager:
			connected = self.session.mcp_manager.get_connected_servers()
			available = self.session.mcp_manager.get_available_servers()

			print(f"\nConnected Servers ({len(connected)}):")
			if connected:
				for server in connected:
					print(f"  ✅ {server}")
			else:
				print("  (none)")

			print(f"\nAvailable Servers ({len(available)}):")
			for server in available:
				status = "✅ connected" if server in connected else "⚪ disconnected"
				print(f"  {status} - {server}")

		print("="*60 + "\n")

	def _show_tools(self):
		"""Show available tools"""
		print("\n" + "="*60)
		print("Available Tools")
		print("="*60)

		print("\n🌐 Browser Tool:")
		print("  - Always available")
		print("  - Web browsing, searching, data extraction")

		print("\n💬 Chat Tool:")
		print(f"  - {'Disabled' if self.session.disable_chat else 'Enabled'}")
		print("  - Pure conversation without external tools")

		if self.session.enable_mcp:
			print("\n📅 Calendar Tool (MCP):")
			if 'calendar' in self.session.active_mcp_servers:
				print("  - ✅ Connected")
				print("  - List/create/update/delete events, check availability")
			else:
				print("  - ⚪ Not connected (will auto-connect on first use)")

			print("\n📧 Email Tool (MCP):")
			if 'gmail' in self.session.active_mcp_servers:
				print("  - ✅ Connected")
				print("  - List/read/send emails, search, modify labels")
			else:
				print("  - ⚪ Not connected (will auto-connect on first use)")
		else:
			print("\n⚠️  MCP tools disabled")
			print("  Restart with MCP enabled to use Calendar and Email")

		print("="*60 + "\n")
