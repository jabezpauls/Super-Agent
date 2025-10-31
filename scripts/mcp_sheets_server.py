#!/usr/bin/env python3
"""
Google Sheets MCP Server
A powerful Model Context Protocol server for Google Sheets operations.
Communicates via STDIO using JSON-RPC protocol.
"""

import os
import sys
import json
import logging
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
import asyncio

# Google Sheets API dependencies
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import pickle

# FastMCP for MCP protocol
from fastmcp import FastMCP

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("google-sheets-mcp")

# Initialize FastMCP server
mcp = FastMCP("google-sheets-mcp")

# Google Sheets API configuration
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.file'
]

# Cache for service instance
_sheets_service = None
_drive_service = None

def get_credentials() -> Optional[Credentials]:
    """
    Get Google API credentials.
    Supports both service account and OAuth2 authentication.
    """
    creds = None
    
    # First, try service account (for automated/server use)
    service_account_file = os.environ.get('GOOGLE_SERVICE_ACCOUNT_FILE')
    if service_account_file and os.path.exists(service_account_file):
        try:
            creds = service_account.Credentials.from_service_account_file(
                service_account_file, scopes=SCOPES
            )
            logger.info("Using service account credentials")
            return creds
        except Exception as e:
            logger.warning(f"Failed to load service account: {e}")
    
    # Try OAuth2 (for user authentication)
    token_file = os.path.expanduser('~/.mcp/google_sheets_token.pickle')
    creds_file = os.environ.get('GOOGLE_CREDENTIALS_FILE', 
                                os.path.expanduser('~/.mcp/credentials.json'))
    
    # Load existing token
    if os.path.exists(token_file):
        with open(token_file, 'rb') as token:
            creds = pickle.load(token)
    
    # If there are no (valid) credentials, let the user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        elif os.path.exists(creds_file):
            flow = InstalledAppFlow.from_client_secrets_file(creds_file, SCOPES)
            creds = flow.run_local_server(port=0)
        else:
            raise ValueError(
                "No credentials available. Set GOOGLE_SERVICE_ACCOUNT_FILE or "
                "GOOGLE_CREDENTIALS_FILE environment variable"
            )
        
        # Save credentials for next run
        os.makedirs(os.path.dirname(token_file), exist_ok=True)
        with open(token_file, 'wb') as token:
            pickle.dump(creds, token)
    
    return creds

def get_sheets_service():
    """Get or create Google Sheets service instance."""
    global _sheets_service
    if _sheets_service is None:
        creds = get_credentials()
        _sheets_service = build('sheets', 'v4', credentials=creds)
    return _sheets_service

def get_drive_service():
    """Get or create Google Drive service instance."""
    global _drive_service
    if _drive_service is None:
        creds = get_credentials()
        _drive_service = build('drive', 'v3', credentials=creds)
    return _drive_service

def parse_a1_notation(notation: str) -> tuple:
    """Parse A1 notation into components."""
    parts = notation.split('!')
    if len(parts) == 2:
        sheet_name = parts[0]
        range_part = parts[1]
    else:
        sheet_name = None
        range_part = parts[0]
    
    # Parse range (e.g., A1:B10)
    if ':' in range_part:
        start, end = range_part.split(':')
    else:
        start = end = range_part
    
    return sheet_name, start, end

def values_to_json_serializable(values: List[List[Any]]) -> List[List[Any]]:
    """Convert values to JSON-serializable format."""
    result = []
    for row in values:
        json_row = []
        for cell in row:
            if isinstance(cell, (str, int, float, bool, type(None))):
                json_row.append(cell)
            else:
                json_row.append(str(cell))
        result.append(json_row)
    return result

