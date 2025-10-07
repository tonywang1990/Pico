"""
Model Context Protocol (MCP) - Interface between PicoAgent and Plugins

MCP defines a standardized way for plugins to expose their capabilities
and for agents to discover and interact with them.

This implementation uses the standard MCP library.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from mcp.types import Tool, Resource, TextContent
from pydantic import BaseModel


class MCPServer(ABC):
    """
    MCP Server interface - Plugins implement this to expose their capabilities
    Uses standard MCP types from the mcp library
    """
    
    @abstractmethod
    def get_name(self) -> str:
        """Get the plugin name"""
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """Get plugin description"""
        pass
    
    @abstractmethod
    def list_tools(self) -> List[Tool]:
        """List all tools this plugin provides (using standard MCP Tool type)"""
        pass
    
    @abstractmethod
    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Execute a tool with given arguments"""
        pass
    
    @abstractmethod
    def list_resources(self) -> List[Resource]:
        """List all data resources this plugin provides (using standard MCP Resource type)"""
        pass
    
    @abstractmethod
    def read_resource(self, uri: str) -> str:
        """Read a resource by its URI"""
        pass


class MCPClient:
    """
    MCP Client - PicoAgent uses this to interact with plugin servers
    Compatible with standard MCP types
    """
    
    def __init__(self):
        self.servers: Dict[str, MCPServer] = {}
    
    def register_server(self, server: MCPServer):
        """Register a plugin server"""
        self.servers[server.get_name()] = server
    
    def list_servers(self) -> List[str]:
        """List all registered server names"""
        return list(self.servers.keys())
    
    def get_server(self, name: str) -> Optional[MCPServer]:
        """Get a specific server by name"""
        return self.servers.get(name)
    
    def discover_all_tools(self) -> List[Tool]:
        """Discover all tools from all servers (standard MCP Tool type)"""
        all_tools = []
        for server in self.servers.values():
            tools = server.list_tools()
            all_tools.extend(tools)
        return all_tools
    
    def discover_all_resources(self) -> List[Resource]:
        """Discover all resources from all servers (standard MCP Resource type)"""
        all_resources = []
        for server in self.servers.values():
            resources = server.list_resources()
            all_resources.extend(resources)
        return all_resources
    
    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call a tool by name (searches all servers)"""
        for server in self.servers.values():
            tools = server.list_tools()
            if any(tool.name == tool_name for tool in tools):
                return server.call_tool(tool_name, arguments)
        raise ValueError(f"Tool {tool_name} not found in any server")
    
    def read_resource(self, uri: str) -> str:
        """Read a resource by URI (searches all servers)"""
        for server in self.servers.values():
            resources = server.list_resources()
            if any(res.uri == uri for res in resources):
                return server.read_resource(uri)
        raise ValueError(f"Resource {uri} not found in any server")
    
    def get_all_context(self) -> str:
        """Get all available context from all resources"""
        context_parts = []
        
        for server in self.servers.values():
            resources = server.list_resources()
            for resource in resources:
                try:
                    content = server.read_resource(str(resource.uri))
                    if content:
                        context_parts.append(f"## {resource.name}\n{content}")
                except Exception as e:
                    print(f"Error reading resource {resource.uri}: {e}")
        
        return "\n\n".join(context_parts)
    
    def get_tools_for_claude(self) -> List[Dict[str, Any]]:
        """
        Convert standard MCP Tools to Anthropic Claude tool format
        """
        tools = self.discover_all_tools()
        claude_tools = []
        
        for tool in tools:
            # MCP Tool already has inputSchema, convert to Claude format
            claude_tool = {
                "name": tool.name,
                "description": tool.description or "",
                "input_schema": tool.inputSchema
            }
            claude_tools.append(claude_tool)
        
        return claude_tools


# Helper functions for creating standard MCP types
def create_tool(
    name: str,
    description: str,
    parameters: Dict[str, Dict[str, Any]],
    required: List[str] = None
) -> Tool:
    """
    Helper to create a standard MCP Tool
    
    Args:
        name: Tool name
        description: Tool description
        parameters: Dict of parameter_name -> {"type": "string", "description": "..."}
        required: List of required parameter names
    """
    input_schema = {
        "type": "object",
        "properties": parameters,
    }
    if required:
        input_schema["required"] = required
    
    return Tool(
        name=name,
        description=description,
        inputSchema=input_schema
    )


def create_resource(
    name: str,
    uri: str,
    description: str = None,
    mime_type: str = "text/plain"
) -> Resource:
    """
    Helper to create a standard MCP Resource
    
    Args:
        name: Resource name
        uri: Unique URI for the resource
        description: Resource description
        mime_type: MIME type of the resource
    """
    return Resource(
        name=name,
        uri=uri,
        description=description,
        mimeType=mime_type
    )