"""
TodoPlugin - Manages todo list
"""

import os
import json
import time
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dateutil import parser as date_parser
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
    
    def search(self, query: str) -> List[Dict[str, Any]]:
        """Search todos using LLM for intelligent matching"""
        todos = self.get_all()
        
        if not todos:
            return []
        
        # If no API key, fall back to simple search
        if not self.anthropic_api_key:
            logger.warning("No Anthropic API key, using simple text search")
            query_lower = query.lower()
            return [todo for todo in todos if query_lower in todo['text'].lower()]
        
        try:
            # Prepare prompt for LLM
            prompt = f"""You are helping search through a todo list. Given a search query and a list of todos, return ONLY the todos that match the search.

SEARCH QUERY: "{query}"

ALL TODOS:
{json.dumps(todos, indent=2)}

INSTRUCTIONS:
1. Find todos that match the search query
2. Match by: text content, tags, due dates (handle different date formats like "10/17" = "Oct 17" = "2025-10-17")
3. Return ONLY a JSON array of the matching todos (exact same format as input)
4. Return empty array [] if no matches
5. Do NOT include any explanation, just the JSON array

Output format: [{{...todo1...}}, {{...todo2...}}]"""

            results = call_llm_for_json(
                api_key=self.anthropic_api_key,
                model="claude-sonnet-4-5-20250929",
                prompt=prompt,
                max_tokens=4096,
                operation_name=f"Todo search for '{query}'"
            )
            
            logger.info(f"🔍 Found {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Error in LLM search: {e}")
            # Fallback to simple text search
            query_lower = query.lower()
            return [todo for todo in todos if query_lower in todo['text'].lower()]
    
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
                name="search_todos",
                description="Search todos by text, tags, or due date. Supports flexible matching - can search by keywords, partial dates (e.g., '10/17', 'Oct 17'), or tags. Returns matching todos with their full information including IDs for updates.",
                parameters={
                    "query": {
                        "type": "string",
                        "description": "Search query - can be keywords from todo text, tag names, or dates in various formats (e.g., 'dentist', 'work', '10/17', 'Oct 17')"
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
