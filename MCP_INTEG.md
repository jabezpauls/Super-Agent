# MCP Integration Guide for Browser-Use Agent System

## Overview
This guide will help you integrate Google Calendar and Gmail MCP servers into your existing browser-use agent system, creating a unified AI assistant that can:
- Chat naturally with users
- Browse the web (via browser-use)
- Manage calendar events
- Read and send emails
- Decide which tools to use based on context

## Architecture Overview

```
User Input → Orchestrator LLM → Tool Router
                                    ↓
                    ┌───────────────┼───────────────┐
                    ↓               ↓               ↓
              Browser-Use    Google Calendar   Gmail MCP
                Agent           MCP Server      Server
```

## Step 1: Install Required Dependencies

```bash
# Core MCP dependencies
pip install mcp fastmcp

# Google API dependencies
pip install google-auth google-auth-oauthlib google-auth-httplib2
pip install google-api-python-client

# Additional utilities
pip install pydantic aiohttp python-dotenv
```

## Step 2: Set Up Google API Credentials

### 2.1 Enable APIs in Google Cloud Console
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable these APIs:
   - Gmail API
   - Google Calendar API

### 2.2 Create OAuth2 Credentials
1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth client ID"
3. Choose "Desktop app" as application type
4. Download the credentials JSON file
5. Save it as `credentials.json` in your project root

### 2.3 Create .env file
```bash
# .env
GOOGLE_CREDENTIALS_PATH=./credentials.json
GOOGLE_TOKEN_PATH=./token.json
MCP_GMAIL_PORT=8001
MCP_CALENDAR_PORT=8002
```

## Step 3: Create Google Calendar MCP Server

Create `mcp_calendar_server.py`:

```python
#!/usr/bin/env python3
"""
Google Calendar MCP Server
Provides calendar management capabilities via MCP protocol
"""

import os
import asyncio
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pathlib import Path

from fastmcp import FastMCP
from pydantic import BaseModel, Field
import httpx
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import pickle

# Constants
SCOPES = ['https://www.googleapis.com/auth/calendar']
CHARACTER_LIMIT = 25000

# Initialize MCP server
mcp = FastMCP("google-calendar-server")

# Pydantic models for input validation
class ListEventsInput(BaseModel):
    """Input for listing calendar events"""
    calendar_id: str = Field(
        default="primary",
        description="Calendar ID (default: 'primary' for user's main calendar)"
    )
    time_min: Optional[str] = Field(
        None,
        description="Lower bound for event start time (RFC3339 timestamp, e.g., '2024-01-01T00:00:00Z')"
    )
    time_max: Optional[str] = Field(
        None,
        description="Upper bound for event start time (RFC3339 timestamp)"
    )
    max_results: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of events to return (1-100)"
    )
    query: Optional[str] = Field(
        None,
        description="Search query to filter events"
    )
    response_format: str = Field(
        default="markdown",
        description="Response format: 'markdown' or 'json'"
    )

class CreateEventInput(BaseModel):
    """Input for creating a calendar event"""
    summary: str = Field(
        description="Event title/summary"
    )
    start_time: str = Field(
        description="Start time (RFC3339 format or 'YYYY-MM-DD' for all-day)"
    )
    end_time: str = Field(
        description="End time (RFC3339 format or 'YYYY-MM-DD' for all-day)"
    )
    description: Optional[str] = Field(
        None,
        description="Event description"
    )
    location: Optional[str] = Field(
        None,
        description="Event location"
    )
    attendees: Optional[List[str]] = Field(
        None,
        description="List of attendee email addresses"
    )
    calendar_id: str = Field(
        default="primary",
        description="Calendar ID to create event in"
    )
    send_notifications: bool = Field(
        default=True,
        description="Whether to send notifications to attendees"
    )

class UpdateEventInput(BaseModel):
    """Input for updating an event"""
    event_id: str = Field(
        description="ID of the event to update"
    )
    calendar_id: str = Field(
        default="primary",
        description="Calendar ID containing the event"
    )
    summary: Optional[str] = Field(None, description="New event title")
    start_time: Optional[str] = Field(None, description="New start time")
    end_time: Optional[str] = Field(None, description="New end time")
    description: Optional[str] = Field(None, description="New description")
    location: Optional[str] = Field(None, description="New location")

class DeleteEventInput(BaseModel):
    """Input for deleting an event"""
    event_id: str = Field(description="ID of the event to delete")
    calendar_id: str = Field(default="primary", description="Calendar ID")
    send_notifications: bool = Field(
        default=True,
        description="Whether to send cancellation notifications"
    )

# Authentication helper
def get_google_service():
    """Get authenticated Google Calendar service"""
    creds = None
    token_path = Path(os.getenv('GOOGLE_TOKEN_PATH', 'token.pickle'))
    
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
            creds = flow.run_local_server(port=0)
        
        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)
    
    return build('calendar', 'v3', credentials=creds)

# Format helpers
def format_event_markdown(event: Dict[str, Any]) -> str:
    """Format a single event as markdown"""
    lines = []
    lines.append(f"**{event.get('summary', 'Untitled Event')}**")
    
    start = event.get('start', {})
    end = event.get('end', {})
    
    if 'dateTime' in start:
        lines.append(f"- Start: {start['dateTime']}")
        lines.append(f"- End: {end.get('dateTime', 'N/A')}")
    elif 'date' in start:
        lines.append(f"- Date: {start['date']} (All day)")
    
    if event.get('location'):
        lines.append(f"- Location: {event['location']}")
    
    if event.get('description'):
        desc = event['description'][:200] + '...' if len(event['description']) > 200 else event['description']
        lines.append(f"- Description: {desc}")
    
    if event.get('attendees'):
        attendee_list = ', '.join([a['email'] for a in event['attendees'][:5]])
        if len(event['attendees']) > 5:
            attendee_list += f" (+{len(event['attendees'])-5} more)"
        lines.append(f"- Attendees: {attendee_list}")
    
    return '\n'.join(lines)

# MCP Tools
@mcp.tool()
async def list_calendar_events(
    input_data: ListEventsInput
) -> str:
    """
    List calendar events with optional filtering.
    
    Returns events from the specified calendar within the given time range.
    Supports searching by query and different response formats.
    
    Example usage:
    - List today's events: time_min=today's date, time_max=tomorrow's date
    - Search for specific events: query="meeting with John"
    - Get next week's events: appropriate time_min and time_max
    """
    try:
        service = get_google_service()
        
        # Build query parameters
        params = {
            'calendarId': input_data.calendar_id,
            'maxResults': input_data.max_results,
            'singleEvents': True,
            'orderBy': 'startTime'
        }
        
        if input_data.time_min:
            params['timeMin'] = input_data.time_min
        else:
            # Default to current time
            params['timeMin'] = datetime.utcnow().isoformat() + 'Z'
        
        if input_data.time_max:
            params['timeMax'] = input_data.time_max
        
        if input_data.query:
            params['q'] = input_data.query
        
        # Execute query
        events_result = service.events().list(**params).execute()
        events = events_result.get('items', [])
        
        if not events:
            return "No events found for the specified criteria."
        
        # Format response
        if input_data.response_format == 'json':
            return json.dumps(events, indent=2)[:CHARACTER_LIMIT]
        else:
            # Markdown format
            lines = [f"# Calendar Events ({len(events)} found)\n"]
            for event in events:
                lines.append(format_event_markdown(event))
                lines.append("")  # Empty line between events
            
            result = '\n'.join(lines)
            return result[:CHARACTER_LIMIT]
            
    except Exception as e:
        return f"Error listing calendar events: {str(e)}"

@mcp.tool()
async def create_calendar_event(
    input_data: CreateEventInput
) -> str:
    """
    Create a new calendar event.
    
    Creates an event with the specified details. Supports both timed and all-day events.
    Can include attendees and send invitation notifications.
    
    Time format examples:
    - Timed event: "2024-01-15T14:00:00-08:00" (includes timezone)
    - All-day event: "2024-01-15" (date only)
    
    Returns the created event details including its ID.
    """
    try:
        service = get_google_service()
        
        # Build event object
        event = {
            'summary': input_data.summary,
            'description': input_data.description,
            'location': input_data.location,
        }
        
        # Handle datetime vs date
        if 'T' in input_data.start_time:
            event['start'] = {'dateTime': input_data.start_time}
            event['end'] = {'dateTime': input_data.end_time}
        else:
            event['start'] = {'date': input_data.start_time}
            event['end'] = {'date': input_data.end_time}
        
        # Add attendees if provided
        if input_data.attendees:
            event['attendees'] = [{'email': email} for email in input_data.attendees]
        
        # Create the event
        created_event = service.events().insert(
            calendarId=input_data.calendar_id,
            body=event,
            sendNotifications=input_data.send_notifications
        ).execute()
        
        return f"""Event created successfully!

**Event Details:**
- ID: {created_event['id']}
- Title: {created_event['summary']}
- Link: {created_event.get('htmlLink', 'N/A')}

{format_event_markdown(created_event)}"""
        
    except Exception as e:
        return f"Error creating calendar event: {str(e)}"

@mcp.tool()
async def update_calendar_event(
    input_data: UpdateEventInput
) -> str:
    """
    Update an existing calendar event.
    
    Modifies specified fields of an event. Only provided fields will be updated.
    Requires the event ID which can be obtained from list_calendar_events.
    """
    try:
        service = get_google_service()
        
        # Get existing event
        event = service.events().get(
            calendarId=input_data.calendar_id,
            eventId=input_data.event_id
        ).execute()
        
        # Update fields
        if input_data.summary is not None:
            event['summary'] = input_data.summary
        if input_data.description is not None:
            event['description'] = input_data.description
        if input_data.location is not None:
            event['location'] = input_data.location
        
        if input_data.start_time is not None:
            if 'T' in input_data.start_time:
                event['start'] = {'dateTime': input_data.start_time}
            else:
                event['start'] = {'date': input_data.start_time}
        
        if input_data.end_time is not None:
            if 'T' in input_data.end_time:
                event['end'] = {'dateTime': input_data.end_time}
            else:
                event['end'] = {'date': input_data.end_time}
        
        # Update the event
        updated_event = service.events().update(
            calendarId=input_data.calendar_id,
            eventId=input_data.event_id,
            body=event
        ).execute()
        
        return f"""Event updated successfully!

**Updated Event:**
{format_event_markdown(updated_event)}"""
        
    except Exception as e:
        return f"Error updating calendar event: {str(e)}"

@mcp.tool()
async def delete_calendar_event(
    input_data: DeleteEventInput
) -> str:
    """
    Delete a calendar event.
    
    Permanently removes an event from the calendar.
    Can optionally send cancellation notifications to attendees.
    """
    try:
        service = get_google_service()
        
        service.events().delete(
            calendarId=input_data.calendar_id,
            eventId=input_data.event_id,
            sendNotifications=input_data.send_notifications
        ).execute()
        
        return f"Event {input_data.event_id} deleted successfully."
        
    except Exception as e:
        return f"Error deleting calendar event: {str(e)}"

@mcp.tool()
async def check_availability(
    calendar_id: str = "primary",
    time_min: str = None,
    time_max: str = None
) -> str:
    """
    Check calendar availability for scheduling.
    
    Returns free/busy information for the specified time range.
    Useful for finding available time slots for new meetings.
    """
    try:
        service = get_google_service()
        
        if not time_min:
            time_min = datetime.utcnow().isoformat() + 'Z'
        if not time_max:
            time_max = (datetime.utcnow() + timedelta(days=7)).isoformat() + 'Z'
        
        body = {
            "timeMin": time_min,
            "timeMax": time_max,
            "items": [{"id": calendar_id}]
        }
        
        busy_times = service.freebusy().query(body=body).execute()
        calendar_busy = busy_times['calendars'].get(calendar_id, {})
        
        if calendar_busy.get('errors'):
            return f"Error checking availability: {calendar_busy['errors']}"
        
        busy_periods = calendar_busy.get('busy', [])
        
        if not busy_periods:
            return f"Completely available between {time_min} and {time_max}"
        
        lines = ["# Busy Periods:\n"]
        for period in busy_periods:
            lines.append(f"- {period['start']} to {period['end']}")
        
        return '\n'.join(lines)
        
    except Exception as e:
        return f"Error checking availability: {str(e)}"

if __name__ == "__main__":
    # Run the MCP server
    import uvicorn
    uvicorn.run(
        mcp.app,
        host="0.0.0.0",
        port=int(os.getenv('MCP_CALENDAR_PORT', 8002))
    )
```

