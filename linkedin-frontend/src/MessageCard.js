import React from "react";
import "./MessageCard.css";

function getInitials(name) {
  if (!name) return "";
  return name
    .split(" ")
    .map((n) => n[0])
    .join("")
    .toUpperCase();
}

const MessageCard = ({ message, isSelected, onClick }) => {
  // Extract role and location from sender_name if it contains them
  const nameParts = message.sender_name.split(' · ');
  const displayName = nameParts[0];
  const role = nameParts[1] || '';
  const location = nameParts[2] || '';

  // Get the latest message (sent or received) for preview
  const getLastMessage = () => {
    if (message.all_messages && message.all_messages.length > 0) {
      const msgs = [...message.all_messages];
      // Prefer ordering by message_index when present
      msgs.sort((a, b) => {
        const ai = typeof a.message_index === 'number' ? a.message_index : -1;
        const bi = typeof b.message_index === 'number' ? b.message_index : -1;
        return ai - bi;
      });
      const last = msgs[msgs.length - 1];
      if (last && last.message) return last.message;
    }
    // Fallbacks: last_received_message -> conversation_preview -> message
    if (message.last_received_message) return message.last_received_message;
    return message.conversation_preview || message.message || '';
  };

  // Mock skills for demonstration (you can add real skills data later)
  const mockSkills = ['React', 'JavaScript'].slice(0, 2);
  const lastMessage = getLastMessage();
  const messageCount = message.message_count || (message.all_messages ? message.all_messages.length : 0);

  return (
    <div 
      className={`message-card ${isSelected ? 'selected' : ''}`}
      onClick={onClick}
    >
      <div className="card-header">
        <div className="avatar">{getInitials(displayName)}</div>
        <div className="user-info">
          <div className="name">{displayName}</div>
          {role && <div className="role">{role}</div>}
          {location && <div className="location">{location}</div>}
        </div>
        {message.is_unread && (
          <div className="unread-indicator">
            {message.unread_count > 1 && <span className="unread-count">{message.unread_count}</span>}
          </div>
        )}
      </div>
      
      <div className="card-body">
        {lastMessage && (
          <div className="preview-message">{lastMessage}</div>
        )}
        <div className="card-meta">
          <div className="message-count">💬 {messageCount}</div>
          <div className="skills-container">
            {mockSkills.map((skill, idx) => (
              <span key={idx} className="skill-tag">{skill}</span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default MessageCard; 