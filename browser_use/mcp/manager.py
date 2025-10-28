"""
MCP Manager for Browser-Use Agent
Manages lifecycle of multiple MCP server connections and tool registration
"""

import os
import sys
import asyncio
import subprocess
import time
from typing import Dict, Optional, List, Set
from pathlib import Path
from dataclasses import dataclass

from browser_use.mcp.client import MCPClient
from browser_use.tools.service import Tools


@dataclass
class MCPServerConfig:
	"""Configuration for an MCP server"""
	name: str
	command: str
	args: List[str]
	port: Optional[int] = None
	env: Optional[Dict[str, str]] = None


# Predefined MCP server configurations
# Use sys.executable to ensure we use the same Python as the main process
MCP_SERVER_CONFIGS = {
	'calendar': MCPServerConfig(
		name='google-calendar',
		command=sys.executable,
		args=['scripts/mcp_calendar_server.py'],
		port=8002,
		env={
			'GOOGLE_CREDENTIALS_PATH': os.getenv('GOOGLE_CREDENTIALS_PATH', 'credentials.json'),
			'GOOGLE_TOKEN_PATH': os.getenv('GOOGLE_TOKEN_PATH', 'token.pickle'),
			'MCP_CALENDAR_PORT': str(os.getenv('MCP_CALENDAR_PORT', 8002)),
			'BROWSER': os.getenv('BROWSER', '/usr/bin/google-chrome')  # For OAuth browser launch
		}
	),
	'gmail': MCPServerConfig(
		name='gmail',
		command=sys.executable,
		args=['scripts/mcp_gmail_server.py'],
		port=8001,
		env={
			'GOOGLE_CREDENTIALS_PATH': os.getenv('GOOGLE_CREDENTIALS_PATH', 'credentials.json'),
			'GOOGLE_TOKEN_PATH': os.getenv('GOOGLE_TOKEN_PATH', 'gmail_token.pickle'),
			'MCP_GMAIL_PORT': str(os.getenv('MCP_GMAIL_PORT', 8001)),
			'BROWSER': os.getenv('BROWSER', '/usr/bin/google-chrome')  # For OAuth browser launch
		}
	)
}


