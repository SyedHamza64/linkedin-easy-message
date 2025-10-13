import React, { useEffect, useState } from "react";
import MessageCard from "./MessageCard";
import ConversationDetail from "./ConversationDetail";
import "./App.css";

function App() {
  const [conversations, setConversations] = useState([]);
  const [selectedConversation, setSelectedConversation] = useState(null);
  const [templates, setTemplates] = useState([]);
  const [notification, setNotification] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isBackgroundLoading, setIsBackgroundLoading] = useState(false);
  const [isFullSyncing, setIsFullSyncing] = useState(false);
  const [autoRefreshEnabled, setAutoRefreshEnabled] = useState(false);
  const [autoRefreshInterval, setAutoRefreshInterval] = useState(30); // seconds
  const [showSettings, setShowSettings] = useState(false);
  const [autoRefreshTimer, setAutoRefreshTimer] = useState(null);
  const [syncProgress, setSyncProgress] = useState(null);
  const [progressTimer, setProgressTimer] = useState(null);
  const [hrName, setHrName] = useState(() => {
    // Load HR name from localStorage or default to empty string
    return localStorage.getItem('linkedin-hr-name') || '';
  });
  const [isDarkMode, setIsDarkMode] = useState(() => {
    // Load theme preference from localStorage or default to light
    return localStorage.getItem('linkedin-theme') === 'dark';
  });
  const [filterUnreadOnly, setFilterUnreadOnly] = useState(false);
  const [sortOrder, setSortOrder] = useState("newest"); // 'newest' or 'alpha'
  const [searchQuery, setSearchQuery] = useState("");
  const prevSelectedConversationRef = React.useRef(null);
  // Track last filter state
  const [lastFilterUnreadOnly, setLastFilterUnreadOnly] = useState(false);

  // Helper function to show notifications with auto-disappear
  const showNotification = (type, text, duration = null, isAutoRefresh = false) => {
    setNotification({ type, text, isAutoRefresh });
    
    // Set default durations based on type
    const defaultDuration = duration || (
      type === "error" ? 5000 :
      type === "success" ? 3000 :
      3000 // info default
    );
    
    setTimeout(() => {
      setNotification(prev => {
        // Only clear if it's the same notification
        if (prev && prev.type === type && prev.text === text) {
          return null;
        }
        return prev;
      });
    }, defaultDuration);
  };

  // Load saved conversations immediately
  const loadSavedConversations = async () => {
    try {
      console.log("📁 Loading saved conversations...");
      const res = await fetch("http://127.0.0.1:5000/api/messages?load_saved_only=1");
      const data = await res.json();
      let savedConvs = [];
      if (data.conversations) {
        savedConvs = data.conversations;
      } else if (Array.isArray(data)) {
        savedConvs = data;
      }
      setConversations(savedConvs);
      console.log(`📁 Loaded ${savedConvs.length} saved conversations`);
      setIsLoading(false);
    } catch (err) {
      console.error("Error loading saved conversations:", err);
      setConversations([]);
      setIsLoading(false);
    }
  };

  // Fetch new conversations in background
  const fetchNewConversations = async (unreadOnly = false) => {
    try {
      setIsBackgroundLoading(true);
      console.log("🔄 Fetching new conversations in background...");
      const res = await fetch(`http://127.0.0.1:5000/api/messages/background?unread_only=${unreadOnly ? '1' : '0'}`);
      const data = await res.json();
      
      if (data.success) {
        let newConvs = [];
        if (data.conversations) {
          newConvs = data.conversations;
        } else if (Array.isArray(data)) {
          newConvs = data;
        }
        
        setConversations(newConvs);
        
        // Keep selected conversation in sync
        if (selectedConversation) {
          const updated = newConvs.find(
            c => c.sender_name === selectedConversation.sender_name
          );
          if (updated) {
            setSelectedConversation(updated);
          }
        }
        
        // Show notification based on results
        if (data.new_count > 0 || data.updated_count > 0) {
          const message = unreadOnly 
            ? `Updated ${data.new_count + data.updated_count} unread conversation(s)!`
            : `Found ${data.new_count} new and updated ${data.updated_count} existing conversation(s)!`;
          setNotification({ type: "success", text: message });
          setTimeout(() => setNotification(null), 3000);
        } else {
          setNotification({ type: "info", text: "No new conversations found." });
          setTimeout(() => setNotification(null), 3000);
        }
        
        console.log(`✅ Background fetch complete: ${data.new_count} new, ${data.updated_count} updated`);
      } else {
        console.error("Background fetch failed:", data.error);
        setNotification({ type: "error", text: "Failed to fetch new conversations." });
        setTimeout(() => setNotification(null), 4000);
      }
    } catch (err) {
      console.error("Error in background fetch:", err);
      setNotification({ type: "error", text: "Network error during background fetch." });
      setTimeout(() => setNotification(null), 4000);
    } finally {
      setIsBackgroundLoading(false);
      // Clear the initial background fetch notification after a delay
      setTimeout(() => {
        setNotification(prev => {
          if (prev && prev.text === "Checking for new conversations in background...") {
            return null;
          }
          return prev;
        });
      }, 3000);
    }
  };

  // Auto-refresh timer effect
  useEffect(() => {
    if (autoRefreshEnabled && autoRefreshInterval > 0) {
      console.log(`🔄 Starting auto-refresh every ${autoRefreshInterval} seconds`);
      
      const timer = setInterval(() => {
        console.log(`⏰ Auto-refresh triggered (${autoRefreshInterval}s interval)`);
        showNotification("info", "Auto-refreshing conversations...", 2000, true);
        
        fetchNewConversations(true).then(() => {
          // Clear auto-refresh notification after 2 seconds
          setTimeout(() => {
            setNotification(prev => {
              if (prev && prev.isAutoRefresh) {
                return null;
              }
              return prev;
            });
          }, 2000);
        });
      }, autoRefreshInterval * 1000);

      setAutoRefreshTimer(timer);
      
      return () => {
        if (timer) {
          clearInterval(timer);
        }
      };
    } else {
      // Clear existing timer if auto-refresh is disabled
      if (autoRefreshTimer) {
        clearInterval(autoRefreshTimer);
        setAutoRefreshTimer(null);
      }
    }
  }, [autoRefreshEnabled, autoRefreshInterval]);

  // Cleanup timer on unmount
  useEffect(() => {
    return () => {
      if (autoRefreshTimer) {
        clearInterval(autoRefreshTimer);
      }
    };
  }, []);

  const handleAutoRefreshToggle = () => {
    setAutoRefreshEnabled(!autoRefreshEnabled);
    if (!autoRefreshEnabled) {
      showNotification("success", `Auto-refresh enabled (${autoRefreshInterval}s)`, 2000);
    } else {
      showNotification("info", "Auto-refresh disabled", 2000);
    }
  };

  const handleIntervalChange = (newInterval) => {
    setAutoRefreshInterval(newInterval);
    showNotification("success", `Auto-refresh interval set to ${newInterval < 60 ? newInterval + 's' : newInterval === 60 ? '1min' : '5min'}`, 2000);
  };

  const handleHrNameChange = (name) => {
    setHrName(name);
    localStorage.setItem('linkedin-hr-name', name);
    const displayName = name.trim() || 'Default HR Team';
    showNotification("success", `HR name updated: ${displayName}`, 2000);
  };

  const handleThemeToggle = () => {
    const newTheme = !isDarkMode;
    setIsDarkMode(newTheme);
    localStorage.setItem('linkedin-theme', newTheme ? 'dark' : 'light');
    document.documentElement.setAttribute('data-theme', newTheme ? 'dark' : 'light');
    showNotification("success", `Switched to ${newTheme ? 'dark' : 'light'} mode`, 2000);
  };

  // Apply theme on component mount
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', isDarkMode ? 'dark' : 'light');
  }, [isDarkMode]);

  // Initial load: load saved conversations immediately, then fetch new ones in background
  useEffect(() => {
    const initializeApp = async () => {
      // Load saved conversations immediately
      await loadSavedConversations();
      
      // Load templates
      try {
        console.log("🔄 Loading templates...");
        const templatesRes = await fetch("http://127.0.0.1:5000/api/templates");
        
        if (!templatesRes.ok) {
          throw new Error(`HTTP ${templatesRes.status}: ${templatesRes.statusText}`);
        }
        
        const templatesData = await templatesRes.json();
        console.log("✅ Loaded templates:", templatesData);
        
        setTemplates(templatesData || []);
        
        if (!templatesData || templatesData.length === 0) {
          showNotification("error", "No response templates found", 4000);
        } else {
          showNotification("success", `Loaded ${templatesData.length} response templates`, 2000);
        }
      } catch (err) {
        console.error("❌ Error loading templates:", err);
        setTemplates([]);
        showNotification("error", `Failed to load templates: ${err.message}`, 5000);
      }
      
      // Fetch new conversations in background after a short delay
      setTimeout(() => {
        console.log("🔄 Starting background fetch for new conversations...");
        setNotification({ type: "info", text: "Checking for new conversations in background..." });
        fetchNewConversations(true); // Fetch only unread conversations in background for efficiency
      }, 1000);
    };
    
    initializeApp();
  }, []);

  const markConversationAsRead = (conv) => {
    setConversations(prevConvs => {
      return prevConvs.map(c => {
        if (c.sender_name === conv.sender_name) {
          return { ...c, is_unread: false, unread_count: 0 };
        }
        return c;
      });
    });
    // Call backend to mark as read
    fetch(`http://127.0.0.1:5000/api/mark_read/${encodeURIComponent(conv.sender_name)}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    }).catch(err => {
      console.log('Error marking conversation as read:', err);
    });
  };

  useEffect(() => {
    // When selectedConversation changes, mark the previous one as read if needed
    const prev = prevSelectedConversationRef.current;
    if (prev && prev.is_unread) {
      markConversationAsRead(prev);
    }
    prevSelectedConversationRef.current = selectedConversation;
  }, [selectedConversation]);

  // When switching filterUnreadOnly, if going from unread to all, mark selected as read if needed
  useEffect(() => {
    if (lastFilterUnreadOnly && !filterUnreadOnly && selectedConversation && selectedConversation.is_unread) {
      // Mark as read only when switching to All
      markConversationAsRead(selectedConversation);
      // Also update selectedConversation state to reflect read
      setSelectedConversation({ ...selectedConversation, is_unread: false, unread_count: 0 });
    }
    setLastFilterUnreadOnly(filterUnreadOnly);
  }, [filterUnreadOnly]);

  const handleSelectConversation = async (conv) => {
    setNotification(null);
    // Only mark as read if not in unread-only mode
    if (conv.is_unread && !filterUnreadOnly) {
      setConversations(prevConvs => prevConvs.map(c =>
        c.sender_name === conv.sender_name ? { ...c, is_unread: false, unread_count: 0 } : c
      ));
      try {
        await fetch('http://127.0.0.1:5000/api/mark_read_by_switch', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ sender_name: conv.sender_name })
        });
      } catch (err) {
        console.log('Error marking as read by switch:', err);
      }
      setSelectedConversation({ ...conv, is_unread: false, unread_count: 0 });
    } else {
      setSelectedConversation(conv);
    }
  };

  const handleSendMessage = async (sender_name, message) => {
    try {
      const res = await fetch("http://127.0.0.1:5000/api/send_message", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sender_name, message }),
      });
      const data = await res.json();
      if (data.success && data.conversation) {
        setNotification({ type: "success", text: "Message sent successfully!" });
        setTimeout(() => setNotification(null), 3000);
        // Update only the affected conversation in state
        setConversations(prevConvs => {
          const idx = prevConvs.findIndex(c => c.sender_name === data.conversation.sender_name);
          if (idx !== -1) {
            const updated = [...prevConvs];
            updated[idx] = data.conversation;
            return updated;
          } else {
            return [...prevConvs, data.conversation];
          }
        });
        setSelectedConversation(data.conversation);
      } else {
        setNotification({ type: "error", text: data.error || "Failed to send message." });
        setTimeout(() => setNotification(null), 4000);
      }
    } catch (err) {
      setNotification({ type: "error", text: "Network error." });
      setTimeout(() => setNotification(null), 4000);
    }
  };

  const handleManualRefresh = async () => {
    // Fetch only unread conversations in background
    await fetchNewConversations(true);
  };

  const handleFullSync = async () => {
    try {
      setIsFullSyncing(true);
      showNotification("info", "Starting progressive sync...", 2000);
      console.log("🔄 Starting progressive sync...");
      
      const res = await fetch("http://127.0.0.1:5000/api/full_sync_progressive", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ limit: 100 })
      });
      
      const data = await res.json();
      
      if (data.success) {
        // Start monitoring progress
        startProgressMonitoring();
        showNotification("success", "Progressive sync started! Watch conversations update in real-time.", 3000);
        console.log("✅ Progressive sync started");
      } else {
        console.error("Progressive sync failed:", data.error);
        showNotification("error", `Progressive sync failed: ${data.error || data.message}`, 5000);
        setIsFullSyncing(false);
      }
    } catch (err) {
      console.error("Error starting progressive sync:", err);
      showNotification("error", "Network error during progressive sync.", 5000);
      setIsFullSyncing(false);
    }
  };

  const startProgressMonitoring = () => {
    const timer = setInterval(async () => {
      try {
        const res = await fetch("http://127.0.0.1:5000/api/sync_progress");
        const progress = await res.json();
        
        setSyncProgress(progress);
        
        // Update conversations in real-time
        if (progress.conversations && progress.conversations.length > 0) {
          setConversations(progress.conversations);
          
          // Update selected conversation if it exists and was updated
          if (selectedConversation) {
            const updated = progress.conversations.find(
              c => c.sender_name === selectedConversation.sender_name
            );
            if (updated) {
              setSelectedConversation(updated);
            }
          }
        }
        
        // Show progress notification
        if (progress.active) {
          showNotification(
            "info", 
            `Syncing: ${progress.current_conversation} (${progress.current}/${progress.total})`,
            1000,
            true
          );
        } else {
          // Sync completed or failed
          clearInterval(timer);
          setProgressTimer(null);
          setIsFullSyncing(false);
          
          if (progress.current_conversation.includes('Completed')) {
            showNotification("success", `Sync complete! ${progress.current_conversation}`, 4000);
          } else if (progress.current_conversation.includes('Error')) {
            showNotification("error", progress.current_conversation, 5000);
          } else if (progress.current_conversation.includes('Cancelled')) {
            showNotification("info", "Sync cancelled by user", 3000);
          }
          
          setSyncProgress(null);
        }
      } catch (err) {
        console.error("Error fetching progress:", err);
        clearInterval(timer);
        setProgressTimer(null);
        setIsFullSyncing(false);
        setSyncProgress(null);
        showNotification("error", "Error monitoring sync progress", 4000);
      }
    }, 1000); // Poll every second
    
    setProgressTimer(timer);
  };

  const handleCancelSync = async () => {
    try {
      const res = await fetch("http://127.0.0.1:5000/api/sync_cancel", {
        method: "POST"
      });
      
      const data = await res.json();
      if (data.success) {
        showNotification("info", "Sync cancellation requested...", 2000);
      }
    } catch (err) {
      console.error("Error cancelling sync:", err);
      showNotification("error", "Error cancelling sync", 3000);
    }
  };

  // Cleanup progress timer on unmount
  useEffect(() => {
    return () => {
      if (progressTimer) {
        clearInterval(progressTimer);
      }
    };
  }, []);

  return (
    <div className="app-container">
      {/* Theme Toggle Button */}
      <button 
        className="theme-toggle" 
        onClick={handleThemeToggle}
        title={`Switch to ${isDarkMode ? 'light' : 'dark'} mode`}
      >
        {isDarkMode ? '☀️' : '🌙'}
      </button>

      {/* Top-right notification */}
      {notification && (
        <div className={`notification notification-${notification.type}`}>
          {notification.text}
        </div>
      )}
      
      <div className="sidebar">
        <div className="sidebar-header">
          <h2>LinkedIn Messages</h2>
          {/* Place filter buttons in their own row below the conversation count */}
          <div className="conversation-count">
            <span className="count-text">{conversations.length} conversations</span>
          </div>
          {/* Search bar */}
          <div style={{ margin: '8px 0' }}>
            <input
              type="text"
              placeholder="Search by name..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              style={{ width: '100%', padding: '6px 10px', borderRadius: 6, border: '1px solid #ccc', fontSize: 14 }}
            />
          </div>
          {/* Sort dropdown */}
          <div style={{ marginBottom: 8 }}>
            <label htmlFor="sortOrder" style={{ fontSize: 13, marginRight: 6 }}>Sort by:</label>
            <select
              id="sortOrder"
              value={sortOrder}
              onChange={e => setSortOrder(e.target.value)}
              style={{ fontSize: 13, borderRadius: 4, padding: '2px 6px' }}
            >
              <option value="newest">Newest to Oldest</option>
              <option value="alpha">Alphabetical (A-Z)</option>
            </select>
          </div>
          <div className="filter-group">
            <button
              className={`filter-btn${!filterUnreadOnly ? ' selected' : ''}`}
              onClick={() => setFilterUnreadOnly(false)}
              title="Show all conversations"
            >
              All
            </button>
            <button
              className={`filter-btn${filterUnreadOnly ? ' selected' : ''}`}
              onClick={() => setFilterUnreadOnly(true)}
              title="Show only unread conversations"
            >
              Unread
            </button>
          </div>
          <div className="button-group">
            {/* Keep only the original action buttons here */}
            <button 
              className={`action-btn refresh-btn ${isBackgroundLoading ? 'loading' : ''}`} 
              onClick={handleManualRefresh} 
              title="Refresh unread conversations"
              disabled={isBackgroundLoading || isFullSyncing}
            >
              🔄
            </button>
            <button 
              className={`action-btn sync-btn ${isFullSyncing ? 'loading' : ''}`} 
              onClick={handleFullSync} 
              title="Progressive sync - fetch and update all conversations in real-time"
              disabled={isBackgroundLoading || isFullSyncing}
            >
              💯
            </button>
            {isFullSyncing && (
              <button 
                className="action-btn cancel-sync-btn" 
                onClick={handleCancelSync} 
                title="Cancel ongoing sync"
              >
                ❌
              </button>
            )}
            <button 
              className={`action-btn auto-refresh-btn ${autoRefreshEnabled ? 'active' : ''}`} 
              onClick={handleAutoRefreshToggle}
              title={autoRefreshEnabled ? `Disable auto-refresh (${autoRefreshInterval}s)` : `Enable auto-refresh (${autoRefreshInterval}s)`}
              disabled={isBackgroundLoading || isFullSyncing}
            >
              {autoRefreshEnabled ? '⏸️' : '⏯️'}
            </button>
            <button 
              className="action-btn settings-btn" 
              onClick={() => setShowSettings((prev) => !prev)}
              title="Settings"
              disabled={isBackgroundLoading || isFullSyncing}
            >
              ⚙️
            </button>
          </div>
          
          {showSettings && (
            <div className="settings-panel">
              <h4>Settings</h4>
              
              <div className="setting-section">
                <h5>HR Name Configuration</h5>
                <div className="hr-name-input">
                  <input
                    type="text"
                    placeholder="Enter HR name (e.g., Mario Rossi)"
                    value={hrName}
                    onChange={(e) => handleHrNameChange(e.target.value)}
                    className="hr-name-field"
                  />
                  <div className="hr-name-preview">
                    Preview: {hrName.trim() || 'Default HR Team'}
                  </div>
                </div>
              </div>

              <div className="setting-section">
                <h5>Auto-Refresh Settings</h5>
                <div className="interval-options">
                  {[10, 30, 60, 300].map(interval => (
                    <button
                      key={interval}
                      className={`interval-btn ${autoRefreshInterval === interval ? 'active' : ''}`}
                      onClick={() => handleIntervalChange(interval)}
                    >
                      {interval < 60 ? `${interval}s` : interval === 60 ? '1min' : '5min'}
                    </button>
                  ))}
                </div>
                <div className="auto-refresh-status">
                  Status: <span className={autoRefreshEnabled ? 'enabled' : 'disabled'}>
                    {autoRefreshEnabled ? `Active (${autoRefreshInterval}s)` : 'Disabled'}
                  </span>
                </div>
              </div>
            </div>
           )}
           
           {/* Progress indicator for sync */}
           {syncProgress && syncProgress.active && (
             <div className="sync-progress">
               <div className="progress-header">
                 <span className="progress-title">Progressive Sync</span>
                 <span className="progress-stats">{syncProgress.current}/{syncProgress.total}</span>
               </div>
               <div className="progress-bar">
                 <div 
                   className="progress-fill" 
                   style={{width: `${syncProgress.progress_percent}%`}}
                 ></div>
               </div>
               <div className="progress-status">{syncProgress.current_conversation}</div>
               <div className="progress-time">⏱️ {syncProgress.elapsed_time}s</div>
             </div>
           )}
        </div>
        
        <div className="conversation-list">
          {isLoading ? (
            <div className="loading-message">Loading saved conversations...</div>
          ) : conversations.length === 0 ? (
            <div className="no-conversations">No conversations found.</div>
          ) : (
            (() => {
              // Filter by unread if needed
              let filtered = filterUnreadOnly
                ? conversations.filter(conv => conv.is_unread)
                : [...conversations];
              // Filter by search query (case-insensitive, partial match on sender_name)
              if (searchQuery.trim()) {
                const q = searchQuery.trim().toLowerCase();
                filtered = filtered.filter(conv =>
                  conv.sender_name && conv.sender_name.toLowerCase().includes(q)
                );
              }
              // Sort
              if (sortOrder === "alpha") {
                filtered.sort((a, b) => {
                  const nameA = (a.sender_name || '').toLowerCase();
                  const nameB = (b.sender_name || '').toLowerCase();
                  return nameA.localeCompare(nameB);
                });
              } else {
                // Default: newest to oldest (by last message timestamp if available, fallback to unread priority)
                filtered.sort((a, b) => {
                  // Try to use last_message_timestamp if available
                  if (a.last_message_timestamp && b.last_message_timestamp) {
                    return new Date(b.last_message_timestamp) - new Date(a.last_message_timestamp);
                  }
                  // Fallback: unread first
                  return (b.is_unread ? 1 : 0) - (a.is_unread ? 1 : 0);
                });
              }
              if (filtered.length === 0) {
                return (
                  <div className="no-conversations">
                    <span role="img" aria-label="party">🎉</span><br/>
                    No conversations found.<br/>
                    <span style={{fontSize: '14px'}}>Press the blue refresh button to fetch new conversations :)</span>
                  </div>
                );
              }
              return filtered.map((conv, idx) => (
                <MessageCard
                  key={idx}
                  message={conv}
                  isSelected={selectedConversation?.sender_name === conv.sender_name}
                  onClick={() => handleSelectConversation(conv)}
                />
              ));
            })()
          )}
        </div>
      </div>
      
      <div className="detail-panel">
        {selectedConversation ? (
          <ConversationDetail
            conversation={selectedConversation}
            templates={templates}
            onSend={handleSendMessage}
            hrName={hrName}
          />
        ) : (
          <div className="placeholder">
            <div className="placeholder-icon">💬</div>
            <h3>Select a conversation</h3>
            <p>Choose a conversation from the sidebar to start messaging</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
