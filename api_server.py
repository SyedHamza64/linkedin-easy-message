from flask import Flask, jsonify, request
from flask_cors import CORS
import json
import os
import time
import pickle
import signal
import sys
import re
from src.csv_handler import CSVHandler
from selenium.webdriver.common.by import By
from src.linkedin_auth import LinkedInAuthenticator
from src.linkedin_responder import LinkedInResponder
from src.linkedin_messages import LinkedInMessageFetcher
from datetime import datetime

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes (for local frontend dev)

CONVERSATIONS_DIR = 'data/conversations'
ORDER_FILE = os.path.join(CONVERSATIONS_DIR, '_order.json')
DRIVER_SESSION_FILE = 'data/driver_session.pkl'
CACHE_TTL = 10  # seconds

# In-memory cache for conversations
conversation_cache = {
    'data': None,
    'last_fetched': 0
}

# Progress tracking for full sync
sync_progress = {
    'active': False,
    'current': 0,
    'total': 0,
    'current_conversation': '',
    'conversations': [],
    'start_time': None
}

authenticator = None
responder = None

def _safe_filename(sender_name):
    """Generate a safe filename from sender name"""
    if not sender_name or sender_name.strip() == "":
        return "Unknown_Contact"
    
    # Replace spaces with underscores and remove/replace unsafe characters
    safe_name = sender_name.strip()
    safe_name = re.sub(r'[<>:"/\\|?*]', '_', safe_name)  # Replace unsafe chars
    safe_name = re.sub(r'\s+', '_', safe_name)  # Replace spaces and multiple whitespace
    safe_name = re.sub(r'_+', '_', safe_name)  # Replace multiple underscores with single
    safe_name = safe_name.strip('_')  # Remove leading/trailing underscores
    
    # Ensure we don't have an empty filename
    if not safe_name:
        safe_name = "Unknown_Contact"
        
    return safe_name

def ensure_conversations_directory():
    """Ensure the conversations directory exists with proper permissions"""
    try:
        if not os.path.exists(CONVERSATIONS_DIR):
            os.makedirs(CONVERSATIONS_DIR, exist_ok=True)
            print(f"✅ Created conversations directory: {CONVERSATIONS_DIR}")
        return True
    except Exception as e:
        print(f"❌ Error creating conversations directory: {str(e)}")
        return False

