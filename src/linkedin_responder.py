from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import time
from datetime import datetime

class LinkedInResponder:
    def __init__(self, driver):
        self.driver = driver
        self.responses_sent = []
    
    def navigate_to_conversation(self, sender_name):
        """Navigate to a specific conversation by sender name"""
        try:
            # Make sure we're on messages page
            if "/messaging/" not in self.driver.current_url:
                self.driver.get('https://www.linkedin.com/messaging/')
                time.sleep(3)
            
            # Find all conversations
            conversations = self.driver.find_elements(
                By.CSS_SELECTOR, 
                "li.msg-conversation-listitem"
            )
            
            # Look for the conversation with matching name
            for conv in conversations:
                try:
                    name_element = conv.find_element(
                        By.CSS_SELECTOR, 
                        ".msg-conversation-listitem__participant-names"
                    )
                    conv_name = name_element.text.strip()
                    
                    if sender_name.lower() in conv_name.lower():
                        # Click to open conversation
                        conv.click()
                        time.sleep(2)
                        print(f"✓ Opened conversation with {sender_name}")
                        return True
                except:
                    continue
            
            print(f"✗ Could not find conversation with {sender_name}")
            return False
            
        except Exception as e:
            print(f"✗ Error navigating to conversation: {str(e)}")
            return False
    
    def send_message(self, message_text):
        """Send a message in the current conversation"""
        try:
            # Find the message input box
            message_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((
                    By.CSS_SELECTOR, 
                    ".msg-form__contenteditable"
                ))
            )
            
            # Click to focus
            message_input.click()
            time.sleep(0.5)
            
            # Clear any existing text
            message_input.clear()
            
            # Type the message
            message_input.send_keys(message_text)
            time.sleep(0.5)
            
            # Find and click send button
            send_button = self.driver.find_element(
                By.CSS_SELECTOR, 
                ".msg-form__send-button"
            )
            
            # Check if send button is enabled
            if send_button.is_enabled():
                send_button.click()
                print("✓ Message sent successfully")
                return True
            else:
                print("✗ Send button is disabled")
                return False
                
        except Exception as e:
            print(f"✗ Error sending message: {str(e)}")
            return False
    
    def send_response(self, sender_name, response_text):
        """Send a response to a specific person"""
        try:
            # Navigate to the conversation
            if not self.navigate_to_conversation(sender_name):
                return False
            
            # Send the message
            if self.send_message(response_text):
                # Record the sent response
                self.responses_sent.append({
                    'sender_name': sender_name,
                    'response': response_text,
                    'timestamp': datetime.now().isoformat()
                })
                return True
            
            return False
            
        except Exception as e:
            print(f"✗ Error in send_response: {str(e)}")
            return False
    
    def send_multiple_responses(self, response_list, delay_between=3):
        """Send multiple responses with delay between them"""
        results = []
        
        for idx, response_data in enumerate(response_list):
            print(f"\nProcessing response {idx + 1}/{len(response_list)}")
            print(f"To: {response_data['sender_name']}")
            
            success = self.send_response(
                response_data['sender_name'],
                response_data['personalized_response']
            )
            
            results.append({
                'sender_name': response_data['sender_name'],
                'success': success,
                'response': response_data['personalized_response']
            })
            
            # Delay between messages to avoid rate limiting
            if idx < len(response_list) - 1:
                print(f"Waiting {delay_between} seconds before next message...")
                time.sleep(delay_between)
        
        return results
    
    def get_sent_responses_summary(self):
        """Get summary of sent responses"""
        return {
            'total_sent': len(self.responses_sent),
            'responses': self.responses_sent
        }