## Step 4: Create Gmail MCP Server

Create `mcp_gmail_server.py`:

```python
#!/usr/bin/env python3
"""
Gmail MCP Server
Provides email management capabilities via MCP protocol
"""

import os
import asyncio
import json
import base64
from typing import Optional, List, Dict, Any
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

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
    import uvicorn
    uvicorn.run(
        mcp.app,
        host="0.0.0.0",
        port=int(os.getenv('MCP_GMAIL_PORT', 8001))
    )
```

## Step 5: Create the Unified Orchestrator

Create `unified_agent.py`:

```python
#!/usr/bin/env python3
"""
Unified AI Agent Orchestrator
Combines browser-use, Google Calendar, and Gmail capabilities
"""

import os
import asyncio
import json
from typing import Dict, Any, List, Optional
from enum import Enum
import subprocess
import requests
from dataclasses import dataclass

from langchain_community.llms import Ollama
from pydantic import BaseModel, Field

# Tool types
class ToolType(Enum):
    BROWSER = "browser"
    CALENDAR = "calendar"
    EMAIL = "email"
    CHAT = "chat"

# Tool routing configuration
TOOL_ROUTING_PROMPT = """You are an AI assistant with access to multiple tools. Based on the user's request, determine which tool(s) to use.

Available tools:
1. BROWSER - Web browsing, searching, extracting information from websites
2. CALENDAR - View, create, update, delete calendar events, check availability
3. EMAIL - Read, send, search emails, manage labels
4. CHAT - General conversation, answering questions from knowledge

Analyze the user's request and respond with a JSON object:
{
    "primary_tool": "tool_name",
    "secondary_tools": ["tool1", "tool2"],  // optional
    "reasoning": "why these tools were chosen",
    "specific_actions": ["action1", "action2"]  // what to do with each tool
}

User request: {user_input}
"""

@dataclass
class ToolDecision:
    primary_tool: ToolType
    secondary_tools: List[ToolType]
    reasoning: str
    specific_actions: List[str]

class UnifiedAgent:
    def __init__(self, model_name: str = "deepseek-r1:14b"):
        self.model_name = model_name
        self.llm = Ollama(model=model_name)
        
        # MCP server endpoints
        self.calendar_url = f"http://localhost:{os.getenv('MCP_CALENDAR_PORT', 8002)}"
        self.gmail_url = f"http://localhost:{os.getenv('MCP_GMAIL_PORT', 8001)}"
        
        # Start MCP servers in background
        self._start_mcp_servers()
    
    def _start_mcp_servers(self):
        """Start MCP servers as background processes"""
        try:
            # Start Calendar MCP server
            subprocess.Popen(
                ["python", "mcp_calendar_server.py"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            # Start Gmail MCP server
            subprocess.Popen(
                ["python", "mcp_gmail_server.py"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            # Wait for servers to start
            import time
            time.sleep(3)
            
            print("MCP servers started successfully")
        except Exception as e:
            print(f"Error starting MCP servers: {e}")
    
    async def route_request(self, user_input: str) -> ToolDecision:
        """Determine which tool(s) to use for the request"""
        prompt = TOOL_ROUTING_PROMPT.format(user_input=user_input)
        
        response = self.llm.invoke(prompt)
        
        try:
            # Parse JSON response
            decision_data = json.loads(response)
            
            primary = ToolType(decision_data["primary_tool"].lower())
            secondary = [ToolType(t.lower()) for t in decision_data.get("secondary_tools", [])]
            
            return ToolDecision(
                primary_tool=primary,
                secondary_tools=secondary,
                reasoning=decision_data["reasoning"],
                specific_actions=decision_data["specific_actions"]
            )
        except Exception as e:
            # Default to chat if parsing fails
            return ToolDecision(
                primary_tool=ToolType.CHAT,
                secondary_tools=[],
                reasoning="Could not parse tool decision, defaulting to chat",
                specific_actions=["Respond to user query"]
            )
    
    async def execute_browser_task(self, task: str, optimize: bool = False):
        """Execute browser-use task"""
        # This integrates with your existing browser_use_repl.py
        cmd = ["python", "browser_use_repl.py", "--model", self.model_name]
        
        if optimize:
            cmd.append("--optimize")
        
        # Run browser-use with the task
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        output, error = process.communicate(input=task)
        
        if process.returncode == 0:
            return output
        else:
            return f"Browser task failed: {error}"
    
    async def execute_calendar_action(self, action: str, params: Dict[str, Any]):
        """Execute calendar MCP action"""
        endpoint = f"{self.calendar_url}/tools/{action}"
        
        try:
            response = requests.post(
                endpoint,
                json=params,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return f"Calendar action failed: {response.text}"
        except Exception as e:
            return f"Calendar error: {str(e)}"
    
    async def execute_email_action(self, action: str, params: Dict[str, Any]):
        """Execute email MCP action"""
        endpoint = f"{self.gmail_url}/tools/{action}"
        
        try:
            response = requests.post(
                endpoint,
                json=params,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return f"Email action failed: {response.text}"
        except Exception as e:
            return f"Email error: {str(e)}"
    
    async def chat_response(self, user_input: str, context: str = ""):
        """Generate a chat response"""
        prompt = f"""You are a helpful AI assistant. 
        
Context: {context}

User: {user_input}        
Assistant: Respond helpfully and accurately."""
        
        response = self.llm.invoke(prompt)
        return response
    
    async def process_request(self, user_input: str):
        """Main entry point for processing user requests"""
        print(f"\n🤖 Processing: {user_input}\n")
        
        # Route the request
        decision = await self.route_request(user_input)
        print(f"📋 Tool Decision: {decision.primary_tool.value}")
        print(f"   Reasoning: {decision.reasoning}")
        print(f"   Actions: {', '.join(decision.specific_actions)}\n")
        
        results = []
        
        # Execute primary tool
        if decision.primary_tool == ToolType.BROWSER:
            print("🌐 Executing browser task...")
            result = await self.execute_browser_task(user_input, optimize=True)
            results.append(("Browser", result))
        
        elif decision.primary_tool == ToolType.CALENDAR:
            print("📅 Executing calendar action...")
            # Parse specific calendar action from user input
            action_prompt = f"""Given this request: '{user_input}'
            
Determine the calendar action and parameters needed.
Available actions: list_calendar_events, create_calendar_event, update_calendar_event, delete_calendar_event, check_availability

Respond with JSON:
{{
    "action": "action_name",
    "parameters": {{...}}
}}"""
            
            action_response = self.llm.invoke(action_prompt)
            try:
                action_data = json.loads(action_response)
                result = await self.execute_calendar_action(
                    action_data["action"],
                    action_data["parameters"]
                )
                results.append(("Calendar", result))
            except Exception as e:
                results.append(("Calendar", f"Error: {str(e)}"))
        
        elif decision.primary_tool == ToolType.EMAIL:
            print("📧 Executing email action...")
            # Parse specific email action from user input
            action_prompt = f"""Given this request: '{user_input}'
            
Determine the email action and parameters needed.
Available actions: list_emails, read_email, send_email, modify_email_labels, search_emails

Respond with JSON:
{{
    "action": "action_name",
    "parameters": {{...}}
}}"""
            
            action_response = self.llm.invoke(action_prompt)
            try:
                action_data = json.loads(action_response)
                result = await self.execute_email_action(
                    action_data["action"],
                    action_data["parameters"]
                )
                results.append(("Email", result))
            except Exception as e:
                results.append(("Email", f"Error: {str(e)}"))
        
        else:  # CHAT
            print("💬 Generating chat response...")
            result = await self.chat_response(user_input)
            results.append(("Chat", result))
        
        # Execute secondary tools if any
        for tool in decision.secondary_tools:
            print(f"🔄 Executing secondary tool: {tool.value}")
            # Similar logic for secondary tools
            # ... (implement based on tool type)
        
        # Combine and format results
        final_response = self._format_results(results, decision)
        return final_response
    
    def _format_results(self, results: List[tuple], decision: ToolDecision) -> str:
        """Format all results into a cohesive response"""
        if len(results) == 1:
            return results[0][1]
        
        # Combine multiple results
        formatted = "Here's what I found:\n\n"
        for tool_name, result in results:
            formatted += f"**{tool_name} Results:**\n{result}\n\n"
        
        return formatted

class InteractiveAgent:
    """Interactive REPL for the unified agent"""
    
    def __init__(self, model_name: str = "deepseek-r1:14b"):
        self.agent = UnifiedAgent(model_name)
    
    async def run_repl(self):
        """Run interactive REPL"""
        print("=" * 60)
        print("🤖 Unified AI Agent with Browser, Calendar & Email")
        print("=" * 60)
        print("Available capabilities:")
        print("  🌐 Web browsing and automation")
        print("  📅 Google Calendar management")
        print("  📧 Gmail email operations")
        print("  💬 General chat and Q&A")
        print("-" * 60)
        print("Examples:")
        print("  - 'Get the latest news about AI'")
        print("  - 'Schedule a meeting tomorrow at 2pm'")
        print("  - 'Check my unread emails'")
        print("  - 'Find flight prices from NYC to London'")
        print("-" * 60)
        print("Type 'exit' to quit\n")
        
        while True:
            try:
                user_input = input("You: ").strip()
                
                if user_input.lower() in ['exit', 'quit', 'q']:
                    print("👋 Goodbye!")
                    break
                
                if not user_input:
                    continue
                
                # Process request
                response = await self.agent.process_request(user_input)
                
                print("\n" + "=" * 60)
                print("Assistant:", response)
                print("=" * 60 + "\n")
                
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {str(e)}")

# Main entry point
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Unified AI Agent")
    parser.add_argument(
        "--model",
        default="deepseek-r1:14b",
        help="LLM model to use"
    )
    args = parser.parse_args()
    
    # Run the interactive agent
    agent = InteractiveAgent(model_name=args.model)
    asyncio.run(agent.run_repl())
# Additional Examples and Features

## Example Interactions

```
You: Check my calendar for tomorrow and find any unread emails about the meeting
Assistant: I'll check both your calendar and emails for you.

