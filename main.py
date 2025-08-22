# Testing automatic deployment trigger
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ValidationError
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from lxml import html
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from collections import defaultdict
from urllib.parse import urljoin, urlparse
from pathlib import Path
import undetected_chromedriver as uc
import re
import time
import random
import threading
import queue
import atexit
import os
import json
import google.generativeai as genai
from dotenv import load_dotenv
from database import db_service
from daily_vn30_update import daily_vn30_update
from stock_price_updater import update_mentioned_stocks_prices
from company_info_updater import update_company_information
from debug_logger import get_debug_logger, reset_debug_logger, initialize_debug_session
from chrome_driver_fix import get_chrome_driver as get_robust_chrome_driver, return_chrome_driver as return_robust_chrome_driver
import tempfile
from urllib.parse import urljoin, urlparse
import requests
from markitdown import MarkItDown
import traceback


load_dotenv()
app = FastAPI(title="AI Stock Application", version="1.0.0")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.5-pro")


# Global driver pool
driver_pool = queue.Queue()
driver_lock = threading.Lock()
MAX_DRIVERS = 3

# Chrome version configuration - change this single value if version mismatch occurs
CHROME_VERSION = 139

def create_stealth_driver():
    """Create a new undetected Chrome driver with stealth settings optimized for servers"""
    try:
        options = uc.ChromeOptions()
        
        # Essential headless and server-friendly options
        options.add_argument('--headless')  # Run in headless mode
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-plugins')
        options.add_argument('--disable-images')
        options.add_argument('--disable-logging')
        options.add_argument('--disable-log-level')
        options.add_argument('--log-level=3')
        options.add_argument('--silent')
        
        # Memory and performance optimization for weak servers
        options.add_argument('--max_old_space_size=4096')
        options.add_argument('--disable-background-timer-throttling')
        options.add_argument('--disable-backgrounding-occluded-windows')
        options.add_argument('--disable-renderer-backgrounding')
        options.add_argument('--disable-features=TranslateUI')
        options.add_argument('--disable-ipc-flooding-protection')
        
        # Basic stealth options (compatible with most Chrome versions)
        options.add_argument('--no-first-run')
        options.add_argument('--disable-default-apps')
        options.add_argument('--disable-popup-blocking')
        options.add_argument('--disable-translate')
        options.add_argument('--disable-sync')
        options.add_argument('--disable-crash-reporter')
        options.add_argument('--disable-web-security')
        options.add_argument('--allow-running-insecure-content')
        options.add_argument('--disable-features=VizDisplayCompositor')
        
        # Window size (still needed even in headless)
        window_sizes = ['1920,1080', '1366,768', '1440,900', '1536,864', '1280,720']
        selected_size = random.choice(window_sizes)
        options.add_argument(f'--window-size={selected_size}')
        
        # Random user agent
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
        ]
        selected_ua = random.choice(user_agents)
        options.add_argument(f'--user-agent={selected_ua}')
        
        # Prefs for stealth (compatible settings)
        prefs = {
            "profile.default_content_setting_values": {
                "notifications": 2,
                "media_stream": 2,
                "geolocation": 2,
                "microphone": 2,
                "camera": 2
            },
            "profile.default_content_settings.popups": 0,
            "profile.managed_default_content_settings.images": 2,
            "profile.password_manager_enabled": False,
            "credentials_enable_service": False,
        }
        options.add_experimental_option("prefs", prefs)
        
        # Only add advanced stealth options if they're supported
        try:
            # Test if these options are supported
            options.add_experimental_option('excludeSwitches', ['load-extension', 'enable-automation'])
            options.add_experimental_option('useAutomationExtension', False)
            print("Advanced stealth options added successfully")
        except Exception as e:
            print(f"Advanced stealth options not supported: {e}")
            # Remove the problematic options and continue
            pass
        
        print("Creating undetected Chrome driver (headless mode)...")
        
        # Try to create driver with correct Chrome version
        try:
            driver = uc.Chrome(options=options, version_main=CHROME_VERSION)
            print(f"Chrome driver created successfully with version {CHROME_VERSION}!")
        except Exception as e:
            print(f"Version {CHROME_VERSION} failed: {e}")
            # Try with automatic version detection as fallback
            driver = uc.Chrome(options=options, version_main=None, driver_executable_path=None, use_subprocess=True)
            print("Chrome driver created with subprocess method!")
        
        # Additional stealth measures (with better error handling)
        try:
            # Remove webdriver property
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            print("Removed webdriver property")
        except Exception as e:
            print(f"Could not remove webdriver property: {e}")
        
        try:
            # Override user agent via CDP if supported
            driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                "userAgent": selected_ua,
                "acceptLanguage": "en-US,en;q=0.9",
                "platform": "Linux x86_64"  # More appropriate for server
            })
            print("User agent overridden via CDP")
        except Exception as e:
            print(f"Could not override user agent via CDP: {e}")
        
        try:
            # Additional stealth scripts
            driver.execute_script("Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]})")
            driver.execute_script("Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']})")
            print("Additional stealth properties set")
        except Exception as e:
            print(f"Could not set additional stealth properties: {e}")
        
        print("Chrome driver setup completed successfully!")
        return driver
        
    except Exception as e:
        print(f"Failed to create Chrome driver with advanced options: {e}")
        print("Trying with minimal headless options...")
        
        # Fallback: try with absolutely minimal options for weak servers
        try:
            options = uc.ChromeOptions()
            # Absolutely essential options only
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--disable-logging')
            options.add_argument('--log-level=3')
            options.add_argument('--silent')
            options.add_argument('--window-size=1920,1080')
            
            # Simple prefs
            prefs = {"profile.managed_default_content_settings.images": 2}
            options.add_experimental_option("prefs", prefs)
            
            driver = uc.Chrome(options=options, version_main=CHROME_VERSION)
            print(f"Chrome driver created with minimal headless options and version {CHROME_VERSION}!")
            return driver
            
        except Exception as e2:
            print(f"Even minimal Chrome driver failed: {e2}")
            print("This might be due to:")
            print("1. Chrome/ChromeDriver version mismatch")
            print("2. Missing Chrome installation")
            print("3. Insufficient server permissions")
            print("4. Missing dependencies (try: apt-get install -y chromium-browser)")
            return None

def get_driver():
    """Get a driver using robust Chrome driver manager"""
    return get_robust_chrome_driver()

def return_driver(driver):
    """Return a driver using robust Chrome driver manager"""
    return_robust_chrome_driver(driver)

def cleanup_drivers():
    """Cleanup all drivers"""
    with driver_lock:
        while not driver_pool.empty():
            try:
                driver = driver_pool.get_nowait()
                driver.quit()
            except:
                pass

# Register cleanup function
atexit.register(cleanup_drivers)

@app.get("/health")
def health_check():
    """Health check endpoint for Docker containers"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/test")
def test_deployment():
    """Test endpoint to verify auto-deployment is working"""
    deployment_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
    return {
        "message": "Auto-deployment is working! 🚀",
        "deployed_at": deployment_time,
        "git_push_time": "2025-08-18 18:30:00 UTC",
        "status": "success"
    }

# Add validation error handler
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    print(f"\n=== Validation Error ===")
    print(f"Request body: {await request.body()}")
    print(f"Validation errors: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body": str(await request.body())}
    )

class CrawlRequest(BaseModel):
    url: str
    sourceName: str
    sourceType: str
    xpath: str
    pagination: Optional[str] = None
    contentXpath: str
    contentDateXpath: str
    contentType: Optional[str] = "text"  # "text" or "pdf"

class MultipleCrawlRequest(BaseModel):
    sources: List[CrawlRequest]
    days: Optional[int] = 3  # Default to 3 days if not specified
    debug: Optional[bool] = False  # Debug mode: crawl only 1 valid post

class CompanyUpdateRequest(BaseModel):
    debug: Optional[bool] = False  # Debug mode: process only VIC symbol

class StockAnalysis(BaseModel):
    stock_symbol: str
    mentioned_times: int
    sentiment: str
    summary: str

class CrawlResponse(BaseModel):
    response: str
    posts_found: int
    posts_within_3_days: int
    stocks_analysis: List[StockAnalysis] = [] #new added

def analyze_with_gemini(all_posts_content: str) -> List[dict]:
    """Analyze collected posts using Gemini to extract stock information"""
    if not model or not all_posts_content.strip():
        print("Gemini model not available or no content to analyze")
        return []
    
    try:
        prompt = f"""
        You are stock investment consultant in Vietnam. 
        Analyze the following financial news content about Vietnamese companies 
        and extract information about stocks mentioned. 
        Keep in mind that all those stocks are Vietnamese stocks just to 
        distinguish with foreign stocks having the same symbol.
        For each stock symbol found, provide the analysis in this exact JSON format:

        {{
            "stock_symbol": "SYMBOL",
            "mentioned_times": number,
            "sentiment": "positive/negative/neutral",
            "summary": "Brief summary of how this stock was mentioned and what news affects it"
        }}

        Rules:
        1. Only include actual stock symbols (like HPG, ACB, LDG, etc.)
        2. Count how many posts each symbol is mentioned across all posts
        3. Determine if the overall sentiment is positive, negative, or neutral
        4. Provide a concise summary of the key points about each stock
        5. Return ONLY a valid JSON array, no other text
        6. If no stocks are found, return an empty array []
        7. You always consult in Vietnamese

        Content to analyze:
        {all_posts_content}
        """
        
        print("Sending content to Gemini for analysis...")
        response = model.generate_content(prompt)
        
        if response and response.text:
            print("Received response from Gemini")
            
            # Clean the response text
            response_text = response.text.replace("```json", "").replace("```", "").strip()
            
            # Try to extract JSON from the response
            try:
                # Look for JSON array in the response
                start_idx = response_text.find('[')
                end_idx = response_text.rfind(']') + 1
                
                if start_idx != -1 and end_idx != -1:
                    json_str = response_text[start_idx:end_idx]
                    stocks_data = json.loads(json_str)
                    
                    print(f"Successfully parsed {len(stocks_data)} stock analyses from Gemini")
                    return stocks_data
                else:
                    print("No JSON array found in Gemini response")
                    return []
                    
            except json.JSONDecodeError as e:
                print(f"Failed to parse JSON from Gemini response: {e}")
                print(f"Raw response: {response_text[:500]}...")
                return []
        else:
            print("No valid response from Gemini")
            return []
            
    except Exception as e:
        print(f"Error calling Gemini API: {e}")
        return []

def parse_date(date_str: str) -> Optional[datetime]:
    """Parse date string in DD/MM/YYYY format"""
    try:
        date_str = date_str.strip()
        
        # Try to extract date in DD/MM/YYYY format
        date_match = re.search(r'(\d{1,2})/(\d{1,2})/(\d{4})', date_str)
        if date_match:
            day, month, year = date_match.groups()
            return datetime(int(year), int(month), int(day))
        
        # Try other common formats
        formats = [
            '%d/%m/%Y',
            '%d-%m-%Y',
            '%Y-%m-%d',
            '%d.%m.%Y',
            '%B %d, %Y',
            '%d %B %Y'
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
                
        return None
    except Exception as e:
        print(f"Error parsing date '{date_str}': {e}")
        return None

def is_within_3_days(post_date: datetime) -> bool:
    """Check if post date is within 3 days from today"""
    today = datetime.now().date()
    three_days_ago = today - timedelta(days=3)
    return three_days_ago <= post_date.date() <= today

def extract_pagination_rule(pagination_input: Optional[str]) -> str:
    """Extract pagination rule from input string"""
    if not pagination_input:
        return '/page/'
    
    if '<page>' in pagination_input:
        return pagination_input.replace('<page>', '{}')
    elif pagination_input.startswith('/'):
        return pagination_input if pagination_input.endswith('/') else pagination_input + '/'
    else:
        return '/page/'

def human_like_delay():
    """Add human-like random delays"""
    delay = random.uniform(2, 8)  # Random delay between 2-8 seconds
    time.sleep(delay)

def get_page_content_with_selenium(url: str, retries: int = 3) -> Optional[html.HtmlElement]:
    """Get page content using Selenium with stealth driver, fallback to requests"""
    driver = None
    
    for attempt in range(retries):
        try:
            if attempt > 0:
                wait_time = random.uniform(15, 30)
                print(f"Waiting {wait_time:.1f} seconds before retry {attempt + 1}...")
                time.sleep(wait_time)
            
            print(f"Attempting to fetch with Selenium: {url} (attempt {attempt + 1}/{retries})")
            
            driver = get_driver()
            if not driver:
                print("Failed to get Chrome driver, trying fallback...")
                return get_page_content_fallback(url)
                
            # Set page load timeout
            driver.set_page_load_timeout(30)
            
            # Navigate to page
            driver.get(url)
            
            # Human-like behavior: scroll a bit
            try:
                driver.execute_script("window.scrollTo(0, Math.floor(Math.random() * 500));")
            except:
                pass
            
            # Wait for page to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Add random delay to mimic reading
            time.sleep(random.uniform(1, 3))
            
            # Get page source and convert to lxml tree
            page_source = driver.page_source
            tree = html.fromstring(page_source)
            
            return_driver(driver)
            return tree
            
        except TimeoutException:
            print(f"Timeout loading {url}")
        except WebDriverException as e:
            print(f"WebDriver error for {url}: {e}")
            if "chrome not reachable" in str(e).lower():
                # Chrome crashed, don't return driver to pool
                driver = None
        except Exception as e:
            print(f"Unexpected error for {url}: {e}")
        finally:
            if driver and attempt == retries - 1:
                try:
                    driver.quit()
                except:
                    pass
    
    print(f"Selenium failed for {url}, trying fallback method...")
    return get_page_content_fallback(url)

def get_page_content_fallback(url: str) -> Optional[html.HtmlElement]:
    """Fallback method using requests with stealth headers"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0',
        }
        
        import requests
        session = requests.Session()
        session.headers.update(headers)
        
        print(f"Fallback: fetching {url} with requests")
        response = session.get(url, timeout=30)
        
        if response.status_code == 200:
            return html.fromstring(response.content)
        else:
            print(f"Fallback failed with status {response.status_code}")
            return None
            
    except Exception as e:
        print(f"Fallback method also failed: {e}")
        return None

