# Pico Agent Logging

Comprehensive logging has been added to track tool usage and agent behavior during chat sessions.

## What Gets Logged

### **1. Initialization**
When the backend starts:
```
INFO - PicoAgent initialized with 2 MCP servers: ['Notes', 'Todos']
INFO - Discovered 6 tools: ['search_notes', 'create_note', 'update_note', 'create_todo', 'complete_todo', 'search_todos']
```

### **2. Chat Session Start**
Every time a user sends a message:
```
INFO - === New chat session ===
INFO - User query: Can you search my notes for meetings about the Q4 planning?...
INFO - Available tools for this session: 6
INFO - Claude response stop_reason: tool_use
```

### **3. Tool Execution**
When Claude decides to use a tool:
```
INFO - 🔧 Claude requested tool use
INFO - 📞 Calling tool: search_notes
INFO -    Arguments: {
  "query": "Q4 planning meeting"
}
INFO - ✅ Tool search_notes executed successfully
INFO -    Result: [{"id": "note-123", "title": "Q4 Planning Meeting", "content": "..."}]...
```

### **4. Tool Results**
After tools execute:
```
INFO - 🔄 Sending 1 tool results back to Claude
INFO - Final response stop_reason: end_turn
```

### **5. Session Complete**
At the end of each chat:
```
INFO - 💬 Response length: 524 characters
INFO - === Chat session complete ===
```

### **6. Error Handling**
If a tool fails:
```
ERROR - ❌ Tool create_note failed: Missing required parameter 'title'
```

## Log Icons

- **🔧** Tool use requested
- **📞** Calling a specific tool
- **✅** Tool succeeded
- **❌** Tool failed
- **🔄** Sending results back to Claude
- **💬** Final response ready

## Example Full Session

```
2025-10-04 15:32:10 - pico_agent - INFO - === New chat session ===
2025-10-04 15:32:10 - pico_agent - INFO - User query: Find my notes about emotes project...
2025-10-04 15:32:10 - pico_agent - INFO - Available tools for this session: 6
2025-10-04 15:32:12 - pico_agent - INFO - Claude response stop_reason: tool_use
2025-10-04 15:32:12 - pico_agent - INFO - 🔧 Claude requested tool use
2025-10-04 15:32:12 - pico_agent - INFO - 📞 Calling tool: search_notes
2025-10-04 15:32:12 - pico_agent - INFO -    Arguments: {
  "query": "emotes"
}
2025-10-04 15:32:12 - pico_agent - INFO - ✅ Tool search_notes executed successfully
2025-10-04 15:32:12 - pico_agent - INFO -    Result: [{"id": "tab-1234", "title": "Emotes Project Notes", "content": "## Current Status..."}]...
2025-10-04 15:32:12 - pico_agent - INFO - 🔄 Sending 1 tool results back to Claude
2025-10-04 15:32:14 - pico_agent - INFO - Final response stop_reason: end_turn
2025-10-04 15:32:14 - pico_agent - INFO - 💬 Response length: 856 characters
2025-10-04 15:32:14 - pico_agent - INFO - === Chat session complete ===
```

## Viewing Logs

### **In Terminal**
When you run the backend, you'll see logs in real-time:
```bash
python3 backend/main.py
```

### **Filter for Tool Usage**
To see only tool-related logs:
```bash
python3 backend/main.py 2>&1 | grep -E "tool|Tool|🔧|📞"
```

### **Filter for Errors**
To see only errors:
```bash
python3 backend/main.py 2>&1 | grep -E "ERROR|❌"
```

## Benefits

1. **Debugging** - See exactly what Claude is doing
2. **Performance** - Track tool execution time
3. **Monitoring** - Catch errors in real-time
4. **Understanding** - Learn how Claude uses tools
5. **Development** - Verify plugin behavior

## Adjusting Log Level

To change verbosity, edit `pico_agent.py`:

```python
# More detailed (DEBUG level)
logging.basicConfig(level=logging.DEBUG, ...)

# Less verbose (WARNING level)
logging.basicConfig(level=logging.WARNING, ...)
```

Happy debugging! 🐛
