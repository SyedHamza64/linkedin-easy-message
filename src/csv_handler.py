import csv
import os
import pandas as pd
from datetime import datetime

class CSVHandler:
    def __init__(self):
        self.templates_path = 'data/response_templates.csv'
        self.history_path = 'data/message_history.csv'
        self.ensure_files_exist()
    
    def ensure_files_exist(self):
        """Ensure CSV files and directories exist"""
        os.makedirs('data', exist_ok=True)
        
        # Create message history file if it doesn't exist
        if not os.path.exists(self.history_path):
            with open(self.history_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'timestamp', 'sender_name', 'original_message', 
                    'category', 'matched_keyword', 'response_template', 
                    'personalized_response', 'response_sent'
                ])
            print(f"✓ Created message history file: {self.history_path}")
    
    def load_templates(self):
        """Load response templates from CSV"""
        try:
            templates = []
            df = pd.read_csv(self.templates_path, encoding='utf-8')
            
            for _, row in df.iterrows():
                # Split keywords by pipe character
                keywords = [k.strip() for k in row['keywords'].split('|')]
                
                templates.append({
                    'status': row['status'],
                    'keywords': keywords,
                    'response': row['response']
                })
            
            print(f"✓ Loaded {len(templates)} response templates")
            return templates
            
        except Exception as e:
            print(f"✗ Error loading templates: {str(e)}")
            return []
    
    def save_message_history(self, message_data):
        """Save processed message to history"""
        try:
            with open(self.history_path, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    message_data.get('timestamp', datetime.now().isoformat()),
                    message_data.get('sender_name', ''),
                    message_data.get('original_message', ''),
                    message_data.get('category', ''),
                    message_data.get('matched_keyword', ''),
                    message_data.get('response_template', ''),
                    message_data.get('personalized_response', ''),
                    message_data.get('response_sent', False)
                ])
            
            return True
            
        except Exception as e:
            print(f"✗ Error saving to history: {str(e)}")
            return False
    
    def get_message_history(self):
        """Load message history from CSV"""
        try:
            if not os.path.exists(self.history_path):
                return []
            
            df = pd.read_csv(self.history_path, encoding='utf-8')
            return df.to_dict('records')
            
        except Exception as e:
            print(f"✗ Error loading history: {str(e)}")
            return []
    
    def is_message_processed(self, sender_name, message_text):
        """Check if a message has already been processed"""
        history = self.get_message_history()
        
        for record in history:
            if (record['sender_name'] == sender_name and 
                record['original_message'] == message_text):
                return True
        
        return False    