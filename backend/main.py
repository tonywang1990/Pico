from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os
from pathlib import Path
from dotenv import load_dotenv

# Import our MCP architecture
from plugins import NotePlugin, TodoPlugin, PreferencePlugin
from pico_agent import PicoAgent
from mcp_protocol import MCPClient

load_dotenv()

# Get absolute paths relative to project root with validation
def get_project_root() -> Path:
    """
    Get project root directory with validation.
    Looks for marker files to confirm we found the right directory.
    """
    # Start from this file's directory
    current = Path(__file__).resolve().parent
    
    # Go up to find project root (look for setup.sh or README.md as markers)
    for parent in [current, current.parent, current.parent.parent]:
        if (parent / "setup.sh").exists() and (parent / "README.md").exists():
            return parent
    
    # If we can't find the project root, raise an exception
    raise RuntimeError("Could not determine project root directory. Please ensure 'setup.sh' and 'README.md' exist in the project root.")

PROJECT_ROOT = get_project_root()
DATA_DIR = PROJECT_ROOT / "data"
NOTES_DIR = DATA_DIR / "notes"
TODOS_FILE = DATA_DIR / "todos.json"
PREFERENCES_FILE = DATA_DIR / "preferences.json"

# Ensure data directories exist
DATA_DIR.mkdir(exist_ok=True)
NOTES_DIR.mkdir(exist_ok=True)

print(f"📁 Project root: {PROJECT_ROOT}")
print(f"📁 Data directory: {DATA_DIR}")

app = FastAPI(title="Pico - Personal Assistant")

# CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize plugin servers (MCP Servers) with absolute paths
note_plugin = NotePlugin(str(NOTES_DIR))
todo_plugin = TodoPlugin(
    todos_file=str(TODOS_FILE),
    anthropic_api_key=os.getenv("ANTHROPIC_API_KEY")  # For AI-based search
)
preference_plugin = PreferencePlugin(
    preferences_file=str(PREFERENCES_FILE),
    anthropic_api_key=os.getenv("ANTHROPIC_API_KEY")  # For AI-based preference merging
)

# Initialize MCP Client and register servers
mcp_client = MCPClient()
mcp_client.register_server(preference_plugin)  # Register first so preferences load early
mcp_client.register_server(note_plugin)
mcp_client.register_server(todo_plugin)

# Initialize Pico Agent with MCP Client
pico_agent = PicoAgent(
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    mcp_client=mcp_client
)

# Models
class Note(BaseModel):
    id: str
    title: str
    content: str
    created_at: str
    updated_at: str

class Todo(BaseModel):
    id: str
    text: str
    completed: bool
    created_at: str
    priority: Optional[str] = "medium"
    due_date: Optional[str] = None
    tags: Optional[list] = []

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]

# Routes
@app.get("/")
async def root():
    return {"message": "Pico API is running"}

# Notes endpoints - using NotePlugin
@app.get("/api/notes")
async def get_notes():
    return note_plugin.get_all()

@app.get("/api/notes/{note_id}")
async def get_note(note_id: str):
    note = note_plugin.get(note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note

@app.post("/api/notes")
async def create_note(note: Note):
    return note_plugin.create(**note.dict())

@app.put("/api/notes/{note_id}")
async def update_note(note_id: str, note: Note):
    try:
        return note_plugin.update(note_id, **note.dict())
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.delete("/api/notes/{note_id}")
async def delete_note(note_id: str):
    success = note_plugin.delete(note_id)
    if success:
        return {"message": "Note deleted"}
    raise HTTPException(status_code=404, detail="Note not found")

# Todos endpoints - using TodoPlugin
@app.get("/api/todos")
async def get_todos():
    return todo_plugin.get_all()

@app.post("/api/todos")
async def create_todo(todo: Todo):
    return todo_plugin.create(**todo.dict())

@app.put("/api/todos/{todo_id}")
async def update_todo(todo_id: str, todo: Todo):
    try:
        return todo_plugin.update(todo_id, **todo.dict())
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.delete("/api/todos/{todo_id}")
async def delete_todo(todo_id: str):
    success = todo_plugin.delete(todo_id)
    if success:
        return {"message": "Todo deleted"}
    raise HTTPException(status_code=404, detail="Todo not found")

# Chat endpoint - using PicoAgent
@app.post("/api/chat")
async def chat(request: ChatRequest):
    try:
        # Convert messages to format expected by agent
        messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]
        
        # Use Pico Agent to process the chat
        result = pico_agent.chat(messages=messages)

        return {
            "response": result["response"],
            "model": pico_agent.model,
            "metadata": result.get("metadata", {})
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

