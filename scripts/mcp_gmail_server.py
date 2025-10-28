#!/usr/bin/env python3
"""
Gmail MCP Server
Provides email management capabilities via MCP protocol
"""

import os
import sys
import asyncio
import json
import base64
from typing import Optional, List, Dict, Any
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from contextlib import redirect_stdout, redirect_stderr
import io

from fastmcp import FastMCP
from pydantic import BaseModel, Field
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import pickle

# Constants
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']
CHARACTER_LIMIT = 25000

# Initialize MCP server
mcp = FastMCP("gmail-server")

# Pydantic models
class ListEmailsInput(BaseModel):
	"""Input for listing emails"""
	query: Optional[str] = Field(
		None,
		description="Gmail search query (e.g., 'is:unread', 'from:user@example.com', 'subject:meeting')"
	)
	max_results: int = Field(
		default=10,
		ge=1,
		le=50,
		description="Maximum number of emails to return (1-50)"
	)
	label_ids: Optional[List[str]] = Field(
		None,
		description="Filter by label IDs (e.g., ['INBOX', 'UNREAD'])"
	)
	include_spam_trash: bool = Field(
		default=False,
		description="Whether to include SPAM and TRASH folders"
	)
	response_format: str = Field(
		default="markdown",
		description="Response format: 'markdown' or 'json'"
	)

class ReadEmailInput(BaseModel):
	"""Input for reading a specific email"""
	email_id: str = Field(
		description="ID of the email to read"
	)
	include_attachments: bool = Field(
		default=False,
		description="Whether to include attachment information"
	)
	response_format: str = Field(
		default="markdown",
		description="Response format: 'markdown' or 'json'"
	)

class SendEmailInput(BaseModel):
	"""Input for sending an email"""
	to: List[str] = Field(
		description="List of recipient email addresses"
	)
	subject: str = Field(
		description="Email subject line"
	)
	body: str = Field(
		description="Email body content (plain text or HTML)"
	)
	cc: Optional[List[str]] = Field(
		None,
		description="List of CC recipient email addresses"
	)
	bcc: Optional[List[str]] = Field(
		None,
		description="List of BCC recipient email addresses"
	)
	is_html: bool = Field(
		default=False,
		description="Whether body content is HTML"
	)
	reply_to_id: Optional[str] = Field(
		None,
		description="Message ID to reply to (for threading)"
	)

class ModifyLabelsInput(BaseModel):
	"""Input for modifying email labels"""
	email_id: str = Field(
		description="ID of the email to modify"
	)
	add_labels: Optional[List[str]] = Field(
		None,
		description="Label IDs to add (e.g., ['IMPORTANT', 'STARRED'])"
	)
	remove_labels: Optional[List[str]] = Field(
		None,
		description="Label IDs to remove"
	)

# Authentication helper
def get_gmail_service():
	"""Get authenticated Gmail service"""
	creds = None
	token_path = Path(os.getenv('GOOGLE_TOKEN_PATH', 'gmail_token.pickle'))

	if token_path.exists():
		with open(token_path, 'rb') as token:
			creds = pickle.load(token)

	if not creds or not creds.valid:
		if creds and creds.expired and creds.refresh_token:
			creds.refresh(Request())
		else:
			flow = InstalledAppFlow.from_client_secrets_file(
				os.getenv('GOOGLE_CREDENTIALS_PATH', 'credentials.json'),
				SCOPES
			)
			# Suppress browser output to prevent STDIO interference
			with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
				creds = flow.run_local_server(port=0)

		with open(token_path, 'wb') as token:
			pickle.dump(creds, token)

	return build('gmail', 'v1', credentials=creds)

# Format helpers
def parse_email_headers(headers: List[Dict]) -> Dict[str, str]:
	"""Parse email headers into a dictionary"""
	result = {}
	for header in headers:
		name = header['name']
		value = header['value']
		if name in ['From', 'To', 'Subject', 'Date', 'Cc']:
			result[name] = value
	return result

