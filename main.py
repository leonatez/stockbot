from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, HTMLResponse
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
            driver = uc.Chrome(options=options, version_main=137)
            print("Chrome driver created successfully with version 137!")
        except Exception as e:
            print(f"Version 137 failed: {e}")
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
            
            driver = uc.Chrome(options=options, version_main=137)
            print("Chrome driver created with minimal headless options and version 137!")
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
    """Get a driver from the pool or create a new one"""
    with driver_lock:
        try:
            driver = driver_pool.get_nowait()
            # Check if driver is still alive
            try:
                driver.current_url
                return driver
            except Exception:
                # Driver is dead, create a new one
                try:
                    driver.quit()
                except:
                    pass
                return create_stealth_driver()
        except queue.Empty:
            return create_stealth_driver()

def return_driver(driver):
    """Return a driver to the pool"""
    if driver:
        with driver_lock:
            if driver_pool.qsize() < MAX_DRIVERS:
                driver_pool.put(driver)
            else:
                try:
                    driver.quit()
                except:
                    pass

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

class MultipleCrawlRequest(BaseModel):
    sources: List[CrawlRequest]
    days: Optional[int] = 3  # Default to 3 days if not specified

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

async def crawl_posts(request: CrawlRequest, days: int = 3) -> tuple[List[dict], int]:
    """Crawl posts and return those within specified days using Selenium"""
    collected_posts = []
    total_posts_found = 0
    page = 1
    
    # Use date-only comparison to include entire days
    target_date_ago = (datetime.now().date() - timedelta(days=days))
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
                        continue
                    
                    print(f"✓ Post not in database, fetching fresh content from: {post_url}")
                    
                    # Longer delay before fetching individual posts
                    human_like_delay()
                    
                    post_tree = get_page_content_with_selenium(post_url)
                    if post_tree:
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
    try:
        print(f"\n=== Received Request ===")
        print(f"Raw request: {request}")
        print(f"Request dict: {request.dict()}")
        
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
        collected_posts, total_posts_found = await crawl_posts(request, days=3)
        
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
                    # Analyze individual post with Gemini
                    gemini_result = analyze_individual_post_with_gemini(post['content'])
                    
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
                            await db_service.save_post_with_analysis(post, source_id, mentioned_stocks_data, post_summary)
                            print(f"✓ Post and analysis saved to database")
                        except Exception as db_error:
                            print(f"✗ Error saving to database: {db_error}")
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
        
        return JSONResponse(content=response_data)
        
    except Exception as e:
        print(f"Error during crawling: {e}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Crawling failed: {str(e)}")