def load_individual_conversations():
    """Load all conversations from individual JSON files, respecting processing order if available"""
    conversations = []
    if not os.path.exists(CONVERSATIONS_DIR):
        print(f"⚠️  Conversations directory {CONVERSATIONS_DIR} not found")
        return conversations
    order = None
    if os.path.exists(ORDER_FILE):
        try:
            with open(ORDER_FILE, 'r', encoding='utf-8') as f:
                order = json.load(f)
            print(f"🔢 Loaded processing order from _order.json: {order}")
        except Exception as e:
            print(f"⚠️ Could not read _order.json: {e}")
            order = None
    files = [f for f in os.listdir(CONVERSATIONS_DIR) if f.endswith('.json') and f != '_order.json']
    if order:
        # Use the order from _order.json, append any missing files at the end
        ordered_files = []
        for name in order:
            # Find the file that starts with the safe filename for this sender_name
            safe_name = name.replace(' ', '_')
            match = next((f for f in files if f.startswith(safe_name)), None)
            if match:
                ordered_files.append(match)
        # Add any files not in order.json at the end
        ordered_files += [f for f in files if f not in ordered_files]
    else:
        ordered_files = sorted(files)
    for idx, filename in enumerate(ordered_files):
        filepath = os.path.join(CONVERSATIONS_DIR, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                conversation_data = json.load(f)
                api_conversation = {
                    'sender_name': conversation_data.get('sender_name', ''),
                    'is_unread': conversation_data.get('is_unread', False),
                    'message_count': conversation_data.get('total_messages', 0),
                    'all_messages': conversation_data.get('messages', []),
                    'fetch_time': conversation_data.get('fetch_time', ''),
                    'last_received_message': conversation_data.get('last_received_message', ''),
                    'index': idx
                }
                conversations.append(api_conversation)
        except Exception as e:
            print(f"❌ Error loading {filename}: {str(e)}")
            continue
    print(f"📁 Loaded {len(conversations)} conversations from individual files (ordered)")
    return conversations

def save_driver_session():
    """Save driver session info for restoration"""
    global authenticator
    if authenticator and authenticator.driver:
        try:
            # Check if driver is still responsive before trying to save
            current_url = authenticator.driver.current_url
            if not current_url:
                print("⚠️ Driver not responsive, skipping session save")
                return
                
            session_data = {
                'cookies': authenticator.driver.get_cookies(),
                'session_id': authenticator.driver.session_id,
                'command_executor': authenticator.driver.command_executor._url,
                'capabilities': authenticator.driver.capabilities
            }
            os.makedirs(os.path.dirname(DRIVER_SESSION_FILE), exist_ok=True)
            with open(DRIVER_SESSION_FILE, 'wb') as f:
                pickle.dump(session_data, f)
            print("💾 Driver session saved")
        except Exception as e:
            print(f"⚠️ Could not save driver session (driver may be closed): {str(e)[:100]}")
            # Don't re-raise, just continue with shutdown

def restore_driver_session():
    """Try to restore driver session from saved data"""
    global authenticator
    if os.path.exists(DRIVER_SESSION_FILE):
        try:
            with open(DRIVER_SESSION_FILE, 'rb') as f:
                session_data = pickle.load(f)
            
            # Create new driver with same capabilities
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            
            chrome_options = Options()
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
            chrome_options.add_argument('--log-level=3')
            chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            driver = webdriver.Chrome(options=chrome_options)
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            # Navigate to LinkedIn and restore cookies
            driver.get('https://www.linkedin.com')
            for cookie in session_data['cookies']:
                try:
                    driver.add_cookie(cookie)
                except:
                    pass
            
            driver.refresh()
            time.sleep(2)
            
            # Check if still logged in
            if "/feed" in driver.current_url or authenticator.is_logged_in_check():
                print("✅ Successfully restored driver session")
                authenticator.driver = driver
                return True
            else:
                print("❌ Restored session is invalid, will re-login")
                driver.quit()
                return False
                
        except Exception as e:
            print(f"Error restoring driver session: {e}")
            return False
    return False

def kill_orphaned_chromedrivers():
    """Kill only orphaned ChromeDriver processes (safe - doesn't touch user's Chrome windows)"""
    try:
        import subprocess
        subprocess.run(['taskkill', '/F', '/IM', 'chromedriver.exe'], 
                      stdout=subprocess.DEVNULL, 
                      stderr=subprocess.DEVNULL)
        time.sleep(0.5)
    except:
        pass

def show_profile_locked_message():
    """Display message when profile is locked"""
    print("\n" + "="*60)
    print("⚠️  PROFILE IS ALREADY OPENED BY ANOTHER BROWSER INSTANCE")
    print("="*60)
    print("\n📋 Please close the LinkedIn automation browser window manually.")
    print("   (Look for the Chrome window with 'Chrome is being controlled by automated test software')")
    print("\n✅ After closing the browser, restart this script.")
    print("="*60 + "\n")

def ensure_authenticator():
    """Ensure authenticator is initialized and driver is ready"""
    global authenticator
    
    # Check if authenticator exists and driver is still functional
    if authenticator is not None and authenticator.driver is not None:
        try:
            _ = authenticator.driver.current_url
            print("♻️ Reusing existing browser session")
            return authenticator
        except:
            # Driver is dead, cleanup
            try:
                authenticator.driver.quit()
            except:
                pass
            authenticator = None
    
    # Need to initialize browser
    print("🚀 Initializing LinkedIn browser session...")
    
    # PRE-CHECK: Check if profile is locked before attempting to open browser
    profile_path = os.path.abspath("./chrome_profiles/linkedin_session")
    lockfile = os.path.join(profile_path, 'lockfile')
    
    if os.path.exists(lockfile):
        show_profile_locked_message()
        raise Exception("Browser profile is locked - please close the automation browser and restart the script")
    
    # Kill orphaned ChromeDriver processes
    kill_orphaned_chromedrivers()
    
    # Create new authenticator
    authenticator = LinkedInAuthenticator()
    
    # Try to restore existing session first
    if restore_driver_session():
        print("♻️ Using restored browser session")
    else:
        try:
            # Try to create new browser
            authenticator.setup_driver(headless=False)
            
            if not authenticator.is_logged_in:
                print("🔐 No active session found, logging in...")
                if not authenticator.login():
                    raise Exception("LinkedIn login failed")
            else:
                print("✓ Using persistent session (already logged in)")
                
        except Exception as e:
            if "user data directory is already in use" in str(e).lower():
                show_profile_locked_message()
                raise Exception("Browser profile is locked - please close the automation browser and restart the script")
            else:
                raise
    
    return authenticator

def get_responder():
    global responder
    authenticator = ensure_authenticator()
    if responder is None:
        responder = LinkedInResponder(authenticator.driver)
    return responder

@app.route('/api/messages', methods=['GET'])
def get_messages():
    now = time.time()
    force_refresh = request.args.get('force_refresh', '0') == '1'
    unread_only = request.args.get('unread_only', '0') == '1'
    load_saved_only = request.args.get('load_saved_only', '0') == '1'
    
    print(f"🔍 GET /api/messages - force_refresh={force_refresh}, unread_only={unread_only}, load_saved_only={load_saved_only}")
    
    # If load_saved_only is requested, immediately return saved conversations without LinkedIn fetch
    if load_saved_only:
        print("📁 Loading saved conversations only...")
        conversations = load_individual_conversations()
        if conversations:
            conversation_cache['data'] = conversations
            conversation_cache['last_fetched'] = now
            print(f"📁 Loaded {len(conversations)} saved conversations")
            # If unread_only is requested, filter saved data
            if unread_only:
                filtered_data = [conv for conv in conversations if conv.get('is_unread', False)]
                print(f"📬 Filtered to {len(filtered_data)} unread conversations from saved data")
                return jsonify(filtered_data)
            return jsonify(conversations)
        else:
            print("📁 No saved conversations found")
            return jsonify([])
    
    # Check cache first (existing logic)
    if not force_refresh and conversation_cache['data'] is not None and now - conversation_cache['last_fetched'] < CACHE_TTL:
        print("📋 Returning cached data (not expired)")
        # If unread_only is requested, filter cached data
        if unread_only:
            filtered_data = [conv for conv in conversation_cache['data'] if conv.get('is_unread', False)]
            print(f"📬 Filtered to {len(filtered_data)} unread conversations from cache")
            # If no unread conversations found, return all conversations from cache
            if len(filtered_data) == 0:
                print("📬 No unread conversations in cache, returning all cached conversations")
                return jsonify(conversation_cache['data'])
            return jsonify(filtered_data)
        return jsonify(conversation_cache['data'])
    
    # If force_refresh or cache is stale, fetch from LinkedIn
    print("🌐 Fetching fresh data from LinkedIn...")
    try:
        # Ensure conversations directory exists
        if not ensure_conversations_directory():
            return jsonify({"error": "Could not create conversations directory"}), 500
        
        # Ensure authenticator is initialized
        authenticator = ensure_authenticator()
        print("✅ Authenticator ready, starting LinkedIn fetch...")
        fetcher = LinkedInMessageFetcher(authenticator.driver)
        
        # If unread_only is requested, fetch only new/unread conversations efficiently
        if unread_only:
            print("📬 Fetching only new/unread conversations efficiently...")
            # Use new method that saves directly to individual files
            saved_files = fetcher.fetch_new_conversations_only(limit=50)
            
            # Load the conversations from individual files
            conversations = load_individual_conversations()
            
            # If no new/unread conversations found, check if we have any conversations
            if len(saved_files) == 0:
                if len(conversations) > 0:
                    print("📬 No new/unread conversations found, returning existing conversations")
                    conversation_cache['data'] = conversations
                    conversation_cache['last_fetched'] = now
                    return jsonify(conversations)
                else:
                    print("📬 No new/unread conversations found and no saved conversations, fetching all as fallback...")
                    saved_files = fetcher.fetch_and_save_to_individual_files(include_read=True, limit=50, conversations_dir=CONVERSATIONS_DIR)
                    conversations = load_individual_conversations()
        else:
            # Fetch all conversations and save to individual files
            saved_files = fetcher.fetch_and_save_to_individual_files(include_read=True, limit=50, conversations_dir=CONVERSATIONS_DIR)
            conversations = load_individual_conversations()
        
        if conversations:
            conversation_cache['data'] = conversations
            conversation_cache['last_fetched'] = now
            
            print(f"✅ Fresh data loaded: {len(conversations)} conversations")
            
            # If unread_only is requested, filter the fresh data
            if unread_only:
                filtered_data = [conv for conv in conversations if conv.get('is_unread', False)]
                print(f"📬 Filtered to {len(filtered_data)} unread conversations from fresh data")
                # If no unread conversations found, return all conversations
                if len(filtered_data) == 0:
                    print("📬 No unread conversations in fresh data, returning all conversations")
                    return jsonify(conversations)
                return jsonify(filtered_data)
            
            return jsonify(conversations)
        else:
            print("❌ Failed to fetch fresh data")
            # Fallback to loading existing individual files
            fallback_conversations = load_individual_conversations()
            if fallback_conversations:
                print(f"📁 Returning fallback data: {len(fallback_conversations)} conversations")
                return jsonify(fallback_conversations)
            return jsonify([])
        
    except Exception as e:
        print(f"❌ Error fetching messages: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Try to return cached data as fallback
        if conversation_cache['data'] is not None:
            print("🔄 Returning cached data as fallback")
            return jsonify(conversation_cache['data'])
        
        # Last resort: try loading from individual files
        try:
            fallback_conversations = load_individual_conversations()
            if fallback_conversations:
                print(f"📁 Returning individual file data as fallback: {len(fallback_conversations)} conversations")
                return jsonify(fallback_conversations)
        except Exception as fallback_e:
            print(f"❌ Fallback also failed: {str(fallback_e)}")
        
        return jsonify({"error": str(e)}), 500

@app.route('/api/messages/background', methods=['GET'])
def get_messages_background():
    """Background endpoint to fetch new/unread conversations without blocking the UI"""
    now = time.time()
    unread_only = request.args.get('unread_only', '0') == '1'
    
    print(f"🔄 Background fetch - unread_only={unread_only}")
    
    try:
        # Ensure conversations directory exists
        if not ensure_conversations_directory():
            return jsonify({
                'success': False,
                'error': 'Could not create conversations directory'
            }), 500
        
        # Ensure authenticator is initialized
        authenticator = ensure_authenticator()
        print("✅ Authenticator ready, starting background LinkedIn fetch...")
        fetcher = LinkedInMessageFetcher(authenticator.driver)
        
        # Fast path: if unread_only, do a very quick unread badge probe and exit early
        if unread_only:
            try:
                # Avoid navigating if already on messages
                if "/messaging/" not in authenticator.driver.current_url:
                    authenticator.driver.get('https://www.linkedin.com/messaging/')
                # Quick check for any unread badge on page (broaden selector)
                badges = authenticator.driver.find_elements(By.CSS_SELECTOR, ".notification-badge__count")
                any_unread = False
                for b in badges:
                    txt = (b.text or '').strip()
                    if txt.isdigit() and int(txt) > 0:
                        any_unread = True
                        break
                if not any_unread:
                    print("📬 Fast path: No unread badges detected; returning immediately")
                    existing = conversation_cache['data'] if conversation_cache['data'] is not None else load_individual_conversations()
                    return jsonify({
                        'success': True,
                        'new_count': 0,
                        'updated_count': 0,
                        'total_count': len(existing or []),
                        'conversations': existing or []
                    })
            except Exception as e:
                print(f"[WARN] Fast unread probe failed, proceeding normally: {e}")

        # Get existing conversations from cache/file
        existing_conversations = []
        if conversation_cache['data'] is not None:
            existing_conversations = conversation_cache['data']
        elif os.path.exists(CONVERSATIONS_DIR):
            existing_conversations = load_individual_conversations()
        
        # Use the new efficient method to fetch only new/unread conversations with configurable limit
        try:
            limit = int(request.args.get('limit', 25))
        except Exception:
            limit = 25
        if unread_only:
            print("📬 Background: Fetching only new/unread conversations efficiently...")
            new_conversations = fetcher.fetch_new_or_unread_conversations(limit=limit)
        else:
            print("📬 Background: Fetching only new/unread conversations efficiently (not unread_only)...")
            new_conversations = fetcher.fetch_new_or_unread_conversations(limit=limit)
        
        # Merge new conversations with existing ones
        merged_conversations = existing_conversations.copy()
        new_count = 0
        updated_count = 0
        
        for new_conv in new_conversations:
            existing_index = None
            for i, existing_conv in enumerate(merged_conversations):
                if existing_conv['sender_name'].lower() == new_conv['sender_name'].lower():
                    existing_index = i
                    break
            
            if existing_index is not None:
                # Update existing conversation
                merged_conversations[existing_index] = new_conv
                updated_count += 1
            else:
                # Add new conversation
                merged_conversations.append(new_conv)
                new_count += 1
        
        # Save ONLY the changed conversations to individual files to avoid heavy I/O
        try:
            fetcher.save_conversations_to_individual_files(new_conversations, CONVERSATIONS_DIR)
        except Exception as e:
            print(f"⚠️ Error saving changed conversations: {e}")
        
        # Update in-memory cache
        conversation_cache['data'] = merged_conversations
        conversation_cache['last_fetched'] = time.time()
        
        print(f"✅ Background fetch complete: {new_count} new, {updated_count} updated conversations")
        
        return jsonify({
            'success': True,
            'new_count': new_count,
            'updated_count': updated_count,
            'total_count': len(merged_conversations),
            'conversations': merged_conversations
        })
        
    except Exception as e:
        print(f"❌ Error in background fetch: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/conversation/<sender_name>', methods=['GET'])
def get_single_conversation(sender_name):
    try:
        # Ensure authenticator is initialized
        authenticator = ensure_authenticator()
        fetcher = LinkedInMessageFetcher(authenticator.driver)
        # Fetch all conversations to get the list and find the right one
        all_convs = fetcher.get_conversation_list(limit=1000)
        target_conv = None
        for conv in all_convs:
            if sender_name.lower() in conv['sender_name'].lower():
                target_conv = conv
                break
        if not target_conv:
            return jsonify({'error': 'Conversation not found'}), 404
        if fetcher.open_conversation(target_conv):
            messages = fetcher.get_conversation_messages()
            conversation_data = {
                'sender_name': target_conv['sender_name'],
                'is_unread': target_conv['is_unread'],
                'message_count': len(messages),
                'all_messages': messages,
                'fetch_time': time.strftime('%Y-%m-%dT%H:%M:%S')
            }
            # Update cache and file
            now = time.time()
            # Update in-memory cache
            if conversation_cache['data'] is not None:
                updated = False
                for idx, conv in enumerate(conversation_cache['data']):
                    if conv['sender_name'].lower() == sender_name.lower():
                        conversation_cache['data'][idx] = conversation_data
                        updated = True
                        break
                if not updated:
                    conversation_cache['data'].append(conversation_data)
            else:
                conversation_cache['data'] = [conversation_data]
            conversation_cache['last_fetched'] = now
            # Update JSON file using the established individual-file schema
            try:
                os.makedirs(CONVERSATIONS_DIR, exist_ok=True)
                filepath = os.path.join(CONVERSATIONS_DIR, f"{_safe_filename(sender_name)}.json")
                # If we failed to extract any messages, do not overwrite an existing file with empty data
                if len(messages) == 0 and os.path.exists(filepath):
                    print(f"⚠️ No messages extracted for {sender_name}, preserving existing file contents")
                else:
                    # Find last received (incoming) message for preview
                    last_received = ""
                    for msg in reversed(messages):
                        if not msg.get('is_sent', False):
                            last_received = msg.get('message', '')
                            break
                    individual_data = {
                        'sender_name': target_conv['sender_name'],
                        'is_unread': target_conv.get('is_unread', False),
                        'conversation_preview': (last_received[:100] + "...") if len(last_received) > 100 else last_received,
                        'total_messages': len(messages),
                        'messages': [
                            {
                                'is_sent': m.get('is_sent', False),
                                'message': m.get('message', ''),
                                'timestamp': m.get('timestamp', '')
                            }
                            for m in messages
                        ],
                        'fetch_time': conversation_data.get('fetch_time', time.strftime('%Y-%m-%dT%H:%M:%S')),
                        'last_received_message': last_received
                    }
                    with open(filepath, 'w', encoding='utf-8') as f:
                        json.dump(individual_data, f, indent=2, ensure_ascii=False)
            except Exception as e:
                print(f"⚠️ Could not write individual conversation file for {sender_name}: {e}")
            return jsonify(conversation_data)
        else:
            return jsonify({'error': 'Failed to open conversation'}), 500
    except Exception as e:
        print(f"Error fetching single conversation: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/templates', methods=['GET'])
def get_templates():
    handler = CSVHandler()
    templates = handler.load_templates()
    return jsonify(templates)

@app.route('/api/preview_response', methods=['POST'])
def preview_response():
    """Preview a categorized response for a message with custom HR name"""
    try:
        data = request.get_json()
        message_text = data.get('message', '')
        sender_name = data.get('sender_name', 'Test User')
        hr_name = data.get('hr_name', 'HR Team')
        
        if not message_text.strip():
            return jsonify({'error': 'Message text is required'}), 400
        
        # Initialize categorizer
        from src.message_categorizer import MessageCategorizer
        categorizer = MessageCategorizer()
        
        # Categorize the message
        categorization = categorizer.categorize_message(message_text)
        
        # Extract first name
        first_name = categorizer.extract_first_name(sender_name)
        
        # Personalize response if category found
        personalized_response = None
        if categorization['template']:
            personalized_response = categorizer.personalize_response(
                categorization['template'],
                {
                    'firstName': first_name,
                    'hrName': hr_name
                }
            )
        
        return jsonify({
            'sender_name': sender_name,
            'first_name': first_name,
            'hr_name': hr_name,
            'original_message': message_text,
            'category': categorization['category'],
            'matched_keyword': categorization['matched_keyword'],
            'response_template': categorization['template'],
            'personalized_response': personalized_response
        })
        
    except Exception as e:
        print(f"Error in preview_response: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/send_message', methods=['POST'])
def send_message():
    data = request.get_json()
    sender_name = data.get('sender_name')
    message = data.get('message')
    if not sender_name or not message:
        return jsonify({'success': False, 'error': 'Missing sender_name or message'}), 400
    try:
        responder = get_responder()
        success = responder.send_response(sender_name, message)

        # Optimistic, fast return: update cache and file without a slow re-fetch
        now_iso = datetime.now().isoformat()

        # Start from existing conversation (cache or file) if available
        existing_conv = None
        if conversation_cache['data'] is not None:
            for conv in conversation_cache['data']:
                if conv.get('sender_name', '').lower() == sender_name.lower():
                    existing_conv = conv
                    break

        # If not in cache, try to read individual file
        if existing_conv is None:
            try:
                filepath = os.path.join(CONVERSATIONS_DIR, f"{_safe_filename(sender_name)}.json")
                if os.path.exists(filepath):
                    with open(filepath, 'r', encoding='utf-8') as f:
                        file_data = json.load(f)
                    # Convert individual file schema to API shape
                    existing_conv = {
                        'sender_name': file_data.get('sender_name', sender_name),
                        'is_unread': file_data.get('is_unread', False),
                        'message_count': file_data.get('total_messages', 0),
                        'all_messages': file_data.get('messages', []),
                        'fetch_time': file_data.get('fetch_time', now_iso)
                    }
            except Exception as e:
                print(f"[WARN] Could not read existing individual file for {sender_name}: {e}")

        # Build updated conversation
        if existing_conv is None:
            existing_conv = {
                'sender_name': sender_name,
                'is_unread': False,
                'message_count': 0,
                'all_messages': [],
                'fetch_time': now_iso
            }

        sent_msg = {
            'is_sent': True,
            'message': message,
            'timestamp': now_iso,
            'message_index': len(existing_conv.get('all_messages', []))
        }
        all_messages = existing_conv.get('all_messages', []) + [sent_msg]

        updated_conv = {
            **existing_conv,
            'all_messages': all_messages,
            'message_count': len(all_messages),
            'fetch_time': now_iso
        }

        # Update cache entry in-place or append
        try:
            if conversation_cache['data'] is None:
                conversation_cache['data'] = [updated_conv]
            else:
                replaced = False
                for i, conv in enumerate(conversation_cache['data']):
                    if conv.get('sender_name', '').lower() == sender_name.lower():
                        conversation_cache['data'][i] = updated_conv
                        replaced = True
                        break
                if not replaced:
                    conversation_cache['data'].append(updated_conv)
            conversation_cache['last_fetched'] = time.time()
        except Exception as e:
            print(f"[WARN] Could not update cache after send: {e}")

        # Write individual file in established schema (best-effort)
        try:
            os.makedirs(CONVERSATIONS_DIR, exist_ok=True)
            last_received = ""
            for msg in reversed(all_messages):
                if not msg.get('is_sent', False):
                    last_received = msg.get('message', '')
                    break
            individual_data = {
                'sender_name': updated_conv['sender_name'],
                'is_unread': updated_conv.get('is_unread', False),
                'conversation_preview': (last_received[:100] + "...") if len(last_received) > 100 else last_received,
                'total_messages': len(all_messages),
                'messages': [
                    {
                        'is_sent': m.get('is_sent', False),
                        'message': m.get('message', ''),
                        'timestamp': m.get('timestamp', '')
                    } for m in all_messages
                ],
                'fetch_time': now_iso,
                'last_received_message': last_received
            }
            with open(os.path.join(CONVERSATIONS_DIR, f"{_safe_filename(sender_name)}.json"), 'w', encoding='utf-8') as f:
                json.dump(individual_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[WARN] Could not persist individual file after send: {e}")

        return jsonify({'success': success, 'conversation': updated_conv})
    except Exception as e:
        print(f"Error sending message: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/mark_read/<sender_name>', methods=['POST'])
def mark_conversation_read(sender_name):
    """Mark a conversation as read (and trigger LinkedIn UI switch)"""
    try:
        # --- NEW: Switch to another conversation, then to the target one in Selenium ---
        try:
            authenticator = ensure_authenticator()
            if authenticator and hasattr(authenticator, 'driver') and authenticator.driver:
                fetcher = LinkedInMessageFetcher(authenticator.driver)
                if fetcher.navigate_to_messages():
                    conversations = fetcher.get_conversation_list(limit=10)
                    # Find the target and another conversation
                    target_conv = None
                    other_conv = None
                    for conv in conversations:
                        if conv['sender_name'].lower() == sender_name.lower():
                            target_conv = conv
                        elif not other_conv:
                            other_conv = conv
                    # Switch to another conversation first (if available and not the same)
                    if other_conv and other_conv['sender_name'].lower() != sender_name.lower():
                        fetcher.open_conversation(other_conv)
                        time.sleep(1)
                    # Now switch to the target conversation
                    if target_conv:
                        fetcher.open_conversation(target_conv)
                        time.sleep(2)
                        print(f"✓ Switched to {sender_name} in Selenium to mark as read")
        except Exception as e:
            print(f"[WARN] Selenium mark-read switch failed: {e}")
        # --- END NEW ---

        # Update the cache to mark conversation as read
        if conversation_cache['data'] is not None:
            for conv in conversation_cache['data']:
                if conv['sender_name'].lower() == sender_name.lower():
                    conv['is_unread'] = False
                    conv['unread_count'] = 0
                    print(f"📬 Marked conversation with {sender_name} as read")
                    break
        # Update the individual JSON file to mark as read using the same schema
        try:
            filepath = os.path.join(CONVERSATIONS_DIR, f"{_safe_filename(sender_name)}.json")
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    individual_data = json.load(f)
                # Ensure boolean field is consistent
                individual_data['is_unread'] = False
                # Write back preserving the established schema
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(individual_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[WARN] Could not update individual file for mark_read: {e}")
        return jsonify({'success': True, 'message': f'Marked {sender_name} as read'})
    except Exception as e:
        print(f"Error marking conversation as read: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/full_sync', methods=['POST'])
def full_sync():
    """Full sync: fetch ALL conversations and update individual JSON files"""
    try:
        # Get parameters
        data = request.get_json() or {}
        limit = data.get('limit', 100)  # Default to 100 conversations
        
        print(f"🔄 Starting full sync for up to {limit} conversations...")
        
        # Ensure conversations directory exists
        if not ensure_conversations_directory():
            return jsonify({
                'success': False,
                'error': 'Could not create conversations directory',
                'message': 'Directory creation failed'
            }), 500
        
        # Ensure authenticator is initialized
        authenticator = ensure_authenticator()
        print("✅ Authenticator ready, starting full LinkedIn sync...")
        fetcher = LinkedInMessageFetcher(authenticator.driver)
        
        processing_order = []
        # Fetch all conversations and save to individual files
        print(f"📥 Fetching all conversations (limit: {limit})...")
        saved_files = []
        for conv in fetcher.get_conversation_list(limit=limit):
            if not sync_progress['active']:  # Check if cancelled
                break
                
            sync_progress.update({
                'current': len(processing_order) + 1,
                'current_conversation': f"Processing: {conv['sender_name']}"
            })
            
            print(f"\n📥 Processing conversation {len(processing_order) + 1}/{limit}: {conv['sender_name']}")
            
            if fetcher.open_conversation(conv):
                messages = fetcher.get_conversation_messages()
                
                if messages:
                    # Find last received message
                    last_received = ""
                    for msg in reversed(messages):
                        if not msg.get('is_sent', False):
                            last_received = msg.get('message', '')
                            break
                    
                    conversation_data = {
                        'sender_name': conv['sender_name'],
                        'is_unread': conv['is_unread'],
                        'message_count': len(messages),
                        'all_messages': messages,
                        'fetch_time': datetime.now().isoformat(),
                        'last_received_message': last_received
                    }
                    
                    # Save individual file immediately
                    try:
                        filename = fetcher._safe_filename(conv['sender_name']) + ".json"
                        filepath = os.path.join(CONVERSATIONS_DIR, filename)
                        
                        individual_data = {
                            'sender_name': conv['sender_name'],
                            'is_unread': conv.get('is_unread', False),
                            'conversation_preview': last_received[:100] + "..." if len(last_received) > 100 else last_received,
                            'total_messages': len(messages),
                            'messages': [{'is_sent': m.get('is_sent', False), 'message': m.get('message', ''), 'timestamp': m.get('timestamp', '')} for m in messages],
                            'fetch_time': conversation_data['fetch_time'],
                            'last_received_message': last_received
                        }
                        
                        with open(filepath, 'w', encoding='utf-8') as f:
                            json.dump(individual_data, f, indent=2, ensure_ascii=False)
                        
                        print(f"✅ Saved {conv['sender_name']}: {len(messages)} messages")
                        
                        # Add to processed list and update progress
                        processed_conversations.append(conversation_data)
                        
                        # Update conversations in progress (merge with existing)
                        existing_conversations = sync_progress['conversations'].copy()
                        
                        # Find and update existing conversation or add new one
                        updated = False
                        for i, existing_conv in enumerate(existing_conversations):
                            if existing_conv['sender_name'].lower() == conv['sender_name'].lower():
                                existing_conversations[i] = conversation_data
                                updated = True
                                break
                        
                        if not updated:
                            existing_conversations.append(conversation_data)
                        
                        sync_progress['conversations'] = existing_conversations
                        
                        # Add to processing order
                        processing_order.append(conv['sender_name'])
                        
                    except Exception as e:
                        print(f"❌ Error saving {conv['sender_name']}: {str(e)}")
                        continue
                
                time.sleep(1)  # Small delay between conversations
        
        # Complete the sync
        final_conversations = load_individual_conversations()
        
        # Update in-memory cache
        conversation_cache['data'] = final_conversations
        conversation_cache['last_fetched'] = time.time()
        
        sync_result = {
            'success': True,
            'message': f'Full sync completed successfully',
            'total_processed': len(saved_files),
            'total_conversations': len(final_conversations),
            'conversations': final_conversations,
            'sync_time': time.strftime('%Y-%m-%dT%H:%M:%S')
        }
        
        print(f"✅ Full sync complete: {len(saved_files)} conversations processed, {len(final_conversations)} total conversations")
        # After saving all conversations, save the processing order
        try:
            with open(ORDER_FILE, 'w', encoding='utf-8') as f:
                json.dump(processing_order, f, ensure_ascii=False, indent=2)
            print(f"🔢 Saved processing order to _order.json: {processing_order}")
        except Exception as e:
            print(f"⚠️ Could not save _order.json: {e}")
        return jsonify(sync_result)
        
    except Exception as e:
        print(f"❌ Error in full sync: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Full sync failed'
        }), 500

@app.route('/api/full_sync_progressive', methods=['POST'])
def full_sync_progressive():
    """Start progressive full sync that can be monitored via /api/sync_progress"""
    global sync_progress
    
    try:
        # Check if sync is already running
        if sync_progress['active']:
            return jsonify({
                'success': False,
                'error': 'Sync already in progress',
                'message': 'Another sync operation is currently running'
            }), 409
        
        # Get parameters
        data = request.get_json() or {}
        limit = data.get('limit', 100)
        
        print(f"🔄 Starting progressive full sync for up to {limit} conversations...")
        
        # Initialize progress tracking
        sync_progress.update({
            'active': True,
            'current': 0,
            'total': limit,
            'current_conversation': 'Initializing...',
            'conversations': load_individual_conversations(),  # Start with existing
            'start_time': time.time()
        })
        
        # Ensure conversations directory exists
        if not ensure_conversations_directory():
            sync_progress['active'] = False
            return jsonify({
                'success': False,
                'error': 'Could not create conversations directory',
                'message': 'Directory creation failed'
            }), 500
        
        # Start sync in background thread
        import threading
        sync_thread = threading.Thread(target=run_progressive_sync, args=(limit,))
        sync_thread.daemon = True
        sync_thread.start()
        
        return jsonify({
            'success': True,
            'message': 'Progressive sync started',
            'progress_endpoint': '/api/sync_progress'
        })
        
    except Exception as e:
        sync_progress['active'] = False
        print(f"❌ Error starting progressive sync: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Failed to start progressive sync'
        }), 500

def run_progressive_sync(limit):
    """Run the progressive sync in background"""
    global sync_progress
    
    try:
        # Ensure authenticator is initialized
        authenticator = ensure_authenticator()
        print("✅ Authenticator ready, starting progressive LinkedIn sync...")
        fetcher = LinkedInMessageFetcher(authenticator.driver)
        
        # Navigate to messages
        if not fetcher.navigate_to_messages():
            sync_progress.update({
                'active': False,
                'current_conversation': 'Failed to navigate to messages'
            })
            return
        
        # Get conversation list
        sync_progress['current_conversation'] = 'Fetching conversation list...'
        conversations_list = fetcher.get_conversation_list(limit=limit)
        sync_progress['total'] = len(conversations_list)
        
        if not conversations_list:
            sync_progress.update({
                'active': False,
                'current_conversation': 'No conversations found'
            })
            return
        
        print(f"📥 Processing {len(conversations_list)} conversations progressively...")
        
        processed_conversations = []
        processing_order = []
        
        for conv_index, conv in enumerate(conversations_list):
            if not sync_progress['active']:  # Check if cancelled
                break
                
            sync_progress.update({
                'current': conv_index + 1,
                'current_conversation': f"Processing: {conv['sender_name']}"
            })
            
            # Check if conversation already exists and is read - skip if so
            filename = fetcher._safe_filename(conv['sender_name']) + ".json"
            filepath = os.path.join(CONVERSATIONS_DIR, filename)
            
            should_skip = False
            if os.path.exists(filepath):
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        existing_data = json.load(f)
                    # Skip if conversation is read (not unread)
                    if not existing_data.get('is_unread', False) and not conv.get('is_unread', False):
                        print(f"⏭️ Skipping conversation {conv_index + 1}/{len(conversations_list)}: {conv['sender_name']} (already saved and read)")
                        
                        # Still add to processing order
                        processing_order.append(conv['sender_name'])
                        
                        # Add existing conversation to progress (convert to API format)
                        conversation_data = {
                            'sender_name': existing_data.get('sender_name', ''),
                            'is_unread': existing_data.get('is_unread', False),
                            'message_count': existing_data.get('total_messages', 0),
                            'all_messages': existing_data.get('messages', []),
                            'fetch_time': existing_data.get('fetch_time', ''),
                            'last_received_message': existing_data.get('last_received_message', ''),
                            'index': conv_index
                        }
                        
                        # Update sync progress with existing conversation
                        existing_conversations = sync_progress['conversations'].copy()
                        updated = False
                        for i, existing_conv in enumerate(existing_conversations):
                            if existing_conv['sender_name'].lower() == conv['sender_name'].lower():
                                existing_conversations[i] = conversation_data
                                updated = True
                                break
                        if not updated:
                            existing_conversations.append(conversation_data)
                        sync_progress['conversations'] = existing_conversations
                        
                        should_skip = True
                except Exception as e:
                    print(f"⚠️ Could not read existing file for {conv['sender_name']}: {e}")
            
            if should_skip:
                continue
            
            print(f"\n📥 Processing conversation {conv_index + 1}/{len(conversations_list)}: {conv['sender_name']}")
            
            if fetcher.open_conversation(conv):
                messages = fetcher.get_conversation_messages()
                
                if messages:
                    # Find last received message
                    last_received = ""
                    for msg in reversed(messages):
                        if not msg.get('is_sent', False):
                            last_received = msg.get('message', '')
                            break
                    
                    conversation_data = {
                        'sender_name': conv['sender_name'],
                        'is_unread': conv['is_unread'],
                        'message_count': len(messages),
                        'all_messages': messages,
                        'fetch_time': datetime.now().isoformat(),
                        'last_received_message': last_received
                    }
                    
                    # Save individual file immediately
                    try:
                        filename = fetcher._safe_filename(conv['sender_name']) + ".json"
                        filepath = os.path.join(CONVERSATIONS_DIR, filename)
                        
                        individual_data = {
                            'sender_name': conv['sender_name'],
                            'is_unread': conv.get('is_unread', False),
                            'conversation_preview': last_received[:100] + "..." if len(last_received) > 100 else last_received,
                            'total_messages': len(messages),
                            'messages': [{'is_sent': m.get('is_sent', False), 'message': m.get('message', ''), 'timestamp': m.get('timestamp', '')} for m in messages],
                            'fetch_time': conversation_data['fetch_time'],
                            'last_received_message': last_received
                        }
                        
                        with open(filepath, 'w', encoding='utf-8') as f:
                            json.dump(individual_data, f, indent=2, ensure_ascii=False)
                        
                        print(f"✅ Saved {conv['sender_name']}: {len(messages)} messages")
                        
                        # Add to processed list and update progress
                        processed_conversations.append(conversation_data)
                        
                        # Update conversations in progress (merge with existing)
                        existing_conversations = sync_progress['conversations'].copy()
                        
                        # Find and update existing conversation or add new one
                        updated = False
                        for i, existing_conv in enumerate(existing_conversations):
                            if existing_conv['sender_name'].lower() == conv['sender_name'].lower():
                                existing_conversations[i] = conversation_data
                                updated = True
                                break
                        
                        if not updated:
                            existing_conversations.append(conversation_data)
                        
                        sync_progress['conversations'] = existing_conversations
                        
                        # Add to processing order
                        processing_order.append(conv['sender_name'])
                        
                    except Exception as e:
                        print(f"❌ Error saving {conv['sender_name']}: {str(e)}")
                        continue
                
                time.sleep(1)  # Small delay between conversations
        
        # Complete the sync
        final_conversations = load_individual_conversations()
        
        # Update in-memory cache
        conversation_cache['data'] = final_conversations
        conversation_cache['last_fetched'] = time.time()
        
        sync_progress.update({
            'active': False,
            'current_conversation': f'Completed! Processed {len(processed_conversations)} conversations',
            'conversations': final_conversations
        })
        
        print(f"✅ Progressive sync complete: {len(processed_conversations)} conversations processed")
        # After saving all conversations, save the processing order
        try:
            with open(ORDER_FILE, 'w', encoding='utf-8') as f:
                json.dump(processing_order, f, ensure_ascii=False, indent=2)
            print(f"🔢 Saved processing order to _order.json: {processing_order}")
        except Exception as e:
            print(f"⚠️ Could not save _order.json: {e}")
        
    except Exception as e:
        print(f"❌ Error in progressive sync: {str(e)}")
        sync_progress.update({
            'active': False,
            'current_conversation': f'Error: {str(e)}'
        })

@app.route('/api/sync_progress', methods=['GET'])
def get_sync_progress():
    """Get current sync progress"""
    global sync_progress
    
    return jsonify({
        'active': sync_progress['active'],
        'current': sync_progress['current'],
        'total': sync_progress['total'],
        'current_conversation': sync_progress['current_conversation'],
        'conversations': sync_progress['conversations'],
        'progress_percent': round((sync_progress['current'] / max(sync_progress['total'], 1)) * 100, 1) if sync_progress['total'] > 0 else 0,
        'elapsed_time': round(time.time() - sync_progress['start_time'], 1) if sync_progress['start_time'] else 0
    })

@app.route('/api/sync_cancel', methods=['POST'])
def cancel_sync():
    """Cancel ongoing sync"""
    global sync_progress
    
    if sync_progress['active']:
        sync_progress['active'] = False
        sync_progress['current_conversation'] = 'Cancelled by user'
        return jsonify({'success': True, 'message': 'Sync cancelled'})
    else:
        return jsonify({'success': False, 'message': 'No active sync to cancel'})

def signal_handler(sig, frame):
    """Handle shutdown signals to save driver session"""
    print("\n🛑 Shutting down gracefully...")
    
    # Set a timeout for the entire shutdown process
    import threading
    shutdown_timer = threading.Timer(5.0, lambda: (print("⚠️ Shutdown timeout, forcing exit"), os._exit(1)))
    shutdown_timer.start()
    
    try:
        # Try to save session quickly
        save_driver_session()
    except Exception as e:
        print(f"⚠️ Error during session save: {str(e)[:50]}")
    
    # Close driver quickly
    if authenticator and authenticator.driver:
        try:
            authenticator.driver.quit()
        except Exception as e:
            print(f"⚠️ Error closing driver: {str(e)[:50]}")
    
    shutdown_timer.cancel()
    print("✅ Shutdown complete")
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

@app.route('/api/shutdown', methods=['POST'])
def shutdown():
    """Graceful shutdown endpoint"""
    try:
        save_driver_session()
    except Exception as e:
        print(f"⚠️ Error during session save: {str(e)[:50]}")
    
    if authenticator and authenticator.driver:
        try:
            authenticator.driver.quit()
        except Exception as e:
            print(f"⚠️ Error closing driver: {str(e)[:50]}")
    
    return jsonify({'success': True, 'message': 'Shutdown initiated'})

def initialize_on_startup():
    """Initialize browser and fetch conversations on server startup"""
    try:
        print("\n🔄 Initializing browser and fetching conversations...")
        
        # Initialize browser (will use saved session if available)
        auth = ensure_authenticator()
        
        if auth.is_logged_in:
            print("✅ Already logged in from saved session!")
        else:
            print("✅ Logged in successfully!")
        
        # Navigate to messages page and scroll to load conversations
        fetcher = LinkedInMessageFetcher(auth.driver)
        
        print("📍 Navigating to LinkedIn messages page...")
        if fetcher.navigate_to_messages():
            print("✅ Successfully navigated to messages")
            
            # Scroll to load conversations (minimum 3 scrolls)
            print("📜 Scrolling to load conversations...")
            fetcher.scroll_to_load_conversations(target_count=50, min_scrolls=3)
        else:
            print("⚠️ Failed to navigate to messages page")
        
        # Check if we have existing conversations
        existing_conversations = load_individual_conversations()
        
        if existing_conversations and len(existing_conversations) > 0:
            # We have existing conversations, just fetch new/unread ones
            print(f"📁 Found {len(existing_conversations)} existing conversations")
            print("📬 Fetching only new/unread conversations...")
            saved_files = fetcher.fetch_new_conversations_only(limit=50)
            
            if saved_files and len(saved_files) > 0:
                print(f"✅ Fetched {len(saved_files)} new unread conversation(s)")
            else:
                print("📭 No new unread messages")
        else:
            # No existing conversations, do a full fetch
            print("📥 No existing conversations found - fetching all conversations...")
            saved_files = fetcher.fetch_and_save_to_individual_files(
                include_read=True, 
                limit=50, 
                conversations_dir=CONVERSATIONS_DIR
            )
            
            if saved_files and len(saved_files) > 0:
                print(f"✅ Fetched {len(saved_files)} conversation(s)")
            else:
                print("📭 No conversations found")
        
        # Update conversation cache after fetching
        all_conversations = load_individual_conversations()
        conversation_cache['data'] = all_conversations
        conversation_cache['last_fetched'] = time.time()
        print(f"✅ Cache updated with {len(all_conversations)} conversation(s)")
        
        print("🎉 Initialization complete! Browser is ready.\n")
        
    except Exception as e:
        print(f"⚠️ Error during initialization: {e}")
        import traceback
        traceback.print_exc()
        print("Server will continue running. Browser will open when you click refresh.\n")

if __name__ == '__main__':
    # Initialize browser on startup
    initialize_on_startup()
    
    # Run the Flask app
    app.run(debug=True, host='127.0.0.1', port=5000, use_reloader=False) 