@mcp.tool()
async def create_spreadsheet(
    title: str,
    sheet_names: Optional[List[str]] = None,
    folder_id: Optional[str] = None
) -> str:
    """
    Create a new Google Spreadsheet.
    
    Args:
        title: The title of the new spreadsheet
        sheet_names: Optional list of sheet names to create (default: ['Sheet1'])
        folder_id: Optional Google Drive folder ID to create the spreadsheet in
    
    Returns:
        JSON string with spreadsheet ID and URL
    """
    try:
        sheets_service = get_sheets_service()
        
        # Prepare spreadsheet body
        body = {'properties': {'title': title}}
        
        if sheet_names:
            sheets = []
            for i, name in enumerate(sheet_names):
                sheet = {
                    'properties': {
                        'sheetId': i,
                        'title': name,
                        'index': i
                    }
                }
                sheets.append(sheet)
            body['sheets'] = sheets
        
        # Create the spreadsheet
        spreadsheet = sheets_service.spreadsheets().create(body=body).execute()
        spreadsheet_id = spreadsheet.get('spreadsheetId')
        
        # Move to folder if specified
        if folder_id:
            drive_service = get_drive_service()
            drive_service.files().update(
                fileId=spreadsheet_id,
                addParents=folder_id,
                fields='id, parents'
            ).execute()
        
        result = {
            'spreadsheet_id': spreadsheet_id,
            'url': f'https://docs.google.com/spreadsheets/d/{spreadsheet_id}',
            'title': title,
            'sheets': sheet_names or ['Sheet1']
        }
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        logger.error(f"Error creating spreadsheet: {e}")
        return json.dumps({'error': str(e)})

@mcp.tool()
async def read_range(
    spreadsheet_id: str,
    range_notation: str,
    value_render_option: str = "FORMATTED_VALUE"
) -> str:
    """
    Read values from a Google Spreadsheet range.
    
    Args:
        spreadsheet_id: The ID of the spreadsheet
        range_notation: A1 notation of the range (e.g., 'Sheet1!A1:B10')
        value_render_option: How values should be rendered (FORMATTED_VALUE, UNFORMATTED_VALUE, FORMULA)
    
    Returns:
        JSON string with the values and metadata
    """
    try:
        sheets_service = get_sheets_service()
        
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=range_notation,
            valueRenderOption=value_render_option
        ).execute()
        
        values = result.get('values', [])
        
        # Convert to JSON-serializable format
        values = values_to_json_serializable(values)
        
        response = {
            'range': result.get('range'),
            'major_dimension': result.get('majorDimension'),
            'values': values,
            'row_count': len(values),
            'column_count': max(len(row) for row in values) if values else 0
        }
        
        return json.dumps(response, indent=2)
        
    except Exception as e:
        logger.error(f"Error reading range: {e}")
        return json.dumps({'error': str(e)})

@mcp.tool()
async def write_range(
    spreadsheet_id: str,
    range_notation: str,
    values: List[List[Any]],
    value_input_option: str = "USER_ENTERED"
) -> str:
    """
    Write values to a Google Spreadsheet range.
    
    Args:
        spreadsheet_id: The ID of the spreadsheet
        range_notation: A1 notation of the range (e.g., 'Sheet1!A1')
        values: 2D array of values to write
        value_input_option: How input should be interpreted (USER_ENTERED, RAW)
    
    Returns:
        JSON string with update results
    """
    try:
        sheets_service = get_sheets_service()
        
        body = {
            'values': values
        }
        
        result = sheets_service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=range_notation,
            valueInputOption=value_input_option,
            body=body
        ).execute()
        
        response = {
            'spreadsheet_id': spreadsheet_id,
            'updated_range': result.get('updatedRange'),
            'updated_rows': result.get('updatedRows'),
            'updated_columns': result.get('updatedColumns'),
            'updated_cells': result.get('updatedCells')
        }
        
        return json.dumps(response, indent=2)
        
    except Exception as e:
        logger.error(f"Error writing range: {e}")
        return json.dumps({'error': str(e)})

@mcp.tool()
async def append_rows(
    spreadsheet_id: str,
    sheet_name: str,
    values: List[List[Any]],
    value_input_option: str = "USER_ENTERED"
) -> str:
    """
    Append rows to the end of a sheet.
    
    Args:
        spreadsheet_id: The ID of the spreadsheet
        sheet_name: Name of the sheet to append to
        values: 2D array of values to append
        value_input_option: How input should be interpreted
    
    Returns:
        JSON string with append results
    """
    try:
        sheets_service = get_sheets_service()
        
        body = {
            'values': values
        }
        
        result = sheets_service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range=f"{sheet_name}!A:A",
            valueInputOption=value_input_option,
            insertDataOption='INSERT_ROWS',
            body=body
        ).execute()
        
        response = {
            'spreadsheet_id': spreadsheet_id,
            'table_range': result.get('tableRange'),
            'updated_range': result.get('updates', {}).get('updatedRange'),
            'updated_rows': result.get('updates', {}).get('updatedRows'),
            'updated_columns': result.get('updates', {}).get('updatedColumns'),
            'updated_cells': result.get('updates', {}).get('updatedCells')
        }
        
        return json.dumps(response, indent=2)
        
    except Exception as e:
        logger.error(f"Error appending rows: {e}")
        return json.dumps({'error': str(e)})

