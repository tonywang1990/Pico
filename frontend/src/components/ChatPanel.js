import React, { useState, useRef, useEffect } from 'react';
import { Send, Loader, Sparkles } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import './ChatPanel.css';

const API_URL = 'http://localhost:8000/api';

function ChatPanel({ onChatAction }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);


  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Keyboard shortcut: Cmd+K to focus chat input
  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        inputRef.current?.focus();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const sendMessage = async (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage = { role: 'user', content: input.trim() };
    const newMessages = [...messages, userMessage];
    setMessages(newMessages);
    setInput('');
    setIsLoading(true);

    try {
      // Filter out any messages with empty content before sending
      const validMessages = newMessages.filter(msg => msg.content && msg.content.trim() !== '');
      
      // Use non-streaming endpoint
      const response = await fetch(`${API_URL}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          messages: validMessages,
          include_notes: false,  // Agentic mode - let agent search when needed
        }),
      });

      if (!response.ok) {
        throw new Error('Network response was not ok');
      }

      const data = await response.json();
      
      // Add assistant message if there's content
      if (data.response && data.response.trim()) {
        setMessages([...newMessages, {
          role: 'assistant',
          content: data.response,
        }]);
      }

      // Notify parent about actions
      if (data.metadata && Object.keys(data.metadata).length > 0 && onChatAction) {
        onChatAction(data.metadata);
      }

    } catch (error) {
      console.error('Error sending message:', error);
      
      const errorMsg = error.message || 'Sorry, I encountered an error. Please try again.';
      setMessages(newMessages);
      
      setTimeout(() => {
        alert(`Error: ${errorMsg}`);
      }, 100);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="chat-panel">
      <div className="chat-header">
        <div className="chat-title-row">
          <Sparkles size={16} className="chat-icon" />
          <h2>Pico</h2>
        </div>
        <p className="chat-subtitle">AI personal assistant, yours truly</p>
      </div>

      <div className="messages">
        {messages.length === 0 && (
          <div className="empty-chat">
            <p>👋 Hi! I'm Pico, your personal assistant.</p>
            <p>I have access to all your notes and can help you organize, summarize, and find information.</p>
            <p className="keyboard-hint">Press <kbd>⌘K</kbd> anytime to start chatting</p>
          </div>
        )}
        {messages.map((msg, idx) => (
          <div key={idx} className={`message ${msg.role}`}>
            <div className="message-content">
              {msg.role === 'assistant' ? (
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {msg.content}
                </ReactMarkdown>
              ) : (
                msg.content
              )}
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="thinking-indicator">
            <Loader size={14} className="spinner" />
            <span>Thinking...</span>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <form onSubmit={sendMessage} className="chat-input-form">
        <input
          ref={inputRef}
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask Pico anything..."
          className="chat-input"
          disabled={isLoading}
        />
        <button type="submit" className="send-btn" disabled={isLoading || !input.trim()}>
          <Send size={18} />
        </button>
      </form>
    </div>
  );
}

export default ChatPanel;