def clean_text_content(text: str) -> str:
    """Clean and normalize text content for LLM usage"""
    if not text:
        return ""
    
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    
    # Remove CSS and JavaScript
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
    text = re.sub(r'<script.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'javascript:', '', text, flags=re.IGNORECASE)
    
    # Remove CSS selectors and properties
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        line = line.strip()
        if (line.startswith('.') or 
            line.startswith('#') or 
            line.startswith('@') or
            ':' in line and '{' in line or '}' in line or
            line.startswith('/*') or
            line.endswith('*/') or
            'elementor' in line.lower() or
            'jquery' in line.lower() or
            'function(' in line or
            'var ' in line or
            'const ' in line or
            'let ' in line):
            continue
        
        if len(line) > 3:
            cleaned_lines.append(line)
    
    text = '\n'.join(cleaned_lines)
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[^\w\s\.\,\!\?\;\:\-\(\)\[\]\{\}\"\'\/\%\$\@\&\#\+\=\<\>\|\\\~\`]', '', text)
    text = re.sub(r'\.{3,}', '...', text)
    text = re.sub(r'-{3,}', '---', text)
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    
    return text

def extract_text_content(tree: html.HtmlElement, xpath: str) -> str:
    """Extract and clean text content using xpath"""
    try:
        elements = tree.xpath(xpath)
        if elements:
            if isinstance(elements[0], html.HtmlElement):
                raw_text = elements[0].text_content()
            else:
                raw_text = str(elements[0])
            
            cleaned_text = clean_text_content(raw_text)
            return cleaned_text
        return ""
    except Exception as e:
        print(f"Error extracting content with xpath '{xpath}': {e}")
        return ""

def extract_pdf_link(tree: html.HtmlElement, xpath: str) -> str:
    """Extract PDF download link using xpath"""
    try:
        elements = tree.xpath(xpath)
        if elements:
            if isinstance(elements[0], html.HtmlElement):
                # Check if it's a link element with href
                href = elements[0].get('href')
                if href:
                    return href
                # Otherwise get text content (might be a direct URL)
                return elements[0].text_content().strip()
            else:
                return str(elements[0]).strip()
        return ""
    except Exception as e:
        print(f"Error extracting PDF link with xpath '{xpath}': {e}")
        return ""

def download_pdf_from_url(pdf_url: str, base_url: str = None) -> Optional[str]:
    """Download PDF from URL and return local path"""
    try:
        # Handle relative URLs
        if base_url and not pdf_url.startswith(('http://', 'https://')):
            pdf_url = urljoin(base_url, pdf_url)
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        print(f"Downloading PDF from: {pdf_url}")
        response = requests.get(pdf_url, headers=headers, stream=True, timeout=30)
        response.raise_for_status()
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            for chunk in response.iter_content(chunk_size=8192):
                tmp_file.write(chunk)
            temp_path = tmp_file.name
        
        print(f"PDF downloaded to: {temp_path}")
        return temp_path
        
    except Exception as e:
        print(f"Error downloading PDF: {e}")
        return None

def convert_pdf_to_markdown(pdf_path: str) -> Optional[str]:
    """Convert PDF to markdown using MarkItDown"""
    try:
        print(f"Converting PDF to markdown: {pdf_path}")
        
        # Initialize MarkItDown
        md = MarkItDown()
        
        # Convert PDF to markdown
        result = md.convert(pdf_path)
        
        if not result or not result.text_content:
            print("MarkItDown conversion failed or returned empty content")
            return None
        
        markdown_content = result.text_content
        print(f"PDF converted to markdown successfully ({len(markdown_content)} characters)")
        
        # Clean up temporary file
        try:
            os.unlink(pdf_path)
        except:
            pass
        
        return markdown_content
        
    except Exception as e:
        print(f"Error converting PDF to markdown: {e}")
        # Clean up temporary file on error
        try:
            os.unlink(pdf_path)
        except:
            pass
        return None

def process_pdf_content(tree: html.HtmlElement, xpath: str, base_url: str = None) -> str:
    """Extract PDF link, download and convert to markdown"""
    try:
        # Extract PDF URL
        pdf_url = extract_pdf_link(tree, xpath)
        if not pdf_url:
            print("No PDF URL found")
            return ""
        
        # Download PDF
        pdf_path = download_pdf_from_url(pdf_url, base_url)
        if not pdf_path:
            print("Failed to download PDF")
            return ""
        
        # Convert to markdown
        markdown_content = convert_pdf_to_markdown(pdf_path)
        if not markdown_content:
            print("Failed to convert PDF to markdown")
            return ""
        
        return markdown_content
        
    except Exception as e:
        print(f"Error processing PDF content: {e}")
        return ""

async def crawl_posts(request: CrawlRequest, days: int = 3, debug: bool = False, debug_logger=None, op_id=None) -> tuple[List[dict], int]:
    """Crawl posts and return those within specified days using Selenium"""
    collected_posts = []
    total_posts_found = 0
    page = 1
    
    # Use date-only comparison to include entire days
    target_date_ago = (datetime.now().date() - timedelta(days=days))
    if debug:
        print(f"🐛 DEBUG MODE: Crawling only 1 valid post from the last {days} days (since {target_date_ago.strftime('%d/%m/%Y')})")
    else:
        print(f"Crawling posts from the last {days} days (since {target_date_ago.strftime('%d/%m/%Y')})")
    
    while True:
        # Construct URL for current page
        if page == 1:
            current_url = request.url
        else:
            pagination_rule = extract_pagination_rule(request.pagination)
            
            if '{}' in pagination_rule:
                page_part = pagination_rule.format(page)
            else:
                page_part = pagination_rule + str(page)
            
            current_url = request.url.rstrip('/') + page_part
        
        print(f"\nCrawling page {page}: {current_url}")
        
        # Get page content with Selenium
        tree = get_page_content_with_selenium(current_url)
        if not tree:
            print(f"Failed to get content from {current_url}")
            break
        
        # Add delay between pages
        human_like_delay()
        
        # Extract post elements
        try:
            post_elements = tree.xpath(request.xpath)
            print(f"Found {len(post_elements)} post elements on page {page}")
            
            # Log page crawl if debug logger available
            if debug_logger and op_id:
                debug_logger.log_page_crawl(op_id, page, current_url, len(post_elements))
                
        except Exception as e:
            print(f"Error with xpath '{request.xpath}': {e}")
            break
        
        if not post_elements:
            print(f"No posts found on page {page}")
            break
        
        posts_within_3_days_on_page = 0
        oldest_post_date = None
        
        for post_element in post_elements:
            total_posts_found += 1
            
            try:
                # Extract post URL
                post_url = None
                if hasattr(post_element, 'get'):
                    post_url = post_element.get('href')
                if not post_url:
                    links = post_element.xpath('.//a/@href')
                    if links:
                        post_url = links[0]
                
                if not post_url:
                    print(f"No URL found for post element")
                    continue
                
                post_url = urljoin(current_url, post_url)
                
                # Extract post date
                try:
                    date_elements = post_element.xpath(request.contentDateXpath)
                    if date_elements:
                        if isinstance(date_elements[0], html.HtmlElement):
                            date_text = date_elements[0].text_content().strip()
                        else:
                            date_text = str(date_elements[0]).strip()
                    else:
                        date_text = None
                except Exception as e:
                    print(f"Error extracting date with xpath '{request.contentDateXpath}': {e}")
                    date_text = None
                
                if not date_text:
                    print(f"No date found for post: {post_url}")
                    continue
                
                post_date = parse_date(date_text)
                if not post_date:
                    print(f"Could not parse date '{date_text}' for post: {post_url}")
                    continue
                
                print(f"Post date: {post_date.strftime('%d/%m/%Y')} for URL: {post_url}")
                
                if oldest_post_date is None or post_date < oldest_post_date:
                    oldest_post_date = post_date
                
                # Check if post is within specified days (date-only comparison)
                if post_date.date() >= target_date_ago:
                    posts_within_3_days_on_page += 1
                    
                    print(f"✓ Post within {days} days! Checking if exists in database: {post_url}")
                    
                    # Check if post already exists in database
                    post_exists = await db_service.check_post_exists(post_url)
                    if post_exists:
                        # Get existing post data from database
                        existing_post_data = await db_service.get_existing_post_data(post_url)
                        if existing_post_data:
                            print(f"✓ Using existing post data from database")
                            collected_posts.append({
                                'url': post_url,
                                'date': post_date.strftime('%d/%m/%Y'),
                                'content': existing_post_data['content'],
                                'existing_data': existing_post_data  # Mark as existing for later processing
                            })
                            
                            # In debug mode, exit after collecting the first valid post (even if from database)
                            if debug:
                                print(f"🐛 DEBUG MODE: Collected 1 post from database, stopping crawl")
                                return collected_posts, total_posts_found
                        continue
                    
                    print(f"✓ Post not in database, fetching fresh content from: {post_url}")
                    
                    # Longer delay before fetching individual posts
                    human_like_delay()
                    
                    post_tree = get_page_content_with_selenium(post_url)
                    if post_tree:
                        # Check content type and extract accordingly
                        if hasattr(request, 'contentType') and request.contentType == 'pdf':
                            content = process_pdf_content(post_tree, request.contentXpath, request.url)
                        else:
                            content = extract_text_content(post_tree, request.contentXpath)
                        
                        if content and len(content) > 100:
                            post_data = {
                                'url': post_url,
                                'date': post_date.strftime('%d/%m/%Y'),
                                'content': content
                            }
                            collected_posts.append(post_data)
                            print(f"✓ Successfully collected new post from {post_date.strftime('%d/%m/%Y')}")
                            print(f"Content preview: {content[:200]}...")
                            
                            # In debug mode, exit after collecting the first valid post
                            if debug:
                                print(f"🐛 DEBUG MODE: Collected 1 post, stopping crawl")
                                return collected_posts, total_posts_found
                        else:
                            print(f"Content too short or empty for post: {post_url}")
                    else:
                        print(f"Failed to fetch post content from: {post_url}")
                else:
                    print(f"✗ Post from {post_date.strftime('%d/%m/%Y')} is older than {days} days, skipping")
                
                # Delay between processing posts
                time.sleep(random.uniform(1, 3))
                
            except Exception as e:
                print(f"Error processing post element: {e}")
                continue
        
        print(f"Page {page}: {posts_within_3_days_on_page} posts within {days} days")
        
        # Check if we should continue to next page (date-only comparison)
        if oldest_post_date and oldest_post_date.date() < target_date_ago:
            print(f"Oldest post on page {page} is from {oldest_post_date.strftime('%d/%m/%Y')}, older than {days} days. Stopping.")
            break
        
        if posts_within_3_days_on_page == 0 and page < 10:
            print(f"No posts within {days} days on page {page}, trying next page...")
            page += 1
            continue
        
        if posts_within_3_days_on_page > 0:
            print(f"Found {posts_within_3_days_on_page} posts within {days} days on page {page}")
            print("Waiting before going to next page...")
            human_like_delay()
            page += 1
            continue
        
        break
    
    return collected_posts, total_posts_found
    
@app.post("/crawl")
async def crawl_endpoint(request: CrawlRequest):
    """Crawl posts from the specified URL and return stock-level analysis"""
    # Initialize debug logging session
    debug_logger = initialize_debug_session()
    
    try:
        print(f"\n=== Received Request ===")
        print(f"Raw request: {request}")
        print(f"Request dict: {request.dict()}")
        
        # Log crawl start
        op_id = debug_logger.log_crawl_start(
            request_data=request.dict(),
            source_name=request.sourceName,
            url=request.url
        )
        
        # Perform daily VN30 update at the start of analysis
        print(f"\n=== Daily VN30 Update ===")
        vn30_success = daily_vn30_update()
        if vn30_success:
            print("✓ VN30 update completed successfully")
        else:
            print("⚠️ VN30 update had issues, continuing with analysis...")
        
        print(f"\n=== Starting stealth crawl for {request.sourceName} ===")
        print(f"URL: {request.url}")
        print(f"Source Type: {request.sourceType}")
        print(f"XPath: {request.xpath}")
        print(f"Pagination: {request.pagination}")
        print(f"Content XPath: {request.contentXpath}")
        print(f"Date XPath: {request.contentDateXpath}")
        
        # Crawl posts (default to 3 days for single crawl)
        collected_posts, total_posts_found = await crawl_posts(request, days=3, debug_logger=debug_logger, op_id=op_id)
        
        print(f"\n=== Crawl Summary ===")
        print(f"Total posts found: {total_posts_found}")
        print(f"Posts within 3 days: {len(collected_posts)}")
        print(f"DEBUGGING: collected posts: {collected_posts}")
        
        # Process each post individually with Gemini - STOCK-LEVEL APPROACH
        processed_posts = []
        stock_mentions = defaultdict(lambda: {
            'post_details': [],  # List of posts mentioning this stock
            'sentiments': [],    # List of sentiments for this stock
            'summaries': []      # List of summaries about this stock
        })
        
        # Get source from database (or create if needed)
        source_in_db = await db_service.get_source_by_url(request.url)
        if not source_in_db:
            print(f"Source not found in database, creating new source: {request.sourceName}")
            source_id = await db_service.save_source(request.dict())
        else:
            source_id = source_in_db['id']
            print(f"Using existing source from database: {source_in_db['name']}")
        
        for i, post in enumerate(collected_posts, 1):
            print(f"\n=== Processing Post {i}/{len(collected_posts)} ===")
            print(f"URL: {post['url']}")
            print(f"Date: {post['date']}")
            print(f"Content preview: {post['content'][:200]}...")
            
            # Log post extraction
            debug_logger.log_post_extraction(
                op_id=op_id,
                post_url=post['url'],
                post_date=post['date'],
                content_length=len(post['content']),
                content_preview=post['content'][:500],
                source_type=request.sourceType
            )
            
            try:
                # Check if this post already has existing analysis data
                if 'existing_data' in post:
                    print(f"✓ Using existing post analysis from database")
                    post_object = post['existing_data']
                    mentioned_stocks_data = [
                        {
                            "stock_symbol": stock["stock_symbol"],
                            "sentiment": stock["sentiment"],
                            "summary": stock["stock_summary"]
                        }
                        for stock in post_object["mentionedStocks"]
                    ]
                else:
                    print(f"✓ Running fresh AI analysis for new post")
                    
                    # Log Gemini call
                    call_type = "pdf_analysis" if hasattr(request, 'contentType') and request.contentType == 'pdf' else "individual_post_analysis"
                    gemini_call_id = debug_logger.log_gemini_prompt(
                        call_type=call_type,
                        prompt=post['content'],  # This will be updated in the actual analysis functions
                        post_urls=[post['url']],
                        context_info={"source_type": request.sourceType, "post_date": post['date']}
                    )
                    
                    # Analyze individual post with Gemini - use PDF analysis for PDF content
                    try:
                        if hasattr(request, 'contentType') and request.contentType == 'pdf':
                            gemini_result = analyze_pdf_report_with_gemini(post['content'])
                        else:
                            gemini_result = analyze_individual_post_with_gemini(post['content'])
                        
                        # Log Gemini response
                        debug_logger.log_gemini_response(
                            call_id=gemini_call_id,
                            response=gemini_result
                        )
                    except Exception as gemini_error:
                        # Log Gemini error
                        debug_logger.log_gemini_error(
                            call_id=gemini_call_id,
                            error=gemini_error,
                            error_context={"post_url": post['url'], "content_length": len(post['content'])}
                        )
                        raise  # Re-raise to be caught by outer exception handler
                    
                    # Handle different response formats from Gemini
                    mentioned_stocks_data = []
                    if isinstance(gemini_result, dict) and 'mentioned_stocks' in gemini_result:
                        mentioned_stocks_data = gemini_result['mentioned_stocks']
                    elif isinstance(gemini_result, list):
                        mentioned_stocks_data = gemini_result
                    
                    print(f"DEBUG: Gemini result type: {type(gemini_result)}")
                    print(f"DEBUG: Gemini result: {gemini_result}")
                    print(f"DEBUG: Extracted mentioned_stocks_data: {mentioned_stocks_data}")
                    
                    # Create post object
                    post_object = {
                        "url": post['url'],
                        "type": request.sourceType,
                        "createdDate": post['date'],
                        "content": post['content'],
                        "summary": gemini_result.get('post_summary', '') if isinstance(gemini_result, dict) else '',
                        "mentionedStocks": [],
                        "source_name": request.sourceName
                    }
                    
                    # Save new post and analysis to database
                    if mentioned_stocks_data:
                        print(f"DEBUG: Attempting to save post to database with {len(mentioned_stocks_data)} stocks")
                        try:
                            post_summary = gemini_result.get('post_summary', '') if isinstance(gemini_result, dict) else ''
                            
                            # Add structured_analysis to each stock mention
                            structured_analysis = gemini_result.get('structured_analysis', {}) if isinstance(gemini_result, dict) else {}
                            enriched_stocks_data = []
                            for stock_data in mentioned_stocks_data:
                                if isinstance(stock_data, dict):
                                    enriched_stock = stock_data.copy()
                                    enriched_stock['structured_analysis'] = structured_analysis
                                    enriched_stocks_data.append(enriched_stock)
                            
                            await db_service.save_post_with_analysis(post, source_id, enriched_stocks_data, post_summary)
                            print(f"✓ Post and analysis with structured data saved to database")
                            
                            # Log database operation
                            debug_logger.log_database_operation(
                                operation_type="save_post_with_analysis",
                                table="posts",
                                data={"post_url": post['url'], "stocks_count": len(enriched_stocks_data)},
                                result="success"
                            )
                        except Exception as db_error:
                            print(f"✗ Error saving to database: {db_error}")
                            
                            # Log database error
                            debug_logger.log_database_operation(
                                operation_type="save_post_with_analysis",
                                table="posts",
                                data={"post_url": post['url'], "stocks_count": len(enriched_stocks_data)},
                                error=db_error
                            )
                            # Continue processing even if database save fails
                    else:
                        print(f"DEBUG: No stocks found in analysis, skipping database save")
                    
                    # Add stock mentions to post object
                    for stock_data in mentioned_stocks_data:
                        if isinstance(stock_data, dict):
                            stock_symbol = stock_data.get('stock_symbol', '')
                            sentiment = stock_data.get('sentiment', 'neutral')
                            stock_summary = stock_data.get('summary', '')
                            
                            if stock_symbol:
                                post_object["mentionedStocks"].append({
                                    "stock_symbol": stock_symbol,
                                    "sentiment": sentiment,
                                    "stock_summary": stock_summary
                                })
                
                # Process each stock mentioned in this post
                for stock_data in mentioned_stocks_data:
                    if isinstance(stock_data, dict):
                        stock_symbol = stock_data.get('stock_symbol', '')
                        sentiment = stock_data.get('sentiment', 'neutral')
                        stock_summary = stock_data.get('summary', '') or stock_data.get('stock_summary', '')
                        
                        if stock_symbol:  # Only process if symbol is not empty
                            # Add to post's mentioned stocks
                            stock_info = {
                                "stock_symbol": stock_symbol,
                                "sentiment": sentiment,
                                "stock_summary": stock_summary
                            }
                            post_object["mentionedStocks"].append(stock_info)
                            
                            # Aggregate at stock level - THIS IS THE KEY CHANGE
                            stock_mentions[stock_symbol]['post_details'].append({
                                'url': post['url'],
                                'date': post['date'],
                                'sentiment': sentiment,
                                'summary': stock_summary,
                                'post_summary': post_object['summary']
                            })
                            stock_mentions[stock_symbol]['sentiments'].append(sentiment)
                            stock_mentions[stock_symbol]['summaries'].append(stock_summary)
                
                processed_posts.append(post_object)
                
                print(f"✓ Post {i} processed - Found {len(post_object['mentionedStocks'])} stocks")
                for stock in post_object['mentionedStocks']:
                    print(f"  - {stock['stock_symbol']}: {stock['sentiment']}")
                
            except Exception as e:
                print(f"✗ Error analyzing post {i}: {e}")
                import traceback
                print(f"Error traceback: {traceback.format_exc()}")
                
                # Create post object without analysis
                post_object = {
                    "url": post['url'],
                    "type": request.sourceType,
                    "createdDate": post['date'],
                    "content": post['content'],
                    "summary": "Analysis failed",
                    "mentionedStocks": []
                }
                processed_posts.append(post_object)
                continue
        
        # Create STOCK-LEVEL analysis (this is what you want!)
        stock_level_analysis = []
        for stock_symbol, data in stock_mentions.items():
            # Calculate overall sentiment (majority wins)
            sentiment_counts = defaultdict(int)
            for sentiment in data['sentiments']:
                sentiment_counts[sentiment.lower()] += 1
            
            overall_sentiment = max(sentiment_counts.items(), key=lambda x: x[1])[0] if sentiment_counts else 'neutral'
            
            # Combine all summaries about this stock
            combined_summary = '. '.join(filter(None, data['summaries']))
            if len(combined_summary) > 500:  # Truncate if too long
                combined_summary = combined_summary[:500] + "..."
            
            # Create stock analysis object
            stock_analysis = {
                "stock_symbol": stock_symbol,
                "mentioned_count": len(data['post_details']),  # How many posts mention this stock
                "overall_sentiment": overall_sentiment,
                "stock_summary": combined_summary,
                "post_details": data['post_details']  # All posts mentioning this stock with their sentiments
            }
            stock_level_analysis.append(stock_analysis)
        
        # Sort by mention count (most mentioned first)
        stock_level_analysis.sort(key=lambda x: x['mentioned_count'], reverse=True)
        
        print(f"\n=== STOCK-LEVEL Analysis Summary ===")
        for stock in stock_level_analysis:
            print(f"Stock: {stock['stock_symbol']}")
            print(f"  Mentioned in {stock['mentioned_count']} posts")
            print(f"  Overall sentiment: {stock['overall_sentiment']}")
            print(f"  Posts mentioning this stock:")
            for post_detail in stock['post_details']:
                print(f"    - {post_detail['url']} (sentiment: {post_detail['sentiment']})")
            print("-" * 60)
        
        # Create JSON response for frontend
        response_data = {
            "posts": processed_posts,
            "stock_analysis": stock_level_analysis,  # This is now STOCK-LEVEL focused
            "metadata": {
                "source_name": request.sourceName,
                "source_type": request.sourceType,
                "total_posts_found": total_posts_found,
                "posts_within_3_days": len(collected_posts),
                "posts_analyzed": len(processed_posts),
                "unique_stocks_found": len(stock_level_analysis),
                "crawl_timestamp": datetime.now().isoformat()
            }
        }
        
        print(f"\n=== Final Response Summary ===")
        print(f"Posts processed: {len(processed_posts)}")
        print(f"Unique stocks found: {len(stock_level_analysis)}")
        print(f"Response structure: {list(response_data.keys())}")
        
        # Update stock prices for mentioned stocks
        if stock_level_analysis:
            print(f"\n=== Updating Stock Prices ===")
            try:
                price_update_results = update_mentioned_stocks_prices(stock_level_analysis)
                print(f"✓ Price update completed for {len(price_update_results)} stocks")
            except Exception as price_error:
                print(f"⚠️ Error updating stock prices: {price_error}")
                # Continue with response even if price update fails
            
            # Update company information for mentioned stocks
            print(f"\n=== Updating Company Information ===")
            try:
                mentioned_symbols = [stock["stock_symbol"] for stock in stock_level_analysis]
                company_update_results = await update_company_information(mentioned_symbols)
                successful_updates = sum(1 for success in company_update_results.values() if success)
                print(f"✓ Company info update completed for {successful_updates}/{len(mentioned_symbols)} stocks")
            except Exception as company_error:
                print(f"⚠️ Error updating company information: {company_error}")
                # Continue with response even if company update fails
        
        # Log analysis results
        debug_logger.log_analysis_result(
            operation_id=op_id,
            analysis_type="stock_level_analysis",
            stocks_found=stock_level_analysis,
            summary={
                "total_posts": len(processed_posts),
                "unique_stocks": len(stock_level_analysis),
                "source_type": request.sourceType
            }
        )
        
        # Finalize debug session
        debug_logger.finalize_session()
        
        return JSONResponse(content=response_data)
        
    except Exception as e:
        # Log error in debug session
        debug_logger.log_error(
            error_type="crawl_endpoint_error",
            error_message=str(e),
            context={"source_name": request.sourceName, "url": request.url}
        )
        
        # Finalize session even on error
        debug_logger.finalize_session()
        
        print(f"Error during crawling: {e}")
        print(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Crawling failed: {str(e)}")


def analyze_pdf_report_with_gemini(content: str) -> Dict:
    """
    Analyze PDF financial report content with structured table format
    """
    if not model or not content.strip():
        print("Gemini model not available or no content to analyze")
        return {"post_summary": "", "mentioned_stocks": []}
    
    try:
        prompt = f"""
        Bạn là chuyên gia phân tích tài chính. Hãy đọc báo cáo phân tích cổ phiếu và tóm tắt thành bảng theo đúng cấu trúc dưới đây.  
        Chỉ lấy thông tin từ báo cáo, không tự suy diễn.  
        Phải bao gồm cả yếu tố tích cực và tiêu cực, không được bỏ sót.  
        Không viết nhận định chung chung, hãy cụ thể hóa số liệu và nguyên nhân.  
        Các tỷ lệ % cần ghi kèm dấu % và chỉ rõ so sánh với kỳ nào (YoY hoặc QoQ).  

        Chỉ trả lời theo đúng format JSON phía dưới, tuyệt đối không nói gì ngoài JSON này:
        {{
            "post_summary": "Tóm tắt ngắn gọn báo cáo",
            "mentioned_stocks": [
                {{
                    "stock_symbol": "SYMBOL",
                    "sentiment": "positive/negative/neutral",
                    "summary": "Phân tích chi tiết"
                }}
            ],
            "structured_analysis": {{
                "ket_qua_kinh_doanh_quy": {{
                    "doanh_thu": "",
                    "loi_nhuan_gop": "",
                    "bien_loi_nhuan_gop": "",
                    "lnst": "",
                    "bien_lnst": "",
                    "thay_doi_yoy": "",
                    "thay_doi_qoq": "",
                    "nguyen_nhan_tich_cuc": "",
                    "nguyen_nhan_tieu_cuc": "",
                    "yeu_to_bat_thuong": ""
                }},
                "luy_ke_6t_nam": {{
                    "doanh_thu": "",
                    "lnst": "",
                    "thay_doi_yoy": "",
                    "hoan_thanh_ke_hoach": ""
                }},
                "phan_tich_mang_kinh_doanh": {{
                    "ty_trong_doanh_thu": "",
                    "ty_trong_loi_nhuan": "",
                    "xu_huong_cac_mang": ""
                }},
                "tai_chinh_dong_tien": {{
                    "tien_mat": "",
                    "cac_khoan_phai_thu": "",
                    "hang_ton_kho": "",
                    "tai_san_do_dang": "",
                    "no_vay": "",
                    "dong_tien_hoat_dong": "",
                    "dong_tien_dau_tu": "",
                    "dong_tien_tai_chinh": "",
                    "chi_so_an_toan": ""
                }},
                "trien_vong": {{
                    "yeu_to_ho_tro_ngan_han": "",
                    "yeu_to_ho_tro_dai_han": "",
                    "ke_hoach_du_an": "",
                    "du_bao_doanh_thu": "",
                    "du_bao_lnst": "",
                    "du_bao_eps": "",
                    "du_bao_roe": ""
                }},
                "rui_ro": {{
                    "rui_ro_thi_truong": "",
                    "rui_ro_nguyen_lieu": "",
                    "rui_ro_phap_ly": "",
                    "rui_ro_canh_tranh": ""
                }},
                "dinh_gia_khuyen_nghi": {{
                    "pe_forward": "",
                    "pb_forward": "",
                    "quan_diem": "",
                    "ly_do": ""
                }}
            }}
        }}

        Nội dung báo cáo:
        {content}
        """
        
        print("Sending PDF report to Gemini for structured analysis...")
        response = model.generate_content(prompt)
        
        if response and response.text:
            print("Received structured PDF analysis from Gemini")
            
            # Clean the response text
            response_text = response.text.replace("```json", "").replace("```", "").strip()
            
            try:
                # Look for JSON object in the response
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}') + 1
                
                if start_idx != -1 and end_idx != -1:
                    json_str = response_text[start_idx:end_idx]
                    analysis_result = json.loads(json_str)
                    
                    print(f"Successfully parsed structured PDF analysis")
                    return analysis_result
                else:
                    print("Could not find valid JSON in PDF analysis response")
                    return {"post_summary": "", "mentioned_stocks": []}
                    
            except json.JSONDecodeError as e:
                print(f"JSON decode error in PDF analysis: {e}")
                print(f"Response text: {response_text[:500]}...")
                return {"post_summary": "", "mentioned_stocks": []}
                
        else:
            print("No response from Gemini for PDF analysis")
            return {"post_summary": "", "mentioned_stocks": []}
            
    except Exception as e:
        print(f"Error in PDF analysis with Gemini: {e}")
        return {"post_summary": "", "mentioned_stocks": []}

def analyze_individual_post_with_gemini(content: str) -> Dict:
    """
    Analyze individual post content with Gemini to extract both post summary and stock mentions
    """
    if not model or not content.strip():
        print("Gemini model not available or no content to analyze")
        return {"post_summary": "", "mentioned_stocks": []}
    
    try:
        prompt = f"""
        Bạn là chuyên gia phân tích tài chính. Hãy đọc nội dung tin tức tài chính và phân tích theo đúng cấu trúc dưới đây.  
        Chỉ lấy thông tin từ nội dung, không tự suy diễn.  
        Phải bao gồm cả yếu tố tích cực và tiêu cực, không được bỏ sót.  
        Không viết nhận định chung chung, hãy cụ thể hóa số liệu và nguyên nhân.  
        Các tỷ lệ % cần ghi kèm dấu % và chỉ rõ so sánh với kỳ nào (YoY hoặc QoQ).  

        Chỉ trả lời theo đúng format JSON phía dưới, tuyệt đối không nói gì ngoài JSON này:
        {{
            "post_summary": "Tóm tắt ngắn gọn nội dung tin tức",
            "mentioned_stocks": [
                {{
                    "stock_symbol": "SYMBOL",
                    "sentiment": "positive/negative/neutral",
                    "summary": "Phân tích chi tiết"
                }}
            ],
            "structured_analysis": {{
                "ket_qua_kinh_doanh_quy": {{
                    "doanh_thu": "",
                    "loi_nhuan_gop": "",
                    "bien_loi_nhuan_gop": "",
                    "lnst": "",
                    "bien_lnst": "",
                    "thay_doi_yoy": "",
                    "thay_doi_qoq": "",
                    "nguyen_nhan_tich_cuc": "",
                    "nguyen_nhan_tieu_cuc": "",
                    "yeu_to_bat_thuong": ""
                }},
                "luy_ke_6t_nam": {{
                    "doanh_thu": "",
                    "lnst": "",
                    "thay_doi_yoy": "",
                    "hoan_thanh_ke_hoach": ""
                }},
                "phan_tich_mang_kinh_doanh": {{
                    "ty_trong_doanh_thu": "",
                    "ty_trong_loi_nhuan": "",
                    "xu_huong_cac_mang": ""
                }},
                "tai_chinh_dong_tien": {{
                    "tien_mat": "",
                    "cac_khoan_phai_thu": "",
                    "hang_ton_kho": "",
                    "tai_san_do_dang": "",
                    "no_vay": "",
                    "dong_tien_hoat_dong": "",
                    "dong_tien_dau_tu": "",
                    "dong_tien_tai_chinh": "",
                    "chi_so_an_toan": ""
                }},
                "trien_vong": {{
                    "yeu_to_ho_tro_ngan_han": "",
                    "yeu_to_ho_tro_dai_han": "",
                    "ke_hoach_du_an": "",
                    "du_bao_doanh_thu": "",
                    "du_bao_lnst": "",
                    "du_bao_eps": "",
                    "du_bao_roe": ""
                }},
                "rui_ro": {{
                    "rui_ro_thi_truong": "",
                    "rui_ro_nguyen_lieu": "",
                    "rui_ro_phap_ly": "",
                    "rui_ro_canh_tranh": ""
                }},
                "dinh_gia_khuyen_nghi": {{
                    "pe_forward": "",
                    "pb_forward": "",
                    "quan_diem": "",
                    "ly_do": ""
                }}
            }}
        }}

        Lưu ý:
        - Chỉ đưa ra thông tin có trong nội dung, không tự suy diễn
        - Nếu không có thông tin cho trường nào thì để trống ""
        - mentioned_stocks chỉ bao gồm các mã cổ phiếu Việt Nam thực sự (HPG, VPB, ACB, v.v.)
        - Trả về JSON hợp lệ, không có text nào khác

        Nội dung phân tích:
        {content}
        """
        
        print("Sending individual post to Gemini for analysis...")
        response = model.generate_content(prompt)
        
        if response and response.text:
            print("Received individual post analysis from Gemini")
            
            # Clean the response text
            response_text = response.text.replace("```json", "").replace("```", "").strip()
            
            try:
                # Look for JSON object in the response
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}') + 1
                
                if start_idx != -1 and end_idx != -1:
                    json_str = response_text[start_idx:end_idx]
                    analysis_result = json.loads(json_str)
                    
                    # Ensure we have the expected structure
                    if "post_summary" in analysis_result and "mentioned_stocks" in analysis_result:
                        # Also check if structured_analysis is present
                        if "structured_analysis" not in analysis_result:
                            analysis_result["structured_analysis"] = {}
                        
                        print(f"✓ Successfully parsed post analysis with {len(analysis_result['mentioned_stocks'])} stocks and structured analysis")
                        return analysis_result
                    else:
                        print("✗ Invalid JSON structure from Gemini")
                        return {"post_summary": "Analysis completed", "mentioned_stocks": [], "structured_analysis": {}}
                else:
                    print("✗ No JSON object found in Gemini response")
                    return {"post_summary": "Analysis completed", "mentioned_stocks": [], "structured_analysis": {}}
                    
            except json.JSONDecodeError as e:
                print(f"✗ Failed to parse JSON from Gemini response: {e}")
                print(f"Raw response: {response_text[:300]}...")
                return {"post_summary": "Analysis completed", "mentioned_stocks": [], "structured_analysis": {}}
        else:
            print("✗ No valid response from Gemini")
            return {"post_summary": "", "mentioned_stocks": [], "structured_analysis": {}}
            
    except Exception as e:
        print(f"✗ Error calling Gemini API for individual post: {e}")
        return {"post_summary": "Analysis failed", "mentioned_stocks": [], "structured_analysis": {}}


@app.post("/crawl-multiple")
async def crawl_multiple_endpoints(request: MultipleCrawlRequest):
    """
    Enhanced holistic crawl-multiple analysis
    
    New approach:
    1. Collect all posts from all sources (existing or crawled)
    2. Generate market context from industry + macro posts with ICB intelligence
    3. Analyze company posts with full market context
    4. Consolidate stock analysis with price context
    """
    
    # Import the new holistic implementation
    from holistic_crawl_multiple import holistic_crawl_multiple_endpoints
    
    # Call the new holistic implementation
    return await holistic_crawl_multiple_endpoints(request, db_service)


# ===== SOURCE MANAGEMENT ENDPOINTS =====

@app.post("/sources")
async def create_source(request: CrawlRequest):
    """Save a new crawling source configuration to database"""
    try:
        # Check if source already exists
        existing_source = await db_service.get_source_by_url(request.url)
        if existing_source:
            return JSONResponse(
                status_code=400,
                content={"error": f"Source with URL {request.url} already exists"}
            )
        
        # Save source to database
        source_id = await db_service.save_source(request.dict())
        
        return JSONResponse(content={
            "message": "Source saved successfully", 
            "source_id": source_id,
            "source_name": request.sourceName
        })
        
    except Exception as e:
        print(f"Error saving source: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save source: {str(e)}")

@app.get("/sources")
async def get_sources():
    """Get all active sources from database"""
    try:
        sources = await db_service.get_all_sources()
        return JSONResponse(content={"sources": sources})
    except Exception as e:
        print(f"Error fetching sources: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch sources: {str(e)}")

@app.get("/dashboard/stats")
async def get_dashboard_stats():
    """Get dashboard statistics"""
    try:
        stats = await db_service.get_dashboard_stats()
        return JSONResponse(content=stats)
    except Exception as e:
        print(f"Error fetching dashboard stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch stats: {str(e)}")

@app.put("/sources/{source_id}/status")
async def update_source_status(source_id: str, request: dict):
    """Update source status (active/inactive)"""
    try:
        new_status = request.get("status")
        if new_status not in ["active", "inactive"]:
            raise HTTPException(status_code=400, detail="Status must be 'active' or 'inactive'")
        
        # Update source status in database
        success = await db_service.update_source_status(source_id, new_status)
        
        if success:
            return JSONResponse(content={
                "message": f"Source status updated to {new_status}",
                "source_id": source_id,
                "status": new_status
            })
        else:
            raise HTTPException(status_code=404, detail="Source not found")
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error updating source status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update source status: {str(e)}")

@app.put("/sources/{source_id}")
async def update_source(source_id: str, request: CrawlRequest):
    """Update source configuration"""
    try:
        # Update source in database
        success = await db_service.update_source(source_id, request.dict())
        
        if success:
            return JSONResponse(content={
                "message": "Source updated successfully",
                "source_id": source_id,
                "source_name": request.sourceName
            })
        else:
            raise HTTPException(status_code=404, detail="Source not found")
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error updating source: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update source: {str(e)}")

@app.delete("/sources/{source_id}")
async def delete_source(source_id: str):
    """Delete a source from database"""
    try:
        # Delete source from database
        success = await db_service.delete_source(source_id)
        
        if success:
            return JSONResponse(content={
                "message": "Source deleted successfully",
                "source_id": source_id
            })
        else:
            raise HTTPException(status_code=404, detail="Source not found")
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error deleting source: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete source: {str(e)}")

@app.get("/recent-stocks")
async def get_recent_stocks(days: int = 3):
    """Get stocks mentioned in the last N days"""
    try:
        stocks = await db_service.get_recent_stocks(days)
        return JSONResponse(content={
            "stocks": stocks,
            "days": days,
            "count": len(stocks)
        })
    except Exception as e:
        print(f"Error fetching recent stocks: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch recent stocks: {str(e)}")

@app.get("/company-info/{symbol}")
async def get_company_info(symbol: str):
    """
    Get additional company information (overview, events, dividends) for a stock symbol
    
    Args:
        symbol: Stock symbol (e.g., ACB, HPG)
    
    Returns:
        JSON with company overview, recent events, and recent dividends
    """
    try:
        company_info = await db_service.get_company_additional_info(symbol)
        
        if not company_info:
            raise HTTPException(status_code=404, detail=f"Company information not found for {symbol}")
        
        return JSONResponse(content={
            "symbol": symbol,
            "company_info": company_info,
            "data_updated": True
        })
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching company info for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch company info: {str(e)}")


@app.get("/company/{symbol}/finance")
async def get_company_finance(symbol: str, limit: int = 12):
    """
    Get company financial data (balance sheet, income statement, cash flow, ratios)
    
    Args:
        symbol: Stock symbol (e.g., ACB, HPG)
        limit: Maximum number of quarters to return (default: 12)
    
    Returns:
        JSON with financial data by quarter
    """
    try:
        finance_data = await db_service.get_company_finance(symbol, limit)
        
        if not finance_data:
            return JSONResponse(content={
                "symbol": symbol,
                "finance_data": [],
                "message": f"No financial data found for {symbol}. Try updating finance data first.",
                "quarters_count": 0
            })
        
        return JSONResponse(content={
            "symbol": symbol,
            "finance_data": finance_data,
            "quarters_count": len(finance_data),
            "data_updated": True
        })
        
    except Exception as e:
        print(f"Error fetching finance data for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch finance data: {str(e)}")


@app.get("/stock-analysis/{symbol}")
async def get_stock_structured_analysis(symbol: str, post_url: str):
    """
    Get detailed structured analysis for a specific stock mention in a specific post
    
    Args:
        symbol: Stock symbol (e.g., ACB, HPG) 
        post_url: URL of the post containing the analysis (query parameter)
    
    Returns:
        JSON with detailed structured analysis data
    """
    try:
        if not post_url:
            raise HTTPException(status_code=400, detail="post_url query parameter is required")
            
        analysis_data = await db_service.get_stock_structured_analysis(symbol, post_url)
        
        if not analysis_data:
            raise HTTPException(status_code=404, detail=f"Structured analysis not found for {symbol} in specified post")
        
        return JSONResponse(content=analysis_data)
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching structured analysis for {symbol} in post {post_url}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch structured analysis: {str(e)}")

@app.get("/stock-prices/{symbol}")
async def get_stock_prices(symbol: str, period: str = "1m", interval: str = "day"):
    """
    Get stock price data for charting.
    
    Args:
        symbol: Stock symbol (e.g., ACB, HPG)
        period: Time period - "1m", "3m", "1y" (1 month, 3 months, 1 year), "1d" (1 day for hourly)
        interval: Time interval - "day" for daily prices, "hour" for hourly prices
    
    Returns:
        JSON with price data and chart configuration
    """
    try:
        from datetime import datetime, timedelta
        
        # Calculate date range based on period and interval
        today = datetime.now().date()
        
        if interval == "hour":
            # Hourly intervals with appropriate periods
            if period == "1d":
                start_date = (today - timedelta(days=1)).isoformat()
                period_label = "1 Day"
            elif period == "7d":
                start_date = (today - timedelta(days=7)).isoformat()
                period_label = "7 Days"
            elif period == "1m":
                start_date = (today - timedelta(days=30)).isoformat()
                period_label = "1 Month"
            else:
                raise HTTPException(status_code=400, detail="Invalid period for hourly data. Use '1d', '7d', or '1m'")
        else:
            # Daily intervals with existing periods
            if period == "1m":
                start_date = (today - timedelta(days=30)).isoformat()
                period_label = "1 Month"
            elif period == "3m":
                start_date = (today - timedelta(days=90)).isoformat()
                period_label = "3 Months"
            elif period == "1y":
                start_date = (today - timedelta(days=365)).isoformat()
                period_label = "1 Year"
            else:
                raise HTTPException(status_code=400, detail="Invalid period for daily data. Use '1m', '3m', or '1y'")
        
        # Get stock info and price data
        stock_result = db_service.supabase.table("stocks").select("id, symbol, organ_name, exchange, isvn30").eq("symbol", symbol).execute()
        
        if not stock_result.data:
            raise HTTPException(status_code=404, detail=f"Stock {symbol} not found")
        
        stock_info = stock_result.data[0]
        stock_id = stock_info["id"]
        
        # Handle hourly vs daily data
        if interval == "hour":
            # For hourly data, we need to check if we have it and potentially fetch it
            hourly_result = db_service.supabase.table("stock_prices_hourly").select(
                "date, hour, open, high, low, close, volume"
            ).eq("stock_id", stock_id).gte("date", start_date).order("date, hour").execute()
            
            # If no hourly data exists, fetch it from vnstock for the requested period
            if not hourly_result.data:
                print(f"No hourly data found for {symbol}, fetching from vnstock...")
                try:
                    # Import and fetch hourly data using vnstock
                    from vnstock import Vnstock
                    import pandas as pd
                    from datetime import datetime, timedelta
                    import time
                    
                    stock = Vnstock().stock(symbol=symbol, source='VCI')
                    
                    # Calculate the end date (today)
                    end_date = datetime.now().date().isoformat()
                    
                    # Fetch hourly data with retry logic
                    max_retries = 3
                    retry_delay = 2
                    
                    df = None
                    for attempt in range(max_retries):
                        try:
                            print(f"Attempting to fetch hourly data for {symbol} (attempt {attempt + 1})")
                            df = stock.quote.history(start=start_date, end=end_date, interval='1H')
                            print(f"Successfully fetched hourly data: {len(df)} records")
                            break
                        except Exception as e:
                            print(f"Error on attempt {attempt + 1}: {e}")
                            if "rate limit" in str(e).lower() and attempt < max_retries - 1:
                                print(f"Rate limit hit, retrying in {retry_delay} seconds...")
                                time.sleep(retry_delay)
                                retry_delay *= 2  # Exponential backoff
                            elif attempt == max_retries - 1:
                                raise e
                    
                    if df is not None and not df.empty:
                        # Process and insert hourly data
                        hourly_records = []
                        for index, row in df.iterrows():
                            # Extract date and hour from 'time' column (vnstock format)
                            dt = pd.to_datetime(row['time'])
                            date_str = dt.date().isoformat()
                            hour_str = dt.time().isoformat()
                            
                            hourly_records.append({
                                "stock_id": stock_id,
                                "date": date_str,
                                "hour": hour_str,
                                "open": float(row.get('open', 0)),
                                "high": float(row.get('high', 0)),
                                "low": float(row.get('low', 0)),
                                "close": float(row.get('close', 0)),
                                "volume": int(row.get('volume', 0))
                            })
                        
                        # Insert hourly data in batches to avoid conflicts
                        if hourly_records:
                            print(f"Inserting {len(hourly_records)} hourly records to database...")
                            db_service.supabase.table("stock_prices_hourly").upsert(hourly_records).execute()
                            print(f"Successfully inserted {len(hourly_records)} hourly price records for {symbol}")
                        
                        # Now fetch the data we just inserted
                        hourly_result = db_service.supabase.table("stock_prices_hourly").select(
                            "date, hour, open, high, low, close, volume"
                        ).eq("stock_id", stock_id).gte("date", start_date).order("date, hour").execute()
                        print(f"Retrieved {len(hourly_result.data)} hourly records from database")
                    else:
                        print(f"No hourly data returned from vnstock for {symbol}")
                        raise Exception(f"No hourly data available for {symbol}")
                    
                except Exception as e:
                    print(f"Error fetching hourly data for {symbol}: {e}")
                    # Fall back to daily data if hourly fetch fails
                    interval = "day"
            
            if interval == "hour" and hourly_result and hourly_result.data:
                price_result = hourly_result
            else:
                # Fall back to daily if no hourly data
                interval = "day"
        
        if interval == "day":
            # Get daily price data
            price_result = db_service.supabase.table("stock_prices").select(
                "date, open, high, low, close, volume"
            ).eq("stock_id", stock_id).gte("date", start_date).order("date").execute()
        
        if not price_result.data:
            return JSONResponse(content={
                "stock_info": stock_info,
                "period": period_label,
                "data": [],
                "message": f"No price data available for {symbol} in the last {period_label.lower()}"
            })
        
        # Prepare candlestick chart data
        candlestick_data = []
        volume_data = []
        
        for record in price_result.data:
            # Handle time field based on interval
            if interval == "hour":
                # Combine date and hour for hourly data
                time_value = f"{record['date']}T{record['hour']}"
            else:
                # Use date for daily data
                time_value = record["date"]
            
            candlestick_data.append({
                "t": time_value,  # time
                "o": float(record["open"]),    # open
                "h": float(record["high"]),    # high
                "l": float(record["low"]),     # low
                "c": float(record["close"]),   # close
                "v": int(record["volume"]) if record["volume"] else 0  # volume for reference
            })
            
            # Prepare volume data for potential secondary chart
            volume_data.append({
                "t": time_value,
                "y": int(record["volume"]) if record["volume"] else 0
            })
        
        chart_data = {
            "datasets": [{
                "label": f"{symbol} OHLC",
                "data": candlestick_data,
                "borderColor": {
                    "up": "#10b981",      # green for bullish candles
                    "down": "#ef4444",    # red for bearish candles
                    "unchanged": "#6b7280" # gray for unchanged
                },
                "backgroundColor": {
                    "up": "rgba(16, 185, 129, 0.8)",
                    "down": "rgba(239, 68, 68, 0.8)", 
                    "unchanged": "rgba(107, 114, 128, 0.8)"
                }
            }]
        }
        
        # Use bar chart to create candlestick-like visualization
        # Create datasets for High-Low range and Open-Close body
        high_low_data = []
        open_close_data = []
        
        for record in price_result.data:
            # Handle time field based on interval
            if interval == "hour":
                time_value = f"{record['date']}T{record['hour']}"
            else:
                time_value = record["date"]
            
            o, h, l, c = float(record["open"]), float(record["high"]), float(record["low"]), float(record["close"])
            
            high_low_data.append({
                "x": time_value,
                "y": [l, h]  # Low to High range
            })
            
            # Color based on bullish/bearish
            color = "#10b981" if c >= o else "#ef4444"  # green if close >= open, red otherwise
            
            open_close_data.append({
                "x": time_value,
                "y": [min(o, c), max(o, c)],  # Open to Close body
                "backgroundColor": color,
                "borderColor": color,
                "ohlc": {"o": o, "h": h, "l": l, "c": c, "v": int(record["volume"]) if record["volume"] else 0}
            })
        
        chart_data = {
            "datasets": [
                {
                    "label": "Price Range",
                    "type": "bar",
                    "data": high_low_data,
                    "backgroundColor": "rgba(107, 114, 128, 0.8)",
                    "borderColor": "#6b7280",
                    "borderWidth": 1,
                    "barThickness": 2,
                    "categoryPercentage": 0.8,
                    "barPercentage": 0.1
                },
                {
                    "label": f"{symbol} OHLC",
                    "type": "bar", 
                    "data": open_close_data,
                    "borderWidth": 1,
                    "barThickness": 8,
                    "categoryPercentage": 0.8,
                    "barPercentage": 0.8
                }
            ]
        }
        
        # Chart configuration for OHLC bar chart
        chart_config = {
            "type": "bar",
            "data": chart_data,
            "options": {
                "responsive": True,
                "maintainAspectRatio": False,
                "scales": {
                    "x": {
                        "type": "time",
                        "time": {
                            "unit": "hour" if interval == "hour" else "day",
                            "displayFormats": {
                                "hour": "MMM dd HH:mm",
                                "day": "MMM dd"
                            }
                        },
                        "title": {
                            "display": True,
                            "text": "Time" if interval == "hour" else "Date"
                        }
                    },
                    "y": {
                        "beginAtZero": False,
                        "title": {
                            "display": True,
                            "text": "Price (VND)"
                        }
                    }
                },
                "plugins": {
                    "title": {
                        "display": True,
                        "text": f"{symbol} - {period_label} {'Hourly' if interval == 'hour' else 'Daily'} OHLC Chart"
                    },
                    "legend": {
                        "display": False
                    }
                }
            }
        }
        
        return JSONResponse(content={
            "stock_info": stock_info,
            "period": period_label,
            "chart_config": chart_config,
            "raw_data": price_result.data,
            "data_points": len(price_result.data)
        })
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching stock prices for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch stock prices: {str(e)}")

@app.get("/", response_class=HTMLResponse)
async def root():
    """Root endpoint that redirects to news page"""
    return RedirectResponse(url="/news")

@app.get("/health")
async def health_check():
    """Health check endpoint for deployment monitoring"""
    try:
        # Test database connection
        test_result = db_service.supabase.table("sources").select("count").execute()
        db_status = "healthy" if test_result else "unhealthy"
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "database": db_status,
            "version": "1.0.0",
            "environment": os.getenv("ENVIRONMENT", "production")
        }
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
                "version": "1.0.0"
            }
        )

