import React, { useState, useRef, useEffect } from 'react';
import { Send, Loader, Sparkles } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import axios from 'axios';
import './ChatPanel.css';

const API_URL = 'http://localhost:8000/api';

function ChatPanel({ onChatAction }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

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
      
      const response = await axios.post(`${API_URL}/chat`, {
        messages: validMessages,
        include_notes: false,  // Agentic mode - let agent search when needed
      });

      // Only add assistant message if there's actual content
      if (response.data.response && response.data.response.trim()) {
        setMessages([...newMessages, {
          role: 'assistant',
          content: response.data.response,
        }]);
      }

      // Check if any actions were taken and notify parent
      const metadata = response.data.metadata || {};
      if (Object.keys(metadata).length > 0 && onChatAction) {
        // Notify parent component about all actions taken
        onChatAction(metadata);
      }
    } catch (error) {
      console.error('Error sending message:', error);
      
      // Show error in UI but don't add to message history
      // This prevents empty messages from being sent to Claude
      const errorMsg = error.response?.data?.detail || 'Sorry, I encountered an error. Please try again.';
      
      // Reset to just show the user message without broken assistant response
      setMessages(newMessages);
      
      // Show error temporarily (could use a toast notification instead)
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
          <div className="message assistant loading">
            <Loader size={16} className="spinner" />
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <form onSubmit={sendMessage} className="chat-input-form">
        <input
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

