import re
from src.csv_handler import CSVHandler

class MessageCategorizer:
    def __init__(self):
        self.csv_handler = CSVHandler()
        self.templates = self.csv_handler.load_templates()
    
    def categorize_message(self, message_text):
        """Categorize a message based on keywords"""
        # Convert message to lowercase for comparison
        message_lower = message_text.lower()
        
        # Check each template's keywords
        for template in self.templates:
            for keyword in template['keywords']:
                # Use word boundaries for better matching
                # This prevents matching "interessato" in "disinteressato"
                if keyword.lower() in message_lower:
                    return {
                        'category': template['status'],
                        'template': template['response'],
                        'matched_keyword': keyword
                    }
        
        # No match found
        return {
            'category': 'uncategorized',
            'template': None,
            'matched_keyword': None
        }
    
    def personalize_response(self, template, user_data):
        """Replace placeholders in template with actual data"""
        if not template:
            return None
        
        personalized = template
        
        # Replace [firstname] with actual name
        if user_data.get('firstName'):
            personalized = personalized.replace('[firstname]', user_data['firstName'])
        
        # Replace HR name placeholders with actual HR name
        if user_data.get('hrName'):
            personalized = personalized.replace('[hrname]', user_data['hrName'])
            personalized = personalized.replace('[Nome HR]', user_data['hrName'])  # Legacy support
        
        return personalized
    
    def extract_first_name(self, full_name):
        """Extract first name from full name"""
        if not full_name:
            return ""
        
        # Split by space and take the first part
        parts = full_name.strip().split()
        return parts[0] if parts else ""
    
    def process_messages(self, conversations, hr_name="HR Team"):
        """Process conversations and categorize their messages"""
        results = []
        
        for conv in conversations:
            # Handle both conversation format (with all_messages) and individual message format
            if 'all_messages' in conv:
                # Process each message in the conversation
                messages = conv['all_messages']
                sender_name = conv['sender_name']
                
                for message in messages:
                    # Skip messages sent by us (we only want to categorize received messages)
                    if message.get('is_sent', False):
                        continue
                    
                    message_text = message.get('message', '')
                    if not message_text.strip():
                        continue
                    
                    # Check if this specific message was already processed
                    if self.csv_handler.is_message_processed(sender_name, message_text):
                        print(f"⏭️  Skipping already processed message from {sender_name}")
                        continue
                    
                    # Categorize the message
                    categorization = self.categorize_message(message_text)
                    
                    # Extract first name
                    first_name = self.extract_first_name(sender_name)
                    
                    # Personalize response if category found
                    personalized_response = None
                    if categorization['template']:
                        personalized_response = self.personalize_response(
                            categorization['template'],
                            {
                                'firstName': first_name,
                                'hrName': hr_name
                            }
                        )
                    
                    # Prepare result
                    result = {
                        'timestamp': message.get('timestamp', ''),
                        'sender_name': sender_name,
                        'original_message': message_text,
                        'category': categorization['category'],
                        'matched_keyword': categorization['matched_keyword'],
                        'response_template': categorization['template'],
                        'personalized_response': personalized_response,
                        'response_sent': False
                    }
                    
                    # Save to history
                    self.csv_handler.save_message_history(result)
                    
                    results.append(result)
                    
                    print(f"✓ Processed message from {sender_name}")
                    print(f"  Message: {message_text[:50]}...")
                    print(f"  Category: {categorization['category']}")
                    print(f"  Matched keyword: {categorization['matched_keyword']}")
            
            else:
                # Handle legacy individual message format
                msg = conv
                
                # Skip if already processed
                if self.csv_handler.is_message_processed(
                    msg['sender_name'], 
                    msg['message']
                ):
                    print(f"⏭️  Skipping already processed message from {msg['sender_name']}")
                    continue
                
                # Categorize the message
                categorization = self.categorize_message(msg['message'])
                
                # Extract first name
                first_name = self.extract_first_name(msg['sender_name'])
                
                # Personalize response if category found
                personalized_response = None
                if categorization['template']:
                    personalized_response = self.personalize_response(
                        categorization['template'],
                        {
                            'firstName': first_name,
                            'hrName': hr_name
                        }
                    )
                
                # Prepare result
                result = {
                    'timestamp': msg.get('timestamp'),
                    'sender_name': msg['sender_name'],
                    'original_message': msg['message'],
                    'category': categorization['category'],
                    'matched_keyword': categorization['matched_keyword'],
                    'response_template': categorization['template'],
                    'personalized_response': personalized_response,
                    'response_sent': False
                }
                
                # Save to history
                self.csv_handler.save_message_history(result)
                
                results.append(result)
                
                print(f"✓ Processed message from {msg['sender_name']}")
                print(f"  Category: {categorization['category']}")
                print(f"  Matched keyword: {categorization['matched_keyword']}")
        
        return results