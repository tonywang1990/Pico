import React, { useState } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import './Calendar.css';

function Calendar({ todos, onDateClick, selectedTags = [] }) {
  const [currentDate, setCurrentDate] = useState(new Date());

  const getDaysInMonth = (date) => {
    const year = date.getFullYear();
    const month = date.getMonth();
    return new Date(year, month + 1, 0).getDate();
  };

  const getFirstDayOfMonth = (date) => {
    const year = date.getFullYear();
    const month = date.getMonth();
    return new Date(year, month, 1).getDay();
  };

  const goToPreviousMonth = () => {
    setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() - 1, 1));
  };

  const goToNextMonth = () => {
    setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() + 1, 1));
  };

  const getPriorityForDate = (day) => {
    const year = currentDate.getFullYear();
    const month = currentDate.getMonth();
    // Format date string without timezone conversion
    const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
    
    // Find all ACTIVE (non-completed) todos with this due date
    const todosOnDate = todos.filter(todo => {
      if (!todo.due_date || todo.completed) return false; // Filter out completed todos
      
      // Apply tag filter
      if (selectedTags.length > 0) {
        if (!todo.tags || todo.tags.length === 0) return false;
        if (!selectedTags.some(tag => todo.tags.includes(tag))) return false;
      }
      
      // Handle both date-only strings and ISO datetime strings
      let todoDateStr;
      if (typeof todo.due_date === 'string') {
        // If it contains 'T', split it; otherwise use as-is
        todoDateStr = todo.due_date.includes('T') ? todo.due_date.split('T')[0] : todo.due_date;
      } else if (todo.due_date instanceof Date) {
        // If it's a Date object, format it
        const d = todo.due_date;
        todoDateStr = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
      } else {
        return false;
      }
      
      return todoDateStr === dateStr;
    });

    if (todosOnDate.length === 0) return null;

    // Return highest priority (high > medium > low)
    if (todosOnDate.some(t => t.priority === 'high')) return 'high';
    if (todosOnDate.some(t => t.priority === 'medium')) return 'medium';
    return 'low';
  };

  const isToday = (day) => {
    const today = new Date();
    return (
      day === today.getDate() &&
      currentDate.getMonth() === today.getMonth() &&
      currentDate.getFullYear() === today.getFullYear()
    );
  };

  const renderCalendar = () => {
    const daysInMonth = getDaysInMonth(currentDate);
    const firstDay = getFirstDayOfMonth(currentDate);
    const days = [];

    // Empty cells for days before the first day of the month
    for (let i = 0; i < firstDay; i++) {
      days.push(<div key={`empty-${i}`} className="calendar-day empty"></div>);
    }

    // Days of the month
    for (let day = 1; day <= daysInMonth; day++) {
      const priority = getPriorityForDate(day);
      const today = isToday(day);
      
      days.push(
        <div
          key={day}
          className={`calendar-day ${priority ? `has-todo priority-${priority}` : ''} ${today ? 'today' : ''}`}
          onClick={() => {
            if (onDateClick) {
              const year = currentDate.getFullYear();
              const month = currentDate.getMonth();
              const clickedDate = new Date(year, month, day);
              onDateClick(clickedDate);
            }
          }}
        >
          <span className="day-number">{day}</span>
        </div>
      );
    }

    return days;
  };

  const monthNames = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'
  ];

  return (
    <div className="calendar-container">
      <div className="calendar-header">
        <button onClick={goToPreviousMonth} className="calendar-nav-btn">
          <ChevronLeft size={16} />
        </button>
        <div className="calendar-title">
          {monthNames[currentDate.getMonth()]} {currentDate.getFullYear()}
        </div>
        <button onClick={goToNextMonth} className="calendar-nav-btn">
          <ChevronRight size={16} />
        </button>
      </div>
      
      <div className="calendar-weekdays">
        <div className="weekday">Su</div>
        <div className="weekday">Mo</div>
        <div className="weekday">Tu</div>
        <div className="weekday">We</div>
        <div className="weekday">Th</div>
        <div className="weekday">Fr</div>
        <div className="weekday">Sa</div>
      </div>
      
      <div className="calendar-grid">
        {renderCalendar()}
      </div>
    </div>
  );
}

export default Calendar;
