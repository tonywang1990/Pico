import React, { useState, useRef, useEffect } from 'react';
import { Send, Loader, Sparkles, Wrench, CheckCircle, XCircle, ChevronDown, ChevronUp, Clock, Zap, Activity } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import './ChatPanel.css';

const API_URL = 'http://localhost:8000/api';

function ChatPanel({ onChatAction }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [thinkingSteps, setThinkingSteps] = useState([]);
  const [expandedProfiling, setExpandedProfiling] = useState({});
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const toggleProfiling = (index) => {
    setExpandedProfiling(prev => ({
      ...prev,
      [index]: !prev[index]
    }));
  };

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
    setThinkingSteps([]);

    try {
      // Filter out any messages with empty content before sending
      const validMessages = newMessages.filter(msg => msg.content && msg.content.trim() !== '');
      
      // Use streaming endpoint
      const response = await fetch(`${API_URL}/chat/stream`, {
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

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let assistantResponse = '';
      let metadata = {};
      let profiling = null;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = JSON.parse(line.slice(6));
            
            switch (data.type) {
              case 'thinking':
                setThinkingSteps(prev => [...prev, { type: 'thinking', timestamp: Date.now() }]);
                break;
              
              case 'tool_call':
                setThinkingSteps(prev => [...prev, {
                  type: 'tool_call',
                  tool: data.tool,
                  args: data.args,
                  timestamp: Date.now()
                }]);
                break;
              
              case 'tool_result':
                setThinkingSteps(prev => [...prev, {
                  type: 'tool_result',
                  tool: data.tool,
                  success: data.success,
                  result: data.result,
                  error: data.error,
                  timestamp: Date.now()
                }]);
                break;
              
              case 'response':
                assistantResponse = data.text;
                break;
              
              case 'done':
                metadata = data.metadata || {};
                profiling = data.profiling || null;
                break;
              
              case 'error':
                throw new Error(data.error);
              
              default:
                // Ignore unknown event types
                break;
            }
          }
        }
      }

      // Add assistant message if there's content
      if (assistantResponse && assistantResponse.trim()) {
        console.log('Profiling data received:', profiling);
        setMessages([...newMessages, {
          role: 'assistant',
          content: assistantResponse,
          profiling: profiling,
        }]);
      }

      // Notify parent about actions
      if (Object.keys(metadata).length > 0 && onChatAction) {
        onChatAction(metadata);
      }

      // Clear thinking steps after a delay
      setTimeout(() => {
        setThinkingSteps([]);
      }, 2000);

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
            {msg.role === 'assistant' && (() => {
              console.log('Message profiling check:', {
                hasRole: msg.role === 'assistant',
                hasProfiling: !!msg.profiling,
                hasTimeline: msg.profiling?.timeline ? true : false,
                profiling: msg.profiling
              });
              return msg.profiling && msg.profiling.timeline;
            })() && (
              <div className="profiling-section">
                <button 
                  className="profiling-toggle"
                  onClick={() => toggleProfiling(idx)}
                >
                  <Activity size={12} />
                  <span>Performance details</span>
                  {expandedProfiling[idx] ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                </button>
                
                {expandedProfiling[idx] && (
                  <div className="profiling-details">
                    <div className="profiling-summary">
                      <div className="profiling-stat">
                        <Clock size={14} />
                        <span className="stat-label">Total Duration</span>
                        <span className="stat-value">{msg.profiling.total_duration_ms}ms</span>
                      </div>
                      <div className="profiling-stat">
                        <Zap size={14} />
                        <span className="stat-label">LLM Calls</span>
                        <span className="stat-value">
                          {msg.profiling.timeline.filter(c => c.type === 'llm').length}
                        </span>
                      </div>
                      <div className="profiling-stat">
                        <Wrench size={14} />
                        <span className="stat-label">Tool Calls</span>
                        <span className="stat-value">
                          {msg.profiling.timeline.filter(c => c.type === 'tool').length}
                        </span>
                      </div>
                    </div>

                    <div className="profiling-tokens">
                      <div className="token-stat">
                        <span className="token-label">Input Tokens</span>
                        <span className="token-value">{msg.profiling.total_input_tokens.toLocaleString()}</span>
                      </div>
                      <div className="token-stat">
                        <span className="token-label">Output Tokens</span>
                        <span className="token-value">{msg.profiling.total_output_tokens.toLocaleString()}</span>
                      </div>
                      <div className="token-stat total">
                        <span className="token-label">Total</span>
                        <span className="token-value">
                          {(msg.profiling.total_input_tokens + msg.profiling.total_output_tokens).toLocaleString()}
                        </span>
                      </div>
                    </div>

                    {msg.profiling.timeline.length > 0 && (
                      <div className="profiling-breakdown">
                        <div className="breakdown-title">Call Timeline</div>
                        {msg.profiling.timeline.map((call, i) => (
                          <div key={i} className={`breakdown-item ${call.type}`}>
                            <span className="item-sequence">#{call.sequence}</span>
                            {call.type === 'llm' ? (
                              <>
                                <Zap size={12} className="item-icon" />
                                <span className="item-label">LLM (iter {call.iteration})</span>
                                <span className="item-value">{call.duration_ms}ms</span>
                                <span className="item-tokens">
                                  {call.input_tokens} in / {call.output_tokens} out
                                </span>
                              </>
                            ) : (
                              <>
                                <Wrench size={12} className="item-icon" />
                                <span className="item-label">{call.tool}</span>
                                <span className="item-value">{call.duration_ms}ms</span>
                                <span className={`item-status ${call.success ? 'success' : 'error'}`}>
                                  {call.success ? '✓' : '✗'}
                                </span>
                              </>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
        {isLoading && (
          <div className="message assistant thinking-container">
            {thinkingSteps.map((step, idx) => (
              <div key={idx} className="thinking-step">
                {step.type === 'thinking' && (
                  <div className="thinking-indicator">
                    <Loader size={14} className="spinner" />
                    <span>Thinking...</span>
                  </div>
                )}
                {step.type === 'tool_call' && (
                  <div className="tool-call">
                    <Wrench size={14} />
                    <span>Calling <strong>{step.tool}</strong></span>
                  </div>
                )}
                {step.type === 'tool_result' && (
                  <div className={`tool-result ${step.success ? 'success' : 'error'}`}>
                    {step.success ? (
                      <>
                        <CheckCircle size={14} />
                        <span><strong>{step.tool}</strong> completed</span>
                      </>
                    ) : (
                      <>
                        <XCircle size={14} />
                        <span><strong>{step.tool}</strong> failed</span>
                      </>
                    )}
                  </div>
                )}
              </div>
            ))}
            {thinkingSteps.length === 0 && (
              <div className="thinking-indicator">
                <Loader size={14} className="spinner" />
                <span>Starting...</span>
              </div>
            )}
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