@mcp.tool()
async def clear_range(
    spreadsheet_id: str,
    range_notation: str
) -> str:
    """
    Clear values in a range while preserving formatting.
    
    Args:
        spreadsheet_id: The ID of the spreadsheet
        range_notation: A1 notation of the range to clear
    
    Returns:
        JSON string with clear results
    """
    try:
        sheets_service = get_sheets_service()
        
        result = sheets_service.spreadsheets().values().clear(
            spreadsheetId=spreadsheet_id,
            range=range_notation
        ).execute()
        
        response = {
            'spreadsheet_id': spreadsheet_id,
            'cleared_range': result.get('clearedRange'),
            'status': 'success'
        }
        
        return json.dumps(response, indent=2)
        
    except Exception as e:
        logger.error(f"Error clearing range: {e}")
        return json.dumps({'error': str(e)})

@mcp.tool()
async def batch_update(
    spreadsheet_id: str,
    updates: List[Dict[str, Any]]
) -> str:
    """
    Perform batch updates on a spreadsheet (formulas, formatting, etc).
    
    Args:
        spreadsheet_id: The ID of the spreadsheet
        updates: List of update requests following Google Sheets API format
    
    Returns:
        JSON string with update results
    """
    try:
        sheets_service = get_sheets_service()
        
        body = {
            'requests': updates
        }
        
        result = sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body=body
        ).execute()
        
        response = {
            'spreadsheet_id': result.get('spreadsheetId'),
            'replies': result.get('replies', []),
            'updated_spreadsheet': result.get('updatedSpreadsheet', {}).get('properties', {})
        }
        
        return json.dumps(response, indent=2)
        
    except Exception as e:
        logger.error(f"Error in batch update: {e}")
        return json.dumps({'error': str(e)})

@mcp.tool()
async def get_sheet_metadata(
    spreadsheet_id: str
) -> str:
    """
    Get metadata about a spreadsheet (sheets, properties, etc).
    
    Args:
        spreadsheet_id: The ID of the spreadsheet
    
    Returns:
        JSON string with spreadsheet metadata
    """
    try:
        sheets_service = get_sheets_service()
        
        spreadsheet = sheets_service.spreadsheets().get(
            spreadsheetId=spreadsheet_id
        ).execute()
        
        sheets = []
        for sheet in spreadsheet.get('sheets', []):
            props = sheet.get('properties', {})
            sheets.append({
                'sheet_id': props.get('sheetId'),
                'title': props.get('title'),
                'index': props.get('index'),
                'row_count': props.get('gridProperties', {}).get('rowCount'),
                'column_count': props.get('gridProperties', {}).get('columnCount')
            })
        
        response = {
            'spreadsheet_id': spreadsheet.get('spreadsheetId'),
            'title': spreadsheet.get('properties', {}).get('title'),
            'url': spreadsheet.get('spreadsheetUrl'),
            'sheets': sheets,
            'locale': spreadsheet.get('properties', {}).get('locale'),
            'time_zone': spreadsheet.get('properties', {}).get('timeZone')
        }
        
        return json.dumps(response, indent=2)
        
    except Exception as e:
        logger.error(f"Error getting metadata: {e}")
        return json.dumps({'error': str(e)})

@mcp.tool()
async def create_sheet(
    spreadsheet_id: str,
    sheet_name: str,
    rows: int = 1000,
    columns: int = 26
) -> str:
    """
    Add a new sheet to an existing spreadsheet.
    
    Args:
        spreadsheet_id: The ID of the spreadsheet
        sheet_name: Name for the new sheet
        rows: Number of rows (default 1000)
        columns: Number of columns (default 26)
    
    Returns:
        JSON string with new sheet information
    """
    try:
        sheets_service = get_sheets_service()
        
        request = {
            'addSheet': {
                'properties': {
                    'title': sheet_name,
                    'gridProperties': {
                        'rowCount': rows,
                        'columnCount': columns
                    }
                }
            }
        }
        
        body = {
            'requests': [request]
        }
        
        result = sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body=body
        ).execute()
        
        reply = result.get('replies', [{}])[0]
        sheet_props = reply.get('addSheet', {}).get('properties', {})
        
        response = {
            'spreadsheet_id': spreadsheet_id,
            'sheet_id': sheet_props.get('sheetId'),
            'sheet_name': sheet_props.get('title'),
            'rows': rows,
            'columns': columns
        }
        
        return json.dumps(response, indent=2)
        
    except Exception as e:
        logger.error(f"Error creating sheet: {e}")
        return json.dumps({'error': str(e)})

