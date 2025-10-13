import React, { useState, useEffect } from "react";
import "./ConversationDetail.css";

function ConversationDetail({ conversation, templates, onSend, hrName }) {
  const [selectedTemplateIdx, setSelectedTemplateIdx] = useState(null);
  const [message, setMessage] = useState("");
  const [pendingMessages, setPendingMessages] = useState([]); // For optimistic UI



  // Categorize the last received message and highlight the matching template
  useEffect(() => {
    if (!conversation || !templates.length) return;
    // Get the last received message (not pending)
    const sortedMessages = conversation.all_messages
      ? [...conversation.all_messages].sort((a, b) => a.message_index - b.message_index)
      : [];
    const lastReceivedMsgObj = [...sortedMessages].reverse().find(m => m.is_sent === false);
    const lastMsg = lastReceivedMsgObj ? lastReceivedMsgObj.message : "";
    // Find the template whose keywords match the last received message
    let foundIdx = null;
    if (lastMsg) {
      const lastMsgLower = lastMsg.toLowerCase();
      for (let i = 0; i < templates.length; i++) {
        const tpl = templates[i];
        if (tpl.keywords && Array.isArray(tpl.keywords)) {
          for (let k = 0; k < tpl.keywords.length; k++) {
            const keyword = tpl.keywords[k].toLowerCase();
            if (keyword && lastMsgLower.includes(keyword)) {
              foundIdx = i;
              break;
            }
          }
        }
        if (foundIdx !== null) break;
      }
    }
    setSelectedTemplateIdx(foundIdx);
  }, [conversation, templates]);

  const handleTemplateClick = async (idx) => {
    setSelectedTemplateIdx(idx);
    
    try {
      // Use the preview response API for proper personalization
      const response = await fetch("http://127.0.0.1:5000/api/preview_response", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message: "template preview", // Dummy message to get template
          sender_name: conversation.sender_name || "",
          hr_name: hrName || "HR Team"
        })
      });
      
      if (response.ok) {
        const data = await response.json();
        // Use the template response and personalize it
        const template = templates[idx];
        const firstName = data.first_name || conversation.sender_name?.split(" ")[0] || "";
        const effectiveHrName = hrName || "HR Team";
        
        let personalized = template.response || "";
        personalized = personalized.replace(/\[firstname\]/gi, firstName);
        personalized = personalized.replace(/\[hrname\]/gi, effectiveHrName);
        personalized = personalized.replace(/\[Nome HR\]/gi, effectiveHrName); // Legacy support
        
        setMessage(personalized);
      } else {
        // Fallback to simple personalization
        const firstName = conversation.sender_name?.split(" ")[0] || "";
        const effectiveHrName = hrName || "HR Team";
        let personalized = templates[idx].response || "";
        personalized = personalized.replace(/\[firstname\]/gi, firstName);
        personalized = personalized.replace(/\[hrname\]/gi, effectiveHrName);
        personalized = personalized.replace(/\[Nome HR\]/gi, effectiveHrName);
        setMessage(personalized);
      }
    } catch (error) {
      console.error("Error personalizing template:", error);
      // Fallback to simple personalization
      const firstName = conversation.sender_name?.split(" ")[0] || "";
      const effectiveHrName = hrName || "HR Team";
      let personalized = templates[idx].response || "";
      personalized = personalized.replace(/\[firstname\]/gi, firstName);
      personalized = personalized.replace(/\[hrname\]/gi, effectiveHrName);
      personalized = personalized.replace(/\[Nome HR\]/gi, effectiveHrName);
      setMessage(personalized);
    }
  };

  const handleSend = () => {
    if (message.trim()) {
      // Add pending message to UI
      const pendingMsg = {
        is_sent: true,
        message,
        timestamp: "Sending...",
        message_index: (conversation.all_messages?.length || 0) + pendingMessages.length,
        pending: true
      };
      setPendingMessages((prev) => [...prev, pendingMsg]);
      onSend(conversation.sender_name, message).then(() => {
        // On success, pending message will be replaced by real one from backend
        setPendingMessages([]);
        setMessage("");
        setSelectedTemplateIdx(null);
      }).catch(() => {
        // On error, remove pending message
        setPendingMessages([]);
      });
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Sort messages by message_index to ensure proper order
  const sortedMessages = conversation.all_messages 
    ? [...conversation.all_messages].sort((a, b) => a.message_index - b.message_index)
    : [];
  // Combine with pending messages
  const allMessagesWithPending = [...sortedMessages, ...pendingMessages];

  return (
    <div className="conversation-detail">
      <div className="chat-main">
        <div className="conversation-header">
          <div className="header-info">
            <h3>{conversation.sender_name}</h3>
            <div className="conversation-stats">
              <span className="message-count">{conversation.message_count || sortedMessages.length} messages</span>
              {conversation.is_unread && <span className="unread-badge">UNREAD</span>}
            </div>
          </div>
        </div>
        <div className="message-history">
          {allMessagesWithPending.length > 0 ? (
            allMessagesWithPending.map((msg, idx) => (
              <div
                key={idx}
                className={
                  (msg.is_sent ? "message-row sent" : "message-row received") + (msg.pending ? " pending" : "")
                }
              >
                <div className="bubble">
                  <div className="message-text">{msg.message}</div>
                  {msg.pending ? (
                    <div className="message-time"><span className="sending-spinner"></span> Sending...</div>
                  ) : (
                    msg.timestamp && <div className="message-time">{msg.timestamp}</div>
                  )}
                </div>
              </div>
            ))
          ) : (
            <div className="no-messages">No messages in this conversation.</div>
          )}
        </div>
        <div className="message-input-section">
          <div className="input-container">
            <textarea
              className="message-input"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Type your message here..."
              rows={3}
            />
            <button 
              className="send-btn" 
              onClick={handleSend} 
              disabled={!message.trim()}
            >
              Send
            </button>
          </div>
        </div>
      </div>
      <div className="template-sidebar">
        <div className="template-list-label">
          Response Templates ({templates.length}):
        </div>
        <div className="template-list">
          {templates && templates.length > 0 ? (
            templates.map((template, idx) => (
              <div
                key={idx}
                className={`template-list-item${selectedTemplateIdx === idx ? " selected" : ""}`}
                onClick={() => handleTemplateClick(idx)}
              >
                {template.status}
              </div>
            ))
          ) : (
            <div className="no-templates">
              No templates available
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default ConversationDetail; 