@app.get("/news", response_class=HTMLResponse)
async def news_page():
    """News page endpoint"""
    with open("static/news.html", "r", encoding="utf-8") as f:
        return f.read()

@app.get("/analyze", response_class=HTMLResponse)
async def analyze_page():
    """Analyze page endpoint"""
    with open("static/analyze.html", "r", encoding="utf-8") as f:
        return f.read()

@app.get("/documents", response_class=HTMLResponse)
async def documents_page():
    """Documents page endpoint"""
    with open("static/documents.html", "r", encoding="utf-8") as f:
        return f.read()

@app.get("/technical-docs", response_class=HTMLResponse)
async def technical_docs_page():
    """Technical Documentation page endpoint"""
    with open("static/technical-docs.html", "r", encoding="utf-8") as f:
        return f.read()

@app.get("/vnindex-data")
async def get_vnindex_data(period: str = "1M"):
    """
    Get VNINDEX data using vnstock for charting.
    
    Args:
        period: Time period - "1M", "3M", "6M", "1Y"
    
    Returns:
        JSON with VNINDEX price data for Chart.js
    """
    try:
        from vnstock import Vnstock
        from datetime import timedelta
        
        # Map frontend periods to date ranges
        today = datetime.now().date()
        period_mapping = {
            "1M": today - timedelta(days=30),
            "3M": today - timedelta(days=90), 
            "6M": today - timedelta(days=180),
            "1Y": today - timedelta(days=365)
        }
        
        start_date = period_mapping.get(period, today - timedelta(days=30))
        
        print(f"Fetching VNINDEX data for period: {period} from {start_date} to {today}")
        
        # Get VNINDEX data using vnstock - using VNINDEX as a stock symbol
        stock = Vnstock().stock(symbol='VNINDEX', source='VCI')
        data = stock.quote.history(start=start_date.strftime('%Y-%m-%d'), end=today.strftime('%Y-%m-%d'), interval='1D')
        
        if data is None or data.empty:
            # Try alternative approach with a major stock as proxy
            print("VNINDEX direct query failed, trying VIC as market proxy")
            stock = Vnstock().stock(symbol='VIC', source='VCI')
            data = stock.quote.history(start=start_date.strftime('%Y-%m-%d'), end=today.strftime('%Y-%m-%d'), interval='1D')
            
            if data is None or data.empty:
                return JSONResponse(
                    status_code=404,
                    content={"error": "No market data available for the requested period"}
                )
        
        # Reset index to access data properly
        data = data.reset_index()
        
        # Sort by date (oldest first for chart)  
        data = data.sort_values('time')
        
        # Format data for Chart.js
        chart_data = {
            "labels": data['time'].dt.strftime('%m-%d').tolist(),
            "datasets": [{
                "label": "Market Index",
                "data": data['close'].tolist(),
                "borderColor": "#2F80ED",
                "backgroundColor": "rgba(47, 128, 237, 0.1)",
                "borderWidth": 2,
                "fill": True,
                "tension": 0.4,
                "pointRadius": 0,
                "pointHoverRadius": 4
            }]
        }
        
        # Calculate price change
        latest_price = float(data['close'].iloc[-1])
        previous_price = float(data['close'].iloc[-2]) if len(data) > 1 else latest_price
        price_change = latest_price - previous_price
        price_change_percent = (price_change / previous_price * 100) if previous_price != 0 else 0
        
        # Chart configuration optimized for the frontend design
        chart_config = {
            "type": "line",
            "data": chart_data,
            "options": {
                "responsive": True,
                "maintainAspectRatio": False,
                "interaction": {
                    "intersect": False,
                    "mode": 'index'
                },
                "scales": {
                    "y": {
                        "beginAtZero": False,
                        "grid": {
                            "color": "rgba(200, 200, 200, 0.2)"
                        },
                        "ticks": {
                            "color": "#666"
                        }
                    },
                    "x": {
                        "grid": {
                            "display": False
                        },
                        "ticks": {
                            "color": "#666",
                            "maxTicksLimit": 8
                        }
                    }
                },
                "plugins": {
                    "legend": {
                        "display": False
                    },
                    "tooltip": {
                        "backgroundColor": "rgba(0, 0, 0, 0.8)",
                        "titleColor": "white",
                        "bodyColor": "white",
                        "borderColor": "#2F80ED",
                        "borderWidth": 1
                    }
                },
                "elements": {
                    "line": {
                        "tension": 0.4
                    }
                }
            }
        }
        
        return JSONResponse(content={
            "success": True,
            "period": period,
            "chart_config": chart_config,
            "latest_price": latest_price,
            "price_change": price_change,
            "price_change_percent": price_change_percent,
            "data_points": len(data),
            "last_updated": data['time'].iloc[-1].isoformat() if len(data) > 0 else None
        })
        
    except ImportError:
        return JSONResponse(
            status_code=500,
            content={"error": "vnstock library not available"}
        )
    except Exception as e:
        print(f"Error fetching VNINDEX data: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to fetch VNINDEX data: {str(e)}"}
        )

