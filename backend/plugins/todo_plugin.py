"""
TodoPlugin - Manages todo list
"""

import os
import json
import time
import logging
import re
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from dateutil import parser as date_parser
from difflib import SequenceMatcher
from mcp.types import Tool, Resource
from mcp_protocol import MCPServer, create_tool, create_resource
from .base import Plugin
from .utils import call_llm_for_json

logger = logging.getLogger(__name__)


class TodoPlugin(Plugin, MCPServer):
    """Plugin for managing todos - implements MCP Server"""
    
    def __init__(self, todos_file: str = "data/todos.json", anthropic_api_key: str = None):
        self.todos_file = todos_file
        self.anthropic_api_key = anthropic_api_key
        os.makedirs(os.path.dirname(todos_file), exist_ok=True)
        if not os.path.exists(todos_file):
            self._save([])
    
    def get_name(self) -> str:
        return "Todos"
    
    def get_description(self) -> str:
        return "Manages todo list with create, update, complete, and delete capabilities"
    
    def get_all_content(self) -> str:
        """Get all todos formatted for AI context"""
        todos = self.get_all()
        if not todos:
            return "No todos available."
        
        incomplete = [t for t in todos if not t['completed']]
        complete = [t for t in todos if t['completed']]
        
        content = []
        if incomplete:
            content.append("## Active Todos:")
            for todo in incomplete:
                content.append(f"- [ ] {todo['text']}")
        
        if complete:
            content.append("\n## Completed Todos:")
            for todo in complete:
                content.append(f"- [x] {todo['text']}")
        
        return "\n".join(content)
    
    def _load(self) -> List[Dict[str, Any]]:
        """Load todos from file"""
        with open(self.todos_file, 'r') as f:
            return json.load(f)
    
    def _save(self, todos: List[Dict[str, Any]]):
        """Save todos to file"""
        with open(self.todos_file, 'w') as f:
            json.dump(todos, f, indent=2)
    
    def get_all(self) -> List[Dict[str, Any]]:
        """Get all todos"""
        return self._load()
    
    def get(self, todo_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific todo"""
        todos = self._load()
        for todo in todos:
            if todo['id'] == todo_id:
                return todo
        return None
    
    def _parse_date_query(self, query: str) -> Optional[str]:
        """
        Try to parse date from query and convert to YYYY-MM-DD format.
        Handles: "today", "tomorrow", "Oct 9", "10/9", "next Monday", etc.
        """
        query_lower = query.lower().strip()
        today = datetime.now().date()
        
        # Handle relative dates
        if query_lower == "today":
            return today.strftime("%Y-%m-%d")
        elif query_lower == "tomorrow":
            return (today + timedelta(days=1)).strftime("%Y-%m-%d")
        elif query_lower == "yesterday":
            return (today - timedelta(days=1)).strftime("%Y-%m-%d")
        
        # Try parsing with dateutil
        try:
            parsed_date = date_parser.parse(query, fuzzy=True).date()
            return parsed_date.strftime("%Y-%m-%d")
        except:
            return None
    
    def _fuzzy_match_score(self, query: str, text: str) -> float:
        """Calculate fuzzy match score between query and text (0-1)"""
        return SequenceMatcher(None, query.lower(), text.lower()).ratio()
    
    def search(self, query: str) -> List[Dict[str, Any]]:
        """
        Search todos using fuzzy string matching.
        Searches across text, tags, and due_date fields.
        Returns list of todo objects sorted by relevance.
        """
        todos = self.get_all()
        
        if not todos:
            return []
        
        # If query is empty or just whitespace, return all todos
        if not query or not query.strip():
            logger.info("Empty query - returning all todos")
            return todos
        
        query_lower = query.lower()
        scored_todos: List[Tuple[Dict[str, Any], float]] = []
        
        # Try parsing as date
        date_str = self._parse_date_query(query)
        
        for todo in todos:
            score = 0.0
            
            # Check for exact substring match in text (high score)
            if query_lower in todo['text'].lower():
                score = max(score, 0.9)
            
            # Fuzzy match on text
            text_score = self._fuzzy_match_score(query, todo['text'])
            score = max(score, text_score * 0.8)
            
            # Check tags for exact or fuzzy match
            if 'tags' in todo and todo['tags']:
                for tag in todo['tags']:
                    if query_lower in tag.lower():
                        score = max(score, 0.85)
                    else:
                        tag_score = self._fuzzy_match_score(query, tag)
                        score = max(score, tag_score * 0.7)
            
            # Check due_date if query looks like a date
            if date_str and 'due_date' in todo and todo['due_date']:
                if todo['due_date'] == date_str:
                    score = max(score, 1.0)  # Perfect date match
                # Also check if query date is mentioned in text
                elif date_str in todo['text']:
                    score = max(score, 0.85)
            
            # Include todos with score > threshold
            if score > 0.3:  # Threshold for relevance
                scored_todos.append((todo, score))
        
        # Sort by score descending
        scored_todos.sort(key=lambda x: x[1], reverse=True)
        matched_todos = [todo for todo, _ in scored_todos]
        
        logger.info(f"🔍 Found {len(matched_todos)} matching todos for query: '{query}'")
        if date_str:
            logger.info(f"   Parsed date: {date_str}")
        
        return matched_todos
    
    def _parse_priority(self, text: str) -> str:
        """Extract priority from text (high/medium/low)"""
        text_lower = text.lower()
        if any(word in text_lower for word in ['urgent', 'important', 'critical', 'asap', 'high priority']):
            return 'high'
        elif any(word in text_lower for word in ['low priority', 'minor', 'someday', 'maybe']):
            return 'low'
        else:
            return 'medium'
    
    def _parse_due_date(self, text: str) -> Optional[str]:
        """Extract due date from natural language in text"""
        text_lower = text.lower()
        
        # Handle common relative dates
        if 'today' in text_lower:
            return datetime.now().date().isoformat()
        elif 'tomorrow' in text_lower:
            return (datetime.now() + timedelta(days=1)).date().isoformat()
        elif 'next week' in text_lower:
            return (datetime.now() + timedelta(weeks=1)).date().isoformat()
        elif 'next month' in text_lower:
            return (datetime.now() + timedelta(days=30)).date().isoformat()
        
        # Try to parse date formats like "by Friday", "on Oct 15", "10/15"
        try:
            # Look for date patterns in the text
            words = text.split()
            for i, word in enumerate(words):
                if word.lower() in ['by', 'on', 'before', 'due']:
                    # Try to parse the next few words as a date
                    remaining_text = ' '.join(words[i+1:i+4])
                    try:
                        parsed_date = date_parser.parse(remaining_text, fuzzy=True)
                        return parsed_date.date().isoformat()
                    except:
                        continue
        except:
            pass
        
        return None
    
    def create(self, **kwargs) -> Dict[str, Any]:
        """Create a new todo with priority and due date support"""
        # Use nanoseconds for unique IDs even when creating multiple items rapidly
        text = kwargs.get('text', '')
        
        # Auto-detect priority if not provided
        priority = kwargs.get('priority')
        if not priority:
            priority = self._parse_priority(text)
        
        # Auto-detect due date if not provided
        due_date = kwargs.get('due_date')
        if not due_date and text:
            due_date = self._parse_due_date(text)
        
        todo = {
            'id': kwargs.get('id', f"todo-{time.time_ns()}"),
            'text': text,
            'completed': kwargs.get('completed', False),
            'priority': priority,
            'due_date': due_date,
            'tags': kwargs.get('tags', []),
            'created_at': kwargs.get('created_at', datetime.now().isoformat())
        }
        todos = self._load()
        todos.append(todo)
        self._save(todos)
        return todo
    
    def update(self, todo_id: str, **kwargs) -> Dict[str, Any]:
        """Update an existing todo"""
        todos = self._load()
        for i, todo in enumerate(todos):
            if todo['id'] == todo_id:
                if 'text' in kwargs:
                    todos[i]['text'] = kwargs['text']
                if 'completed' in kwargs:
                    todos[i]['completed'] = kwargs['completed']
                if 'priority' in kwargs:
                    todos[i]['priority'] = kwargs['priority']
                if 'due_date' in kwargs:
                    todos[i]['due_date'] = kwargs['due_date']
                if 'tags' in kwargs:
                    todos[i]['tags'] = kwargs['tags']
                self._save(todos)
                return todos[i]
        raise ValueError(f"Todo {todo_id} not found")
    
    def delete(self, todo_id: str) -> bool:
        """Delete a todo"""
        todos = self._load()
        original_length = len(todos)
        todos = [t for t in todos if t['id'] != todo_id]
        if len(todos) < original_length:
            self._save(todos)
            return True
        return False
    
    def reorder(self, todo_ids: List[str]) -> List[Dict[str, Any]]:
        """Reorder todos based on provided ID list"""
        todos = self._load()
        
        # Create a mapping of id to todo
        todo_map = {todo['id']: todo for todo in todos}
        
        # Build new ordered list
        reordered = []
        
        # First, add todos in the specified order
        for todo_id in todo_ids:
            if todo_id in todo_map:
                reordered.append(todo_map[todo_id])
                del todo_map[todo_id]
        
        # Then append any remaining todos that weren't in the reorder list
        reordered.extend(todo_map.values())
        
        self._save(reordered)
        return reordered
    
    # MCP Server Implementation
    def list_tools(self) -> List[Tool]:
        """List all tools this plugin provides"""
        return [
            create_tool(
                name="create_todo",
                description="Create a new todo item. IMPORTANT: Due date is REQUIRED. If the user hasn't specified when the task is due, you MUST ask them for a due date before creating the todo. Priority is optional and auto-detected from text if not specified.",
                parameters={
                    "text": {
                        "type": "string",
                        "description": "Todo text/description. Should NOT include the due date in the text - use the due_date field instead."
                    },
                    "priority": {
                        "type": "string",
                        "description": "Priority level: 'high', 'medium', or 'low'. Auto-detected from keywords like 'urgent', 'important' if not provided."
                    },
                    "due_date": {
                        "type": "string",
                        "description": "Due date in ISO format (YYYY-MM-DD). REQUIRED - you must ask the user for this if not provided. Can parse natural language like 'tomorrow', 'next Monday', 'Oct 15'."
                    },
                    "tags": {
                        "type": "array",
                        "description": "Optional list of tags to categorize the todo (e.g., ['work', 'urgent', 'meeting'])."
                    }
                },
                required=["text", "due_date"]
            ),
            create_tool(
                name="update_todo",
                description="Update an existing todo's text, priority, or due date. Use this to change a todo's priority level or reschedule its due date.",
                parameters={
                    "todo_id": {
                        "type": "string",
                        "description": "ID of the todo to update"
                    },
                    "text": {
                        "type": "string",
                        "description": "New todo text/description"
                    },
                    "priority": {
                        "type": "string",
                        "description": "New priority level: 'high', 'medium', or 'low'"
                    },
                    "due_date": {
                        "type": "string",
                        "description": "New due date in ISO format (YYYY-MM-DD), or null to remove due date"
                    }
                },
                required=["todo_id"]
            ),
            create_tool(
                name="complete_todo",
                description="Mark a todo as completed",
                parameters={
                    "todo_id": {
                        "type": "string",
                        "description": "ID of the todo to complete"
                    }
                },
                required=["todo_id"]
            ),
            create_tool(
                name="delete_todo",
                description="Delete a todo permanently. Use this when user wants to remove a todo entirely (not just complete it).",
                parameters={
                    "todo_id": {
                        "type": "string",
                        "description": "ID of the todo to delete"
                    }
                },
                required=["todo_id"]
            ),
            create_tool(
                name="search_todos",
                description="Search todos by text, tags, or due date. Returns full todo objects (with id, text, due_date, tags, priority, completed status) sorted by relevance. Supports fuzzy matching and natural language dates like 'today', 'tomorrow', 'Oct 9'. Use empty string to get all todos.",
                parameters={
                    "query": {
                        "type": "string",
                        "description": "Search query - can be keywords from todo text, tag names, or dates in various formats (e.g., 'dentist', 'work', 'today', '10/17', 'Oct 9'). Use empty string '' to get all todos."
                    }
                },
                required=["query"]
            ),
            create_tool(
                name="reorder_todos",
                description="Reorder todos by specifying the desired order of todo IDs. Use this when user wants to move a todo to the top, bottom, or rearrange priority order.",
                parameters={
                    "todo_ids": {
                        "type": "string",
                        "description": "Comma-separated list of todo IDs in the desired order (e.g., 'todo-123,todo-456,todo-789'). Todos not listed will be appended at the end."
                    }
                },
                required=["todo_ids"]
            )
        ]
    
    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Execute a tool"""
        if tool_name == "create_todo":
            return self.create(**arguments)
        elif tool_name == "update_todo":
            todo_id = arguments.pop("todo_id")
            return self.update(todo_id, **arguments)
        elif tool_name == "complete_todo":
            return self.update(arguments["todo_id"], completed=True)
        elif tool_name == "delete_todo":
            success = self.delete(arguments["todo_id"])
            return {"success": success, "id": arguments["todo_id"]}
        elif tool_name == "search_todos":
            return self.search(arguments["query"])
        elif tool_name == "reorder_todos":
            # Parse comma-separated string into list
            todo_ids_str = arguments["todo_ids"]
            todo_ids = [tid.strip() for tid in todo_ids_str.split(",")]
            return self.reorder(todo_ids)
        else:
            raise ValueError(f"Unknown tool: {tool_name}")
    
    def list_resources(self) -> List[Resource]:
        """List all resources this plugin provides"""
        return [
            create_resource(
                name="Todo List",
                uri="todos://all",
                description="Complete todo list with active and completed items"
            )
        ]
    
    def read_resource(self, uri: str) -> str:
        """Read a resource"""
        if uri == "todos://all":
            return self.get_all_content()
        else:
            raise ValueError(f"Unknown resource URI: {uri}")
