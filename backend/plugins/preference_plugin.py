"""
PreferencePlugin - Manages user preferences with AI-based merging
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional
from copy import deepcopy
from mcp.types import Tool, Resource
from mcp_protocol import MCPServer, create_tool, create_resource
from .base import Plugin
from .utils import call_llm_for_json

logger = logging.getLogger(__name__)


class PreferencePlugin(Plugin, MCPServer):
    """Plugin for managing user preferences with AI-based merging - implements MCP Server"""
    
    def __init__(self, preferences_file: str = "data/preferences.json", anthropic_api_key: str = None):
        self.preferences_file = preferences_file
        self.anthropic_api_key = anthropic_api_key
        os.makedirs(os.path.dirname(preferences_file), exist_ok=True)
        if not os.path.exists(preferences_file):
            self._save(self._get_default_preferences())
    
    def _get_default_preferences(self) -> Dict[str, List[str]]:
        """Get default preference structure - dict of lists of strings"""
        return {
            "general": [
                "User prefers concise and helpful responses",
                "User likes proactive suggestions"
            ],
            "notes_plugin": [],
            "todos_plugin": []
        }
    
    def get_name(self) -> str:
        return "Preferences"
    
    def get_description(self) -> str:
        return "Manages user preferences and learns user behavior to provide personalized assistance"
    
    def _load(self) -> Dict[str, Any]:
        """Load preferences from file"""
        with open(self.preferences_file, 'r') as f:
            return json.load(f)
    
    def _save(self, preferences: Dict[str, Any]):
        """Save preferences to file"""
        with open(self.preferences_file, 'w') as f:
            json.dump(preferences, f, indent=2)
    
    def get_all_content(self) -> str:
        """Get all preferences formatted for AI context"""
        prefs = self._load()
        
        content = "# User Preferences\n\n"
        
        for section, preferences in prefs.items():
            if preferences:  # Only show sections with content
                section_name = section.replace("_plugin", "").replace("_", " ").title()
                content += f"## {section_name}\n"
                for pref in preferences:
                    content += f"- {pref}\n"
                content += "\n"
        
        return content
    
    def get_preferences(self, sections: Optional[List[str]] = None) -> Dict[str, List[str]]:
        """Get preferences for specific sections or all preferences"""
        prefs = self._load()
        
        if sections:
            # Return only requested sections
            result = {}
            for section in sections:
                result[section] = prefs.get(section, [])
            return result
        
        return prefs
    
    def _merge_all_preferences_with_llm(self, current_all: Dict[str, List[str]], updates: Dict[str, Dict[str, str]]) -> Dict[str, List[str]]:
        """Use single LLM call to intelligently merge all preference updates"""
        if not self.anthropic_api_key:
            # Fallback: just append new preferences
            logger.warning("No Anthropic API key provided, using simple append for preferences")
            result = deepcopy(current_all)
            for section, new_prefs in updates.items():
                if section not in result:
                    result[section] = []
                for pref in new_prefs.values():
                    if pref not in result[section]:
                        result[section].append(pref)
            return result
        
        try:
            # Prepare the merge prompt with ALL sections
            prompt = f"""You are helping manage user preferences. Given the current preferences across all sections and new information to integrate, create an updated preference structure.

CURRENT PREFERENCES (all sections):
{json.dumps(current_all, indent=2)}

NEW INFORMATION TO INTEGRATE:
{json.dumps(updates, indent=2)}

INSTRUCTIONS:
1. Merge the new information with existing preferences for each section
2. Remove contradictions (keep the newer information)
3. Remove duplicates within each section
4. Keep preferences concise and clear
5. If a section has no preferences, keep it as an empty array
6. Return ONLY a JSON object with the same structure, nothing else

