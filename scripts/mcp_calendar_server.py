#!/usr/bin/env python3
"""
Google Calendar MCP Server
Provides calendar management capabilities via MCP protocol
"""

import os
import sys
import asyncio
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pathlib import Path
from contextlib import redirect_stdout, redirect_stderr
import io

from fastmcp import FastMCP
from pydantic import BaseModel, Field
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
			# Suppress browser output to prevent STDIO interference
			with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
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

	if event.get('id'):
		lines.append(f"- Event ID: {event['id']}")

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
	mcp.run()