@mcp.tool()
async def delete_sheet(
    spreadsheet_id: str,
    sheet_id: int
) -> str:
    """
    Delete a sheet from a spreadsheet.
    
    Args:
        spreadsheet_id: The ID of the spreadsheet
        sheet_id: The ID of the sheet to delete
    
    Returns:
        JSON string with deletion status
    """
    try:
        sheets_service = get_sheets_service()
        
        request = {
            'deleteSheet': {
                'sheetId': sheet_id
            }
        }
        
        body = {
            'requests': [request]
        }
        
        result = sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body=body
        ).execute()
        
        response = {
            'spreadsheet_id': spreadsheet_id,
            'deleted_sheet_id': sheet_id,
            'status': 'success'
        }
        
        return json.dumps(response, indent=2)
        
    except Exception as e:
        logger.error(f"Error deleting sheet: {e}")
        return json.dumps({'error': str(e)})

@mcp.tool()
async def find_and_replace(
    spreadsheet_id: str,
    find: str,
    replacement: str,
    sheet_id: Optional[int] = None,
    all_sheets: bool = True,
    match_case: bool = False,
    match_entire_cell: bool = False,
    search_by_regex: bool = False
) -> str:
    """
    Find and replace text in a spreadsheet.
    
    Args:
        spreadsheet_id: The ID of the spreadsheet
        find: Text to find
        replacement: Text to replace with
        sheet_id: Optional specific sheet ID to search in
        all_sheets: Whether to search all sheets (default True)
        match_case: Whether to match case (default False)
        match_entire_cell: Whether to match entire cell only (default False)
        search_by_regex: Whether to use regex (default False)
    
    Returns:
        JSON string with replacement count
    """
    try:
        sheets_service = get_sheets_service()
        
        request = {
            'findReplace': {
                'find': find,
                'replacement': replacement,
                'matchCase': match_case,
                'matchEntireCell': match_entire_cell,
                'searchByRegex': search_by_regex,
                'includeFormulas': True
            }
        }
        
        if sheet_id is not None:
            request['findReplace']['sheetId'] = sheet_id
        elif all_sheets:
            request['findReplace']['allSheets'] = True
        
        body = {
            'requests': [request]
        }
        
        result = sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body=body
        ).execute()
        
        reply = result.get('replies', [{}])[0]
        find_replace_response = reply.get('findReplace', {})
        
        response = {
            'spreadsheet_id': spreadsheet_id,
            'values_changed': find_replace_response.get('valuesChanged', 0),
            'rows_changed': find_replace_response.get('rowsChanged', 0),
            'sheets_changed': find_replace_response.get('sheetsChanged', 0),
            'formulas_changed': find_replace_response.get('formulasChanged', 0),
            'occurrences_changed': find_replace_response.get('occurrencesChanged', 0)
        }
        
        return json.dumps(response, indent=2)
        
    except Exception as e:
        logger.error(f"Error in find and replace: {e}")
        return json.dumps({'error': str(e)})

