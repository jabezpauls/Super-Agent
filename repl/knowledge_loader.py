"""
Knowledge Loader Module
Loads personal context from knowledge/ directory text files
"""

import os
from pathlib import Path
from typing import Dict, Optional


class KnowledgeLoader:
	"""Load and manage personal knowledge/context from text files"""

	def __init__(self, knowledge_dir: str = "knowledge"):
		"""
		Initialize knowledge loader

		Args:
			knowledge_dir: Directory containing knowledge .txt files
		"""
		self.knowledge_dir = Path(knowledge_dir)
		self.context_cache: Optional[str] = None
		self.files_cache: Dict[str, str] = {}

	def load_all_knowledge(self) -> str:
		"""
		Load all .txt files from knowledge directory and combine into context string

		Returns:
			Combined context string from all knowledge files
		"""
		if not self.knowledge_dir.exists():
			return ""

		knowledge_parts = []

		# Load all .txt files
		txt_files = sorted(self.knowledge_dir.glob("*.txt"))

		if not txt_files:
			return ""

		knowledge_parts.append("=== PERSONAL KNOWLEDGE & CONTEXT ===")
		knowledge_parts.append("")

		for txt_file in txt_files:
			try:
				with open(txt_file, 'r', encoding='utf-8') as f:
					content = f.read().strip()
					if content:
						# Store in cache
						self.files_cache[txt_file.name] = content
						# Add to combined knowledge
						knowledge_parts.append(f"--- {txt_file.stem.upper()} ---")
						knowledge_parts.append(content)
						knowledge_parts.append("")
			except Exception as e:
				print(f"Warning: Could not load {txt_file}: {e}")
				continue

		knowledge_parts.append("=== END KNOWLEDGE ===")

		self.context_cache = "\n".join(knowledge_parts)
		return self.context_cache

	def get_context(self, force_reload: bool = False) -> str:
		"""
		Get combined knowledge context

		Args:
			force_reload: Force reload from disk (default: use cache)

		Returns:
			Combined context string
		"""
		if force_reload or self.context_cache is None:
			return self.load_all_knowledge()
		return self.context_cache

	def get_file_content(self, filename: str) -> Optional[str]:
		"""
		Get content of specific knowledge file

		Args:
			filename: Name of the file (e.g., "contacts.txt")

		Returns:
			File content or None if not found
		"""
		# Ensure cache is loaded
		if not self.files_cache:
			self.load_all_knowledge()

		return self.files_cache.get(filename)

	def search_contact_email(self, name: str) -> Optional[str]:
		"""
		Search for email address by contact name

		Args:
			name: Contact name to search for

		Returns:
			Email address if found, None otherwise
		"""
		contacts_content = self.get_file_content("contacts.txt")
		if not contacts_content:
			return None

		# Simple search: look for "name: email" pattern
		import re
		pattern = rf'^\s*-?\s*{re.escape(name)}\s*:\s*([^\s,]+@[^\s,]+)'
		match = re.search(pattern, contacts_content, re.MULTILINE | re.IGNORECASE)

		if match:
			return match.group(1)

		return None

	def has_knowledge(self) -> bool:
		"""Check if any knowledge files exist"""
		if not self.knowledge_dir.exists():
			return False
		return len(list(self.knowledge_dir.glob("*.txt"))) > 0

	def list_files(self) -> list[str]:
		"""List all knowledge files"""
		if not self.knowledge_dir.exists():
			return []
		return [f.name for f in sorted(self.knowledge_dir.glob("*.txt"))]

	def get_stats(self) -> Dict[str, int]:
		"""Get statistics about loaded knowledge"""
		context = self.get_context()
		return {
			"files_count": len(self.files_cache),
			"total_chars": len(context),
			"total_lines": len(context.split('\n')) if context else 0,
		}