@app.post("/company-info/update")
async def update_all_company_info(request: CompanyUpdateRequest):
    """
    Manual Company Info Update: Updates stock records with ICB codes and company information from VNStock
    """
    try:
        from vnstock import Listing
        
        print("\n=== Manual Company Info Update Started ===")
        
        # Step 1: Get all symbols with industry info
        print("Step 1: Fetching all stock symbols with industry data...")
        listing = Listing()
        symbols_df = listing.symbols_by_industries()
        
        if symbols_df is None or symbols_df.empty:
            return JSONResponse(content={
                "success": False,
                "message": "No stock symbols data available",
                "updated_stocks": 0,
                "failed_stocks": []
            })
        
        print(f"Found {len(symbols_df)} stocks with industry information")
        
        # Debug mode: filter to only VIC symbol
        if request.debug:
            symbols_df = symbols_df[symbols_df['symbol'] == 'VIC']
            print(f"Debug mode enabled: Processing VIC only ({len(symbols_df)} records)")
        
        # Step 2: Process each stock
        updated_stocks = 0
        failed_stocks = []
        
        for _, row in symbols_df.iterrows():
            try:
                stock_symbol = row.get('symbol')
                if not stock_symbol:
                    continue
                
                # Prepare update data with ICB codes and company info
                update_data = {
                    'organ_name': row.get('organ_name', ''),
                    'icb_name1': row.get('icb_name1', ''),
                    'icb_name2': row.get('icb_name2', ''),
                    'icb_name3': row.get('icb_name3', ''),
                    'icb_name4': row.get('icb_name4', ''),
                    'icb_code1': row.get('icb_code1', ''),
                    'icb_code2': row.get('icb_code2', ''),
                    'icb_code3': row.get('icb_code3', ''),
                    'icb_code4': row.get('icb_code4', ''),
                    'com_type_code': row.get('com_type_code', ''),
                    'updated_at': datetime.now().isoformat()
                }
                
                # Remove None/NaN values
                update_data = {k: v for k, v in update_data.items() if v is not None and str(v) != 'nan'}
                
                # Update or create stock record
                result = db_service.supabase.table("stocks").upsert({
                    'symbol': stock_symbol,
                    **update_data
                }, on_conflict="symbol").execute()
                
                if result.data:
                    updated_stocks += 1
                    if updated_stocks % 50 == 0:  # Progress indication
                        print(f"✓ Processed {updated_stocks} stocks...")
                else:
                    failed_stocks.append({
                        "symbol": stock_symbol,
                        "error": "Database upsert failed"
                    })
                    
            except Exception as stock_error:
                failed_stocks.append({
                    "symbol": row.get('symbol', 'Unknown'),
                    "error": str(stock_error)
                })
        
        print(f"\n=== Company Info Update Summary ===")
        print(f"Total stocks processed: {len(symbols_df)}")
        print(f"Successfully updated: {updated_stocks}")
        print(f"Failed updates: {len(failed_stocks)}")
        
        return JSONResponse(content={
            "success": True,
            "message": f"Company info update completed. Updated {updated_stocks} stocks with ICB codes and company information.",
            "summary": {
                "total_stocks_processed": len(symbols_df),
                "successful_updates": updated_stocks,
                "failed_updates": len(failed_stocks)
            },
            "updated_stocks": updated_stocks,
            "failed_stocks": failed_stocks[:10]  # Only return first 10 failures
        })
        
    except Exception as e:
        print(f"Critical error during company info update: {e}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Company info update failed: {str(e)}")