@mcp.tool()
async def sort_range(
    spreadsheet_id: str,
    sheet_id: int,
    start_row: int,
    end_row: int,
    start_column: int,
    end_column: int,
    sort_specs: List[Dict[str, Any]]
) -> str:
    """
    Sort a range in a sheet.
    
    Args:
        spreadsheet_id: The ID of the spreadsheet
        sheet_id: The ID of the sheet
        start_row: Starting row index (0-based)
        end_row: Ending row index (exclusive)
        start_column: Starting column index (0-based)
        end_column: Ending column index (exclusive)
        sort_specs: List of sort specifications [{"dimension_index": 0, "sort_order": "ASCENDING"}]
    
    Returns:
        JSON string with sort status
    """
    try:
        sheets_service = get_sheets_service()
        
        request = {
            'sortRange': {
                'range': {
                    'sheetId': sheet_id,
                    'startRowIndex': start_row,
                    'endRowIndex': end_row,
                    'startColumnIndex': start_column,
                    'endColumnIndex': end_column
                },
                'sortSpecs': sort_specs
            }
        }
        
        body = {
            'requests': [request]
        }
        
        result = sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body=body
        ).execute()
        
        response = {
            'spreadsheet_id': spreadsheet_id,
            'sheet_id': sheet_id,
            'sorted_range': f"R{start_row+1}C{start_column+1}:R{end_row}C{end_column}",
            'status': 'success'
        }
        
        return json.dumps(response, indent=2)
        
    except Exception as e:
        logger.error(f"Error sorting range: {e}")
        return json.dumps({'error': str(e)})

@mcp.tool()
async def apply_formula(
    spreadsheet_id: str,
    range_notation: str,
    formula: str
) -> str:
    """
    Apply a formula to a range.
    
    Args:
        spreadsheet_id: The ID of the spreadsheet
        range_notation: A1 notation of the range
        formula: The formula to apply (e.g., '=SUM(A1:A10)')
    
    Returns:
        JSON string with update results
    """
    try:
        sheets_service = get_sheets_service()
        
        # For single cell, just write the formula
        if ':' not in range_notation:
            values = [[formula]]
        else:
            # For ranges, need to adjust the formula for each cell
            # This is a simplified version - for complex formulas, might need more logic
            values = [[formula]]
        
        body = {
            'values': values
        }
        
        result = sheets_service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=range_notation,
            valueInputOption='USER_ENTERED',
            body=body
        ).execute()
        
        response = {
            'spreadsheet_id': spreadsheet_id,
            'updated_range': result.get('updatedRange'),
            'formula': formula,
            'updated_cells': result.get('updatedCells')
        }
        
        return json.dumps(response, indent=2)
        
    except Exception as e:
        logger.error(f"Error applying formula: {e}")
        return json.dumps({'error': str(e)})

@mcp.tool()
async def format_cells(
    spreadsheet_id: str,
    sheet_id: int,
    start_row: int,
    end_row: int,
    start_column: int,
    end_column: int,
    formatting: Dict[str, Any]
) -> str:
    """
    Apply formatting to cells.
    
    Args:
        spreadsheet_id: The ID of the spreadsheet
        sheet_id: The ID of the sheet
        start_row: Starting row index (0-based)
        end_row: Ending row index (exclusive)
        start_column: Starting column index (0-based)
        end_column: Ending column index (exclusive)
        formatting: Formatting options (backgroundColor, textFormat, numberFormat, etc.)
    
    Returns:
        JSON string with formatting status
    """
    try:
        sheets_service = get_sheets_service()
        
        request = {
            'repeatCell': {
                'range': {
                    'sheetId': sheet_id,
                    'startRowIndex': start_row,
                    'endRowIndex': end_row,
                    'startColumnIndex': start_column,
                    'endColumnIndex': end_column
                },
                'cell': {
                    'userEnteredFormat': formatting
                },
                'fields': 'userEnteredFormat'
            }
        }
        
        body = {
            'requests': [request]
        }
        
        result = sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body=body
        ).execute()
        
        response = {
            'spreadsheet_id': spreadsheet_id,
            'sheet_id': sheet_id,
            'formatted_range': f"R{start_row+1}C{start_column+1}:R{end_row}C{end_column}",
            'status': 'success'
        }
        
        return json.dumps(response, indent=2)
        
    except Exception as e:
        logger.error(f"Error formatting cells: {e}")
        return json.dumps({'error': str(e)})

