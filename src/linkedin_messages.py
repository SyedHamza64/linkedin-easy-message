from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import json
import os
import re
from datetime import datetime

class LinkedInMessageFetcher:
    def __init__(self, driver):
        self.driver = driver
        self.messages = []
        self.wait = WebDriverWait(driver, 10)
        
    def navigate_to_messages(self):
        """Navigate to LinkedIn messaging page"""
        try:
            print("Navigating to LinkedIn messages...")
            
            if "/messaging/" in self.driver.current_url:
                print("✓ Already on messages page")
                return True
                
            self.driver.get('https://www.linkedin.com/messaging/')
            
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "li.msg-conversation-listitem"))
            )
            print("✓ Successfully navigated to messages")
            return True
                    
        except Exception as e:
            print(f"✗ Failed to load messages page: {str(e)}")
            return False
    
    def get_conversation_list(self, limit=20):
        """Get list of conversations from the left sidebar"""
        conversations = []
        
        try:
            conv_elements = self.driver.find_elements(By.CSS_SELECTOR, "li.msg-conversation-listitem")
            print(f"Found {len(conv_elements)} conversation elements")
            
            conv_elements = conv_elements[:limit]
            
            for index, conv in enumerate(conv_elements):
                try:
                    conversation_data = self._extract_conversation_preview(conv, index)
                    if conversation_data:
                        conversations.append(conversation_data)
                        
                except Exception as e:
                    print(f"Error extracting conversation {index}: {str(e)}")
                    continue
                    
            return conversations
            
        except Exception as e:
            print(f"Error getting conversation list: {str(e)}")
            return []
    
    def _extract_conversation_preview(self, conv_element, index):
        """Extract preview data from a conversation element"""
        try:
            sender_name = ""
            try:
                name_element = conv_element.find_element(By.CSS_SELECTOR, ".msg-conversation-listitem__participant-names")
                sender_name = name_element.text.strip()
            except:
                try:
                    h3_elements = conv_element.find_elements(By.TAG_NAME, "h3")
                    if h3_elements:
                        sender_name = h3_elements[0].text.strip()
                except:
                    sender_name = f"Unknown {index}"
            
            # Check for unread messages using multiple methods
            is_unread = False
            unread_count = 0
            
            # Method 1: Notification badge with count (nested structure)
            try:
                # Look for the nested notification badge structure
                notification_badges = conv_element.find_elements(By.CSS_SELECTOR, ".artdeco-notification-badge .notification-badge.notification-badge--show")
                if notification_badges:
                    for badge in notification_badges:
                        try:
                            # Look for the count element inside the badge
                            count_element = badge.find_element(By.CSS_SELECTOR, "span.notification-badge__count")
                            if count_element:
                                count_text = count_element.text.strip()
                                if count_text.isdigit() and int(count_text) > 0:
                                    is_unread = True
                                    unread_count = int(count_text)
                                    print(f"📬 Found unread message(s) for {sender_name}: {count_text} (nested badge method)")
                                    break
                        except:
                            continue
            except Exception as e:
                print(f"Debug: Nested badge method failed for {sender_name}: {e}")
            
            # Method 2: Direct notification badge detection
            if not is_unread:
                try:
                    notification_badges = conv_element.find_elements(By.CSS_SELECTOR, ".notification-badge.notification-badge--show")
                    if notification_badges:
                        for badge in notification_badges:
                            try:
                                count_element = badge.find_element(By.CSS_SELECTOR, ".notification-badge__count")
                                if count_element:
                                    count_text = count_element.text.strip()
                                    if count_text.isdigit() and int(count_text) > 0:
                                        is_unread = True
                                        unread_count = int(count_text)
                                        print(f"📬 Found unread message(s) for {sender_name}: {count_text} (direct badge method)")
                                        break
                            except:
                                continue
                except Exception as e:
                    print(f"Debug: Direct badge method failed for {sender_name}: {e}")
            
            # Method 3: Check for artdeco notification badge with aria-label
            if not is_unread:
                try:
                    artdeco_badges = conv_element.find_elements(By.CSS_SELECTOR, ".artdeco-notification-badge")
                    for badge in artdeco_badges:
                        aria_label = badge.get_attribute("aria-label") or ""
                        if "unread message" in aria_label.lower():
                            # Extract count from aria-label like "1 unread message"
                            count_match = re.search(r'(\d+)\s+unread\s+message', aria_label.lower())
                            if count_match:
                                count_text = count_match.group(1)
                                if count_text.isdigit() and int(count_text) > 0:
                                    is_unread = True
                                    unread_count = int(count_text)
                                    print(f"📬 Found unread message(s) for {sender_name}: {count_text} (aria-label method)")
                                    break
                except Exception as e:
                    print(f"Debug: Aria-label method failed for {sender_name}: {e}")
            
            # Method 4: Check for unread message snippet class
            if not is_unread:
                try:
                    unread_snippets = conv_element.find_elements(By.CSS_SELECTOR, ".msg-conversation-card__message-snippet--unread")
                    if unread_snippets:
                        is_unread = True
                        unread_count = 1
                        print(f"📬 Found unread message for {sender_name} (unread snippet method)")
                except Exception as e:
                    print(f"Debug: Unread snippet method failed for {sender_name}: {e}")
            
            # Method 5: Check for unread class
            if not is_unread:
                try:
                    element_classes = conv_element.get_attribute("class") or ""
                    if "msg-conversation-listitem--unread" in element_classes:
                        is_unread = True
                        unread_count = 1
                        print(f"📬 Found unread message for {sender_name} (class method)")
                except Exception as e:
                    print(f"Debug: Class method failed for {sender_name}: {e}")
            
            # Method 6: Check for bold/unread styling
            if not is_unread:
                try:
                    # Look for bold text which often indicates unread
                    bold_elements = conv_element.find_elements(By.CSS_SELECTOR, "strong, b, .msg-conversation-listitem__participant-names")
                    for element in bold_elements:
                        if element.text.strip() == sender_name:
                            # Check if parent has unread styling
                            parent = element.find_element(By.XPATH, "..")
                            parent_classes = parent.get_attribute("class") or ""
                            if "unread" in parent_classes.lower() or "bold" in parent_classes.lower():
                                is_unread = True
                                unread_count = 1
                                print(f"📬 Found unread message for {sender_name} (styling method)")
                                break
                except Exception as e:
                    print(f"Debug: Styling method failed for {sender_name}: {e}")
            
            print(f"📋 Conversation {index}: {sender_name} - Unread: {is_unread} (Count: {unread_count})")
            
            return {
                'index': index,
                'sender_name': sender_name,
                'is_unread': is_unread,
                'unread_count': unread_count,
                'element': conv_element
            }
            
        except Exception as e:
            print(f"Error in _extract_conversation_preview: {str(e)}")
            return None
    
    def open_conversation(self, conversation):
        """Click on a conversation to open it"""
        try:
            try:
                conversation['element'].click()
            except:
                self.driver.execute_script("arguments[0].click();", conversation['element'])
            # Wait for the message list to appear (dynamic wait instead of sleep)
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".msg-s-message-list"))
            )
            print(f"✓ Opened conversation with {conversation['sender_name']}")
            return True
        except Exception as e:
            print(f"✗ Failed to open conversation: {str(e)}")
            return False
    
    def scroll_to_load_all_messages(self):
        """Scroll up to load all messages in the conversation (optimized, minimal waiting)"""
        try:
            message_area = self.driver.find_element(By.CSS_SELECTOR, ".msg-s-message-list")
            last_count = 0
            same_count_repeats = 0
            max_attempts = 10  # Reduced to avoid too much scrolling
            scroll_attempts = 0
            while same_count_repeats < 2 and max_attempts > 0 and scroll_attempts < 5:
                try:
                    # Scroll to top with a more gentle approach
                    self.driver.execute_script("arguments[0].scrollTop = 0;", message_area)
                    # Wait for new messages to appear (short, only if count increases)
                    message_elements = self.driver.find_elements(By.CSS_SELECTOR, "p.msg-s-event-listitem__body")
                    current_count = len(message_elements)
                    if current_count == last_count:
                        same_count_repeats += 1
                        # Only a very short sleep if nothing new
                        time.sleep(0.3)
                    else:
                        same_count_repeats = 0
                        print(f"📜 Loaded {current_count} messages so far...")
                        # Wait for DOM update if new messages loaded
                        WebDriverWait(self.driver, 1).until(
                            lambda d: len(d.find_elements(By.CSS_SELECTOR, "p.msg-s-event-listitem__body")) > last_count
                        )
                    last_count = current_count
                    max_attempts -= 1
                    scroll_attempts += 1
                except Exception as e:
                    print(f"Scroll attempt {scroll_attempts} failed: {e}")
                    break
            print(f"✓ Finished loading messages. Total: {last_count}")
            return True
        except Exception as e:
            print(f"Error scrolling to load messages: {str(e)}")
            return False
    
    def get_conversation_messages(self):
        """Get all messages from the currently open conversation (optimized)"""
        messages = []
        try:
            self.scroll_to_load_all_messages()
            # No need for extra wait here; scroll already loads messages
            message_elements = self._get_message_elements_with_retry()
            print(f"Found {len(message_elements)} message elements in conversation")
            for index, msg_element in enumerate(message_elements):
                message_data = self._extract_message_data_with_retry(msg_element, index)
                if message_data:
                    messages.append(message_data)
            return messages
        except Exception as e:
            print(f"Error getting conversation messages: {str(e)}")
            return []
    
    def _get_message_elements_with_retry(self, max_retries=3):
        """Get message elements with retry logic for stale elements"""
        for attempt in range(max_retries):
            try:
                message_elements = self.driver.find_elements(By.CSS_SELECTOR, "p.msg-s-event-listitem__body.t-14.t-black--light.t-normal")
                if not message_elements:
                    message_elements = self.driver.find_elements(By.CSS_SELECTOR, "p.msg-s-event-listitem__body")
                return message_elements
            except Exception as e:
                print(f"Attempt {attempt + 1}: Error getting message elements: {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
                else:
                    print("Failed to get message elements after all retries")
                    return []
    
    def _extract_message_data_with_retry(self, msg_element, index, max_retries=3):
        """Extract data from a single message element with retry logic for stale elements"""
        for attempt in range(max_retries):
            try:
                return self._extract_message_data(msg_element, index)
            except Exception as e:
                if "stale element reference" in str(e).lower():
                    print(f"Stale element at index {index}, attempt {attempt + 1}/{max_retries}")
                    if attempt < max_retries - 1:
                        # Re-find the element
                        try:
                            message_elements = self.driver.find_elements(By.CSS_SELECTOR, "p.msg-s-event-listitem__body")
                            if index < len(message_elements):
                                msg_element = message_elements[index]
                                time.sleep(0.5)
                                continue
                        except:
                            pass
                    return {
                        'is_sent': False,
                        'message': f"[Stale element - message {index}]",
                        'timestamp': f"msg_{index:04d}",
                        'message_index': index
                    }
                else:
                    print(f"Error extracting message data at index {index}: {str(e)}")
                    return {
                        'is_sent': False,
                        'message': f"[Error extracting message {index}]",
                        'timestamp': f"msg_{index:04d}",
                        'message_index': index
                    }
        
        return {
            'is_sent': False,
            'message': f"[Failed to extract message {index}]",
            'timestamp': f"msg_{index:04d}",
            'message_index': index
        }
    
    def _extract_message_data(self, msg_element, index):
        """Extract data from a single message element using the working CSS class method"""
        try:
            # Extract message text
            message_body = msg_element.text.strip()
            
            if not message_body:
                inner_html = msg_element.get_attribute("innerHTML")
                if inner_html:
                    message_body = re.sub(r'<[^>]+>', '', inner_html).strip()
                    message_body = re.sub(r'\s+', ' ', message_body).strip()
            
            if not message_body:
                message_body = "[Could not extract message content]"
            
            # Default values
            is_sent = True  # Default to sent
            sender_name = "Hamza Hussain"
            
            # Look up the DOM tree to find the msg-s-event-listitem container
            current_element = msg_element
            for level in range(15):
                try:
                    current_element = current_element.find_element(By.XPATH, "..")
                    container_class = current_element.get_attribute("class") or ""
                    
                    # Look for the msg-s-event-listitem container (but not child elements)
                    if "msg-s-event-listitem" in container_class and "msg-s-event-listitem__" not in container_class:
                        
                        # Check for --other class (RECEIVED message)
                        if "msg-s-event-listitem--other" in container_class:
                            is_sent = False
                            sender_name = "Other Person"
                            break
                        
                        # No --other class means it's YOUR message (SENT)
                        else:
                            is_sent = True
                            sender_name = "Hamza Hussain"
                            break
                            
                except:
                    continue
                
            # Extract timestamp
            timestamp_str = ""
            try:
                current_element = msg_element
                for _ in range(10):
                    current_element = current_element.find_element(By.XPATH, "..")
                    try:
                        time_element = current_element.find_element(By.CSS_SELECTOR, ".msg-s-message-group__timestamp")
                        timestamp_str = time_element.text.strip()
                        break
                    except:
                        continue
            except:
                timestamp_str = f"msg_{index:04d}"
            
            return {
                'is_sent': is_sent,
                'message': message_body,
                'timestamp': timestamp_str,
                'message_index': index
            }
            
        except Exception as e:
            print(f"Error extracting message data at index {index}: {str(e)}")
            return {
                'is_sent': False,
                'message': f"[Error extracting message {index}]",
                'timestamp': f"msg_{index:04d}",
                'message_index': index
            }
    
    def fetch_all_conversations(self, include_read=True, limit=10):
        """Fetch all conversations with all messages"""
        print("Fetching all conversations...")
        
        if not self.navigate_to_messages():
            return []
        
        conversations = self.get_conversation_list(limit=limit)
        
        if not include_read:
            conversations = [c for c in conversations if c['is_unread']]
        
        print(f"Processing {len(conversations)} conversations")
        
        all_data = []
        
        for conv_index, conv in enumerate(conversations):
            print(f"\nProcessing conversation {conv_index + 1}/{len(conversations)}: {conv['sender_name']}")
            
            if self.open_conversation(conv):
                messages = self.get_conversation_messages()
                
                if messages:
                    conversation_data = {
                        'sender_name': conv['sender_name'],
                        'is_unread': conv['is_unread'],
                        'message_count': len(messages),
                        'all_messages': messages,
                        'fetch_time': datetime.now().isoformat()
                    }
                    
                    all_data.append(conversation_data)
                    print(f"✓ Collected {len(messages)} messages from {conv['sender_name']}")
                else:
                    print(f"✗ No messages found for {conv['sender_name']}")
                
                # Dynamic wait: ensure sidebar is ready for next click (wait for conversation list to be clickable)
                try:
                    WebDriverWait(self.driver, 2).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "li.msg-conversation-listitem"))
                    )
                except Exception as e:
                    print(f"Warning: Sidebar not clickable after conversation: {str(e)}")
        
        return all_data
    
    def save_messages_to_json(self, conversations, filename='data/linkedin_messages.json'):
        """Save all messages to a JSON file"""
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        total_messages = sum(len(conv['all_messages']) for conv in conversations)
        
        data = {
            'fetch_time': datetime.now().isoformat(),
            'conversation_count': len(conversations),
            'total_message_count': total_messages,
            'conversations': conversations
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"✓ Saved {len(conversations)} conversations ({total_messages} messages) to {filename}")
        return filename

    def save_conversations_to_individual_files(self, conversations, conversations_dir='data/conversations'):
        """Save each conversation to its own JSON file"""
        try:
            os.makedirs(conversations_dir, exist_ok=True)
        except Exception as e:
            print(f"❌ Error creating conversations directory '{conversations_dir}': {str(e)}")
            raise Exception(f"Cannot create conversations directory: {str(e)}")
        
        saved_files = []
        total_messages = 0
        
        for conv in conversations:
            try:
                sender_name = conv.get('sender_name', 'Unknown')
                filename = self._safe_filename(sender_name) + ".json"
                filepath = os.path.join(conversations_dir, filename)
                
                # Convert to individual file format
                messages = conv.get('all_messages', [])
                
                # Find last received message (not sent by us)
                last_received = ""
                for msg in reversed(messages):
                    if not msg.get('is_sent', False):
                        last_received = msg.get('message', '')
                        break
                
                # Convert messages to individual format
                individual_messages = []
                for msg in messages:
                    individual_messages.append({
                        'is_sent': msg.get('is_sent', False),
                        'message': msg.get('message', ''),
                        'timestamp': msg.get('timestamp', '')
                    })
                
                individual_data = {
                    'sender_name': sender_name,
                    'is_unread': conv.get('is_unread', False),
                    'conversation_preview': last_received[:100] + "..." if len(last_received) > 100 else last_received,
                    'total_messages': len(individual_messages),
                    'messages': individual_messages,
                    'fetch_time': conv.get('fetch_time', datetime.now().isoformat()),
                    'last_received_message': last_received
                }
                
                # Save to individual file
                try:
                    with open(filepath, 'w', encoding='utf-8') as f:
                        json.dump(individual_data, f, indent=2, ensure_ascii=False)
                    
                    saved_files.append(filepath)
                    total_messages += len(individual_messages)
                    print(f"✅ Saved {sender_name}: {len(individual_messages)} messages to {filename}")
                except PermissionError:
                    print(f"❌ Permission denied writing to {filepath}. Check file/directory permissions.")
                    continue
                except Exception as file_error:
                    print(f"❌ Error writing file {filepath}: {str(file_error)}")
                    continue
                
            except Exception as e:
                print(f"❌ Error processing conversation for {conv.get('sender_name', 'Unknown')}: {str(e)}")
                continue
        
        print(f"✅ Saved {len(saved_files)} conversations ({total_messages} total messages) to individual files")
        return saved_files

    def load_individual_conversations(self, conversations_dir='data/conversations'):
        """Load all conversations from individual JSON files"""
        conversations = []
        
        if not os.path.exists(conversations_dir):
            print(f"⚠️  Conversations directory {conversations_dir} not found")
            return conversations
        
        for filename in os.listdir(conversations_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(conversations_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        conversation_data = json.load(f)
                        conversations.append(conversation_data)
                        print(f"📁 Loaded {conversation_data.get('sender_name', 'Unknown')}: {conversation_data.get('total_messages', 0)} messages")
                except Exception as e:
                    print(f"❌ Error loading {filename}: {str(e)}")
                    continue
        
        print(f"📁 Loaded {len(conversations)} conversations from individual files")
        return conversations

    def fetch_and_save_to_individual_files(self, include_read=True, limit=10, conversations_dir='data/conversations'):
        """Fetch conversations from LinkedIn and save directly to individual files"""
        print("🔄 Fetching conversations and saving to individual files...")
        
        # Fetch conversations from LinkedIn
        conversations = self.fetch_all_conversations(include_read=include_read, limit=limit)
        
        if not conversations:
            print("❌ No conversations fetched from LinkedIn")
            return []
        
        # Save directly to individual files
        saved_files = self.save_conversations_to_individual_files(conversations, conversations_dir)
        
        return saved_files

    def fetch_new_conversations_only(self, limit=10, conversations_dir='data/conversations'):
        """Fetch only new/unread conversations and save to individual files"""
        print("📬 Fetching only new/unread conversations...")
        
        # Fetch only new/unread conversations
        new_conversations = self.fetch_new_or_unread_conversations(limit=limit)
        
        if not new_conversations:
            print("📬 No new conversations found")
            return []
        
        # Save to individual files
        saved_files = self.save_conversations_to_individual_files(
            new_conversations, 
            conversations_dir
        )
        
        return saved_files

    def get_unread_conversations(self, limit=20):
        """Get only unread conversations from the left sidebar"""
        unread_conversations = []
        
        try:
            conv_elements = self.driver.find_elements(By.CSS_SELECTOR, "li.msg-conversation-listitem")
            print(f"Found {len(conv_elements)} conversation elements")
            
            conv_elements = conv_elements[:limit]
            
            for index, conv in enumerate(conv_elements):
                try:
                    conversation_data = self._extract_conversation_preview(conv, index)
                    if conversation_data and conversation_data['is_unread']:
                        unread_conversations.append(conversation_data)
                        print(f"📬 Added unread conversation: {conversation_data['sender_name']}")
                        
                except Exception as e:
                    print(f"Error extracting conversation {index}: {str(e)}")
                    continue
                    
            print(f"📬 Found {len(unread_conversations)} unread conversations")
            return unread_conversations
            
        except Exception as e:
            print(f"Error getting unread conversation list: {str(e)}")
            return []

    def fetch_unread_conversations(self, limit=10):
        """Fetch only unread conversations with all messages"""
        print("📬 Fetching only unread conversations...")
        
        if not self.navigate_to_messages():
            return []
        
        unread_conversations = self.get_unread_conversations(limit=limit)
        
        if not unread_conversations:
            print("📬 No unread conversations found")
            return []
        
        print(f"📬 Processing {len(unread_conversations)} unread conversations")
        
        all_data = []
        
        for conv_index, conv in enumerate(unread_conversations):
            print(f"\n📬 Processing unread conversation {conv_index + 1}/{len(unread_conversations)}: {conv['sender_name']}")
            
            if self.open_conversation(conv):
                messages = self.get_conversation_messages()
                
                if messages:
                    conversation_data = {
                        'sender_name': conv['sender_name'],
                        'is_unread': conv['is_unread'],
                        'unread_count': conv.get('unread_count', 1),
                        'message_count': len(messages),
                        'all_messages': messages,
                        'fetch_time': datetime.now().isoformat()
                    }
                    
                    all_data.append(conversation_data)
                    print(f"✅ Collected {len(messages)} messages from unread conversation: {conv['sender_name']}")
                else:
                    print(f"❌ No messages found for unread conversation: {conv['sender_name']}")
                
                time.sleep(2)
        
        return all_data

    def get_new_or_unread_conversations(self, limit=50):
        """Efficiently get only new or unread conversations without processing all"""
        new_or_unread_conversations = []
        
        try:
            conv_elements = self.driver.find_elements(By.CSS_SELECTOR, "li.msg-conversation-listitem")
            print(f"🔍 Scanning {len(conv_elements)} conversations for new/unread messages...")
            
            conv_elements = conv_elements[:limit]
            
            for index, conv in enumerate(conv_elements):
                try:
                    # Quick check for unread indicators without full processing
                    is_new_or_unread = self._quick_unread_check(conv, index)
                    
                    if is_new_or_unread:
                        # Only do full extraction for conversations that are new/unread
                        conversation_data = self._extract_conversation_preview(conv, index)
                        if conversation_data:
                            new_or_unread_conversations.append(conversation_data)
                            print(f"📬 Found new/unread conversation: {conversation_data['sender_name']}")
                    else:
                        # Just log the conversation name for debugging
                        try:
                            name_element = conv.find_element(By.CSS_SELECTOR, ".msg-conversation-listitem__participant-names")
                            sender_name = name_element.text.strip()
                            print(f"📋 Skipped read conversation: {sender_name}")
                        except:
                            print(f"📋 Skipped conversation {index}")
                        
                except Exception as e:
                    print(f"Error checking conversation {index}: {str(e)}")
                    continue
            
            print(f"📬 Found {len(new_or_unread_conversations)} new/unread conversations")
            
            # If no new/unread conversations found, return empty list immediately
            if len(new_or_unread_conversations) == 0:
                print("📬 No new/unread conversations found - returning empty list")
                return []
            
            return new_or_unread_conversations
            
        except Exception as e:
            print(f"Error getting new/unread conversation list: {str(e)}")
            return []

    def fetch_new_or_unread_conversations(self, limit=20):
        """Fetch only new or unread conversations efficiently"""
        print("📬 Fetching only new/unread conversations efficiently...")
        
        if not self.navigate_to_messages():
            return []
        
        new_or_unread_conversations = self.get_new_or_unread_conversations(limit=limit)
        
        if not new_or_unread_conversations:
            print("📬 No new/unread conversations found - no processing needed")
            return []
        
        print(f"📬 Processing {len(new_or_unread_conversations)} new/unread conversations")
        
        all_data = []
        
        for conv_index, conv in enumerate(new_or_unread_conversations):
            print(f"\n📬 Processing new/unread conversation {conv_index + 1}/{len(new_or_unread_conversations)}: {conv['sender_name']}")
            
            if self.open_conversation(conv):
                messages = self.get_conversation_messages()
                
                if messages:
                    conversation_data = {
                        'sender_name': conv['sender_name'],
                        'is_unread': conv['is_unread'],
                        'unread_count': conv.get('unread_count', 1),
                        'message_count': len(messages),
                        'all_messages': messages,
                        'fetch_time': datetime.now().isoformat()
                    }
                    
                    all_data.append(conversation_data)
                    print(f"✅ Collected {len(messages)} messages from new/unread conversation: {conv['sender_name']}")
                else:
                    print(f"❌ No messages found for new/unread conversation: {conv['sender_name']}")
                
                time.sleep(1)  # Reduced delay for faster processing
        
        return all_data

    def _quick_unread_check(self, conv_element, index):
        """Quick check for unread indicators without full processing"""
        try:
            # Method 1: Check for notification badges (fastest)
            try:
                notification_badges = conv_element.find_elements(By.CSS_SELECTOR, ".notification-badge.notification-badge--show")
                if notification_badges:
                    for badge in notification_badges:
                        try:
                            count_element = badge.find_element(By.CSS_SELECTOR, ".notification-badge__count")
                            if count_element:
                                count_text = count_element.text.strip()
                                if count_text.isdigit() and int(count_text) > 0:
                                    return True
                        except:
                            continue
            except:
                pass
            
            # Method 2: Check for artdeco notification badge
            try:
                artdeco_badges = conv_element.find_elements(By.CSS_SELECTOR, ".artdeco-notification-badge")
                for badge in artdeco_badges:
                    aria_label = badge.get_attribute("aria-label") or ""
                    if "unread message" in aria_label.lower():
                        return True
            except:
                pass
            
            # Method 3: Check for unread snippet class
            try:
                unread_snippets = conv_element.find_elements(By.CSS_SELECTOR, ".msg-conversation-card__message-snippet--unread")
                if unread_snippets:
                    return True
            except:
                pass
            
            # Method 4: Check for unread class on the list item
            try:
                element_classes = conv_element.get_attribute("class") or ""
                if "msg-conversation-listitem--unread" in element_classes:
                    return True
            except:
                pass
            
            # Method 5: Check for bold/unread styling
            try:
                bold_elements = conv_element.find_elements(By.CSS_SELECTOR, "strong, b, .msg-conversation-listitem__participant-names")
                for element in bold_elements:
                    parent = element.find_element(By.XPATH, "..")
                    parent_classes = parent.get_attribute("class") or ""
                    if "unread" in parent_classes.lower():
                        return True
            except:
                pass
            
            return False
            
        except Exception as e:
            print(f"Error in quick unread check for conversation {index}: {str(e)}")
            return False

    def _safe_filename(self, sender_name):
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