@app.post("/industries/update")
async def update_industries_table(request: CompanyUpdateRequest):
    """
    Update industries table with data from VNStock industries_icb() function
    """
    try:
        from vnstock import Listing
        
        print("\n=== Industries Table Update Started ===")
        
        # Step 1: Get industries data from VNStock
        print("Step 1: Fetching industries data from VNStock...")
        listing = Listing()
        industries_df = listing.industries_icb()
        
        if industries_df is None or industries_df.empty:
            return JSONResponse(content={
                "success": False,
                "message": "No industries data available from VNStock"
            })
        
        print(f"Found {len(industries_df)} industries")
        
        # Debug mode: limit to first 10 industries only
        if request.debug:
            industries_df = industries_df.head(10)
            print(f"Debug mode enabled: Processing only first {len(industries_df)} industries")
        
        # Step 2: Clear existing industries and insert new data
        print("Step 2: Updating industries table...")
        
        # Process each industry
        updated_count = 0
        failed_count = 0
        
        for _, row in industries_df.iterrows():
            try:
                industry_data = {
                    'icb_code': str(row.get('icb_code')),
                    'icb_name': row.get('icb_name', ''),
                    'en_icb_name': row.get('en_icb_name', ''),
                    'level': int(row.get('level', 0)),
                    'updated_at': datetime.now().isoformat()
                }
                
                # Upsert industry record
                result = db_service.supabase.table("industries").upsert(
                    industry_data, 
                    on_conflict="icb_code"
                ).execute()
                
                if result.data:
                    updated_count += 1
                    if updated_count % 20 == 0:  # Progress indication
                        print(f"✓ Processed {updated_count} industries...")
                else:
                    failed_count += 1
                    
            except Exception as industry_error:
                print(f"✗ Error processing industry {row.get('icb_code', 'Unknown')}: {industry_error}")
                failed_count += 1
        
        print(f"\n=== Industries Update Summary ===")
        print(f"Total industries processed: {len(industries_df)}")
        print(f"Successfully updated: {updated_count}")
        print(f"Failed updates: {failed_count}")
        
        return JSONResponse(content={
            "success": True,
            "message": f"Industries update completed. Updated {updated_count} industries.",
            "summary": {
                "total_industries_processed": len(industries_df),
                "successful_updates": updated_count,
                "failed_updates": failed_count
            },
            "updated_industries": updated_count
        })
        
    except Exception as e:
        print(f"Critical error during industries update: {e}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Industries update failed: {str(e)}")

