# Pico - AI-Powered Personal Assistant

Pico is a minimalist note-taking app with an integrated AI assistant powered by Claude. Take notes, manage todos, and get intelligent assistance—all in one beautiful, distraction-free interface.

## Features

- **📝 Rich Text Note Taking**: Modern editor with seamless formatting
  - Bold, italic, strikethrough
  - Bullet lists and numbered lists
  - Headings (H1, H2, H3)
  - Multi-tab support
  - Paste from Google Docs OR Claude markdown - both work perfectly!
- **🤖 AI Assistant**: Chat with Pico, who has access to all your notes
- **✅ Todo Management**: Track tasks with an integrated todo list
- **📂 Notes Browser**: Easy access to all previously saved notes
- **🎨 Minimalist Design**: Beautiful, macOS-native aesthetic
- **💾 Local Storage**: All notes stored locally as files

## Setup

### Prerequisites

- **Conda** (Miniconda or Anaconda) - [Install Miniconda](https://www.anaconda.com/download)
- **Node.js 16+** - Install via `brew install node`
- **Anthropic API key** (Claude) - Get from [Anthropic Console](https://console.anthropic.com/)

#### Installing Miniconda (if not already installed)

**Quick Install (Terminal):**
```bash
mkdir -p ~/miniconda3
curl https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-arm64.sh -o ~/miniconda3/miniconda.sh
bash ~/miniconda3/miniconda.sh -b -u -p ~/miniconda3
rm ~/miniconda3/miniconda.sh
~/miniconda3/bin/conda init bash
~/miniconda3/bin/conda init zsh
```
*For Intel Macs, replace `arm64` with `x86_64`*

Then restart your terminal. You should see `(base)` in your prompt.

**Or use the graphical installer:**
Download from [anaconda.com/download](https://www.anaconda.com/download) and double-click the `.pkg` file.

### Quick Installation

Run the automated setup script:

```bash
cd Pico
./setup.sh
```

The setup script will:
1. Check for prerequisites (conda, node)
2. Prompt for your Anthropic API key
3. Create a conda environment named `pico`
4. Install all Python dependencies
5. Install all frontend dependencies
6. Set up data directories

### Manual Installation (if preferred)

1. **Set up environment variables:**
   ```bash
   echo "ANTHROPIC_API_KEY=your_api_key_here" > .env
   ```

2. **Create conda environment:**
   ```bash
   conda create -n pico python=3.11 -y
   conda activate pico
   ```

3. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Install frontend dependencies:**
   ```bash
   cd frontend
   npm install
   cd ..
   ```

### Running the App

**Easy way - Use the start script:**
```bash
./start.sh
```

**Manual way - Two terminals:**

**Terminal 1 - Backend:**
```bash
conda activate pico
python backend/main.py
```
The API will start on http://localhost:8000

**Terminal 2 - Frontend:**
```bash
cd frontend
npm start
```
The app will open in your browser at http://localhost:3000

## Usage

### Note Taking
- The main note is always open in the first tab
- **Modern rich text editor** with clean toolbar:
  - Headings (H1, H2, H3)
  - **Bold**, *Italic*, ~~Strikethrough~~
  - Bullet lists and numbered lists
- **Seamless paste from anywhere**:
  - **Google Docs/Word** → Formatting preserved automatically
  - **Claude/Markdown text** → Automatically converts to rich text
    - `# Header` becomes H1
    - `## Header` becomes H2
    - `**bold**` becomes bold
    - Lists convert automatically
  - Works intelligently - detects format and handles it properly!
- Create new tabs with the `+` button
- Click 📁 to browse and load previously saved notes
- Switch between tabs by clicking on them
- Close non-permanent tabs with the `×` button
- All notes auto-save as you type
- Powered by **TipTap** (modern ProseMirror-based editor)

### Todo List
- Add todos in the left panel
- Click the checkbox to mark as complete
- Hover and click trash icon to delete

### Chat with Pico
- Use the right panel to chat with Pico
- Pico has access to all your notes for context
- Ask for summaries, insights, or help organizing information
- Pico can help identify action items and suggest todos
- **Formatted responses**: Pico's messages support rich formatting:
  - Headings (##, ###)
  - **Bold** and *italic* text
  - Bullet and numbered lists
  - ✅ Checkboxes and task lists
  - Code blocks and inline `code`
  - Blockquotes and links

## Project Structure

```
Pico/
├── backend/
│   ├── main.py           # FastAPI backend server
│   ├── pico_agent.py     # AI agent with MCP client
│   ├── mcp_protocol.py   # Model Context Protocol implementation
│   └── plugins/          # Plugin module
│       ├── __init__.py   # Module exports
│       ├── base.py       # Plugin abstract base class
│       ├── utils.py      # Shared LLM utilities
│       ├── note_plugin.py      # Note management
│       ├── todo_plugin.py      # Todo management
│       └── preference_plugin.py # User preferences
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── components/   # React components
│   │   │   ├── TodoList.js
│   │   │   ├── NoteEditor.js
│   │   │   └── ChatPanel.js
│   │   ├── App.js
│   │   └── index.js
│   └── package.json
├── data/
│   ├── notes/           # Stored notes (auto-created)
│   └── todos.json       # Todo list (auto-created)
├── requirements.txt
└── README.md
```

## Backend Architecture

Pico uses a **Model Context Protocol (MCP)** architecture for loose coupling and extensibility:

### **MCP Protocol** (`mcp_protocol.py`)
Defines the communication layer between agent and plugins:

**MCPServer Interface:** Plugins implement this to expose their capabilities
- `list_tools()` - Expose functions the AI can call
- `call_tool()` - Execute a tool with arguments  
- `list_resources()` - Expose data resources
- `read_resource()` - Provide resource content

**MCPClient:** Agent uses this to discover and interact with plugins
- `register_server()` - Add a plugin server
- `discover_all_tools()` - Find all available tools
- `call_tool()` - Execute tools on behalf of the AI
- `get_all_context()` - Gather data from all resources

### **PicoAgent** (`pico_agent.py`)
The main AI assistant that:
- Understands user needs through chat
- Uses Claude's tool-calling to interact with MCP tools
- Automatically executes plugin functions when needed
- Manages context from MCP resources

### **Plugin Servers** (`plugins.py`)
Plugins implement both `Plugin` and `MCPServer` interfaces:

**NotePlugin** - Manages notes
- Tools: `search_notes`, `create_note`, `update_note`
- Resources: All user notes

**TodoPlugin** - Manages todos
- Tools: `create_todo`, `complete_todo`, `search_todos`
- Resources: Complete todo list

### **Why MCP?**

1. **Loose Coupling** - Agent discovers plugin capabilities at runtime
2. **Extensibility** - Add new plugins without changing agent code
3. **Standard Protocol** - Well-defined interface for all plugins
4. **Tool Use** - Claude can automatically call plugin functions
5. **Discoverability** - Agent can learn what each plugin does

### **Adding New Plugins**

Create a new file in `backend/plugins/`:

```python
# backend/plugins/my_plugin.py
from typing import List, Dict, Any
from mcp.types import Tool, Resource
from mcp_protocol import MCPServer, create_tool, create_resource
from .base import Plugin
from .utils import call_llm_for_json  # If you need LLM

class MyPlugin(Plugin, MCPServer):
    def get_name(self) -> str:
        return "MyPlugin"
    
    def list_tools(self) -> List[Tool]:
        return [create_tool(...)]
    
    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        # Handle tool execution
        pass
    
    # Implement other Plugin methods...

# In backend/plugins/__init__.py, add:
from .my_plugin import MyPlugin
__all__ = [..., 'MyPlugin']

# In backend/main.py, register:
my_plugin = MyPlugin()
mcp_client.register_server(my_plugin)
```

## Technology Stack

- **Backend**: Python, FastAPI, Anthropic Claude API, MCP Protocol
- **Frontend**: React, Axios, Lucide Icons, TipTap (modern rich text editor)
- **Storage**: Local file system (JSON)

## Tips

### Formatting Shortcuts

**Keyboard Shortcuts:**
- **Bold**: Cmd/Ctrl + B
- **Italic**: Cmd/Ctrl + I
- **Strikethrough**: Cmd/Ctrl + Shift + X
- **Bullet List**: Cmd/Ctrl + Shift + 8
- **Numbered List**: Cmd/Ctrl + Shift + 7

**Markdown Shortcuts (type and they auto-convert):**
- `# ` at start of line → Heading 1
- `## ` at start of line → Heading 2
- `### ` at start of line → Heading 3
- `**text**` → **Bold text**
- `*text*` → *Italic text*
- `~~text~~` → ~~Strikethrough~~
- `- ` at start of line → Bullet list
- `1. ` at start of line → Numbered list


### AI Assistant
- Use Pico to prepare for meetings by asking about previous conversations
- Draft ideas and get immediate feedback without leaving your notes
- Let Pico organize your chronological notes by topic
- Ask Pico to extract todos from your meeting notes

## Development

To contribute or modify:

1. Backend changes: Edit `backend/main.py`
2. Frontend changes: Edit files in `frontend/src/`
3. The backend runs on port 8000, frontend on port 3000
4. CORS is configured to allow communication between them

## License

MIT License - feel free to use and modify as needed!

