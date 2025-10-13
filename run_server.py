#!/usr/bin/env python3
"""
Enhanced server runner with persistent Selenium session management
"""
import os
import sys
import signal
import time
from api_server import app, save_driver_session, authenticator

def graceful_shutdown(signum, frame):
    """Handle shutdown signals gracefully"""
    print("\n🛑 Received shutdown signal, saving driver session...")
    save_driver_session()
    if authenticator and authenticator.driver:
        try:
            print("🔒 Closing browser...")
            authenticator.driver.quit()
        except Exception as e:
            print(f"Error closing browser: {e}")
    print("✅ Shutdown complete")
    sys.exit(0)

def main():
    """Main function to run the server with enhanced session management"""
    print("🚀 Starting LinkedIn Automation Server...")
    print("📝 Press Ctrl+C to shutdown gracefully")
    
    # Register signal handlers
    signal.signal(signal.SIGINT, graceful_shutdown)
    signal.signal(signal.SIGTERM, graceful_shutdown)
    
    try:
        # Run the Flask app
        app.run(debug=True, host='127.0.0.1', port=5000)
    except KeyboardInterrupt:
        print("\n🛑 Keyboard interrupt received")
        graceful_shutdown(None, None)
    except Exception as e:
        print(f"❌ Server error: {e}")
        graceful_shutdown(None, None)

if __name__ == '__main__':
    main() 