@app.post("/stock-prices/update")
async def update_stock_prices_manual(request: CompanyUpdateRequest):
    """Manual update of stock prices for stocks mentioned in last 7 days"""
    try:
        # Get all stocks mentioned in last 7 days with details
        print("Getting stocks mentioned in last 7 days...")
        mentioned_stocks = await db_service.get_stocks_mentioned_in_last_n_days_with_details(7)
        
        if not mentioned_stocks:
            return JSONResponse(content={
                "success": False,
                "message": "No stocks found mentioned in last 7 days"
            })
        
        # Debug mode: filter to only VIC symbol
        if request.debug:
            mentioned_stocks = [stock for stock in mentioned_stocks if stock['symbol'] == 'VIC']
            if not mentioned_stocks:
                mentioned_stocks = [{'symbol': 'VIC', 'id': None}]  # Force VIC for debug even if not mentioned
            print(f"Debug mode enabled: Processing VIC only")
        else:
            print(f"Found {len(mentioned_stocks)} stocks mentioned in last 7 days")
        
        # Import the stock price updater
        from stock_price_updater import update_stock_prices_selective
        
        # Extract just the symbols for the updater function
        stock_symbols = [stock['symbol'] for stock in mentioned_stocks]
        
        # Update prices only for stocks that need updates
        result = update_stock_prices_selective(stock_symbols)
        
        return JSONResponse(content={
            "success": True,
            "message": f"Price update completed",
            "details": result
        })
        
    except Exception as e:
        print(f"Error in manual stock price update: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(content={
            "success": False,
            "message": f"Failed to update stock prices: {str(e)}"
        }, status_code=500)

@app.post("/stock-prices-hourly/update")
async def update_stock_prices_hourly_manual(request: CompanyUpdateRequest):
    """Manual update of hourly stock prices for stocks mentioned in last 30 days"""
    try:
        # Get all stocks mentioned in last 30 days
        print("Getting stocks mentioned in last 30 days...")
        mentioned_stocks = await db_service.get_stocks_mentioned_in_last_n_days_with_details(30)
        
        if not mentioned_stocks:
            return JSONResponse(content={
                "success": False,
                "message": "No stocks found mentioned in last 30 days",
                "updated_stocks": [],
                "failed_stocks": []
            })
        
        # Debug mode: filter to only VIC symbol
        if request.debug:
            mentioned_stocks = [stock for stock in mentioned_stocks if stock['symbol'] == 'VIC']
            if not mentioned_stocks:
                mentioned_stocks = [{'symbol': 'VIC'}]  # Force VIC for debug even if not mentioned
            print(f"Debug mode enabled: Processing VIC only")
        else:
            print(f"Found {len(mentioned_stocks)} stocks mentioned in last 30 days")
        
        # Import required modules
        from vnstock import Vnstock
        import pandas as pd
        from datetime import datetime, timedelta
        import time
        
        updated_stocks = []
        failed_stocks = []
        
        # Calculate date range (last 30 days)
        today = datetime.now().date()
        start_date = (today - timedelta(days=30)).isoformat()
        end_date = today.isoformat()
        
        for stock_info in mentioned_stocks:
            stock_symbol = stock_info["symbol"]
            stock_id = stock_info["id"]
            
            print(f"\nProcessing hourly data for {stock_symbol}...")
            
            try:
                # Check if we already have recent hourly data
                existing_data = db_service.supabase.table("stock_prices_hourly").select(
                    "date"
                ).eq("stock_id", stock_id).gte("date", start_date).order("date.desc").limit(1).execute()
                
                if existing_data.data:
                    last_date = existing_data.data[0]["date"]
                    print(f"✓ Already has hourly data up to {last_date}, skipping {stock_symbol}")
                    continue
                
                # Fetch hourly data from vnstock with retry logic
                stock = Vnstock().stock(symbol=stock_symbol, source='VCI')
                
                max_retries = 3
                retry_delay = 2
                df = None
                
                for attempt in range(max_retries):
                    try:
                        print(f"  Attempt {attempt + 1}: Fetching hourly data for {stock_symbol}...")
                        df = stock.quote.history(start=start_date, end=end_date, interval='1H')
                        break
                    except Exception as e:
                        error_msg = str(e).lower()
                        if ("rate limit" in error_msg or "too many requests" in error_msg) and attempt < max_retries - 1:
                            print(f"  Rate limit hit, retrying in {retry_delay} seconds...")
                            time.sleep(retry_delay)
                            retry_delay *= 2  # Exponential backoff
                        else:
                            raise e
                
                if df is not None and not df.empty:
                    # Process and insert hourly data
                    hourly_records = []
                    
                    for index, row in df.iterrows():
                        # Extract date and hour from index (datetime)
                        dt = pd.to_datetime(index)
                        date_str = dt.date().isoformat()
                        hour_str = dt.time().isoformat()
                        
                        hourly_records.append({
                            "stock_id": stock_id,
                            "date": date_str,
                            "hour": hour_str,
                            "open": float(row.get('open', 0)),
                            "high": float(row.get('high', 0)),
                            "low": float(row.get('low', 0)),
                            "close": float(row.get('close', 0)),
                            "volume": int(row.get('volume', 0))
                        })
                    
                    # Insert hourly data in batches to avoid conflicts
                    if hourly_records:
                        db_service.supabase.table("stock_prices_hourly").upsert(hourly_records).execute()
                        print(f"✓ Inserted {len(hourly_records)} hourly price records for {stock_symbol}")
                        
                        updated_stocks.append({
                            "symbol": stock_symbol,
                            "records_count": len(hourly_records),
                            "status": "success"
                        })
                    else:
                        print(f"✗ No valid records to insert for {stock_symbol}")
                        failed_stocks.append({
                            "symbol": stock_symbol,
                            "error": "No valid hourly data available"
                        })
                else:
                    print(f"✗ No hourly data available for {stock_symbol}")
                    failed_stocks.append({
                        "symbol": stock_symbol,
                        "error": "No hourly data returned from vnstock"
                    })
                    
                # Add delay between requests to avoid rate limiting
                time.sleep(1)
                
            except Exception as e:
                error_msg = str(e)
                print(f"✗ Error processing {stock_symbol}: {error_msg}")
                failed_stocks.append({
                    "symbol": stock_symbol,
                    "error": error_msg
                })
        
        return JSONResponse(content={
            "success": True,
            "message": f"Hourly price update completed",
            "summary": {
                "total_stocks": len(mentioned_stocks),
                "updated_stocks": len(updated_stocks),
                "failed_stocks": len(failed_stocks)
            },
            "updated_stocks": updated_stocks,
            "failed_stocks": failed_stocks
        })
        
    except Exception as e:
        print(f"Error in manual hourly stock price update: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(content={
            "success": False,
            "message": f"Failed to update hourly stock prices: {str(e)}"
        }, status_code=500)