def format_email_markdown(message: Dict[str, Any], include_body: bool = False) -> str:
	"""Format email as markdown"""
	lines = []

	# Parse headers
	headers = parse_email_headers(message['payload'].get('headers', []))

	lines.append(f"**Subject:** {headers.get('Subject', 'No Subject')}")
	lines.append(f"**From:** {headers.get('From', 'Unknown')}")
	lines.append(f"**To:** {headers.get('To', 'Unknown')}")
	if headers.get('Cc'):
		lines.append(f"**Cc:** {headers['Cc']}")
	lines.append(f"**Date:** {headers.get('Date', 'Unknown')}")
	lines.append(f"**ID:** {message['id']}")

	# Add labels
	if message.get('labelIds'):
		lines.append(f"**Labels:** {', '.join(message['labelIds'])}")

	# Add snippet
	if message.get('snippet'):
		lines.append(f"\n**Preview:** {message['snippet'][:200]}...")

	# Add body if requested
	if include_body:
		body = extract_email_body(message['payload'])
		if body:
			lines.append("\n**Content:**")
			lines.append(body[:5000])  # Limit body length

	return '\n'.join(lines)

def extract_email_body(payload: Dict) -> str:
	"""Extract email body from payload"""
	body = ""

	if 'parts' in payload:
		for part in payload['parts']:
			if part['mimeType'] == 'text/plain':
				data = part['body']['data']
				body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
				break
			elif part['mimeType'] == 'text/html' and not body:
				data = part['body']['data']
				body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
	elif payload['body'].get('data'):
		body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8', errors='ignore')

	return body

# MCP Tools
@mcp.tool()
async def list_emails(
	input_data: ListEmailsInput
) -> str:
	"""
	List emails from Gmail with optional filtering.

	Supports Gmail's advanced search syntax:
	- 'is:unread' - unread emails
	- 'from:sender@example.com' - emails from specific sender
	- 'subject:meeting' - emails with 'meeting' in subject
	- 'has:attachment' - emails with attachments
	- 'after:2024/1/1' - emails after a date
	- Combine with AND/OR: 'is:unread AND from:boss@company.com'

	Returns a list of emails with basic information.
	"""
	try:
		service = get_gmail_service()

		# Build query
		query_params = {
			'maxResults': input_data.max_results
		}

		if input_data.query:
			query_params['q'] = input_data.query

		if input_data.label_ids:
			query_params['labelIds'] = input_data.label_ids

		if not input_data.include_spam_trash:
			query_params['q'] = query_params.get('q', '') + ' -in:spam -in:trash'

		# Get message list
		results = service.users().messages().list(
			userId='me',
			**query_params
		).execute()

		messages = results.get('messages', [])

		if not messages:
			return "No emails found matching the criteria."

		# Get full message details
		email_details = []
		for msg in messages:
			try:
				message = service.users().messages().get(
					userId='me',
					id=msg['id']
				).execute()
				email_details.append(message)
			except Exception as e:
				continue

		# Format response
		if input_data.response_format == 'json':
			return json.dumps(email_details, indent=2)[:CHARACTER_LIMIT]
		else:
			lines = [f"# Emails ({len(email_details)} found)\n"]
			for i, email in enumerate(email_details, 1):
				lines.append(f"## Email {i}")
				lines.append(format_email_markdown(email))
				lines.append("")  # Empty line between emails

			return '\n'.join(lines)[:CHARACTER_LIMIT]

	except Exception as e:
		return f"Error listing emails: {str(e)}"