📅 Calendar (Tomorrow):
- **Team Standup** 9:00 AM - 9:30 AM
- **Product Review Meeting** 2:00 PM - 3:00 PM (Conference Room A)
- **1:1 with Sarah** 4:00 PM - 4:30 PM

📧 Unread Emails about meetings:
1. **Subject:** Re: Product Review Meeting Agenda
   **From:** john@company.com
   **Preview:** Attached the updated agenda for tomorrow's review...
   
2. **Subject:** Team Standup - New Format
   **From:** sarah@company.com
   **Preview:** Starting tomorrow, we'll use the new standup format...

You: Book a meeting with Alex next Tuesday at 3pm for 1 hour about the Q2 roadmap
Assistant: I'll create that meeting for you.

📅 Event created successfully!
- **Title:** Q2 Roadmap Discussion with Alex
- **Date:** Next Tuesday, 3:00 PM - 4:00 PM
- **Attendees:** alex@company.com
- **Description:** Discussion about Q2 roadmap planning

Invitation has been sent to Alex.

You: Find the cheapest flights from San Francisco to Tokyo next month
Assistant: I'll search for flight prices for you.

🌐 Searching for flights from SFO to Tokyo (NRT/HND) in February 2024...

Found the following options:
1. **United Airlines** - $847 roundtrip
   Depart: Feb 10, Return: Feb 17
   