@app.post("/company-events/update")
async def update_all_company_events(request: CompanyUpdateRequest):
    """
    Delete all stock events and update with fresh data from vnstock for stocks mentioned in last 30 days
    """
    try:
        from vnstock.explorer.vci import Company
        import uuid
        
        print("\n=== Company Events Manual Update Started ===")
        
        # Step 1: Get stocks mentioned in last 30 days using existing endpoint logic
        print("Step 1: Getting stocks mentioned in last 30 days...")
        recent_stocks = await db_service.get_recent_stocks(days=30)
        
        if not recent_stocks:
            return JSONResponse(content={
                "success": False,
                "message": "No stocks found in the last 30 days",
                "updated_stocks": [],
                "failed_stocks": []
            })
        
        stock_symbols = [stock["symbol"] for stock in recent_stocks]
        
        # Debug mode: filter to only VIC symbol
        if request.debug:
            stock_symbols = ['VIC']
            print(f"Debug mode enabled: Processing VIC only")
        else:
            print(f"Found {len(stock_symbols)} stocks to update: {', '.join(stock_symbols)}")
        
        # Step 2: Delete all existing stock events
        print("Step 2: Deleting all existing stock events...")
        try:
            # Get count first
            count_result = db_service.supabase.table("stock_events").select("id").execute()
            total_count = len(count_result.data) if count_result.data else 0
            
            # Delete all records (use a proper condition)
            delete_result = db_service.supabase.table("stock_events").delete().not_.is_("id", "null").execute()
            deleted_count = len(delete_result.data) if delete_result.data else total_count
            print(f"✓ Deleted {deleted_count} existing stock events")
        except Exception as delete_error:
            print(f"✗ Error deleting stock events: {delete_error}")
            raise HTTPException(status_code=500, detail=f"Failed to delete existing events: {str(delete_error)}")
        
        # Step 3: Update events for each stock
        print("Step 3: Fetching fresh events from vnstock for each stock...")
        updated_stocks = []
        failed_stocks = []
        
        for stock_symbol in stock_symbols:
            print(f"\nProcessing {stock_symbol}...")
            try:
                # Get events from vnstock
                company = Company(stock_symbol)
                events_df = company.events()
                
                if events_df is not None and not events_df.empty:
                    # Convert DataFrame to list of dictionaries
                    events_data = events_df.to_dict('records')
                    print(f"✓ Retrieved {len(events_data)} events for {stock_symbol}")
                    
                    # Update using the fixed database method
                    success = await db_service.update_company_events(stock_symbol, events_data)
                    
                    if success:
                        updated_stocks.append({
                            "symbol": stock_symbol,
                            "events_count": len(events_data),
                            "status": "success"
                        })
                        print(f"✓ Successfully updated {stock_symbol} with {len(events_data)} events")
                    else:
                        failed_stocks.append({
                            "symbol": stock_symbol,
                            "error": "Database update failed",
                            "status": "failed"
                        })
                        print(f"✗ Failed to update {stock_symbol} in database")
                else:
                    print(f"⚠️ No events found for {stock_symbol}")
                    updated_stocks.append({
                        "symbol": stock_symbol,
                        "events_count": 0,
                        "status": "no_events"
                    })
                    
            except Exception as stock_error:
                error_message = str(stock_error)
                failed_stocks.append({
                    "symbol": stock_symbol,
                    "error": error_message,
                    "status": "failed"
                })
                print(f"✗ Error processing {stock_symbol}: {error_message}")
                continue
        
        # Step 4: Summary
        total_events_added = sum(stock["events_count"] for stock in updated_stocks if "events_count" in stock)
        
        print(f"\n=== Company Events Update Summary ===")
        print(f"Stocks processed: {len(stock_symbols)}")
        print(f"Successfully updated: {len(updated_stocks)}")
        print(f"Failed updates: {len(failed_stocks)}")
        print(f"Total events added: {total_events_added}")
        
        return JSONResponse(content={
            "success": True,
            "message": f"Company events update completed. Updated {len(updated_stocks)} stocks with {total_events_added} total events.",
            "summary": {
                "total_stocks_processed": len(stock_symbols),
                "successful_updates": len(updated_stocks),
                "failed_updates": len(failed_stocks),
                "total_events_added": total_events_added,
                "deleted_old_events": deleted_count
            },
            "updated_stocks": updated_stocks,
            "failed_stocks": failed_stocks,
            "processed_symbols": stock_symbols
        })
        
    except Exception as e:
        print(f"Critical error during company events update: {e}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Company events update failed: {str(e)}")

@app.post("/company-dividends/update")
async def update_all_company_dividends(request: CompanyUpdateRequest):
    """
    Delete all stock dividends and update with fresh data from vnstock for stocks mentioned in last 30 days
    """
    try:
        from vnstock import Vnstock
        
        print("\n=== Company Dividends Manual Update Started ===")
        
        # Step 1: Get stocks mentioned in last 30 days
        print("Step 1: Getting stocks mentioned in last 30 days...")
        recent_stocks = await db_service.get_recent_stocks(days=30)
        
        if not recent_stocks:
            return JSONResponse(content={
                "success": False,
                "message": "No stocks found in the last 30 days",
                "updated_stocks": [],
                "failed_stocks": []
            })
        
        stock_symbols = [stock["symbol"] for stock in recent_stocks]
        
        # Debug mode: filter to only VIC symbol
        if request.debug:
            stock_symbols = ['VIC']
            print(f"Debug mode enabled: Processing VIC only")
        else:
            print(f"Found {len(stock_symbols)} stocks to update dividends: {', '.join(stock_symbols)}")
        
        # Step 2: Delete all existing stock dividends
        print("Step 2: Deleting all existing stock dividends...")
        try:
            # Get count first
            count_result = db_service.supabase.table("stock_dividends").select("id").execute()
            total_count = len(count_result.data) if count_result.data else 0
            
            # Delete all records
            delete_result = db_service.supabase.table("stock_dividends").delete().not_.is_("id", "null").execute()
            deleted_count = len(delete_result.data) if delete_result.data else total_count
            print(f"✓ Deleted {deleted_count} existing stock dividends")
        except Exception as delete_error:
            print(f"✗ Error deleting stock dividends: {delete_error}")
            raise HTTPException(status_code=500, detail=f"Failed to delete existing dividends: {str(delete_error)}")
        
        # Step 3: Update dividends for each stock
        print("Step 3: Fetching fresh dividends from vnstock for each stock...")
        updated_stocks = []
        failed_stocks = []
        
        for stock_symbol in stock_symbols:
            print(f"\nProcessing dividends for {stock_symbol}...")
            try:
                # Get dividends from vnstock (requires different initiation)
                company = Vnstock().stock(symbol=stock_symbol, source='TCBS').company
                dividends_df = company.dividends()
                
                if dividends_df is not None and not dividends_df.empty:
                    # Convert DataFrame to list of dictionaries
                    dividends_data = dividends_df.to_dict('records')
                    print(f"✓ Retrieved {len(dividends_data)} dividends for {stock_symbol}")
                    
                    # Update using the database method
                    success = await db_service.update_company_dividends(stock_symbol, dividends_data)
                    
                    if success:
                        updated_stocks.append({
                            "symbol": stock_symbol,
                            "dividends_count": len(dividends_data),
                            "status": "success"
                        })
                        print(f"✓ Successfully updated {stock_symbol} with {len(dividends_data)} dividends")
                    else:
                        failed_stocks.append({
                            "symbol": stock_symbol,
                            "error": "Database update failed",
                            "status": "failed"
                        })
                        print(f"✗ Failed to update {stock_symbol} in database")
                else:
                    print(f"⚠️ No dividends found for {stock_symbol}")
                    updated_stocks.append({
                        "symbol": stock_symbol,
                        "dividends_count": 0,
                        "status": "no_dividends"
                    })
                    
            except Exception as stock_error:
                error_message = str(stock_error)
                failed_stocks.append({
                    "symbol": stock_symbol,
                    "error": error_message,
                    "status": "failed"
                })
                print(f"✗ Error processing dividends for {stock_symbol}: {error_message}")
                continue
        
        # Step 4: Summary
        total_dividends_added = sum(stock["dividends_count"] for stock in updated_stocks if "dividends_count" in stock)
        
        print(f"\n=== Company Dividends Update Summary ===")
        print(f"Stocks processed: {len(stock_symbols)}")
        print(f"Successfully updated: {len(updated_stocks)}")
        print(f"Failed updates: {len(failed_stocks)}")
        print(f"Total dividends added: {total_dividends_added}")
        
        return JSONResponse(content={
            "success": True,
            "message": f"Company dividends update completed. Updated {len(updated_stocks)} stocks with {total_dividends_added} total dividends.",
            "summary": {
                "total_stocks_processed": len(stock_symbols),
                "successful_updates": len(updated_stocks),
                "failed_updates": len(failed_stocks),
                "total_dividends_added": total_dividends_added,
                "deleted_old_dividends": deleted_count
            },
            "updated_stocks": updated_stocks,
            "failed_stocks": failed_stocks,
            "processed_symbols": stock_symbols
        })
        
    except Exception as e:
        print(f"Critical error during company dividends update: {e}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Company dividends update failed: {str(e)}")


@app.post("/company-finance/update")
async def update_all_company_finance(request: CompanyUpdateRequest):
    """
    Update financial data for stocks mentioned in last 30 days using VNStock
    
    Returns:
        JSON with update results including statistics
    """
    try:
        from company_finance_updater import CompanyFinanceUpdater
        
        print("=== Starting Company Finance Update ===")
        finance_updater = CompanyFinanceUpdater()
        
        # Step 1: Get stock symbols mentioned in last 30 days
        print("Step 1: Getting stocks mentioned in last 30 days...")
        
        cutoff_date = (datetime.now() - timedelta(days=30)).date()
        mentioned_stocks_result = db_service.supabase.table("post_mentioned_stocks").select(
            "stocks(symbol)"
        ).gte("created_at", cutoff_date.isoformat()).execute()
        
        if not mentioned_stocks_result.data:
            return {
                "message": "No stocks mentioned in the last 30 days",
                "updated_stocks": [],
                "total_finance_records_added": 0
            }
        
        # Extract unique stock symbols
        stock_symbols = list(set([
            item["stocks"]["symbol"] for item in mentioned_stocks_result.data 
            if item["stocks"] and item["stocks"]["symbol"]
        ]))
        
        # Debug mode: filter to only VIC symbol
        if request.debug:
            stock_symbols = ['VIC']
            print(f"Debug mode enabled: Processing VIC only")
        else:
            print(f"Found {len(stock_symbols)} stocks to update finance data: {', '.join(stock_symbols)}")
        
        # Step 2: Update finance data for each stock
        print("Step 2: Fetching finance data from VNStock for each stock...")
        updated_stocks = []
        
        for i, stock_symbol in enumerate(stock_symbols):
            try:
                print(f"\nProcessing finance data for {stock_symbol} ({i+1}/{len(stock_symbols)})...")
                
                # Add delay between stocks to avoid rate limiting
                if i > 0:
                    print("Waiting 10 seconds between stocks to avoid rate limits...")
                    time.sleep(10)
                
                # Get comprehensive finance data with better error handling
                finance_df = finance_updater.get_company_finance_data(stock_symbol)
                
                if finance_df is not None and not finance_df.empty:
                    # Prepare data for database
                    finance_records = finance_updater.prepare_finance_data_for_db(finance_df, stock_symbol)
                    print(f"✓ Retrieved {len(finance_records)} finance records for {stock_symbol}")
                    
                    # Update database
                    success = await db_service.update_company_finance(stock_symbol, finance_records)
                    
                    if success:
                        updated_stocks.append({
                            "symbol": stock_symbol,
                            "finance_records_count": len(finance_records),
                            "status": "success"
                        })
                        print(f"✓ Successfully updated {stock_symbol} with {len(finance_records)} finance records")
                    else:
                        updated_stocks.append({
                            "symbol": stock_symbol,
                            "finance_records_count": 0,
                            "status": "failed"
                        })
                        print(f"✗ Failed to update finance data for {stock_symbol}")
                else:
                    print(f"⚠️ No finance data found for {stock_symbol}")
                    updated_stocks.append({
                        "symbol": stock_symbol,
                        "finance_records_count": 0,
                        "status": "no_data"
                    })
                
            except Exception as stock_error:
                error_message = str(stock_error)
                print(f"✗ Error processing finance data for {stock_symbol}: {error_message}")
                
                # Check if it's a rate limiting error
                if "quá nhiều request" in error_message.lower() or "rate limit" in error_message.lower():
                    print("⚠️ Rate limit detected. Waiting 30 seconds before continuing...")
                    time.sleep(30)
                    
                    # Retry once after rate limit
                    try:
                        print(f"Retrying finance data for {stock_symbol}...")
                        finance_df = finance_updater.get_company_finance_data(stock_symbol)
                        
                        if finance_df is not None and not finance_df.empty:
                            finance_records = finance_updater.prepare_finance_data_for_db(finance_df, stock_symbol)
                            success = await db_service.update_company_finance(stock_symbol, finance_records)
                            
                            if success:
                                updated_stocks.append({
                                    "symbol": stock_symbol,
                                    "finance_records_count": len(finance_records),
                                    "status": "success"
                                })
                                print(f"✓ Retry successful for {stock_symbol}")
                            else:
                                updated_stocks.append({
                                    "symbol": stock_symbol,
                                    "finance_records_count": 0,
                                    "status": "failed"
                                })
                        else:
                            updated_stocks.append({
                                "symbol": stock_symbol,
                                "finance_records_count": 0,
                                "status": "no_data"
                            })
                    except Exception as retry_error:
                        print(f"✗ Retry also failed for {stock_symbol}: {str(retry_error)}")
                        updated_stocks.append({
                            "symbol": stock_symbol,
                            "finance_records_count": 0,
                            "status": "error",
                            "error": f"Rate limit retry failed: {str(retry_error)}"
                        })
                else:
                    updated_stocks.append({
                        "symbol": stock_symbol,
                        "finance_records_count": 0,
                        "status": "error",
                        "error": error_message
                    })
        
        # Step 3: Summary
        total_finance_records_added = sum(stock["finance_records_count"] for stock in updated_stocks if "finance_records_count" in stock)
        successful_updates = len([stock for stock in updated_stocks if stock.get("status") == "success"])
        
        print(f"\n=== Company Finance Update Summary ===")
        print(f"Stocks processed: {len(stock_symbols)}")
        print(f"Successful updates: {successful_updates}")
        print(f"Total finance records added: {total_finance_records_added}")
        
        return {
            "message": f"Company finance update completed. Updated {successful_updates} stocks with {total_finance_records_added} total finance records.",
            "summary": {
                "stocks_processed": len(stock_symbols),
                "successful_updates": successful_updates,
                "total_finance_records_added": total_finance_records_added
            },
            "updated_stocks": updated_stocks
        }
        
    except Exception as e:
        print(f"Critical error during company finance update: {e}")
        import traceback
        traceback.print_exc()
        
        raise HTTPException(status_code=500, detail=f"Company finance update failed: {str(e)}")