def analyze_individual_post_with_gemini(content: str) -> Dict:
    """
    Analyze individual post content with Gemini to extract both post summary and stock mentions
    """
    if not model or not content.strip():
        print("Gemini model not available or no content to analyze")
        return {"post_summary": "", "mentioned_stocks": []}
    
    try:
        prompt = f"""
        You are a Vietnamese stock investment consultant. Analyze the following financial news content.
        
        Provide your analysis in this EXACT JSON format:
        {{
            "post_summary": "Brief summary of the main points of this financial news article in Vietnamese (2-3 sentences)",
            "mentioned_stocks": [
                {{
                    "stock_symbol": "SYMBOL",
                    "sentiment": "positive/negative/neutral", 
                    "summary": "How this stock was mentioned and what affects it"
                }}
            ]
        }}
        
        Rules:
        1. post_summary: Summarize the key financial news in Vietnamese (2-3 sentences)
        2. mentioned_stocks: Only include actual Vietnamese stock symbols (HPG, VPB, ACB, etc.)
        3. sentiment: Determine if the news is positive, negative, or neutral for each stock
        4. summary: Brief explanation of how the stock was mentioned
        5. Return ONLY valid JSON, no other text
        6. If no stocks mentioned, use empty array for mentioned_stocks
        7. Always write in Vietnamese
        
        Content to analyze:
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
                        print(f"✓ Successfully parsed post analysis with {len(analysis_result['mentioned_stocks'])} stocks")
                        return analysis_result
                    else:
                        print("✗ Invalid JSON structure from Gemini")
                        return {"post_summary": "Analysis completed", "mentioned_stocks": []}
                else:
                    print("✗ No JSON object found in Gemini response")
                    return {"post_summary": "Analysis completed", "mentioned_stocks": []}
                    
            except json.JSONDecodeError as e:
                print(f"✗ Failed to parse JSON from Gemini response: {e}")
                print(f"Raw response: {response_text[:300]}...")
                return {"post_summary": "Analysis completed", "mentioned_stocks": []}
        else:
            print("✗ No valid response from Gemini")
            return {"post_summary": "", "mentioned_stocks": []}
            
    except Exception as e:
        print(f"✗ Error calling Gemini API for individual post: {e}")
        return {"post_summary": "Analysis failed", "mentioned_stocks": []}


@app.post("/crawl-multiple")
async def crawl_multiple_endpoints(request: MultipleCrawlRequest):
    """Crawl posts from multiple URLs and return aggregated stock analysis"""
    start_time = time.time()
    
    try:
        print(f"\n=== Received Multiple Sources Request ===")
        print(f"Number of sources: {len(request.sources)}")
        print(f"Crawl days: {request.days}")
        for i, source in enumerate(request.sources, 1):
            print(f"Source {i}: {source.sourceName} ({source.sourceType}) - {source.url}")
        
        # Perform daily VN30 update at the start of multiple source analysis
        print(f"\n=== Daily VN30 Update ===")
        vn30_success = daily_vn30_update()
        if vn30_success:
            print("✓ VN30 update completed successfully")
        else:
            print("⚠️ VN30 update had issues, continuing with analysis...")
        
        # Initialize aggregated data structures
        all_processed_posts = []
        combined_stock_mentions = defaultdict(lambda: {
            'post_details': [],
            'sentiments': [],
            'summaries': [],
            'sources': set()  # Track which sources mention this stock
        })
        
        successful_sources = 0
        failed_sources = []
        
        # Process each source
        for i, source_request in enumerate(request.sources, 1):
            print(f"\n{'='*60}")
            print(f"=== Processing Source {i}/{len(request.sources)}: {source_request.sourceName} ===")
            print(f"{'='*60}")
            
            try:
                # Get or create source in database
                source_in_db = await db_service.get_source_by_url(source_request.url)
                if not source_in_db:
                    print(f"Source not found in database, creating new source: {source_request.sourceName}")
                    source_id = await db_service.save_source(source_request.dict())
                else:
                    source_id = source_in_db['id']
                    print(f"Using existing source from database: {source_in_db['name']}")
                
                # Crawl posts from this source
                collected_posts, total_posts_found = await crawl_posts(source_request, days=request.days)
                
                print(f"Source {i} - Posts found: {total_posts_found}, Posts within {request.days} days: {len(collected_posts)}")
                
                # Process each post from this source
                for j, post in enumerate(collected_posts, 1):
                    print(f"\n--- Processing Post {j}/{len(collected_posts)} from {source_request.sourceName} ---")
                    print(f"URL: {post['url']}")
                    print(f"Date: {post['date']}")
                    print(f"Content preview: {post['content'][:200]}...")
                    
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
                            # Analyze individual post with Gemini
                            gemini_result = analyze_individual_post_with_gemini(post['content'])
                            
                            # Handle different response formats from Gemini
                            mentioned_stocks_data = []
                            if isinstance(gemini_result, dict) and 'mentioned_stocks' in gemini_result:
                                mentioned_stocks_data = gemini_result['mentioned_stocks']
                            elif isinstance(gemini_result, list):
                                mentioned_stocks_data = gemini_result
                            
                            print(f"DEBUG: Multi-source Gemini result type: {type(gemini_result)}")
                            print(f"DEBUG: Multi-source Gemini result: {gemini_result}")
                            print(f"DEBUG: Multi-source mentioned_stocks_data: {mentioned_stocks_data}")
                            
                            # Create post object with source information
                            post_object = {
                                "url": post['url'],
                                "type": source_request.sourceType,
                                "createdDate": post['date'],
                                "content": post['content'],
                                "summary": gemini_result.get('post_summary', '') if isinstance(gemini_result, dict) else '',
                                "mentionedStocks": [],
                                "source_name": source_request.sourceName,
                                "source_type": source_request.sourceType
                            }
                            
                            # Save new post and analysis to database
                            if mentioned_stocks_data:
                                print(f"DEBUG: Multi-source attempting to save post to database with {len(mentioned_stocks_data)} stocks")
                                try:
                                    post_summary = gemini_result.get('post_summary', '') if isinstance(gemini_result, dict) else ''
                                    await db_service.save_post_with_analysis(post, source_id, mentioned_stocks_data, post_summary)
                                    print(f"✓ Post and analysis saved to database")
                                except Exception as db_error:
                                    print(f"✗ Error saving to database: {db_error}")
                            else:
                                print(f"DEBUG: Multi-source no stocks found in analysis, skipping database save")
                            
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
                                    
                                    # Aggregate at stock level across all sources
                                    combined_stock_mentions[stock_symbol]['post_details'].append({
                                        'url': post['url'],
                                        'date': post['date'],
                                        'sentiment': sentiment,
                                        'summary': stock_summary,
                                        'post_summary': post_object['summary'],
                                        'source_name': source_request.sourceName,
                                        'source_type': source_request.sourceType
                                    })
                                    combined_stock_mentions[stock_symbol]['sentiments'].append(sentiment)
                                    combined_stock_mentions[stock_symbol]['summaries'].append(stock_summary)
                                    combined_stock_mentions[stock_symbol]['sources'].add(source_request.sourceName)
                        
                        all_processed_posts.append(post_object)
                        
                        print(f"✓ Post {j} processed - Found {len(post_object['mentionedStocks'])} stocks")
                        for stock in post_object['mentionedStocks']:
                            print(f"  - {stock['stock_symbol']}: {stock['sentiment']}")
                        
                    except Exception as e:
                        print(f"✗ Error analyzing post {j} from {source_request.sourceName}: {e}")
                        # Create post object without analysis
                        post_object = {
                            "url": post['url'],
                            "type": source_request.sourceType,
                            "createdDate": post['date'],
                            "content": post['content'],
                            "summary": "Analysis failed",
                            "mentionedStocks": [],
                            "source_name": source_request.sourceName,
                            "source_type": source_request.sourceType
                        }
                        all_processed_posts.append(post_object)
                        continue
                
                successful_sources += 1
                print(f"✓ Source {i} ({source_request.sourceName}) completed successfully")
                
            except Exception as e:
                print(f"✗ Error processing source {i} ({source_request.sourceName}): {e}")
                failed_sources.append({
                    'source_name': source_request.sourceName,
                    'error': str(e)
                })
                continue
        
        # Create aggregated stock analysis across all sources
        aggregated_stock_analysis = []
        for stock_symbol, data in combined_stock_mentions.items():
            # Calculate overall sentiment (majority wins)
            sentiment_counts = defaultdict(int)
            for sentiment in data['sentiments']:
                sentiment_counts[sentiment.lower()] += 1
            
            overall_sentiment = max(sentiment_counts.items(), key=lambda x: x[1])[0] if sentiment_counts else 'neutral'
            
            # Combine all summaries about this stock
            combined_summary = '. '.join(filter(None, data['summaries']))
            if len(combined_summary) > 500:  # Truncate if too long
                combined_summary = combined_summary[:500] + "..."
            
            # Create aggregated stock analysis object
            stock_analysis = {
                "stock_symbol": stock_symbol,
                "mentioned_count": len(data['post_details']),  # Total posts mentioning this stock
                "overall_sentiment": overall_sentiment,
                "stock_summary": combined_summary,
                "post_details": data['post_details'],  # All posts from all sources
                "sources_count": len(data['sources']),  # How many different sources mention this stock
                "sources": list(data['sources'])  # Which sources mention this stock
            }
            aggregated_stock_analysis.append(stock_analysis)
        
        # Sort by mention count (most mentioned first)
        aggregated_stock_analysis.sort(key=lambda x: x['mentioned_count'], reverse=True)
        
        # Calculate execution time
        end_time = time.time()
        execution_duration = f"{end_time - start_time:.2f}s"
        
        print(f"\n{'='*60}")
        print(f"=== MULTI-SOURCE ANALYSIS SUMMARY ===")
        print(f"{'='*60}")
        print(f"Sources processed: {successful_sources}/{len(request.sources)}")
        print(f"Total posts analyzed: {len(all_processed_posts)}")
        print(f"Unique stocks found: {len(aggregated_stock_analysis)}")
        print(f"Execution time: {execution_duration}")
        
        if failed_sources:
            print(f"\nFailed sources:")
            for failed in failed_sources:
                print(f"  - {failed['source_name']}: {failed['error']}")
        
        print(f"\nTop stocks by mention count:")
        for stock in aggregated_stock_analysis[:5]:  # Show top 5
            print(f"  - {stock['stock_symbol']}: {stock['mentioned_count']} mentions from {stock['sources_count']} sources")
            print(f"    Overall sentiment: {stock['overall_sentiment']}")
            print(f"    Sources: {', '.join(stock['sources'])}")
        
        # Create comprehensive JSON response
        response_data = {
            "posts": all_processed_posts,
            "stock_analysis": aggregated_stock_analysis,
            "metadata": {
                "sources_requested": len(request.sources),
                "sources_analyzed": successful_sources,
                "sources_failed": len(failed_sources),
                "failed_sources": failed_sources,
                "total_posts_analyzed": len(all_processed_posts),
                "unique_stocks_found": len(aggregated_stock_analysis),
                "analysis_duration": execution_duration,
                "success_rate": f"{(successful_sources/len(request.sources)*100):.1f}%" if request.sources else "0%",
                "crawl_timestamp": datetime.now().isoformat(),
                "source_breakdown": [
                    {
                        "source_name": source.sourceName,
                        "source_type": source.sourceType,
                        "posts_count": len([p for p in all_processed_posts if p.get('source_name') == source.sourceName])
                    }
                    for source in request.sources
                ]
            }
        }
        
        print(f"\n=== Final Response Summary ===")
        print(f"Posts processed: {len(all_processed_posts)}")
        print(f"Unique stocks found: {len(aggregated_stock_analysis)}")
        print(f"Response structure: {list(response_data.keys())}")
        
        # Update stock prices for mentioned stocks
        if aggregated_stock_analysis:
            print(f"\n=== Updating Stock Prices ===")
            try:
                price_update_results = update_mentioned_stocks_prices(aggregated_stock_analysis)
                print(f"✓ Price update completed for {len(price_update_results)} stocks")
            except Exception as price_error:
                print(f"⚠️ Error updating stock prices: {price_error}")
                # Continue with response even if price update fails
            
            # Update company information for mentioned stocks
            print(f"\n=== Updating Company Information ===")
            try:
                mentioned_symbols = [stock["stock_symbol"] for stock in aggregated_stock_analysis]
                company_update_results = await update_company_information(mentioned_symbols)
                successful_updates = sum(1 for success in company_update_results.values() if success)
                print(f"✓ Company info update completed for {successful_updates}/{len(mentioned_symbols)} stocks")
            except Exception as company_error:
                print(f"⚠️ Error updating company information: {company_error}")
                # Continue with response even if company update fails
        
        return JSONResponse(content=response_data)
        
    except Exception as e:
        print(f"Critical error during multiple source crawling: {e}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Multiple source crawling failed: {str(e)}")


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

@app.get("/stock-prices/{symbol}")
async def get_stock_prices(symbol: str, period: str = "1m"):
    """
    Get stock price data for charting.
    
    Args:
        symbol: Stock symbol (e.g., ACB, HPG)
        period: Time period - "1m", "3m", "1y" (1 month, 3 months, 1 year)
    
    Returns:
        JSON with price data and chart configuration
    """
    try:
        from datetime import datetime, timedelta
        
        # Calculate date range based on period
        today = datetime.now().date()
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
            raise HTTPException(status_code=400, detail="Invalid period. Use '1m', '3m', or '1y'")
        
        # Get stock info and price data
        stock_result = db_service.supabase.table("stocks").select("id, symbol, organ_name, exchange, isvn30").eq("symbol", symbol).execute()
        
        if not stock_result.data:
            raise HTTPException(status_code=404, detail=f"Stock {symbol} not found")
        
        stock_info = stock_result.data[0]
        stock_id = stock_info["id"]
        
        # Get price data
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
        
        # Format data for Chart.js
        chart_data = {
            "labels": [record["date"] for record in price_result.data],
            "datasets": [{
                "label": f"{symbol} Price",
                "data": [float(record["close"]) for record in price_result.data],
                "borderColor": "rgb(59, 130, 246)",
                "backgroundColor": "rgba(59, 130, 246, 0.1)",
                "borderWidth": 2,
                "fill": True,
                "tension": 0.1
            }]
        }
        
        # Chart configuration
        chart_config = {
            "type": "line",
            "data": chart_data,
            "options": {
                "responsive": True,
                "maintainAspectRatio": False,
                "scales": {
                    "y": {
                        "beginAtZero": False,
                        "title": {
                            "display": True,
                            "text": "Price (VND)"
                        }
                    },
                    "x": {
                        "title": {
                            "display": True,
                            "text": "Date"
                        }
                    }
                },
                "plugins": {
                    "title": {
                        "display": True,
                        "text": f"{symbol} - {period_label} Price Trend"
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
    """Root endpoint that returns the index.html page"""
    with open("static/index.html", "r", encoding="utf-8") as f:
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
async def update_all_company_info():
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
async def update_industries_table():
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
async def update_stock_prices_manual():
    """Manual update of stock prices for stocks mentioned in last 7 days"""
    try:
        # Get all stocks mentioned in last 7 days
        print("Getting stocks mentioned in last 7 days...")
        mentioned_stocks = await db_service.get_stocks_mentioned_in_last_n_days(7)
        
        if not mentioned_stocks:
            return JSONResponse(content={
                "success": False,
                "message": "No stocks found mentioned in last 7 days"
            })
        
        print(f"Found {len(mentioned_stocks)} stocks mentioned in last 7 days")
        
        # Import the stock price updater
        from stock_price_updater import update_stock_prices_selective
        
        # Update prices only for stocks that need updates
        result = update_stock_prices_selective(mentioned_stocks)
        
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

@app.post("/company-events/update")
async def update_all_company_events():
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
async def update_all_company_dividends():
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