2. **ANA** - $923 roundtrip
   Depart: Feb 15, Return: Feb 22
   
3. **JAL** - $1,056 roundtrip
   Depart: Feb 8, Return: Feb 15

The cheapest option is United Airlines at $847 for Feb 10-17.
```

## Troubleshooting

### Common Issues and Solutions

1. **Authentication Errors**
   ```bash
   # Delete token files and re-authenticate
   rm token.json gmail_token.pickle
   python -c "from mcp_calendar_server import get_google_service; get_google_service()"
   ```

2. **MCP Server Connection Issues**
   ```bash
   # Check if servers are running
   ps aux | grep mcp_
   
   # Test server directly
   curl http://localhost:8001/health
   curl http://localhost:8002/health
   ```

3. **Permission Errors**
   - Ensure you've enabled Gmail API and Calendar API in Google Cloud Console
   - Check that OAuth scopes include necessary permissions
   - Verify credentials.json is valid

4. **Rate Limiting**
   - Google APIs have quotas - implement exponential backoff
   - Add caching for frequently accessed data
   - Use batch requests when possible

## Advanced Features

### 1. Adding More MCP Servers

To add additional MCP servers (e.g., Slack, Notion, GitHub):

```python
# Example: Adding Slack MCP server
class SlackMCPServer:
    def __init__(self):
        self.mcp = FastMCP("slack-server")
        
    @mcp.tool()
    async def send_slack_message(
        self,
        channel: str,
        message: str,
        thread_ts: Optional[str] = None
    ) -> str:
        # Implementation here
        pass