@app.get("/company-update", response_class=HTMLResponse)
async def company_update_page():
    """Company Update page for manual data updates"""
    try:
        with open("static/company-update.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        # Return a simple HTML if file doesn't exist yet
        return """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Company Update - Vietnamese Stock Analysis</title>
        </head>
        <body>
            <h1>Company Update Page</h1>
            <p>Company Update page is being developed. Please check back later.</p>
            <a href="/">← Back to Home</a>
        </body>
        </html>
        """

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.get("/test-date-logic")
async def test_date_logic(days: int = 1):
    """Test endpoint to verify date logic fix"""
    today = datetime.now().date()
    target_date_ago = today - timedelta(days=days)
    
    # Test if a post from August 1st would be included when crawling "last 1 days" on August 2nd
    test_post_date = datetime(2025, 8, 1, 14, 30)
    would_be_included = test_post_date.date() >= target_date_ago
    
    return {
        "today": today.isoformat(),
        "days_requested": days,
        "cutoff_date": target_date_ago.isoformat(),
        "test_post_date": test_post_date.date().isoformat(),
        "would_be_included": would_be_included,
        "fix_working": would_be_included if days == 1 else "N/A"
    }


# Math Game Endpoints for Kids
class MathQuestion(BaseModel):
    question: str
    answer: int
    options: List[int]

class MathGameRequest(BaseModel):
    max_number: int

class MathGameResponse(BaseModel):
    questions: List[MathQuestion]

class MathAnswerRequest(BaseModel):
    answers: List[int]
    correct_answers: List[int]

class MathAnswerResponse(BaseModel):
    score: int
    total: int
    percentage: float
    message: str

@app.get("/testqr", response_class=HTMLResponse)
async def test_qr_camera():
    """QR camera test endpoint with adjustable square box"""
    with open("static/qr_camera.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.get("/math", response_class=HTMLResponse)
async def math_game():
    """Hidden math game for kids"""
    with open("static/math_game.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.post("/math/generate", response_model=MathGameResponse)
async def generate_math_questions(request: MathGameRequest):
    """Generate 10 random math questions"""
    questions = []
    max_num = min(request.max_number, 100)  # Cap at 100 for safety
    
    for _ in range(10):
        # Randomly choose between addition and subtraction
        operation = random.choice(['+', '-'])
        
        if operation == '+':
            # For addition, ensure sum doesn't exceed max_number
            num1 = random.randint(1, max_num // 2)
            num2 = random.randint(1, max_num - num1)
            answer = num1 + num2
            question = f"{num1} + {num2} = ?"
        else:
            # For subtraction, ensure positive result
            num1 = random.randint(2, max_num)
            num2 = random.randint(1, num1)
            answer = num1 - num2
            question = f"{num1} - {num2} = ?"
        
        # Generate wrong options
        wrong_options = []
        while len(wrong_options) < 3:
            wrong = answer + random.randint(-10, 10)
            if wrong != answer and wrong >= 0 and wrong not in wrong_options:
                wrong_options.append(wrong)
        
        # Create options list with correct answer
        options = [answer] + wrong_options
        random.shuffle(options)
        
        questions.append(MathQuestion(
            question=question,
            answer=answer,
            options=options
        ))
    
    return MathGameResponse(questions=questions)

@app.post("/math/check", response_model=MathAnswerResponse)
async def check_math_answers(request: MathAnswerRequest):
    """Check answers and provide motivational message"""
    correct_count = sum(1 for user_ans, correct_ans in zip(request.answers, request.correct_answers) 
                       if user_ans == correct_ans)
    total = len(request.correct_answers)
    percentage = (correct_count / total) * 100
    
    # Motivational messages based on score
    if percentage == 100:
        message = "🌟 Perfect! You're a math superstar! 🌟"
    elif percentage >= 80:
        message = "🎉 Excellent work! You're amazing at math! 🎉"
    elif percentage >= 60:
        message = "👍 Great job! Keep practicing and you'll be even better! 👍"
    elif percentage >= 40:
        message = "💪 Good effort! Practice makes perfect! 💪"
    else:
        message = "🌈 Don't worry! Every mathematician started somewhere. Try again! 🌈"
    
    return MathAnswerResponse(
        score=correct_count,
        total=total,
        percentage=percentage,
        message=message
    )

# Log File Download Endpoints
@app.get("/logs/list")
async def list_log_files():
    """List all available log files"""
    try:
        logs_data = {
            "debug_logs": [],
            "holistic_analysis_logs": [],
            "log_directories": []
        }
        
        # Check if logs directories exist
        debug_dir = Path("logs/debug")
        holistic_dir = Path("logs/holistic_analysis")
        
        if debug_dir.exists():
            logs_data["log_directories"].append("debug")
            # List debug log files
            for log_file in sorted(debug_dir.glob("*.json"), key=os.path.getmtime, reverse=True):
                file_stats = log_file.stat()
                logs_data["debug_logs"].append({
                    "filename": log_file.name,
                    "path": str(log_file),
                    "size_bytes": file_stats.st_size,
                    "modified": datetime.fromtimestamp(file_stats.st_mtime).isoformat(),
                    "download_url": f"/logs/download/debug/{log_file.name}"
                })
        
        if holistic_dir.exists():
            logs_data["log_directories"].append("holistic_analysis")
            # List holistic analysis log files
            for log_file in sorted(holistic_dir.glob("*.json"), key=os.path.getmtime, reverse=True):
                file_stats = log_file.stat()
                logs_data["holistic_analysis_logs"].append({
                    "filename": log_file.name,
                    "path": str(log_file),
                    "size_bytes": file_stats.st_size,
                    "modified": datetime.fromtimestamp(file_stats.st_mtime).isoformat(),
                    "download_url": f"/logs/download/holistic_analysis/{log_file.name}"
                })
        
        return JSONResponse(content=logs_data)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing log files: {str(e)}")

@app.get("/logs/download/{log_type}/{filename}")
async def download_log_file(log_type: str, filename: str):
    """Download a specific log file"""
    try:
        # Validate log_type
        if log_type not in ["debug", "holistic_analysis"]:
            raise HTTPException(status_code=400, detail="Invalid log type. Use 'debug' or 'holistic_analysis'")
        
        # Construct file path
        file_path = Path(f"logs/{log_type}/{filename}")
        
        # Security check - ensure file is within logs directory
        if not str(file_path.resolve()).startswith(str(Path("logs").resolve())):
            raise HTTPException(status_code=400, detail="Invalid file path")
        
        # Check if file exists
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Log file not found")
        
        # Return file
        return FileResponse(
            path=str(file_path),
            filename=filename,
            media_type="application/json"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error downloading log file: {str(e)}")

@app.get("/logs/latest/{log_type}")
async def get_latest_log(log_type: str):
    """Get the content of the latest log file"""
    try:
        # Validate log_type
        if log_type not in ["debug", "holistic_analysis"]:
            raise HTTPException(status_code=400, detail="Invalid log type. Use 'debug' or 'holistic_analysis'")
        
        # Find latest JSON file
        log_dir = Path(f"logs/{log_type}")
        if not log_dir.exists():
            raise HTTPException(status_code=404, detail=f"Log directory '{log_type}' not found")
        
        json_files = list(log_dir.glob("*.json"))
        if not json_files:
            raise HTTPException(status_code=404, detail=f"No JSON log files found in '{log_type}' directory")
        
        # Get latest file by modification time
        latest_file = max(json_files, key=os.path.getmtime)
        
        # Read and return content
        with open(latest_file, 'r', encoding='utf-8') as f:
            content = json.load(f)
        
        return {
            "filename": latest_file.name,
            "file_path": str(latest_file),
            "file_size": latest_file.stat().st_size,
            "modified": datetime.fromtimestamp(latest_file.stat().st_mtime).isoformat(),
            "content": content
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading latest log: {str(e)}")

@app.get("/logs/browser", response_class=HTMLResponse)
async def log_browser():
    """Simple HTML interface to browse and download logs"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Stock Bot - Log Browser</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .log-section { margin-bottom: 30px; border: 1px solid #ddd; padding: 15px; }
            .log-file { margin: 10px 0; padding: 10px; background: #f5f5f5; border-radius: 4px; }
            .download-btn { background: #007bff; color: white; padding: 5px 10px; text-decoration: none; border-radius: 3px; margin-right: 10px; }
            .view-btn { background: #28a745; color: white; padding: 5px 10px; text-decoration: none; border-radius: 3px; }
            .file-info { color: #666; font-size: 0.9em; }
        </style>
    </head>
    <body>
        <h1>Stock Bot - Log Browser</h1>
        <div id="logs-container">Loading logs...</div>
        
        <script>
            async function loadLogs() {
                try {
                    const response = await fetch('/logs/list');
                    const data = await response.json();
                    
                    let html = '';
                    
                    // Debug logs section
                    if (data.debug_logs.length > 0) {
                        html += '<div class="log-section"><h2>Debug Logs</h2>';
                        data.debug_logs.forEach(log => {
                            html += `
                                <div class="log-file">
                                    <strong>${log.filename}</strong>
                                    <div class="file-info">
                                        Size: ${(log.size_bytes / 1024).toFixed(1)} KB | 
                                        Modified: ${new Date(log.modified).toLocaleString()}
                                    </div>
                                    <a href="${log.download_url}" class="download-btn">Download</a>
                                    <a href="/logs/latest/debug" class="view-btn" target="_blank">View Latest</a>
                                </div>
                            `;
                        });
                        html += '</div>';
                    }
                    
                    // Holistic analysis logs section  
                    if (data.holistic_analysis_logs.length > 0) {
                        html += '<div class="log-section"><h2>Holistic Analysis Logs</h2>';
                        data.holistic_analysis_logs.forEach(log => {
                            html += `
                                <div class="log-file">
                                    <strong>${log.filename}</strong>
                                    <div class="file-info">
                                        Size: ${(log.size_bytes / 1024).toFixed(1)} KB | 
                                        Modified: ${new Date(log.modified).toLocaleString()}
                                    </div>
                                    <a href="${log.download_url}" class="download-btn">Download</a>
                                    <a href="/logs/latest/holistic_analysis" class="view-btn" target="_blank">View Latest</a>
                                </div>
                            `;
                        });
                        html += '</div>';
                    }
                    
                    if (data.debug_logs.length === 0 && data.holistic_analysis_logs.length === 0) {
                        html = '<p>No log files found. Run some crawl operations to generate logs.</p>';
                    }
                    
                    document.getElementById('logs-container').innerHTML = html;
                    
                } catch (error) {
                    document.getElementById('logs-container').innerHTML = `<p>Error loading logs: ${error.message}</p>`;
                }
            }
            
            loadLogs();
            
            // Auto-refresh every 30 seconds
            setInterval(loadLogs, 30000);
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

if __name__ == "__main__":
    import uvicorn
    import os
    
    # Get port from environment, default to 8000 for local development
    port = int(os.environ.get("PORT", 8000))
    
    print(f"Starting server on host=0.0.0.0, port={port}")
    print(f"Environment check:")
    print(f"- SUPABASE_URL: {'SET' if os.getenv('SUPABASE_URL') else 'NOT SET'}")
    print(f"- SUPABASE_SERVICE_ROLE_KEY: {'SET' if os.getenv('SUPABASE_SERVICE_ROLE_KEY') else 'NOT SET'}")
    print(f"- GEMINI_API_KEY: {'SET' if os.getenv('GEMINI_API_KEY') else 'NOT SET'}")
    
    try:
        uvicorn.run(app, host="0.0.0.0", port=port)
    except Exception as e:
        print(f"Failed to start server: {e}")
        raise