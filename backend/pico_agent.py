"""
Pico Agent - The main AI assistant that interacts with plugins via MCP
"""

from typing import List, Dict, Any, Generator
import anthropic
import json
import logging
from mcp_protocol import MCPClient, MCPServer
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class PicoAgent:
    """
    Main AI agent that understands user needs and interacts with plugin servers via MCP Client
    """

    def __init__(self, api_key: str, mcp_client: MCPClient):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.mcp_client = mcp_client
        self.model = "claude-sonnet-4-5-20250929"

        # Log initialization
        servers = self.mcp_client.list_servers()
        logger.info(f"PicoAgent initialized with {len(servers)} MCP servers: {servers}")

        # Log available tools
        tools = self.mcp_client.discover_all_tools()
        tool_names = [t.name for t in tools]
        logger.info(f"Discovered {len(tools)} tools: {tool_names}")

    def _build_system_message(self, include_plugin_data: bool = True) -> str:
        """Build system message with context from MCP resources"""
        today_date = datetime.now().strftime("%Y-%m-%d")
        system_message = f"""You are Pico, a personalized AI assistant integrated into a note-taking app. 

You have access to the user's notes, todos, and preferences through MCP plugins. You can help them by USING TOOLS to:
- Search, create, and update notes
- Create, update, reorder, and complete todos
- Learn and store user preferences over time
- Organize and manage their information

**CRITICAL - ALWAYS USE TOOLS FOR ACTIONS**: 
When users ask you to DO something with their data, you MUST use tools to make changes. Examples:
- "Add a todo" → use create_todo tool
- "Update the appointment" → search_todos to find it, then use update_todo tool  
- "Mark X as done" → search_todos to find it, then use complete_todo tool
- "Delete/Remove X" → search_todos to find it, then use delete_todo tool
- "Create a note" → use create_note tool
- "Add a time to X" → search_todos to find it, then use update_todo tool to modify the text
- "Change priority of X" → search_todos to find it, then use update_todo tool

**WORKFLOW FOR MODIFICATIONS**: When users want to modify/update/delete an existing item:
1. First use search_todos or search_notes to find the item by keywords
2. Get the item's ID from the search results
3. Then call the appropriate tool with that ID:
   - update_todo / update_note - to modify content
   - complete_todo - to mark as done
   - delete_todo - to remove permanently

NEVER just respond with "I've updated..." without actually calling the tool. The user expects you to make real changes to their data.

**CRITICAL TODO CREATION RULE**: When creating todos, a due date is MANDATORY. If the user doesn't specify when a task is due:
1. Ask them for a due date before creating the todo
2. Suggest reasonable due dates based on context (e.g., "When would you like this done? Tomorrow? End of week?")
3. Only create the todo after you have a specific due date
4. You can parse natural language dates like "tomorrow", "next Monday", "in 3 days", etc.

**Example conversations:**

Example 1 - Creating todo:
User: "Add a todo to review the budget report"
Pico: "I'll add that todo. When would you like to review the budget report? Tomorrow? End of this week?"
User: "Next Monday"
Pico: [Calls create_todo tool with due_date for next Monday]

Example 2 - Updating todo:
User: "Add a time for the dentist appointment, 2pm"
Pico: [Calls search_todos to find "dentist", then calls update_todo to add "2pm" to the text]

Today's date is {today_date}.

## Personalization & Learning (IMPORTANT)
You have an **AI-powered preference system** that helps you become progressively smarter:

**Two Simple Tools:**
1. `get_preferences(sections)` - Read preferences (usually auto-loaded via resources)
2. `update_preferences(updates)` - Store learnings using AI merging

**When to Update Preferences:**
After completing tasks or interactions, use `update_preferences()` with this JSON format:
```json
{{
  "general": {{"key": "User's name is Tony"}},
  "todos_plugin": {{"organization": "User organizes by Eisenhower urgency/importance matrix"}},
  "notes_plugin": {{"style": "User prefers markdown with clear headings"}}
}}
```

The system uses **AI to intelligently merge** your learnings with existing preferences, removing contradictions and duplicates automatically.

**Sections:**
- `general` - Name, communication style, work patterns
- `notes_plugin` - Note-taking preferences
- `todos_plugin` - Task management preferences

**CRITICAL**: After organizing todos, creating notes, or any task the user might repeat, ALWAYS call `update_preferences()` to remember the pattern. The AI will merge it intelligently with what's already known.

Be concise, helpful, and proactive. When you spot action items, suggest adding them to the todo list.
Format your responses using Markdown for better readability (headings, lists, bold, etc.).
"""

        if include_plugin_data:
            # Get context from all MCP resources
            context = self.mcp_client.get_all_context()
            if context:
                system_message += f"\n\nAvailable Data:\n{context}"

        return system_message

    def _track_action_metadata(
        self, tool_name: str, result: Any, metadata: Dict[str, Any]
    ) -> None:
        """
        Track metadata for actions taken by tools.
        Generic tracking system that works for any plugin.
        """
        if not isinstance(result, dict) or "id" not in result:
            return

        # Extract action type from tool name (e.g., "create_note" -> "created_notes")
        action_parts = tool_name.split("_")
        if len(action_parts) >= 2:
            action_type = action_parts[0]  # create, update, delete, etc.
            resource_type = "_".join(action_parts[1:])  # note, todo, etc.

            # Build metadata key (e.g., "created_notes")
            metadata_key = (
                f"{action_type}d_{resource_type}s"  # created_notes, updated_todos, etc.
            )

            # Initialize list if not exists
            if metadata_key not in metadata:
                metadata[metadata_key] = []

            # Track the ID
            metadata[metadata_key].append(result["id"])
            logger.info(f"📋 Tracked action: {metadata_key} -> {result['id']}")

    def _execute_tool(
        self, tool_name: str, tool_input: Dict[str, Any], tool_use_id: str
    ) -> Dict[str, Any]:
        """
        Execute a single tool and return the result in Claude's expected format.
        """
        logger.info(f"📞 Calling tool: {tool_name}")
        logger.info(f"   Arguments: {json.dumps(tool_input, indent=2)}")

        try:
            result = self.mcp_client.call_tool(tool_name, tool_input)
            logger.info(f"✅ Tool {tool_name} executed successfully")
            logger.info(f"   Result: {json.dumps(result, indent=2)[:200]}...")

            return {
                "type": "tool_result",
                "tool_use_id": tool_use_id,
                "content": json.dumps(result),
                "success": True,
                "result": result,
            }
        except Exception as e:
            logger.error(f"❌ Tool {tool_name} failed: {str(e)}")
            return {
                "type": "tool_result",
                "tool_use_id": tool_use_id,
                "content": f"Error: {str(e)}",
                "is_error": True,
                "success": False,
                "result": None,
            }

    def _process_tool_calls(
        self, response_content: List[Any], metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Process all tool calls in a response and return tool results.
        """
        tool_results = []

        for block in response_content:
            if block.type == "tool_use":
                tool_result = self._execute_tool(block.name, block.input, block.id)

                # Track successful actions
                if tool_result["success"] and tool_result["result"]:
                    self._track_action_metadata(
                        block.name, tool_result["result"], metadata
                    )

                # Add to results (remove internal fields before sending to Claude)
                tool_results.append(
                    {
                        "type": tool_result["type"],
                        "tool_use_id": tool_result["tool_use_id"],
                        "content": tool_result["content"],
                        **({"is_error": True} if tool_result.get("is_error") else {}),
                    }
                )

        return tool_results

    def _extract_text_from_response(self, response_content: List[Any]) -> str:
        """Extract text content from Claude's response."""
        response_text = ""
        for block in response_content:
            if hasattr(block, "text"):
                response_text += block.text
        return response_text
    
    def _call_claude(self, system_message: str, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]], max_tokens: int) -> Any:
        """Make a Claude API call - extracted for DRY principle"""
        return self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system_message,
            messages=messages,
            tools=tools if tools else None,
        )

    def chat(
        self,
        messages: List[Dict[str, str]],
        include_plugin_data: bool = True,  # Changed default to True so agent always has context
        max_tokens: int = 2048,
    ) -> Dict[str, Any]:
        """
        Process a chat message and return response with tool use support.
        Implements an agentic loop that continues until the agent is satisfied.

        Args:
            messages: List of message dicts with 'role' and 'content'
            include_plugin_data: Whether to include plugin data in context (default False for agentic mode)
            max_tokens: Maximum tokens for response

        Returns:
            Dict with 'response' text and metadata about actions taken
        """
        # Setup
        user_query = messages[-1]["content"] if messages else "No message"
        logger.info(f"=== New chat session ===")
        logger.info(f"User query: {user_query[:100]}...")

        system_message = self._build_system_message(include_plugin_data)
        tools = self.mcp_client.get_tools_for_claude()
        logger.info(f"Available tools for this session: {len(tools)}")

        # Track all actions (plugin-agnostic)
        actions_metadata = {}

        # Agentic loop configuration
        iteration = 0
        max_iterations = 10

        try:
            # Agentic loop: make calls until agent is satisfied
            response = self._call_claude(system_message, messages, tools, max_tokens)
            logger.info(f"Claude response stop_reason: {response.stop_reason}")

            while response.stop_reason == "tool_use" and iteration < max_iterations:
                iteration += 1
                logger.info(
                    f"🔧 Agentic iteration {iteration}: Claude requested tool use"
                )

                # Process all tool calls in this response
                tool_results = self._process_tool_calls(
                    response.content, actions_metadata
                )
                logger.info(
                    f"🔄 Sending {len(tool_results)} tool results back to Claude"
                )

                # Append to conversation
                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "user", "content": tool_results})

                # Get next response
                response = self._call_claude(system_message, messages, tools, max_tokens)
                logger.info(f"Claude response stop_reason: {response.stop_reason}")

            # Check if we hit the iteration limit
            if iteration >= max_iterations:
                logger.warning(
                    f"⚠️ Reached max iterations ({max_iterations}), stopping agentic loop"
                )

        except Exception as e:
            logger.error(f"Error calling Claude API: {str(e)}")
            logger.error(f"Model: {self.model}, Tools: {len(tools)}")
            raise

        # Extract final response
        response_text = self._extract_text_from_response(response.content)

        logger.info(f"💬 Response length: {len(response_text)} characters")
        logger.info(f"🎯 Completed in {iteration} agentic iterations")
        logger.info(f"=== Chat session complete ===\n")

        return {"response": response_text, "metadata": actions_metadata}

    def get_server(self, name: str) -> MCPServer:
        """Get an MCP server by name"""
        return self.mcp_client.get_server(name)

    def list_servers(self) -> List[str]:
        """List all available MCP server names"""
        return self.mcp_client.list_servers()

    def list_available_tools(self) -> List[str]:
        """List all available tool names"""
        tools = self.mcp_client.discover_all_tools()
        return [tool.name for tool in tools]
    
    def chat_stream(
        self,
        messages: List[Dict[str, str]],
        include_plugin_data: bool = True,
        max_tokens: int = 2048,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Process a chat message and yield events showing the thinking process.
        
        Yields events:
        - {"type": "thinking"} - Agent is thinking
        - {"type": "tool_call", "tool": str, "args": dict} - Tool being called
        - {"type": "tool_result", "tool": str, "success": bool, "result": any} - Tool result
        - {"type": "response", "text": str} - Final response text
        - {"type": "done", "metadata": dict} - Completion with metadata
        """
        # Setup
        user_query = messages[-1]["content"] if messages else "No message"
        logger.info(f"=== New streaming chat session ===")
        logger.info(f"User query: {user_query[:100]}...")
        
        yield {"type": "thinking"}
        
        system_message = self._build_system_message(include_plugin_data)
        tools = self.mcp_client.get_tools_for_claude()
        
        # Track all actions
        actions_metadata = {}
        
        # Agentic loop configuration
        iteration = 0
        max_iterations = 10
        
        try:
            # Agentic loop
            response = self._call_claude(system_message, messages, tools, max_tokens)
            
            while response.stop_reason == "tool_use" and iteration < max_iterations:
                iteration += 1
                logger.info(f"🔧 Iteration {iteration}: Tool use requested")
                
                # Process tool calls and yield events
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        # Yield tool call event
                        yield {
                            "type": "tool_call",
                            "tool": block.name,
                            "args": block.input
                        }
                        
                        # Execute tool
                        tool_result = self._execute_tool(block.name, block.input, block.id)
                        
                        # Track successful actions
                        if tool_result["success"] and tool_result["result"]:
                            self._track_action_metadata(
                                block.name, tool_result["result"], actions_metadata
                            )
                        
                        # Yield tool result event
                        yield {
                            "type": "tool_result",
                            "tool": block.name,
                            "success": tool_result["success"],
                            "result": tool_result.get("result"),
                            "error": tool_result.get("content") if tool_result.get("is_error") else None
                        }
                        
                        # Add to results for Claude
                        tool_results.append({
                            "type": tool_result["type"],
                            "tool_use_id": tool_result["tool_use_id"],
                            "content": tool_result["content"],
                            **({"is_error": True} if tool_result.get("is_error") else {}),
                        })
                
                # Append to conversation
                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "user", "content": tool_results})
                
                # Show thinking again
                yield {"type": "thinking"}
                
                # Get next response
                response = self._call_claude(system_message, messages, tools, max_tokens)
            
            # Extract final response
            response_text = self._extract_text_from_response(response.content)
            
            # Yield final response
            yield {
                "type": "response",
                "text": response_text
            }
            
            # Yield completion
            yield {
                "type": "done",
                "metadata": actions_metadata,
                "iterations": iteration
            }
            
        except Exception as e:
            logger.error(f"Error in streaming chat: {str(e)}")
            yield {
                "type": "error",
                "error": str(e)
            }
