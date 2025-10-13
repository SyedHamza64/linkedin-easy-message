# LinkedIn Automation - Frontend Interface

A modern React-based frontend interface for managing LinkedIn messaging automation.

## Features

- **Modern UI/UX**: Clean, responsive design with dark/light mode toggle
- **Message Management**: View and manage LinkedIn conversations
- **Response Templates**: Customizable response templates with HR name personalization
- **Real-time Preview**: Preview message responses before sending
- **Conversation Tracking**: Track message history and conversation status

## Setup

1. Install dependencies:

   ```bash
   npm install
   ```

2. Start the development server:

   ```bash
   npm start
   ```

3. For production build:
   ```bash
   npm run build
   ```

## Usage

1. **HR Name Configuration**: Click the settings (⚙️) button to set your HR name for personalized responses
2. **Dark Mode**: Toggle between light and dark themes using the 🌙 button
3. **Templates**: Use the response templates on the right sidebar to quickly respond to messages
4. **Conversation Management**: Click on any conversation to view details and send responses

## Configuration

- The frontend connects to the Python backend server running on `http://localhost:5000`
- HR name and theme preferences are stored in browser localStorage
- Response templates are managed through the backend API

## Project Structure

- `src/App.js` - Main application component
- `src/ConversationDetail.js` - Individual conversation view
- `src/MessageCard.js` - Conversation list items
- `src/App.css` - Modern styling with CSS variables and theme support

## API Integration

The frontend integrates with the following backend endpoints:

- `/api/conversations` - Fetch conversations
- `/api/messages/{conversation_id}` - Get conversation messages
- `/api/send_message` - Send new messages
- `/api/templates` - Get response templates
- `/api/preview_response` - Preview template responses

## Production Deployment

1. Build the production version:

   ```bash
   npm run build
   ```

2. Serve the `build` folder using a web server of your choice.

## Technical Details

- Built with React 18
- Responsive design with mobile support
- CSS Variables for theming
- LocalStorage for user preferences
- Modern JavaScript (ES6+)
