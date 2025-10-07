import React, { useState, useEffect, useRef } from 'react';
import { Plus, X, FolderOpen, Bold, Italic, Strikethrough, List, ListOrdered, Heading1, Heading2, Heading3, Edit2, Moon, Sun } from 'lucide-react';
import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import Placeholder from '@tiptap/extension-placeholder';
import Typography from '@tiptap/extension-typography';
import Link from '@tiptap/extension-link';
import './NoteEditor.css';

function NoteEditor({ note, tabs, activeTab, notes, onTabChange, onCreateTab, onCloseTab, onUpdateNote, onUpdateTitle, onLoadNote, darkMode, onToggleDarkMode }) {
  const [showNotesMenu, setShowNotesMenu] = useState(false);
  const [editingTabId, setEditingTabId] = useState(null);
  const [editingTitle, setEditingTitle] = useState('');
  const titleInputRef = useRef(null);

  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        heading: {
          levels: [1, 2, 3],
        },
      }),
      Placeholder.configure({
        placeholder: 'Start typing your notes... Paste from Google Docs or Claude works seamlessly!',
      }),
      Typography, // Auto-converts markdown syntax like ## to headings
      Link.configure({
        openOnClick: true,
        autolink: true, // Automatically detect and linkify URLs
        linkOnPaste: true, // Convert pasted URLs to links
        HTMLAttributes: {
          target: '_blank',
          rel: 'noopener noreferrer',
          class: 'note-link',
        },
      }),
    ],
    content: '',
    onUpdate: ({ editor }) => {
      if (note) {
        const html = editor.getHTML();
        onUpdateNote(note.id, html);
      }
    },
    editorProps: {
      attributes: {
        class: 'tiptap-editor-content',
      },
      handlePaste: (view, event, slice) => {
        const text = event.clipboardData?.getData('text/plain');
        const html = event.clipboardData?.getData('text/html');
        
        // If there's HTML (from Google Docs, etc.), let TipTap handle it normally
        if (html && html.trim() && !text.includes('#') && !text.includes('**')) {
          return false; // Let default handler work
        }
        
        // If text looks like markdown, convert it
        if (text && text.trim()) {
          const hasMarkdown = 
            /^#{1,6}\s/m.test(text) ||
            /\*\*[^*]+\*\*/.test(text) ||
            /\*[^*]+\*/.test(text) ||
            /^[-*+]\s/m.test(text) ||
            /^\d+\.\s/m.test(text);
          
          if (hasMarkdown) {
            // Convert markdown to HTML using marked
            import('marked').then(({ marked }) => {
              const htmlContent = marked.parse(text, {
                breaks: true,
                gfm: true
              });
              
              // Insert HTML at current position
              const { state } = view;
              const { $from } = state.selection;
              
              // Create a temporary div to parse HTML
              const tempDiv = document.createElement('div');
              tempDiv.innerHTML = htmlContent;
              
              // Use TipTap's command to insert the content
              editor.chain().focus().insertContent(htmlContent).run();
            });
            
            return true; // Prevent default paste
          }
        }
        
        return false; // Let default handler work for plain text
      },
    },
  });

  useEffect(() => {
    if (editor && note) {
      // Only update if content actually changed to avoid cursor jumping
      const currentContent = editor.getHTML();
      if (currentContent !== note.content) {
        let contentToSet = note.content || '';
        
        // Check if content has raw markdown inside HTML tags (broken format)
        // This happens when markdown was pasted but not converted
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = contentToSet;
        const textContent = tempDiv.textContent || '';
        
        // If the text content has markdown syntax but it's wrapped in basic HTML
        if (textContent.includes('#') || textContent.includes('**')) {
          const hasMarkdown = 
            /^#{1,6}\s/m.test(textContent) ||
            /\*\*[^*]+\*\*/.test(textContent) ||
            /^[-*+]\s/m.test(textContent);
          
          if (hasMarkdown) {
            // Convert the markdown text to proper HTML
            import('marked').then(({ marked }) => {
              const properHtml = marked.parse(textContent, {
                breaks: true,
                gfm: true
              });
              editor.commands.setContent(properHtml);
            });
            return;
          }
        }
        
        editor.commands.setContent(contentToSet);
      }
    }
  }, [note, editor]);

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);
    
    if (diffMins < 1) return 'just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  };

  const handleLoadNote = (noteId) => {
    onLoadNote(noteId);
    setShowNotesMenu(false);
  };

  const startEditingTitle = (tabId, currentTitle, e) => {
    e.stopPropagation();
    setEditingTabId(tabId);
    setEditingTitle(currentTitle);
  };

  const saveTitle = (tabId) => {
    if (editingTitle.trim() && editingTitle !== tabs.find(t => t.id === tabId)?.title) {
      onUpdateTitle(tabId, editingTitle.trim());
    }
    setEditingTabId(null);
  };

  const handleTitleKeyDown = (e, tabId) => {
    if (e.key === 'Enter') {
      saveTitle(tabId);
    } else if (e.key === 'Escape') {
      setEditingTabId(null);
    }
  };

  useEffect(() => {
    if (editingTabId && titleInputRef.current) {
      titleInputRef.current.focus();
      titleInputRef.current.select();
    }
  }, [editingTabId]);

  if (!editor) {
    return null;
  }

  return (
    <div className="note-editor">
      <div className="tabs-bar">
        <div className="tabs">
          {tabs.map((tab) => (
            <div
              key={tab.id}
              className={`tab ${activeTab === tab.id ? 'active' : ''}`}
              onClick={() => onTabChange(tab.id)}
            >
              {editingTabId === tab.id ? (
                <input
                  ref={titleInputRef}
                  type="text"
                  className="tab-title-input"
                  value={editingTitle}
                  onChange={(e) => setEditingTitle(e.target.value)}
                  onBlur={() => saveTitle(tab.id)}
                  onKeyDown={(e) => handleTitleKeyDown(e, tab.id)}
                  onClick={(e) => e.stopPropagation()}
                />
              ) : (
                <>
                  <button
                    className="edit-tab-btn"
                    onClick={(e) => startEditingTitle(tab.id, tab.title, e)}
                    title="Rename"
                  >
                    <Edit2 size={12} />
                  </button>
                  <span 
                    className="tab-title"
                    onDoubleClick={(e) => startEditingTitle(tab.id, tab.title, e)}
                  >
                    {tab.title}
                  </span>
                  {!tab.isPermanent && (
                    <button
                      className="close-tab-btn"
                      onClick={(e) => {
                        e.stopPropagation();
                        onCloseTab(tab.id);
                      }}
                    >
                      <X size={14} />
                    </button>
                  )}
                </>
              )}
            </div>
          ))}
        </div>
        <div className="tab-actions">
          <button 
            className="dark-mode-toggle" 
            onClick={onToggleDarkMode}
            title={darkMode ? "Switch to Light Mode" : "Switch to Dark Mode"}
          >
            {darkMode ? <Sun size={16} /> : <Moon size={16} />}
          </button>
          <div className="notes-browser">
            <button 
              className="notes-browser-btn" 
              onClick={() => setShowNotesMenu(!showNotesMenu)}
              title="Load saved notes"
            >
              <FolderOpen size={16} />
            </button>
            
            {showNotesMenu && (
              <>
                <div 
                  className="notes-menu-overlay" 
                  onClick={() => setShowNotesMenu(false)}
                />
                <div className="notes-menu">
                  <div className="notes-menu-header">Saved Notes</div>
                  <div className="notes-list">
                    {notes && notes.length > 0 ? (
                      notes.map((n) => (
                        <div
                          key={n.id}
                          className={`note-item ${n.id === activeTab ? 'active' : ''}`}
                          onClick={() => handleLoadNote(n.id)}
                        >
                          <div className="note-item-title">{n.title}</div>
                          <div className="note-item-meta">
                            <span className="note-item-date">{formatDate(n.updated_at)}</span>
                            {n.content && (
                              <span className="note-item-preview">
                                {n.content.replace(/<[^>]*>/g, '').substring(0, 50)}...
                              </span>
                            )}
                          </div>
                        </div>
                      ))
                    ) : (
                      <div className="notes-empty">No saved notes</div>
                    )}
                  </div>
                </div>
              </>
            )}
          </div>
          <button className="new-tab-btn" onClick={() => onCreateTab()}>
            <Plus size={16} />
          </button>
        </div>
      </div>

      {/* TipTap Toolbar */}
      <div className="tiptap-toolbar">
        <button
          onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()}
          className={editor.isActive('heading', { level: 1 }) ? 'is-active' : ''}
          title="Heading 1"
        >
          <Heading1 size={18} />
        </button>
        <button
          onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
          className={editor.isActive('heading', { level: 2 }) ? 'is-active' : ''}
          title="Heading 2"
        >
          <Heading2 size={18} />
        </button>
        <button
          onClick={() => editor.chain().focus().toggleHeading({ level: 3 }).run()}
          className={editor.isActive('heading', { level: 3 }) ? 'is-active' : ''}
          title="Heading 3"
        >
          <Heading3 size={18} />
        </button>
        <div className="toolbar-separator" />
        <button
          onClick={() => editor.chain().focus().toggleBold().run()}
          className={editor.isActive('bold') ? 'is-active' : ''}
          title="Bold (Cmd+B)"
        >
          <Bold size={18} />
        </button>
        <button
          onClick={() => editor.chain().focus().toggleItalic().run()}
          className={editor.isActive('italic') ? 'is-active' : ''}
          title="Italic (Cmd+I)"
        >
          <Italic size={18} />
        </button>
        <button
          onClick={() => editor.chain().focus().toggleStrike().run()}
          className={editor.isActive('strike') ? 'is-active' : ''}
          title="Strikethrough"
        >
          <Strikethrough size={18} />
        </button>
        <div className="toolbar-separator" />
        <button
          onClick={() => editor.chain().focus().toggleBulletList().run()}
          className={editor.isActive('bulletList') ? 'is-active' : ''}
          title="Bullet List"
        >
          <List size={18} />
        </button>
        <button
          onClick={() => editor.chain().focus().toggleOrderedList().run()}
          className={editor.isActive('orderedList') ? 'is-active' : ''}
          title="Numbered List"
        >
          <ListOrdered size={18} />
        </button>
      </div>

      <div className="editor-container">
        <EditorContent editor={editor} />
      </div>
    </div>
  );
}

export default NoteEditor;