Output format:
{{
  "general": ["preference 1", "preference 2"],
  "notes_plugin": ["preference 1"],
  "todos_plugin": ["preference 1", "preference 2"]
}}"""

            merged_prefs = call_llm_for_json(
                api_key=self.anthropic_api_key,
                model="claude-sonnet-4-5-20250929",
                prompt=prompt,
                max_tokens=2048,
                operation_name=f"Preference merge ({len(updates)} sections)"
            )
            
            return merged_prefs
            
        except Exception as e:
            logger.error(f"Error merging preferences with LLM: {e}")
            # Fallback: simple append
            result = deepcopy(current_all)
            for section, new_prefs in updates.items():
                if section not in result:
                    result[section] = []
                for pref in new_prefs.values():
                    if pref not in result[section]:
                        result[section].append(pref)
            return result
    
    def update_preferences(self, updates: Dict[str, Dict[str, str]]) -> Dict[str, List[str]]:
        """
        Update preferences using single LLM call for intelligent merging.
        
        Args:
            updates: Dict of section -> dict of key -> preference string
                    e.g., {"general": {"name": "User's name is Tony"}, 
                           "todos_plugin": {"organization": "User prefers urgency matrix"}}
        
        Returns:
            All preferences after merging (entire preference structure)
        """
        current_prefs = self._load()
        
        # Ensure all sections in updates exist
        for section in updates.keys():
            if section not in current_prefs:
                current_prefs[section] = []
        
        # Single LLM call to merge everything
        merged_prefs = self._merge_all_preferences_with_llm(current_prefs, updates)
        
        # Save and return
        self._save(merged_prefs)
        logger.info(f"💾 Saved merged preferences")
        return merged_prefs
    
    # Implement abstract Plugin methods (preferences don't need these)
    def search(self, query: str) -> List[Dict[str, Any]]:
        """Search is not applicable for preferences"""
        return []
    
    def create(self, **kwargs) -> Dict[str, Any]:
        """Create is handled through update_preference"""
        return {}
    
    def update(self, item_id: str, **kwargs) -> Dict[str, Any]:
        """Update is handled through update_preference"""
        return {}
    
    def delete(self, item_id: str) -> bool:
        """Delete is not applicable for preferences"""
        return False
    
    # MCP Server Implementation
    def list_tools(self) -> List[Tool]:
        """List all tools this plugin provides"""
        return [
            create_tool(
                name="get_preferences",
                description="Get user preferences from specified sections or all sections. Use this to understand user's preferences, work style, and learned behaviors.",
                parameters={
                    "sections": {
                        "type": "string",
                        "description": "Comma-separated list of sections to retrieve (e.g., 'general,todos_plugin'). Leave empty for all preferences."
                    }
                },
                required=[]
            ),
            create_tool(
                name="update_preferences",
                description="Update user preferences using AI-based merging. Provide new preferences and they will be intelligently merged with existing ones, removing contradictions and duplicates. Use this after completing tasks or when learning new patterns about the user.",
                parameters={
                    "updates": {
                        "type": "string",
                        "description": """JSON string of updates: {"section": {"key": "preference description"}}. Example: {"general": {"name": "User name is Tony"}, "todos_plugin": {"organization": "User prefers Eisenhower urgency matrix"}}"""
                    }
                },
                required=["updates"]
            )
        ]
    
    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Execute a tool"""
        if tool_name == "get_preferences":
            sections_str = arguments.get("sections", "")
            sections = [s.strip() for s in sections_str.split(",")] if sections_str else None
            return self.get_preferences(sections)
        elif tool_name == "update_preferences":
            updates_str = arguments["updates"]
            try:
                updates = json.loads(updates_str)
                return self.update_preferences(updates)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON in updates parameter: {e}")
        else:
            raise ValueError(f"Unknown tool: {tool_name}")
    
    def list_resources(self) -> List[Resource]:
        """List all resources this plugin provides"""
        return [
            create_resource(
                name="User Preferences",
                uri="preferences://all",
                description="Complete user preferences including general settings and plugin-specific preferences"
            )
        ]
    
    def read_resource(self, uri: str) -> str:
        """Read a resource"""
        if uri == "preferences://all":
            return self.get_all_content()
        else:
            raise ValueError(f"Unknown resource URI: {uri}")
