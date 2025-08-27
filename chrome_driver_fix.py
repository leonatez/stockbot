"""
Robust Chrome Driver Management System
Uses regular Selenium with anti-detection measures (works better than undetected-chromedriver)
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import subprocess
import re
import os
import threading
import time
from typing import Optional, Dict, Any
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ChromeDriverManager:
    """
    Robust Chrome driver management with automatic version detection and fixing
    """
    
    def __init__(self):
        self.lock = threading.Lock()
        self.driver_pool = []
        self.max_drivers = 3
        self.chrome_version = None
        self.chrome_binary_path = None
        self.driver_executable_path = None
        
    def detect_chrome_version(self) -> Optional[str]:
        """Detect installed Chrome version"""
        try:
            # Try different Chrome binary locations (prioritize Chromium which works)
            chrome_paths = [
                "/usr/bin/chromium-browser",  # This one works from our test
                "/usr/bin/chromium",
                "/usr/bin/google-chrome",
                "/usr/bin/google-chrome-stable", 
                "/opt/google/chrome/chrome",
                "/opt/google/chrome/google-chrome",
                "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
            ]
            
            for chrome_path in chrome_paths:
                if os.path.exists(chrome_path):
                    try:
                        result = subprocess.run([chrome_path, "--version"], 
                                              capture_output=True, text=True, timeout=10)
                        if result.returncode == 0:
                            version_output = result.stdout.strip()
                            # Extract version number (e.g., "Google Chrome 138.0.7204.183")
                            version_match = re.search(r'(\d+)\.(\d+)\.(\d+)\.(\d+)', version_output)
                            if version_match:
                                major_version = version_match.group(1)
                                self.chrome_binary_path = chrome_path
                                logger.info(f"✓ Found Chrome {version_output} at {chrome_path}")
                                return major_version
                    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError) as e:
                        logger.debug(f"Failed to get version from {chrome_path}: {e}")
                        continue
            
            logger.warning("Could not detect Chrome version automatically")
            return None
            
        except Exception as e:
            logger.error(f"Error detecting Chrome version: {e}")
            return None
    
    def get_chromedriver_service(self) -> Optional[Service]:
        """Get ChromeDriver service (let webdriver-manager handle the installation)"""
        try:
            # Let Selenium handle ChromeDriver automatically
            return None  # Use default service
        except Exception as e:
            logger.error(f"Failed to create ChromeDriver service: {e}")
            return None
    
    def create_fresh_options(self) -> Options:
        """Create fresh Chrome options object to avoid reuse errors"""
        options = Options()
        
        # Essential headless options
        options.add_argument('--headless=new')  # Use new headless mode
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-web-security')
        options.add_argument('--allow-running-insecure-content')
        options.add_argument('--disable-background-timer-throttling')
        options.add_argument('--disable-backgrounding-occluded-windows')
        options.add_argument('--disable-renderer-backgrounding')
        options.add_argument('--disable-features=TranslateUI')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-plugins')
        options.add_argument('--disable-images')
        
        # Anti-detection measures (from our successful test)
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Memory optimization
        options.add_argument('--memory-pressure-off')
        options.add_argument('--max_old_space_size=4096')
        
        # Window size
        options.add_argument('--window-size=1920,1080')
        
        # User agent (match what worked in our test)
        options.add_argument('--user-agent=Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36')
        
        # Disable logging
        options.add_argument('--disable-logging')
        options.add_argument('--log-level=3')
        options.add_argument('--silent')
        
        return options
    
    def create_driver_safe(self) -> Optional[webdriver.Chrome]:
        """Safely create Chrome driver with proper error handling using regular Selenium"""
        with self.lock:
            try:
                # Detect Chrome binary if not already done
                if not self.chrome_binary_path:
                    self.chrome_version = self.detect_chrome_version()
                    if not self.chrome_binary_path:
                        logger.error("Could not detect Chrome binary")
                        return None
                
                # Method 1: Try with Chromium browser (we know this works)
                try:
                    logger.info(f"Creating driver with Chromium at {self.chrome_binary_path}")
                    options = self.create_fresh_options()
                    options.binary_location = self.chrome_binary_path
                    
                    driver = webdriver.Chrome(options=options)
                    
                    # Test the driver and apply anti-detection measures
                    driver.set_page_load_timeout(30)
                    driver.get("data:text/html,<html><body>Test</body></html>")
                    
                    # Apply anti-detection script
                    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                    
                    logger.info(f"✓ Chrome driver created successfully with {self.chrome_binary_path}")
                    return driver
                    
                except Exception as e:
                    logger.warning(f"Failed with {self.chrome_binary_path}: {e}")
                    
                    # Method 2: Try with minimal options
                    try:
                        logger.info("Trying minimal configuration...")
                        options = Options()
                        options.add_argument('--headless=new')
                        options.add_argument('--no-sandbox')
                        options.add_argument('--disable-dev-shm-usage')
                        options.add_argument('--disable-blink-features=AutomationControlled')
                        options.add_experimental_option("excludeSwitches", ["enable-automation"])
                        options.add_experimental_option('useAutomationExtension', False)
                        options.binary_location = self.chrome_binary_path
                        
                        driver = webdriver.Chrome(options=options)
                        
                        driver.set_page_load_timeout(30)
                        driver.get("data:text/html,<html><body>Test</body></html>")
                        
                        # Apply anti-detection measures
                        try:
                            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                        except:
                            pass
                        
                        logger.info("✓ Chrome driver created with minimal configuration")
                        return driver
                        
                    except Exception as e2:
                        logger.error(f"All Chrome driver creation methods failed:")
                        logger.error(f"  Method 1 (full options): {e}")
                        logger.error(f"  Method 2 (minimal): {e2}")
                        return None
            
            except Exception as e:
                logger.error(f"Unexpected error in create_driver_safe: {e}")
                return None
    
    def get_driver(self) -> Optional[webdriver.Chrome]:
        """Get a driver - simplified without pool to avoid threading issues"""
        # Skip pool management for now to avoid hangs
        # Always create fresh driver
        return self.create_driver_safe()
    
    def return_driver(self, driver: webdriver.Chrome):
        """Return driver - simplified to just quit it"""
        # Skip pool management, just quit the driver to avoid threading issues
        try:
            if driver:
                driver.quit()
        except:
            pass
    
    def cleanup_all(self):
        """Cleanup all drivers"""
        with self.lock:
            while self.driver_pool:
                driver = self.driver_pool.pop()
                try:
                    driver.quit()
                except:
                    pass

# Global instance
chrome_manager = ChromeDriverManager()

def get_chrome_driver() -> Optional[webdriver.Chrome]:
    """Get Chrome driver instance"""
    return chrome_manager.get_driver()

def return_chrome_driver(driver: webdriver.Chrome):
    """Return Chrome driver to pool"""
    chrome_manager.return_driver(driver)

def cleanup_chrome_drivers():
    """Cleanup all Chrome drivers"""
    chrome_manager.cleanup_all()

# Auto-cleanup on exit
import atexit
atexit.register(cleanup_chrome_drivers)