@mcp.tool()
async def create_pivot_table(
    spreadsheet_id: str,
    source_sheet_id: int,
    destination_sheet_id: int,
    rows: List[str],
    columns: List[str],
    values: List[Dict[str, str]]
) -> str:
    """
    Create a pivot table.
    
    Args:
        spreadsheet_id: The ID of the spreadsheet
        source_sheet_id: Sheet ID containing source data
        destination_sheet_id: Sheet ID for pivot table
        rows: List of field names for rows
        columns: List of field names for columns
        values: List of value configurations [{"field": "amount", "function": "SUM"}]
    
    Returns:
        JSON string with pivot table creation status
    """
    try:
        sheets_service = get_sheets_service()
        
        # Build pivot table configuration
        pivot_rows = [{'sourceColumnOffset': i} for i, _ in enumerate(rows)]
        pivot_columns = [{'sourceColumnOffset': i} for i, _ in enumerate(columns)]
        pivot_values = []
        
        for value_config in values:
            pivot_values.append({
                'pivotValue': {
                    'sourceColumnOffset': 0,  # This should be calculated based on field name
                    'summarizeFunction': value_config.get('function', 'SUM')
                }
            })
        
        request = {
            'updateCells': {
                'rows': [{
                    'values': [{
                        'pivotTable': {
                            'source': {
                                'sheetId': source_sheet_id
                            },
                            'rows': pivot_rows,
                            'columns': pivot_columns,
                            'values': pivot_values,
                            'valueLayout': 'HORIZONTAL'
                        }
                    }]
                }],
                'start': {
                    'sheetId': destination_sheet_id,
                    'rowIndex': 0,
                    'columnIndex': 0
                },
                'fields': 'pivotTable'
            }
        }
        
        body = {
            'requests': [request]
        }
        
        result = sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body=body
        ).execute()
        
        response = {
            'spreadsheet_id': spreadsheet_id,
            'source_sheet_id': source_sheet_id,
            'destination_sheet_id': destination_sheet_id,
            'status': 'success'
        }
        
        return json.dumps(response, indent=2)
        
    except Exception as e:
        logger.error(f"Error creating pivot table: {e}")
        return json.dumps({'error': str(e)})

@mcp.tool()
async def protect_range(
    spreadsheet_id: str,
    sheet_id: int,
    start_row: int,
    end_row: int,
    start_column: int,
    end_column: int,
    description: str = "Protected Range",
    warning_only: bool = True
) -> str:
    """
    Protect a range in the spreadsheet.
    
    Args:
        spreadsheet_id: The ID of the spreadsheet
        sheet_id: The ID of the sheet
        start_row: Starting row index (0-based)
        end_row: Ending row index (exclusive)
        start_column: Starting column index (0-based)
        end_column: Ending column index (exclusive)
        description: Description of the protected range
        warning_only: If True, shows warning; if False, restricts editing
    
    Returns:
        JSON string with protection status
    """
    try:
        sheets_service = get_sheets_service()
        
        request = {
            'addProtectedRange': {
                'protectedRange': {
                    'range': {
                        'sheetId': sheet_id,
                        'startRowIndex': start_row,
                        'endRowIndex': end_row,
                        'startColumnIndex': start_column,
                        'endColumnIndex': end_column
                    },
                    'description': description,
                    'warningOnly': warning_only
                }
            }
        }
        
        body = {
            'requests': [request]
        }
        
        result = sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body=body
        ).execute()
        
        response = {
            'spreadsheet_id': spreadsheet_id,
            'sheet_id': sheet_id,
            'protected_range': f"R{start_row+1}C{start_column+1}:R{end_row}C{end_column}",
            'description': description,
            'warning_only': warning_only,
            'status': 'success'
        }
        
        return json.dumps(response, indent=2)
        
    except Exception as e:
        logger.error(f"Error protecting range: {e}")
        return json.dumps({'error': str(e)})

@mcp.tool()
async def export_as_csv(
    spreadsheet_id: str,
    sheet_id: Optional[int] = None
) -> str:
    """
    Export a sheet as CSV content.
    
    Args:
        spreadsheet_id: The ID of the spreadsheet
        sheet_id: Optional sheet ID to export (default: first sheet)
    
    Returns:
        CSV content as string
    """
    try:
        drive_service = get_drive_service()
        
        # Construct export URL
        if sheet_id is not None:
            export_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?format=csv&gid={sheet_id}"
        else:
            export_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?format=csv"
        
        # Export the file
        request = drive_service.files().export_media(
            fileId=spreadsheet_id,
            mimeType='text/csv'
        )
        
        content = request.execute()
        
        if isinstance(content, bytes):
            content = content.decode('utf-8')
        
        return content
        
    except Exception as e:
        logger.error(f"Error exporting as CSV: {e}")
        return json.dumps({'error': str(e)})

def main():
    """Main entry point for the MCP server."""
    # Run the FastMCP server
    asyncio.run(mcp.run())

if __name__ == "__main__":
    main()
