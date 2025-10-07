"""
Plugins module - Extensible content widgets for Pico

Each plugin manages a specific type of content (notes, todos, etc.)
Plugins implement MCPServer to expose their capabilities
"""

from .base import Plugin
from .note_plugin import NotePlugin
from .todo_plugin import TodoPlugin
from .preference_plugin import PreferencePlugin
from .utils import call_llm_for_json

__all__ = [
    'Plugin',
    'NotePlugin', 
    'TodoPlugin',
    'PreferencePlugin',
    'call_llm_for_json'
]
