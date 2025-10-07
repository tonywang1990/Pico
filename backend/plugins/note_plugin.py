"""
NotePlugin - Manages user notes
"""

import os
import json
import time
from typing import List, Dict, Any, Optional
from datetime import datetime
from mcp.types import Tool, Resource
from mcp_protocol import MCPServer, create_tool, create_resource
from .base import Plugin


class NotePlugin(Plugin, MCPServer):
    """Plugin for managing notes - implements MCP Server"""
    
    def __init__(self, notes_dir: str = "data/notes"):
        self.notes_dir = notes_dir
        os.makedirs(self.notes_dir, exist_ok=True)
    
    def get_name(self) -> str:
        return "Notes"
    
    def get_description(self) -> str:
        return "Manages user notes with create, read, update, delete, and search capabilities"
    
    def get_all_content(self) -> str:
        """Get all notes formatted for AI context"""
        notes = self.get_all()
        if not notes:
            return "No notes available."
        
        content_parts = []
        for note in notes:
            content_parts.append(f"# {note['title']}\n{note['content']}\n")
        
        return "\n---\n".join(content_parts)
    
    def get_all(self) -> List[Dict[str, Any]]:
        """Get all notes"""
        notes = []
        if os.path.exists(self.notes_dir):
            for filename in os.listdir(self.notes_dir):
                if filename.endswith('.json'):
                    with open(os.path.join(self.notes_dir, filename), 'r') as f:
                        notes.append(json.load(f))
        notes.sort(key=lambda x: x['updated_at'], reverse=True)
        return notes
    
    def get(self, note_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific note"""
        note_path = os.path.join(self.notes_dir, f"{note_id}.json")
        if not os.path.exists(note_path):
            return None
        with open(note_path, 'r') as f:
            return json.load(f)
    
    def search(self, query: str) -> List[Dict[str, Any]]:
        """Search notes by content or title with flexible matching"""
        query_lower = query.lower()
        notes = self.get_all()
        
        # Split query into words for better matching
        query_words = query_lower.split()
        
        results = []
        for note in notes:
            title_lower = note['title'].lower()
            content_lower = note['content'].lower()
            
            # Check if any query word matches
            word_match = any(
                word in title_lower or word in content_lower 
                for word in query_words
            )
            
            # Also keep exact phrase matching
            exact_match = query_lower in title_lower or query_lower in content_lower
            
            if word_match or exact_match:
                results.append(note)
        
        return results
    
    def create(self, **kwargs) -> Dict[str, Any]:
        """Create a new note"""
        # Use nanoseconds for unique IDs even when creating multiple items rapidly
        note = {
            'id': kwargs.get('id', f"note-{time.time_ns()}"),
            'title': kwargs.get('title', 'Untitled Note'),
            'content': kwargs.get('content', ''),
            'created_at': kwargs.get('created_at', datetime.now().isoformat()),
            'updated_at': datetime.now().isoformat()
        }
        note_path = os.path.join(self.notes_dir, f"{note['id']}.json")
        with open(note_path, 'w') as f:
            json.dump(note, f, indent=2)
        return note
    
    def update(self, note_id: str, **kwargs) -> Dict[str, Any]:
        """Update an existing note"""
        note = self.get(note_id)
        if not note:
            raise ValueError(f"Note {note_id} not found")
        
        # Update fields
        if 'title' in kwargs:
            note['title'] = kwargs['title']
        if 'content' in kwargs:
            note['content'] = kwargs['content']
        note['updated_at'] = datetime.now().isoformat()
        
        note_path = os.path.join(self.notes_dir, f"{note_id}.json")
        with open(note_path, 'w') as f:
            json.dump(note, f, indent=2)
        return note
    
    def delete(self, note_id: str) -> bool:
        """Delete a note"""
        note_path = os.path.join(self.notes_dir, f"{note_id}.json")
        if os.path.exists(note_path):
            os.remove(note_path)
            return True
        return False
    
    # MCP Server Implementation
    def list_tools(self) -> List[Tool]:
        """List all tools this plugin provides"""
        return [
            create_tool(
                name="search_notes",
                description="Search through all notes by title or content",
                parameters={
                    "query": {
                        "type": "string",
                        "description": "Search query string"
                    }
                },
                required=["query"]
            ),
            create_tool(
                name="create_note",
                description="Create a new note",
                parameters={
                    "title": {
                        "type": "string",
                        "description": "Note title"
                    },
                    "content": {
                        "type": "string",
                        "description": "Note content"
                    }
                },
                required=["title"]
            ),
            create_tool(
                name="update_note",
                description="Update an existing note",
                parameters={
                    "note_id": {
                        "type": "string",
                        "description": "ID of the note to update"
                    },
                    "title": {
                        "type": "string",
                        "description": "New title (optional)"
                    },
                    "content": {
                        "type": "string",
                        "description": "New content (optional)"
                    }
                },
                required=["note_id"]
            )
        ]
    
    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Execute a tool"""
        if tool_name == "search_notes":
            return self.search(arguments["query"])
        elif tool_name == "create_note":
            return self.create(**arguments)
        elif tool_name == "update_note":
            note_id = arguments.pop("note_id")
            return self.update(note_id, **arguments)
        else:
            raise ValueError(f"Unknown tool: {tool_name}")
    
    def list_resources(self) -> List[Resource]:
        """List all resources this plugin provides"""
        return [
            create_resource(
                name="All Notes",
                uri="notes://all",
                description="Complete collection of all user notes"
            )
        ]
    
    def read_resource(self, uri: str) -> str:
        """Read a resource"""
        if uri == "notes://all":
            return self.get_all_content()
        else:
            raise ValueError(f"Unknown resource URI: {uri}")
