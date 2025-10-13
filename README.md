# LinkedIn Automation System

A comprehensive LinkedIn messaging automation system with a modern React frontend and Python backend. The system helps automate LinkedIn message responses using AI-powered categorization and customizable templates.

## 🚀 Quick Setup & Launch

### Step 1: Configure Credentials

1. Create a `.env` file in the project root directory
2. Add your LinkedIn credentials:
   ```env
   LINKEDIN_EMAIL=your_linkedin_email@example.com
   LINKEDIN_PASSWORD=your_linkedin_password
   ```

### Step 2: Launch Backend

1. Open a terminal in the project root directory
2. Run the backend server:
   ```bash
   python api_server.py
   ```
   The backend will start on `http://localhost:5000`

### Step 3: Launch Frontend

1. Open **another terminal window**
2. Navigate to the frontend directory:
   ```bash
   cd linkedin-frontend
   ```
3. Start the React development server:
   ```bash
   npm start
   ```
   The frontend will open at `http://localhost:3000`

### Step 4: First Time Setup

1. Once the frontend loads, click the **"Full Sync"** button
2. This will load all your LinkedIn conversations (**ONLY REQUIRED FIRST TIME**)
3. Your conversations will be saved locally for future use

### Step 5: Ongoing Usage

- **New conversations**: Click "Quick Refresh" button to manually update
- **Automatic updates**: Backend automatically refreshes every 30 seconds (customizable)
- **HR Name**: Click the settings (⚙️) button to configure your name for personalized responses

## 🌟 Features

### Backend Capabilities

- **LinkedIn Integration**: Automated login and message fetching using Selenium
- **AI-Powered Categorization**: Intelligent message classification using machine learning
- **Response Templates**: Customizable response templates with personalization
- **HR Name Personalization**: Dynamic name substitution in responses using `[firstname]` and `[hrname]` placeholders
- **Message History Tracking**: Complete conversation and response history
- **RESTful API**: Comprehensive API for frontend integration
- **Auto-refresh**: Configurable automatic conversation updates (default: 30 seconds)

### Frontend Features

- **Modern UI/UX**: Clean, responsive design with CSS variables and animations
- **Dark/Light Mode**: Toggle between themes with localStorage persistence
- **Real-time Updates**: Live conversation and message management
- **Template Management**: Easy-to-use response template system
- **HR Configuration**: Settings panel for HR name customization
- **Conversation Preview**: Quick overview of message content and counts
- **Quick Actions**: Full sync, quick refresh, and auto-refresh controls

## 📋 Prerequisites

- Python 3.8+
- Node.js 14+
- Chrome browser (for Selenium automation)
- LinkedIn account credentials

## 📁 Project Structure

```
linkedin-auto-1/
├── .env                         # LinkedIn credentials (create this file)
├── README.md                    # This file
├── requirements.txt             # Python dependencies
├── api_server.py               # Flask API server (run this for backend)
├── src/                        # Backend Python modules
│   ├── linkedin_auth.py        # LinkedIn authentication
│   ├── linkedin_automation.py  # Main automation logic
│   ├── linkedin_messages.py    # Message fetching and processing
│   ├── linkedin_responder.py   # Response sending
│   ├── message_categorizer.py  # AI-powered message classification
│   └── csv_handler.py         # Data persistence
├── linkedin-frontend/          # React frontend application
│   ├── src/
│   │   ├── App.js             # Main application component
│   │   ├── ConversationDetail.js # Individual conversation view
│   │   ├── MessageCard.js     # Conversation list items
│   │   └── App.css            # Modern styling with theme support
│   └── public/                # Static assets
└── data/                      # Data storage
    ├── conversations/         # Conversation JSON files
    ├── message_history.csv    # Message tracking
    └── response_templates.csv # Response templates
```

## 🔧 Configuration

### Response Templates

Edit `data/response_templates.csv` to customize response templates:

- Use `[firstname]` for automatic name extraction from messages
- Use `[hrname]` for HR name substitution (configured in frontend)
- Categorize templates by message type (interessato, altro, uncategorized)

### Auto-refresh Settings

- Default: Backend refreshes conversations every 30 seconds
- Customizable in the backend code (`api_server.py`)
- Manual refresh available via "Quick Refresh" button

### HR Name Setup

1. Click the settings (⚙️) button in the frontend
2. Enter your HR name for personalized responses
3. Setting is automatically saved and applied to all templates

## 🔌 API Endpoints

- `GET /api/conversations` - Fetch all conversations
- `GET /api/messages/{conversation_id}` - Get conversation messages
- `POST /api/send_message` - Send a new message
- `GET /api/templates` - Get response templates
- `POST /api/preview_response` - Preview template with personalization
- `POST /api/refresh_conversations` - Quick refresh conversation data
- `POST /api/full_sync` - Perform full data synchronization

## 🎨 UI Features

### Theme Support

- **Light Mode**: Clean, professional appearance
- **Dark Mode**: Eye-friendly dark theme
- **Auto-switching**: Remembers user preference

### Responsive Design

- Mobile-friendly layout
- Compact design for efficient space usage
- Custom scrollbars and hover effects

### Interactive Elements

- Loading states for all operations
- Hover effects and smooth transitions
- Real-time template preview
- Success/error notifications

## 📋 Daily Workflow

1. **Morning Setup**: Start both backend and frontend servers
2. **First Use**: Click "Full Sync" to load all conversations
3. **Review Messages**: Browse conversations in the left sidebar
4. **Quick Responses**: Use templates from the right sidebar
5. **Ongoing Updates**: Backend auto-refreshes every 30 seconds
6. **Manual Refresh**: Use "Quick Refresh" for immediate updates

## 🔐 Security & Privacy

- Credentials stored securely in `.env` file
- No sensitive data committed to repository
- LinkedIn credentials handled securely through Selenium
- Conversation data stored locally
- Cookie management for session persistence

## 🤝 Support

This system is designed for HR professionals and recruiters to efficiently manage LinkedIn messaging workflows while maintaining personalized communication.

## 📝 License

This project is for internal use and client delivery.
