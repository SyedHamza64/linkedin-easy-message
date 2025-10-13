import json
from datetime import datetime
from src.linkedin_auth import LinkedInAuthenticator
from src.linkedin_messages import LinkedInMessageFetcher
from src.message_categorizer import MessageCategorizer
from src.linkedin_responder import LinkedInResponder
from src.csv_handler import CSVHandler

class LinkedInHRAutomation:
    def __init__(self, hr_name="HR Team"):
        self.hr_name = hr_name
        self.auth = None
        self.csv_handler = CSVHandler()
        self.conversations_dir = 'data/conversations'
    
    def initialize(self, headless=False):
        """Initialize the automation system"""
        print("Initializing LinkedIn HR Automation...")
        print("=" * 50)
        
        # Setup authentication
        self.auth = LinkedInAuthenticator()
        self.auth.setup_driver(headless=headless)
        
        # Try to use saved cookies first
        if not self.auth.load_cookies():
            print("No valid cookies found, performing fresh login...")
            if not self.auth.login():
                print("✗ Login failed!")
                return False
            self.auth.save_cookies()
        
        return True
    
    def run_automation(self, 
                      fetch_messages=True, 
                      categorize=True, 
                      send_responses=True,
                      auto_send=False,
                      message_limit=10):
        """Run the complete automation process using individual conversation files"""
        
        results = {
            'fetched_messages': [],
            'categorized_messages': [],
            'sent_responses': []
        }
        
        try:
            # Step 1: Fetch messages and save to individual files
            if fetch_messages:
                print("\n📥 STEP 1: Fetching LinkedIn Messages to Individual Files")
                print("-" * 50)
                
                fetcher = LinkedInMessageFetcher(self.auth.driver)
                
                # Fetch and save directly to individual files
                saved_files = fetcher.fetch_and_save_to_individual_files(
                    include_read=True,
                    limit=message_limit,
                    conversations_dir=self.conversations_dir
                )
                
                if saved_files:
                    # Load the conversations from individual files for processing
                    individual_conversations = fetcher.load_individual_conversations(self.conversations_dir)
                    results['fetched_messages'] = individual_conversations
                    print(f"✓ Fetched and saved {len(saved_files)} conversations to individual files")
                else:
                    print("✗ No messages fetched or saved")
                    return results
            
            # Step 2: Categorize messages from individual files
            if categorize:
                print("\n🏷️  STEP 2: Categorizing Messages from Individual Files")
                print("-" * 50)
                
                categorizer = MessageCategorizer()
                
                # Use fetched messages or load from individual files
                if results['fetched_messages']:
                    messages_to_process = results['fetched_messages']
                else:
                    # Load from individual files
                    fetcher = LinkedInMessageFetcher(self.auth.driver)
                    messages_to_process = fetcher.load_individual_conversations(self.conversations_dir)
                
                if not messages_to_process:
                    print("❌ No conversations found to categorize")
                    return results
                
                # Convert individual file format to the format expected by categorizer
                converted_messages = []
                for conv in messages_to_process:
                    # Convert back to the format expected by message categorizer
                    converted_conv = {
                        'sender_name': conv['sender_name'],
                        'all_messages': conv['messages'],  # Use the messages array
                        'is_unread': conv.get('is_unread', False),
                        'fetch_time': conv.get('fetch_time', '')
                    }
                    converted_messages.append(converted_conv)
                
                categorized = categorizer.process_messages(
                    converted_messages, 
                    hr_name=self.hr_name
                )
                
                results['categorized_messages'] = categorized
                
                # Show categorization summary
                print(f"\n📊 Categorization Summary:")
                print(f"Total processed: {len(categorized)}")
                
                # Count by category
                category_counts = {}
                for msg in categorized:
                    cat = msg['category']
                    category_counts[cat] = category_counts.get(cat, 0) + 1
                
                for category, count in category_counts.items():
                    print(f"  {category}: {count}")
            
            # Step 3: Send responses
            if send_responses and results['categorized_messages']:
                print("\n📤 STEP 3: Sending Responses")
                print("-" * 50)
                
                # Filter messages that need responses
                messages_to_respond = [
                    msg for msg in results['categorized_messages']
                    if msg['category'] != 'uncategorized' 
                    and msg['personalized_response']
                    and not msg['response_sent']
                ]
                
                if not messages_to_respond:
                    print("No messages need responses")
                    return results
                
                print(f"Found {len(messages_to_respond)} messages that need responses")
                
                # Show what will be sent
                print("\n📋 Responses to be sent:")
                for idx, msg in enumerate(messages_to_respond):
                    print(f"\n{idx + 1}. To: {msg['sender_name']}")
                    print(f"   Category: {msg['category']}")
                    print(f"   Response: {msg['personalized_response'][:100]}...")
                
                # Ask for confirmation if not auto-send
                if not auto_send:
                    confirm = input("\n⚠️  Do you want to send these responses? (yes/no): ")
                    if confirm.lower() != 'yes':
                        print("Response sending cancelled")
                        return results
                
                # Send responses
                responder = LinkedInResponder(self.auth.driver)
                sent_results = responder.send_multiple_responses(messages_to_respond)
                
                results['sent_responses'] = sent_results
                
                # Update CSV with sent status
                for sent in sent_results:
                    if sent['success']:
                        # Update the response_sent status in history
                        # This is simplified - in production you'd update the specific row
                        print(f"✓ Response sent to {sent['sender_name']}")
                
                # Summary
                successful_sends = sum(1 for s in sent_results if s['success'])
                print(f"\n✅ Successfully sent {successful_sends}/{len(sent_results)} responses")
            
            return results
            
        except Exception as e:
            print(f"\n❌ Error during automation: {str(e)}")
            import traceback
            traceback.print_exc()
            return results

    def get_all_conversations(self):
        """Get all conversations from individual files"""
        fetcher = LinkedInMessageFetcher(None)  # No driver needed for loading files
        return fetcher.load_individual_conversations(self.conversations_dir)

    def fetch_new_conversations_only(self, limit=10):
        """Fetch only new/unread conversations and save to individual files"""
        if not self.auth or not self.auth.driver:
            print("❌ Authentication not initialized")
            return []
        
        print("📬 Fetching only new/unread conversations...")
        
        fetcher = LinkedInMessageFetcher(self.auth.driver)
        
        # Fetch only new/unread conversations
        new_conversations = fetcher.fetch_new_or_unread_conversations(limit=limit)
        
        if not new_conversations:
            print("📬 No new conversations found")
            return []
        
        # Save to individual files
        saved_files = fetcher.save_conversations_to_individual_files(
            new_conversations, 
            self.conversations_dir
        )
        
        return saved_files
        
    def close(self):
        """Close the browser and cleanup"""
        if self.auth:
            self.auth.close()