```

### 2. Context Persistence

Add conversation memory:

```python
class MemoryManager:
    def __init__(self, max_history: int = 10):
        self.conversation_history = []
        self.max_history = max_history
    
    def add_interaction(self, user_input: str, response: str):
        self.conversation_history.append({
            "user": user_input,
            "assistant": response,
            "timestamp": datetime.now()
        })
        
        # Keep only recent history
        if len(self.conversation_history) > self.max_history:
            self.conversation_history.pop(0)
    
    def get_context(self) -> str:
        return "\n".join([
            f"User: {item['user']}\nAssistant: {item['assistant']}"
            for item in self.conversation_history[-3:]  # Last 3 interactions
        ])
```

### 3. Custom Tool Chains

Create complex multi-tool workflows:

```python
async def research_and_schedule_workflow(self, topic: str):
    """Research a topic online and schedule a meeting about it"""
    
    # Step 1: Research the topic
    research_results = await self.execute_browser_task(
        f"research latest developments in {topic}"
    )
    
    # Step 2: Summarize findings
    summary = await self.chat_response(
        f"Summarize these findings: {research_results[:1000]}"
    )
    
    # Step 3: Check calendar availability
    availability = await self.execute_calendar_action(
        "check_availability",
        {"time_min": "tomorrow", "time_max": "next week"}
    )
    
    # Step 4: Schedule meeting
    meeting = await self.execute_calendar_action(
        "create_calendar_event",
        {
            "summary": f"{topic} Discussion",
            "description": f"Agenda:\n{summary}",
            "start_time": "2024-02-01T14:00:00",
            "end_time": "2024-02-01T15:00:00"
        }
    )
    
    # Step 5: Send email with research
    await self.execute_email_action(
        "send_email",
        {
            "to": ["team@company.com"],
            "subject": f"Research on {topic}",
            "body": f"Hi team,\n\n{summary}\n\nMeeting scheduled: {meeting}"
        }
    )
