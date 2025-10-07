import React, { useState, useMemo } from 'react';
import { Check, Trash2, ChevronDown, ChevronLeft, ChevronRight, Archive, CheckSquare, Tag, X } from 'lucide-react';
import Calendar from './Calendar';
import './TodoList.css';

function TodoList({ todos, onToggleTodo, onDeleteTodo }) {
  const [archiveExpanded, setArchiveExpanded] = useState(false);
  const [weekOffset, setWeekOffset] = useState(0); // 0 = current week, -1 = last week, 1 = next week
  const [selectedTags, setSelectedTags] = useState([]);

  const formatDueDate = (dateString) => {
    if (!dateString) return null;
    
    // Parse date without timezone shift
    const dateStr = dateString.includes('T') ? dateString.split('T')[0] : dateString;
    const [year, month, day] = dateStr.split('-').map(Number);
    const dueDate = new Date(year, month - 1, day);
    
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    
    const diffDays = Math.floor((dueDate - today) / (1000 * 60 * 60 * 24));
    
    if (diffDays < 0) return { text: 'Overdue', className: 'overdue' };
    if (diffDays === 0) return { text: 'Today', className: 'today' };
    if (diffDays === 1) return { text: 'Tomorrow', className: 'tomorrow' };
    if (diffDays <= 7) return { text: `${diffDays}d`, className: 'this-week' };
    
    return { text: dueDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }), className: '' };
  };

  const getPriorityColor = (priority) => {
    switch (priority) {
      case 'high': return 'priority-high';
      case 'medium': return 'priority-medium';
      case 'low': return 'priority-low';
      default: return 'priority-medium';
    }
  };

  // Week navigation helpers
  const getWeekBounds = (offset) => {
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const dayOfWeek = today.getDay(); // 0 = Sunday
    
    // Calculate start of week (Sunday)
    const startOfWeek = new Date(today);
    startOfWeek.setDate(today.getDate() - dayOfWeek + (offset * 7));
    
    // Calculate end of week (Saturday)
    const endOfWeek = new Date(startOfWeek);
    endOfWeek.setDate(startOfWeek.getDate() + 6);
    
    return { startOfWeek, endOfWeek };
  };

  const handleDateClick = (clickedDate) => {
    // Calculate which week the clicked date belongs to relative to current week
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const todayDayOfWeek = today.getDay();
    
    // Calculate start of current week (Sunday)
    const currentWeekStart = new Date(today);
    currentWeekStart.setDate(today.getDate() - todayDayOfWeek);
    
    // Calculate start of clicked date's week (Sunday)
    const clickedDayOfWeek = clickedDate.getDay();
    const clickedWeekStart = new Date(clickedDate);
    clickedWeekStart.setDate(clickedDate.getDate() - clickedDayOfWeek);
    
    // Calculate week offset (in weeks)
    const diffTime = clickedWeekStart - currentWeekStart;
    const diffWeeks = Math.round(diffTime / (7 * 24 * 60 * 60 * 1000));
    
    setWeekOffset(diffWeeks);
  };

  const formatWeekRange = (offset) => {
    const { startOfWeek, endOfWeek } = getWeekBounds(offset);
    const options = { month: 'short', day: 'numeric' };
    
    if (startOfWeek.getMonth() === endOfWeek.getMonth()) {
      return `${startOfWeek.toLocaleDateString('en-US', { month: 'short' })} ${startOfWeek.getDate()}-${endOfWeek.getDate()}`;
    }
    return `${startOfWeek.toLocaleDateString('en-US', options)} - ${endOfWeek.toLocaleDateString('en-US', options)}`;
  };

  const isInCurrentWeek = (dateString, offset) => {
    if (!dateString) return false;
    const { startOfWeek, endOfWeek } = getWeekBounds(offset);
    
    // Parse date without timezone shift: extract YYYY-MM-DD and create local date
    const dateStr = dateString.includes('T') ? dateString.split('T')[0] : dateString;
    const [year, month, day] = dateStr.split('-').map(Number);
    const todoDate = new Date(year, month - 1, day);
    
    return todoDate >= startOfWeek && todoDate <= endOfWeek;
  };

  const getDayName = (dateString) => {
    // Parse date without timezone shift: extract YYYY-MM-DD and create local date
    const dateStr = dateString.includes('T') ? dateString.split('T')[0] : dateString;
    const [year, month, day] = dateStr.split('-').map(Number);
    const date = new Date(year, month - 1, day);
    return date.toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric' });
  };

  // Helper function to check if todo matches selected tags
  const matchesTagFilter = (todo) => {
    if (selectedTags.length === 0) return true;
    if (!todo.tags || todo.tags.length === 0) return false;
    return selectedTags.some(tag => todo.tags.includes(tag));
  };

  // Filter and group todos
  const activeTodos = todos.filter(todo => !todo.completed);
  const archivedTodos = todos.filter(todo => todo.completed);
  
  // Get todos in current week with due dates, filtered by tags
  const weekTodos = activeTodos.filter(todo => 
    todo.due_date && isInCurrentWeek(todo.due_date, weekOffset) && matchesTagFilter(todo)
  );

  // Group todos by date
  const todosByDate = weekTodos.reduce((groups, todo) => {
    // Extract date string directly without timezone conversion
    const dateKey = todo.due_date.includes('T') ? todo.due_date.split('T')[0] : todo.due_date;
    if (!groups[dateKey]) {
      groups[dateKey] = [];
    }
    groups[dateKey].push(todo);
    return groups;
  }, {});

  // Sort dates
  const sortedDates = Object.keys(todosByDate).sort();

  // Todos without due dates (not in weekly view), filtered by tags
  const todosWithoutDates = activeTodos.filter(todo => !todo.due_date && matchesTagFilter(todo));

  // Get all unique tags from todos
  const allTags = useMemo(() => {
    const tagSet = new Set();
    todos.forEach(todo => {
      if (todo.tags && Array.isArray(todo.tags)) {
        todo.tags.forEach(tag => tagSet.add(tag));
      }
    });
    return Array.from(tagSet).sort();
  }, [todos]);

  const toggleTagFilter = (tag) => {
    setSelectedTags(prev => 
      prev.includes(tag) 
        ? prev.filter(t => t !== tag)
        : [...prev, tag]
    );
  };

  const clearTagFilters = () => {
    setSelectedTags([]);
  };

  const renderTodo = (todo) => {
    return (
      <div key={todo.id} className={`todo-item ${todo.completed ? 'completed' : ''} ${getPriorityColor(todo.priority || 'medium')}`}>
        <button
          onClick={() => onToggleTodo(todo.id)}
          className="todo-checkbox"
        >
          {todo.completed && <Check size={14} />}
        </button>
        <div className="todo-content">
          <span className="todo-text">{todo.text}</span>
          {todo.tags && todo.tags.length > 0 && (
            <div className="todo-tags">
              {todo.tags.map(tag => (
                <span key={tag} className="todo-tag">
                  <Tag size={10} />
                  {tag}
                </span>
              ))}
            </div>
          )}
        </div>
        <button
          onClick={() => onDeleteTodo(todo.id)}
          className="delete-todo-btn"
        >
          <Trash2 size={14} />
        </button>
      </div>
    );
  };

  return (
    <div className="todo-list">
      <div className="todo-header">
        <div className="todo-title-row">
          <CheckSquare size={16} className="todo-icon" />
          <h2>Calendar</h2>
          {/* Tag Filter Dropdown */}
          {allTags.length > 0 && (
            <div className="tag-filter-dropdown">
              <Tag size={14} />
              <select 
                value={selectedTags[0] || ''}
                onChange={(e) => {
                  const value = e.target.value;
                  if (value) {
                    setSelectedTags([value]);
                  } else {
                    clearTagFilters();
                  }
                }}
                className="tag-select"
              >
                <option value="">All Tags</option>
                {allTags.map(tag => (
                  <option key={tag} value={tag}>
                    {tag}
                  </option>
                ))}
              </select>
              {selectedTags.length > 0 && (
                <button onClick={clearTagFilters} className="clear-tag-btn" title="Clear filter">
                  <X size={14} />
                </button>
              )}
            </div>
          )}
        </div>
        <p className="todo-subtitle">Your schedule and tasks</p>
      </div>

      <Calendar todos={todos} onDateClick={handleDateClick} selectedTags={selectedTags} />

      {/* Week Navigation */}
      <div className="week-navigation">
        <button onClick={() => setWeekOffset(weekOffset - 1)} className="week-nav-btn">
          <ChevronLeft size={16} />
        </button>
        <div className="week-range">
          {weekOffset === 0 ? 'This Week' : formatWeekRange(weekOffset)}
        </div>
        <button onClick={() => setWeekOffset(weekOffset + 1)} className="week-nav-btn">
          <ChevronRight size={16} />
        </button>
      </div>

      <div className="todos-container">
        {/* Weekly Todos Section - Grouped by Date */}
        <div className="weekly-section">
          <div className="weekly-todos-scroll">
            {sortedDates.length > 0 ? (
              sortedDates.map(dateKey => (
                <div key={dateKey} className="date-group">
                  <div className="date-group-header">
                    {getDayName(dateKey)}
                  </div>
                  <div className="date-group-todos">
                    {todosByDate[dateKey].map(renderTodo)}
                  </div>
                </div>
              ))
            ) : (
              <div className="empty-state">
                {weekOffset === 0 ? 'No todos this week' : 'No todos for this week'}
              </div>
            )}
            
            {/* Show todos without dates at the bottom (only for current week) */}
            {weekOffset === 0 && todosWithoutDates.length > 0 && (
              <div className="date-group">
                <div className="date-group-header no-date">No Due Date</div>
                <div className="date-group-todos">
                  {todosWithoutDates.map(renderTodo)}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Archived Todos Section - Bottom Drawer */}
        {archivedTodos.length > 0 && (
          <div className={`archived-drawer ${archiveExpanded ? 'expanded' : 'collapsed'}`}>
            <button 
              className="drawer-handle"
              onClick={() => setArchiveExpanded(!archiveExpanded)}
            >
              <div className="handle-bar"></div>
              <div className="drawer-header">
                {archiveExpanded ? <ChevronDown size={18} /> : <ChevronDown size={18} className="flipped" />}
                <Archive size={16} />
                <span className="drawer-title">Archived ({archivedTodos.length})</span>
              </div>
            </button>
            <div className="archived-todos-scroll">
              {archivedTodos.map(renderTodo)}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default TodoList;

