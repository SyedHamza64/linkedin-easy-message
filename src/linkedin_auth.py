from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import os
from dotenv import load_dotenv
import pickle

load_dotenv()

class LinkedInAuthenticator:
    def __init__(self):
        self.driver = None
        self.is_logged_in = False
        
    def setup_driver(self, headless=False):
        """Set up Chrome driver with anti-detection measures"""
        chrome_options = webdriver.ChromeOptions()
        
        # Anti-detection measures
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Suppress logs
        chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
        chrome_options.add_argument('--log-level=3')
        
        # Add user agent
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        if headless:
            chrome_options.add_argument('--headless')
            
        # Initialize driver (using method that works)
        self.driver = webdriver.Chrome(options=chrome_options)
        
        # Additional anti-detection
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        print("✓ Chrome driver initialized successfully")
    
    def login(self, email=None, password=None):
        """Login to LinkedIn"""
        try:
            # Use provided credentials or get from environment
            email = email or os.getenv('LINKEDIN_EMAIL')
            password = password or os.getenv('LINKEDIN_PASSWORD')
            
            if not email or not password:
                raise ValueError("LinkedIn credentials not provided")
            
            print("Opening LinkedIn login page...")
            self.driver.get('https://www.linkedin.com/login')
            
            # Wait for page to load
            time.sleep(3)
            
            # Find and fill email field
            print("Entering credentials...")
            email_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "username"))
            )
            email_field.clear()
            email_field.send_keys(email)
            
            # Find and fill password field
            password_field = self.driver.find_element(By.ID, "password")
            password_field.clear()
            password_field.send_keys(password)
            
            # Small delay to appear more human-like
            time.sleep(1)
            
            # Click sign in button
            print("Signing in...")
            sign_in_button = self.driver.find_element(By.XPATH, "//button[@type='submit']")
            sign_in_button.click()
            
            # Wait for login to complete
            print("Waiting for login to complete...")
            
            # Check if we're redirected to feed (successful login)
            try:
                WebDriverWait(self.driver, 20).until(
                    EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '/feed/')]"))
                )
                print("✓ Successfully logged into LinkedIn!")
                self.is_logged_in = True
                return True
                
            except:
                # Check for verification challenge
                if "checkpoint" in self.driver.current_url or "challenge" in self.driver.current_url:
                    print("⚠️  LinkedIn is requesting additional verification")
                    print("Please complete the verification in the browser window...")
                    input("Press Enter after completing verification...")
                    
                    # Check again if logged in
                    if "/feed" in self.driver.current_url:
                        print("✓ Successfully logged in after verification!")
                        self.is_logged_in = True
                        return True
                else:
                    print("✗ Login failed - please check your credentials")
                    return False
                    
        except Exception as e:
            print(f"✗ Error during login: {str(e)}")
            return False
    
    def save_cookies(self, filepath='data/linkedin_cookies.pkl'):
        """Save cookies for future sessions"""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        with open(filepath, 'wb') as file:
            pickle.dump(self.driver.get_cookies(), file)
        print(f"✓ Cookies saved to {filepath}")
    
    def load_cookies(self, filepath='data/linkedin_cookies.pkl'):
        """Load cookies from previous session"""
        if os.path.exists(filepath):
            self.driver.get('https://www.linkedin.com')
            
            with open(filepath, 'rb') as file:
                cookies = pickle.load(file)
                
            for cookie in cookies:
                try:
                    self.driver.add_cookie(cookie)
                except:
                    pass  # Some cookies might be invalid
                    
            self.driver.refresh()
            time.sleep(2)
            
            # Check if logged in
            if "/feed" in self.driver.current_url or self.is_logged_in_check():
                print("✓ Logged in using saved cookies")
                self.is_logged_in = True
                return True
            else:
                print("✗ Saved cookies are invalid or expired")
                return False
        return False
    
    def is_logged_in_check(self):
        """Quick check if user is logged in"""
        try:
            self.driver.find_element(By.XPATH, "//a[contains(@href, '/feed/')]")
            return True
        except:
            return False
    
    def close(self):
        """Close the browser"""
        if self.driver:
            self.driver.quit()
            print("✓ Browser closed")