```

### 4. Parallel Tool Execution

Execute multiple tools simultaneously:

```python
import asyncio

async def parallel_tool_execution(self, user_input: str):
    """Execute multiple tools in parallel for faster results"""
    
    tasks = [
        self.execute_browser_task("latest AI news"),
        self.execute_calendar_action("list_calendar_events", {"max_results": 5}),
        self.execute_email_action("search_emails", {"query": "is:unread"})
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Process results
    browser_result, calendar_result, email_result = results
    
    # Combine into unified response
    return self._combine_results(browser_result, calendar_result, email_result)
```

## Testing Your Integration

### Unit Tests

```python
import pytest
import asyncio
from unittest.mock import Mock, patch

class TestUnifiedAgent:
    @pytest.mark.asyncio
    async def test_route_request_browser(self):
        agent = UnifiedAgent()
        decision = await agent.route_request("search for Python tutorials")
        assert decision.primary_tool == ToolType.BROWSER
    
    @pytest.mark.asyncio
    async def test_route_request_calendar(self):
        agent = UnifiedAgent()
        decision = await agent.route_request("schedule a meeting tomorrow")
        assert decision.primary_tool == ToolType.CALENDAR
    
    @pytest.mark.asyncio
    async def test_route_request_email(self):
        agent = UnifiedAgent()
        decision = await agent.route_request("check my unread emails")
        assert decision.primary_tool == ToolType.EMAIL
```

### Integration Tests

```python
async def test_full_workflow():
    """Test complete workflow with all tools"""
    agent = UnifiedAgent()
    
    # Test multi-tool request
    result = await agent.process_request(
        "Check tomorrow's weather, my calendar, and send John an email about lunch"
    )
    
    assert "weather" in result.lower()
    assert "calendar" in result.lower()
    assert "email" in result.lower()
```

## Security Considerations

### 1. Credential Management
- Never commit credentials.json or token files to version control
- Use environment variables or secure vaults for production
- Implement proper OAuth2 refresh token handling

### 2. Input Validation
- Sanitize all user inputs before passing to tools
- Implement rate limiting per user
- Validate email addresses and calendar IDs

### 3. Access Control
```python
class AccessControl:
    def __init__(self):
        self.allowed_domains = ["company.com"]
        self.blocked_senders = []
    
    def can_send_email(self, recipients: List[str]) -> bool:
        # Implement domain restrictions
        for email in recipients:
            domain = email.split('@')[1]
            if domain not in self.allowed_domains:
                return False
        return True
    
    def can_access_calendar(self, calendar_id: str) -> bool:
        # Implement calendar access restrictions
        return calendar_id in ["primary", "team@company.com"]
```

## Performance Optimization

### 1. Caching
```python
from functools import lru_cache
import hashlib

class CacheManager:
    def __init__(self, ttl: int = 300):  # 5 minute TTL
        self.cache = {}
        self.ttl = ttl
    
    def get_cache_key(self, tool: str, params: dict) -> str:
        param_str = json.dumps(params, sort_keys=True)
        return hashlib.md5(f"{tool}:{param_str}".encode()).hexdigest()
    
    async def get_or_compute(self, tool: str, params: dict, compute_func):
        cache_key = self.get_cache_key(tool, params)
        
        if cache_key in self.cache:
            entry = self.cache[cache_key]
            if time.time() - entry['timestamp'] < self.ttl:
                return entry['data']
        
        # Compute and cache
        result = await compute_func()
        self.cache[cache_key] = {
            'data': result,
            'timestamp': time.time()
        }
        return result
```

### 2. Connection Pooling
```python
import aiohttp

class ConnectionPool:
    def __init__(self):
        self.session = None
    
    async def get_session(self):
        if not self.session:
            self.session = aiohttp.ClientSession(
                connector=aiohttp.TCPConnector(
                    limit=100,
                    limit_per_host=30
                )
            )
        return self.session
    
    async def close(self):
        if self.session:
            await self.session.close()
```

## Deployment

### Docker Setup

Create `Dockerfile`:

```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1

CMD ["./start_unified_agent.sh"]
```

### Docker Compose

```yaml
version: '3.8'

services:
  unified-agent:
    build: .
    environment:
      - GOOGLE_CREDENTIALS_PATH=/app/credentials.json
      - MCP_CALENDAR_PORT=8002
      - MCP_GMAIL_PORT=8001
    volumes:
      - ./credentials.json:/app/credentials.json:ro
      - ./tokens:/app/tokens
    ports:
      - "8001:8001"
      - "8002:8002"
    restart: unless-stopped

  ollama:
    image: ollama/ollama
    volumes:
      - ollama_data:/root/.ollama
    ports:
      - "11434:11434"
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

volumes:
  ollama_data:
```

## Final Notes

This integration creates a powerful unified system where your LLM can:
- Naturally chat with users
- Browse the web using browser-use
- Manage Google Calendar events
- Handle Gmail operations
- Intelligently route requests to appropriate tools
- Combine multiple tools for complex tasks

The system is extensible - you can easily add more MCP servers for other services (Slack, Notion, GitHub, etc.) following the same pattern.

Remember to:
1. Keep your credentials secure
2. Test thoroughly before production use
3. Monitor API quotas and rate limits
4. Add proper error handling and logging
5. Consider implementing user authentication for multi-user scenarios
