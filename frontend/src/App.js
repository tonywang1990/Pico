import React, { useState, useEffect } from 'react';
import './App.css';
import TodoList from './components/TodoList';
import NoteEditor from './components/NoteEditor';
import ChatPanel from './components/ChatPanel';
import axios from 'axios';

const API_URL = 'http://localhost:8000/api';

function App() {
  const [todos, setTodos] = useState([]);
  const [notes, setNotes] = useState([]);
  const [activeTab, setActiveTab] = useState(null);
  const [tabs, setTabs] = useState([]);
  const [chatPanelWidth, setChatPanelWidth] = useState(500); // Default 500px (increased from 400px)
  const [todoListWidth, setTodoListWidth] = useState(380); // Default 380px (increased from 300px)
  const [isResizingChat, setIsResizingChat] = useState(false);
  const [isResizingTodo, setIsResizingTodo] = useState(false);
  const [darkMode, setDarkMode] = useState(() => {
    // Load from localStorage or default to false
    const saved = localStorage.getItem('darkMode');
    return saved ? JSON.parse(saved) : false;
  });

  useEffect(() => {
    loadTodos();
    loadNotes();
  }, []);

  useEffect(() => {
    // Apply dark mode class to document
    if (darkMode) {
      document.documentElement.classList.add('dark-mode');
    } else {
      document.documentElement.classList.remove('dark-mode');
    }
    // Save to localStorage
    localStorage.setItem('darkMode', JSON.stringify(darkMode));
  }, [darkMode]);

  const toggleDarkMode = () => {
    setDarkMode(!darkMode);
  };

  const loadNoteInTab = (noteId) => {
    const note = notes.find(n => n.id === noteId);
    if (!note) return;
    
    // Check if tab already exists
    const existingTab = tabs.find(t => t.id === noteId);
    if (existingTab) {
      setActiveTab(noteId);
      return;
    }
    
    // Create new tab for the note
    const isMain = noteId === 'main';
    const newTab = {
      id: note.id,
      title: note.title,
      isPermanent: isMain
    };
    
    setTabs([...tabs, newTab]);
    setActiveTab(note.id);
  };

  const handleChatActions = async (metadata) => {
    // Handle all actions from chat metadata
    try {
      // Refresh todos if any were created or updated
      if (metadata.created_todos || metadata.updated_todos || metadata.deleted_todos) {
        console.log('Refreshing todos due to chat actions...');
        await loadTodos();
      }
      
      // Refresh and open notes if any were created
      if (metadata.created_notes && metadata.created_notes.length > 0) {
        console.log('Refreshing notes due to chat actions...');
        const response = await axios.get(`${API_URL}/notes`);
        let allNotes = response.data;
        
        // Sort notes with main note first
        allNotes.sort((a, b) => {
          if (a.id === 'main') return -1;
          if (b.id === 'main') return 1;
          return new Date(b.updated_at) - new Date(a.updated_at);
        });
        
        setNotes(allNotes);
        
        // Open the first newly created note
        const noteId = metadata.created_notes[0];
        const newNote = allNotes.find(n => n.id === noteId);
        if (newNote) {
          // Check if tab already exists
          const existingTab = tabs.find(t => t.id === noteId);
          if (existingTab) {
            setActiveTab(noteId);
          } else {
            // Create new tab for the note
            const newTab = {
              id: newNote.id,
              title: newNote.title,
              isPermanent: false
            };
            setTabs([...tabs, newTab]);
            setActiveTab(newNote.id);
          }
        }
      }
      // Refresh notes list if any were updated (but don't switch tabs)
      else if (metadata.updated_notes && metadata.updated_notes.length > 0) {
        console.log('Refreshing notes due to updates...');
        await loadNotes();
      }
    } catch (error) {
      console.error('Error handling chat actions:', error);
    }
  };

  const loadTodos = async () => {
    try {
      const response = await axios.get(`${API_URL}/todos`);
      setTodos(response.data);
    } catch (error) {
      console.error('Error loading todos:', error);
    }
  };

  const loadNotes = async () => {
    try {
      const response = await axios.get(`${API_URL}/notes`);
      let allNotes = response.data;
      
      // Ensure main note exists
      let mainNote = allNotes.find(n => n.id === 'main');
      if (!mainNote) {
        mainNote = {
          id: 'main',
          title: 'Main Note',
          content: '',
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        };
        await axios.post(`${API_URL}/notes`, mainNote);
        allNotes = [mainNote, ...allNotes];
      }
      
      // Sort notes with main note first
      allNotes.sort((a, b) => {
        if (a.id === 'main') return -1;
        if (b.id === 'main') return 1;
        return new Date(b.updated_at) - new Date(a.updated_at);
      });
      
      setNotes(allNotes);
      
      // Always open main note by default
      if (tabs.length === 0) {
        setTabs([{ id: 'main', title: 'Main Note', isPermanent: true }]);
        setActiveTab('main');
      }
    } catch (error) {
      console.error('Error loading notes:', error);
    }
  };


  const toggleTodo = async (id) => {
    const todo = todos.find(t => t.id === id);
    if (todo) {
      const updated = { ...todo, completed: !todo.completed };
      try {
        // Update backend first
        const response = await axios.put(`${API_URL}/todos/${id}`, updated);
        // Use the response from backend to ensure consistency
        setTodos(todos.map(t => t.id === id ? response.data : t));
        console.log('Todo toggled:', response.data);
      } catch (error) {
        console.error('Error updating todo:', error);
        // Reload todos on error to ensure consistency
        loadTodos();
      }
    }
  };

  const deleteTodo = async (id) => {
    try {
      await axios.delete(`${API_URL}/todos/${id}`);
      setTodos(todos.filter(t => t.id !== id));
    } catch (error) {
      console.error('Error deleting todo:', error);
    }
  };

  const updateNote = async (id, content) => {
    const note = notes.find(n => n.id === id);
    if (note) {
      const updated = {
        ...note,
        content,
        updated_at: new Date().toISOString(),
      };
      try {
        await axios.put(`${API_URL}/notes/${id}`, updated);
        // Update and re-sort notes by updated time (main note always first)
        const updatedNotes = notes.map(n => n.id === id ? updated : n);
        updatedNotes.sort((a, b) => {
          if (a.id === 'main') return -1;
          if (b.id === 'main') return 1;
          return new Date(b.updated_at) - new Date(a.updated_at);
        });
        setNotes(updatedNotes);
      } catch (error) {
        console.error('Error updating note:', error);
      }
    }
  };

  const updateNoteTitle = async (id, title) => {
    const note = notes.find(n => n.id === id);
    if (note) {
      const updated = {
        ...note,
        title,
        updated_at: new Date().toISOString(),
      };
      try {
        await axios.put(`${API_URL}/notes/${id}`, updated);
        // Update and re-sort notes by updated time (main note always first)
        const updatedNotes = notes.map(n => n.id === id ? updated : n);
        updatedNotes.sort((a, b) => {
          if (a.id === 'main') return -1;
          if (b.id === 'main') return 1;
          return new Date(b.updated_at) - new Date(a.updated_at);
        });
        setNotes(updatedNotes);
        // Also update the tab title
        setTabs(tabs.map(t => t.id === id ? { ...t, title } : t));
      } catch (error) {
        console.error('Error updating note title:', error);
      }
    }
  };

  const createTab = (title = 'New Tab') => {
    const newNote = {
      id: `tab-${Date.now()}`,
      title,
      content: '',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    
    axios.post(`${API_URL}/notes`, newNote)
      .then(() => {
        setNotes([...notes, newNote]);
        setTabs([...tabs, { id: newNote.id, title, isPermanent: false }]);
        setActiveTab(newNote.id);
      })
      .catch(error => console.error('Error creating tab:', error));
  };

  const closeTab = async (tabId) => {
    if (tabs.find(t => t.id === tabId)?.isPermanent) return;
    
    // Check if the note is empty before closing
    const note = notes.find(n => n.id === tabId);
    if (note) {
      // Consider a note empty if content is empty or only contains whitespace/empty HTML
      const isEmpty = !note.content || 
                      note.content.trim() === '' || 
                      note.content === '<p></p>' ||
                      note.content.replace(/<[^>]*>/g, '').trim() === '';
      
      if (isEmpty) {
        // Delete the empty note
        try {
          await axios.delete(`${API_URL}/notes/${tabId}`);
          setNotes(notes.filter(n => n.id !== tabId));
          console.log(`Deleted empty note: ${tabId}`);
        } catch (error) {
          console.error('Error deleting empty note:', error);
        }
      }
    }
    
    // Close the tab
    setTabs(tabs.filter(t => t.id !== tabId));
    if (activeTab === tabId) {
      const remainingTabs = tabs.filter(t => t.id !== tabId);
      setActiveTab(remainingTabs.length > 0 ? remainingTabs[0].id : null);
    }
  };

  const activeNote = notes.find(n => n.id === activeTab);

  // Chat panel resize handlers
  const handleChatMouseDown = (e) => {
    setIsResizingChat(true);
    e.preventDefault();
  };

  const handleChatMouseMove = (e) => {
    if (isResizingChat) {
      const newWidth = window.innerWidth - e.clientX;
      if (newWidth >= 300 && newWidth <= 800) { // Min 300px, Max 800px
        setChatPanelWidth(newWidth);
      }
    }
  };

  const handleChatMouseUp = () => {
    setIsResizingChat(false);
  };

  // Todo list resize handlers
  const handleTodoMouseDown = (e) => {
    setIsResizingTodo(true);
    e.preventDefault();
  };

  const handleTodoMouseMove = (e) => {
    if (isResizingTodo) {
      const newWidth = e.clientX;
      if (newWidth >= 250 && newWidth <= 500) { // Min 250px, Max 500px
        setTodoListWidth(newWidth);
      }
    }
  };

  const handleTodoMouseUp = () => {
    setIsResizingTodo(false);
  };

  useEffect(() => {
    if (isResizingChat) {
      document.addEventListener('mousemove', handleChatMouseMove);
      document.addEventListener('mouseup', handleChatMouseUp);
      return () => {
        document.removeEventListener('mousemove', handleChatMouseMove);
        document.removeEventListener('mouseup', handleChatMouseUp);
      };
    }
  }, [isResizingChat, chatPanelWidth]);

  useEffect(() => {
    if (isResizingTodo) {
      document.addEventListener('mousemove', handleTodoMouseMove);
      document.addEventListener('mouseup', handleTodoMouseUp);
      return () => {
        document.removeEventListener('mousemove', handleTodoMouseMove);
        document.removeEventListener('mouseup', handleTodoMouseUp);
      };
    }
  }, [isResizingTodo, todoListWidth]);

  return (
    <div className="app">
      <div className="todo-panel-container" style={{ width: `${todoListWidth}px` }}>
        <TodoList
          todos={todos}
          onToggleTodo={toggleTodo}
          onDeleteTodo={deleteTodo}
        />
        <div 
          className="todo-resizer" 
          onMouseDown={handleTodoMouseDown}
          style={{ cursor: isResizingTodo ? 'col-resize' : 'col-resize' }}
        />
      </div>
      
      <div className="main-content">
        <NoteEditor
          note={activeNote}
          tabs={tabs}
          activeTab={activeTab}
          notes={notes}
          onTabChange={setActiveTab}
          onCreateTab={createTab}
          onCloseTab={closeTab}
          onUpdateNote={updateNote}
          onUpdateTitle={updateNoteTitle}
          onLoadNote={loadNoteInTab}
          darkMode={darkMode}
          onToggleDarkMode={toggleDarkMode}
        />
      </div>

      <div className="chat-panel-container" style={{ width: `${chatPanelWidth}px` }}>
        <div 
          className="chat-resizer" 
          onMouseDown={handleChatMouseDown}
          style={{ cursor: isResizingChat ? 'col-resize' : 'col-resize' }}
        />
        <ChatPanel onChatAction={handleChatActions} />
      </div>
    </div>
  );
}

export default App;

