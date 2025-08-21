"""
Robust Chrome Driver Management System
Fixes version mismatch, options reuse, and implements proper driver lifecycle
"""

import undetected_chromedriver as uc
from selenium.webdriver.chrome.options import Options
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
            # Try different Chrome binary locations
            chrome_paths = [
                "/usr/bin/google-chrome",
                "/usr/bin/google-chrome-stable", 
                "/usr/bin/chromium-browser",
                "/usr/bin/chromium",
                "/opt/google/chrome/chrome",
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
    
    def install_compatible_chromedriver(self, chrome_version: str) -> bool:
        """Install compatible ChromeDriver version"""
        try:
            logger.info(f"Installing ChromeDriver for Chrome {chrome_version}...")
            
            # Force install specific version
            driver = uc.Chrome(version_main=int(chrome_version), 
                              driver_executable_path=None,
                              browser_executable_path=self.chrome_binary_path,
                              use_subprocess=True)
            driver.quit()
            
            logger.info(f"✓ ChromeDriver for version {chrome_version} installed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to install ChromeDriver for version {chrome_version}: {e}")
            return False
    
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
        options.add_argument('--disable-javascript')
        
        # Memory optimization
        options.add_argument('--memory-pressure-off')
        options.add_argument('--max_old_space_size=4096')
        
        # Window size
        options.add_argument('--window-size=1920,1080')
        
        # User agent
        options.add_argument('--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36')
        
        # Disable logging
        options.add_argument('--disable-logging')
        options.add_argument('--log-level=3')
        options.add_argument('--silent')
        
        # Avoid problematic options that cause "excludeSwitches" errors
        # DO NOT ADD: excludeSwitches, useAutomationExtension
        
        return options
    
    def create_driver_safe(self) -> Optional[uc.Chrome]:
        """Safely create Chrome driver with proper error handling"""
        with self.lock:
            try:
                # Detect Chrome version if not already done
                if not self.chrome_version:
                    self.chrome_version = self.detect_chrome_version()
                    if not self.chrome_version:
                        logger.error("Could not detect Chrome version")
                        return None
                
                # Create fresh options to avoid reuse error
                options = self.create_fresh_options()
                
                # Method 1: Try with detected version
                try:
                    logger.info(f"Creating driver with Chrome version {self.chrome_version}")
                    driver = uc.Chrome(
                        options=options,
                        version_main=int(self.chrome_version),
                        browser_executable_path=self.chrome_binary_path,
                        use_subprocess=True,
                        suppress_welcome=True
                    )
                    
                    # Test the driver
                    driver.set_page_load_timeout(30)
                    driver.get("data:text/html,<html><body>Test</body></html>")
                    
                    logger.info(f"✓ Chrome driver created successfully with version {self.chrome_version}")
                    return driver
                    
                except Exception as e:
                    logger.warning(f"Failed with version {self.chrome_version}: {e}")
                    
                    # Method 2: Try with automatic version detection
                    try:
                        logger.info("Trying automatic version detection...")
                        options = self.create_fresh_options()  # Fresh options
                        driver = uc.Chrome(
                            options=options,
                            version_main=None,  # Auto-detect
                            browser_executable_path=self.chrome_binary_path,
                            use_subprocess=True,
                            suppress_welcome=True
                        )
                        
                        driver.set_page_load_timeout(30)
                        driver.get("data:text/html,<html><body>Test</body></html>")
                        
                        logger.info("✓ Chrome driver created with auto-detection")
                        return driver
                        
                    except Exception as e2:
                        logger.warning(f"Auto-detection failed: {e2}")
                        
                        # Method 3: Minimal fallback
                        try:
                            logger.info("Trying minimal fallback configuration...")
                            options = Options()
                            options.add_argument('--headless=new')
                            options.add_argument('--no-sandbox')
                            options.add_argument('--disable-dev-shm-usage')
                            
                            driver = uc.Chrome(
                                options=options,
                                use_subprocess=True,
                                suppress_welcome=True
                            )
                            
                            driver.set_page_load_timeout(30)
                            driver.get("data:text/html,<html><body>Test</body></html>")
                            
                            logger.info("✓ Chrome driver created with minimal fallback")
                            return driver
                            
                        except Exception as e3:
                            logger.error(f"All Chrome driver creation methods failed:")
                            logger.error(f"  Method 1 (version {self.chrome_version}): {e}")
                            logger.error(f"  Method 2 (auto-detect): {e2}")
                            logger.error(f"  Method 3 (minimal): {e3}")
                            return None
            
            except Exception as e:
                logger.error(f"Unexpected error in create_driver_safe: {e}")
                return None
    
    def get_driver(self) -> Optional[uc.Chrome]:
        """Get a driver from pool or create new one"""
        with self.lock:
            # Try to reuse existing driver
            while self.driver_pool:
                driver = self.driver_pool.pop()
                try:
                    # Test if driver is still alive
                    driver.current_url
                    return driver
                except:
                    # Driver is dead, try to quit it
                    try:
                        driver.quit()
                    except:
                        pass
            
            # Create new driver
            return self.create_driver_safe()
    
    def return_driver(self, driver: uc.Chrome):
        """Return driver to pool"""
        if driver and len(self.driver_pool) < self.max_drivers:
            try:
                # Test if driver is still alive
                driver.current_url
                with self.lock:
                    self.driver_pool.append(driver)
                    return
            except:
                pass
        
        # Driver is dead or pool is full, quit it
        try:
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

def get_chrome_driver() -> Optional[uc.Chrome]:
    """Get Chrome driver instance"""
    return chrome_manager.get_driver()

def return_chrome_driver(driver: uc.Chrome):
    """Return Chrome driver to pool"""
    chrome_manager.return_driver(driver)

def cleanup_chrome_drivers():
    """Cleanup all Chrome drivers"""
    chrome_manager.cleanup_all()

# Auto-cleanup on exit
import atexit
atexit.register(cleanup_chrome_drivers)