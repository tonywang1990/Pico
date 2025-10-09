"""
Pico Agent - The main AI assistant that interacts with plugins via MCP
"""

from typing import List, Dict, Any, Generator
import anthropic
import json
import logging
import time
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
        
        # Cache tools list (doesn't change during runtime)
        self._cached_tools = None
        
        # Cache base system prompt (static part)
        self._base_system_prompt = self._build_base_system_prompt()

        # Log initialization
        servers = self.mcp_client.list_servers()
        logger.info(f"PicoAgent initialized with {len(servers)} MCP servers: {servers}")

        # Log all tools including server tools like web_search
        all_tools = self.get_tools()
        all_tool_names = [t.get('name', t.get('type', 'unknown')) for t in all_tools]
        logger.info(f"Total tools available (including server tools): {len(all_tools)} - {all_tool_names}")

    def _build_base_system_prompt(self) -> str:
        """Build the static base system prompt (cached)"""
        return """You are Pico, a personalized AI assistant for note-taking and task management.

**Core Capabilities (via tools):**
- Search, create, and update notes
- Manage todos (create, update, complete, delete, reorder)
- Learn user preferences over time
- Search the web for current information

**CRITICAL RULES:**
1. **Always use tools for actions** - Don't just say you did something, actually call the tool
2. **Search before modifying** - Use search_todos/search_notes to find items, then call update/delete/complete with the ID
3. **Todos need due dates** - If user doesn't specify, ask before creating
4. **Update preferences** - After completing tasks, call update_preferences() to remember patterns

**Workflow for modifications:**
1. Search for the item
2. Get its ID from results
3. Call the appropriate tool (update/complete/delete)

**Preference Learning:**
Use `update_preferences({"general": {...}, "todos_plugin": {...}, "notes_plugin": {...}})` to store learnings.

**Web Search:**
Use for current events, real-time data, recent updates (5 searches max per request).

Be concise and use Markdown formatting."""

    def _build_system_message(self) -> str:
        """Build system message with current date"""
        today_date = datetime.now().strftime("%Y-%m-%d")
        return f"{self._base_system_prompt}\n\nToday's date is {today_date}."
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """Get tools list (cached for performance)"""
        if self._cached_tools is None:
            self._cached_tools = self.mcp_client.get_tools_for_claude()
        return self._cached_tools

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
        Note: server_tool_use blocks (like web_search) are automatically handled by the API.
        """
        start_time = time.time()
        tool_results = []
        tool_count = 0

        for block in response_content:
            if block.type == "tool_use":
                # MCP plugin tools - we execute these
                tool_count += 1
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
            elif block.type == "server_tool_use":
                # Server tools (like web_search) are automatically executed by Anthropic API
                # We just log them for visibility
                tool_input = getattr(block, 'input', None)
                logger.info(f"🌐 Server tool used: {block.name}")
                if tool_input:
                    logger.info(f"   Input: {tool_input}")

        # Log tool processing performance
        if tool_count > 0:
            latency_ms = (time.time() - start_time) * 1000
            logger.info(f"⚡ Processed {tool_count} tool call(s) in {latency_ms:.0f}ms")

        return tool_results

    def _extract_text_from_response(self, response_content: List[Any]) -> str:
        """Extract text content from Claude's response."""
        response_text = ""
        for block in response_content:
            if hasattr(block, "text") and block.text is not None:
                response_text += block.text
        return response_text
    
    def _call_claude(self, system_message: str, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]], max_tokens: int) -> Any:
        """Make a Claude API call - extracted for DRY principle"""
        start_time = time.time()
        
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system_message,
            messages=messages,
            tools=tools if tools else None,
        )
        
        # Calculate latency
        latency_ms = (time.time() - start_time) * 1000
        
        # Log performance metrics
        logger.info(f"⚡ Claude API call completed in {latency_ms:.0f}ms")
        logger.info(f"📊 Tokens - Input: {response.usage.input_tokens:,} | Output: {response.usage.output_tokens:,}")
        logger.info(f"🔄 Stop reason: {response.stop_reason}")
        
        return response

    def chat(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 2048,
        stream: bool = False,
    ) -> Dict[str, Any] | Generator[Dict[str, Any], None, None]:
        """
        Process a chat message and return response with tool use support.
        Implements an agentic loop that continues until the agent is satisfied.

        Args:
            messages: List of message dicts with 'role' and 'content'
            max_tokens: Maximum tokens for response
            stream: If True, yields streaming events; if False, returns complete response

        Returns:
            Dict with 'response' text and metadata about actions taken (if stream=False)
            Generator yielding events (if stream=True)
        """
        if stream:
            return self._chat_stream(messages, max_tokens)
        
        # Setup
        user_query = messages[-1]["content"] if messages else "No message"
        logger.info(f"=== New chat session ===")
        logger.info(f"User query: {user_query[:100]}...")

        system_message = self._build_system_message()
        tools = self.get_tools()
        logger.info(f"Available tools for this session: {len(tools)}")

        # Track all actions (plugin-agnostic)
        actions_metadata = {}

        # Agentic loop configuration
        iteration = 0
        max_iterations = 10
        response = None

        try:
            # Agentic loop: make calls until agent is satisfied
            while iteration < max_iterations:
                # Call Claude
                response = self._call_claude(system_message, messages, tools, max_tokens)

                # Check if Claude wants to use tools
                if response.stop_reason == "tool_use":
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
                else:
                    # Agent is satisfied, exit loop
                    break


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
    
    def _chat_stream(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 2048,
    ) -> Generator[Dict[str, Any], None, None]:
        """Streaming version of chat - uses Claude's native streaming for minimal latency"""
        # Setup
        user_query = messages[-1]["content"] if messages else "No message"
        logger.info(f"=== New streaming chat session ===")
        logger.info(f"User query: {user_query[:100]}...")

        system_message = self._build_system_message()
        tools = self.get_tools()

        # Track all actions
        actions_metadata = {}

        # Agentic loop configuration
        iteration = 0
        max_iterations = 10

        try:
            # Agentic loop: make calls until agent is satisfied
            while iteration < max_iterations:
                start_time = time.time()
                
                # Use native streaming from Anthropic
                with self.client.messages.stream(
                    model=self.model,
                    max_tokens=max_tokens,
                    system=system_message,
                    messages=messages,
                    tools=tools if tools else None,
                ) as stream:
                    # Log time to first token
                    first_token_time = None
                    response_text = ""
                    
                    # Stream text deltas as they arrive
                    for event in stream:
                        if event.type == "content_block_delta":
                            if event.delta.type == "text_delta":
                                if first_token_time is None:
                                    first_token_time = time.time()
                                    ttft_ms = (first_token_time - start_time) * 1000
                                    logger.info(f"⚡ Time to first token: {ttft_ms:.0f}ms (iteration {iteration})")
                                
                                # Stream ALL text from ALL LLM calls
                                yield {"type": "text_chunk", "text": event.delta.text}
                    
                    # Get the final message
                    final_message = stream.get_final_message()
                    
                    # Log performance
                    latency_ms = (time.time() - start_time) * 1000
                    logger.info(f"⚡ Total streaming completed in {latency_ms:.0f}ms")
                    logger.info(f"📊 Tokens - Input: {final_message.usage.input_tokens:,} | Output: {final_message.usage.output_tokens:,}")
                    logger.info(f"🔄 Stop reason: {final_message.stop_reason}")
                    
                    # Check for server tool usage in content
                    has_server_tools = any(block.type == "server_tool_use" for block in final_message.content)
                    if has_server_tools:
                        logger.info(f"🌐 Server tools detected in response")
                    
                    # Check if Claude wants to use tools OR used server tools
                    if final_message.stop_reason == "tool_use" or has_server_tools:
                        iteration += 1
                        logger.info(f"🔧 Agentic iteration {iteration}: Claude requested tool use")
                        
                        # Process tool calls
                        tool_results = self._process_tool_calls(
                            final_message.content, actions_metadata
                        )

                        # Append to conversation
                        messages.append({"role": "assistant", "content": final_message.content})
                        messages.append({"role": "user", "content": tool_results})
                        
                        # Mark current text as intermediate thinking (not final response)
                        yield {"type": "mark_thinking"}
                        
                        # Add separator for readability between iterations
                        yield {"type": "text_chunk", "text": "\n\n"}
                    else:
                        # Final response received, exit loop
                        break

            # Yield completion with metadata
            yield {"type": "done", "metadata": actions_metadata}
            
            logger.info(f"🎯 Completed in {iteration} agentic iterations")

        except Exception as e:
            logger.error(f"Error in streaming chat: {str(e)}")
            yield {"type": "error", "error": str(e)}

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