class MCPManager:
	"""
	Manages multiple MCP server connections

	Features:
	- Lazy-loading of MCP servers on first use
	- Automatic tool registration to Tools registry
	- Process lifecycle management
	- Connection pooling and cleanup
	"""

	def __init__(self, auto_connect: List[str] = None):
		"""
		Initialize MCP Manager

		Args:
			auto_connect: List of server types to auto-connect on startup
		"""
		self.clients: Dict[str, MCPClient] = {}
		self.processes: Dict[str, subprocess.Popen] = {}
		self.connected_servers: Set[str] = set()
		self.auto_connect = auto_connect or []

	async def connect(self, server_type: str) -> MCPClient:
		"""
		Connect to an MCP server

		Args:
			server_type: Type of server ('calendar', 'gmail', etc.)

		Returns:
			MCPClient instance

		Raises:
			ValueError: If server_type not recognized
			RuntimeError: If connection fails
		"""
		if server_type in self.connected_servers:
			return self.clients[server_type]

		if server_type not in MCP_SERVER_CONFIGS:
			available = ', '.join(MCP_SERVER_CONFIGS.keys())
			raise ValueError(f"Unknown server type: {server_type}. Available: {available}")

		config = MCP_SERVER_CONFIGS[server_type]

		try:
			# Start MCP server process
			print(f"🚀 Starting {config.name} MCP server...")

			# Prepare environment
			env = os.environ.copy()
			if config.env:
				env.update(config.env)

			# Start server process with STDIO pipes for communication
			process = subprocess.Popen(
				[config.command] + config.args,
				env=env,
				stdin=subprocess.PIPE,
				stdout=subprocess.PIPE,
				stderr=subprocess.PIPE,
				cwd=Path.cwd()
			)

			self.processes[server_type] = process

			# Wait for server to start
			await asyncio.sleep(1)

			# Check if process is still running
			if process.poll() is not None:
				# Get stderr output for debugging
				stderr_output = process.stderr.read().decode() if process.stderr else "No error output"
				raise RuntimeError(f"MCP server process died immediately (exit code: {process.returncode})\nError: {stderr_output}")

			# Create MCP client
			# Note: MCPClient expects stdio communication, but for HTTP-based MCP servers
			# we might need a different approach. For now, we'll assume the servers
			# are running and we connect via HTTP/stdio hybrid
			client = MCPClient(
				server_name=config.name,
				command=config.command,
				args=config.args,
				env=config.env
			)

			await client.connect()

			self.clients[server_type] = client
			self.connected_servers.add(server_type)

			print(f"✅ Connected to {config.name} MCP server")

			return client

		except Exception as e:
			# Cleanup on failure
			if server_type in self.processes:
				self.processes[server_type].terminate()
				del self.processes[server_type]

			raise RuntimeError(f"Failed to connect to {server_type} MCP server: {str(e)}")

	async def lazy_connect(self, server_type: str) -> MCPClient:
		"""
		Lazy-load MCP server (connect only if not already connected)

		Args:
			server_type: Type of server to connect

		Returns:
			MCPClient instance
		"""
		if server_type in self.connected_servers:
			return self.clients[server_type]

		return await self.connect(server_type)

	async def register_tools(self, server_type: str, tools: Tools) -> int:
		"""
		Register MCP server tools to the Tools registry

		Args:
			server_type: Type of server
			tools: Tools instance to register to

		Returns:
			Number of tools registered
		"""
		if server_type not in self.connected_servers:
			raise RuntimeError(f"Server {server_type} not connected. Call connect() first.")

		client = self.clients[server_type]

		# Register MCP tools to the tools registry
		await client.register_to_tools(tools)

		# Get tool count (using private attribute _registered_actions)
		tool_count = len(client._registered_actions) if hasattr(client, '_registered_actions') else 0

		print(f"📦 Registered {tool_count} tools from {server_type} MCP server")

		return tool_count

	async def disconnect(self, server_type: str):
		"""
		Disconnect from an MCP server

		Args:
			server_type: Type of server to disconnect
		"""
		if server_type not in self.connected_servers:
			return

		# Close client connection
		if server_type in self.clients:
			client = self.clients[server_type]
			# await client.close()  # Uncomment if MCPClient has close method
			del self.clients[server_type]

		# Terminate server process
		if server_type in self.processes:
			process = self.processes[server_type]
			process.terminate()

			# Wait for graceful shutdown
			try:
				process.wait(timeout=5)
			except subprocess.TimeoutExpired:
				process.kill()

			del self.processes[server_type]

		self.connected_servers.discard(server_type)

		print(f"🔌 Disconnected from {server_type} MCP server")

	async def disconnect_all(self):
		"""Disconnect from all MCP servers"""
		for server_type in list(self.connected_servers):
			await self.disconnect(server_type)

	def is_connected(self, server_type: str) -> bool:
		"""Check if server is connected"""
		return server_type in self.connected_servers

	def get_connected_servers(self) -> List[str]:
		"""Get list of connected server types"""
		return list(self.connected_servers)

	async def health_check(self, server_type: str) -> bool:
		"""
		Check if MCP server is healthy

		Args:
			server_type: Type of server to check

		Returns:
			True if server is healthy, False otherwise
		"""
		if server_type not in self.connected_servers:
			return False

		# Check if process is still running
		if server_type in self.processes:
			process = self.processes[server_type]
			if process.poll() is not None:
				# Process died
				print(f"⚠️  {server_type} MCP server process died (exit code: {process.returncode})")
				await self.disconnect(server_type)
				return False

		return True

	async def reconnect(self, server_type: str) -> MCPClient:
		"""
		Reconnect to an MCP server

		Args:
			server_type: Type of server to reconnect

		Returns:
			MCPClient instance
		"""
		await self.disconnect(server_type)
		return await self.connect(server_type)

	def get_available_servers(self) -> List[str]:
		"""Get list of available (configured) server types"""
		return list(MCP_SERVER_CONFIGS.keys())

	async def ensure_connected(self, server_type: str, tools: Optional[Tools] = None) -> MCPClient:
		"""
		Ensure MCP server is connected, connecting if necessary

		Args:
			server_type: Type of server
			tools: Optional Tools instance to register tools to

		Returns:
			MCPClient instance
		"""
		if not self.is_connected(server_type):
			client = await self.connect(server_type)

			if tools:
				await self.register_tools(server_type, tools)

			return client

		return self.clients[server_type]

	async def __aenter__(self):
		"""Async context manager entry"""
		return self

	async def __aexit__(self, exc_type, exc_val, exc_tb):
		"""Async context manager exit - cleanup all connections"""
		await self.disconnect_all()


# Convenience function for simple use cases
async def get_mcp_client(server_type: str) -> MCPClient:
	"""
	Get an MCP client for a specific server type

	Simple wrapper for one-off connections

	Args:
		server_type: Type of server ('calendar', 'gmail', etc.)

	Returns:
		MCPClient instance
	"""
	manager = MCPManager()
	return await manager.connect(server_type)
