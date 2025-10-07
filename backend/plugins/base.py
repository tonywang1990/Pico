"""
Base Plugin class - abstract interface for all Pico plugins
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any


class Plugin(ABC):
    """Base class for all Pico plugins"""
    
    @abstractmethod
    def get_all_content(self) -> str:
        """Get all content as formatted text for AI context"""
        pass
    
    @abstractmethod
    def search(self, query: str) -> List[Dict[str, Any]]:
        """Search content based on query"""
        pass
    
    @abstractmethod
    def create(self, **kwargs) -> Dict[str, Any]:
        """Create new content"""
        pass
    
    @abstractmethod
    def update(self, item_id: str, **kwargs) -> Dict[str, Any]:
        """Update existing content"""
        pass
    
    @abstractmethod
    def delete(self, item_id: str) -> bool:
        """Delete content"""
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """Get plugin name for AI reference"""
        pass