@mcp.tool()
async def read_email(
	input_data: ReadEmailInput
) -> str:
	"""
	Read a specific email by ID.

	Returns the full email content including headers and body.
	Email IDs can be obtained from list_emails.
	"""
	try:
		service = get_gmail_service()

		message = service.users().messages().get(
			userId='me',
			id=input_data.email_id
		).execute()

		if input_data.response_format == 'json':
			return json.dumps(message, indent=2)[:CHARACTER_LIMIT]
		else:
			result = format_email_markdown(message, include_body=True)

			# Add attachment info if requested
			if input_data.include_attachments:
				attachments = []
				for part in message['payload'].get('parts', []):
					if part.get('filename'):
						attachments.append({
							'filename': part['filename'],
							'mimeType': part['mimeType'],
							'size': part['body'].get('size', 0)
						})

				if attachments:
					result += "\n\n**Attachments:**\n"
					for att in attachments:
						result += f"- {att['filename']} ({att['mimeType']}, {att['size']} bytes)\n"

			return result[:CHARACTER_LIMIT]

	except Exception as e:
		return f"Error reading email: {str(e)}"

@mcp.tool()
async def send_email(
	input_data: SendEmailInput
) -> str:
	"""
	Send a new email.

	Supports plain text and HTML emails.
	Can send to multiple recipients with CC and BCC.
	Returns the sent message ID for reference.
	"""
	try:
		service = get_gmail_service()

		# Create message
		message = MIMEMultipart()
		message['To'] = ', '.join(input_data.to)
		message['Subject'] = input_data.subject

		if input_data.cc:
			message['Cc'] = ', '.join(input_data.cc)

		# Add body
		if input_data.is_html:
			message.attach(MIMEText(input_data.body, 'html'))
		else:
			message.attach(MIMEText(input_data.body, 'plain'))

		# Handle reply threading
		if input_data.reply_to_id:
			message['In-Reply-To'] = input_data.reply_to_id
			message['References'] = input_data.reply_to_id

		# Encode message
		raw_message = base64.urlsafe_b64encode(
			message.as_bytes()
		).decode('utf-8')

		body = {'raw': raw_message}

		if input_data.reply_to_id:
			body['threadId'] = input_data.reply_to_id

		# Send message
		sent_message = service.users().messages().send(
			userId='me',
			body=body
		).execute()

		return f"""Email sent successfully!

**Message ID:** {sent_message['id']}
**To:** {', '.join(input_data.to)}
**Subject:** {input_data.subject}

The email has been delivered to the recipient(s)."""

	except Exception as e:
		return f"Error sending email: {str(e)}"

@mcp.tool()
async def modify_email_labels(
	input_data: ModifyLabelsInput
) -> str:
	"""
	Add or remove labels from an email.

	Common labels: INBOX, UNREAD, IMPORTANT, STARRED, SPAM, TRASH
	Can also use custom label IDs.
	"""
	try:
		service = get_gmail_service()

		body = {}
		if input_data.add_labels:
			body['addLabelIds'] = input_data.add_labels
		if input_data.remove_labels:
			body['removeLabelIds'] = input_data.remove_labels

		result = service.users().messages().modify(
			userId='me',
			id=input_data.email_id,
			body=body
		).execute()

		return f"""Email labels modified successfully!

**Email ID:** {input_data.email_id}
**Added Labels:** {', '.join(input_data.add_labels or [])}
**Removed Labels:** {', '.join(input_data.remove_labels or [])}
**Current Labels:** {', '.join(result.get('labelIds', []))}"""

	except Exception as e:
		return f"Error modifying email labels: {str(e)}"

@mcp.tool()
async def search_emails(
	query: str,
	max_results: int = 10
) -> str:
	"""
	Quick search for emails using Gmail search syntax.

	This is a simplified version of list_emails for quick searches.
	Examples:
	- "from:john@example.com subject:invoice"
	- "has:attachment after:2024/1/1"
	- "is:unread is:important"
	"""
	return await list_emails(
		ListEmailsInput(
			query=query,
			max_results=max_results,
			response_format="markdown"
		)
	)

if __name__ == "__main__":
	# Run the MCP server
	mcp.run()
