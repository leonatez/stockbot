# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a FastAPI-based Vietnamese stock analysis crawler that scrapes financial news from multiple sources and uses Google's Gemini AI to extract stock mentions and sentiment analysis. The application provides both single-source and multi-source crawling capabilities with a web interface.

## Key Architecture Components

### Core Application (`main.py`)
- **FastAPI server** with CORS middleware serving on port 8000
- **Driver Pool Management**: Thread-safe Chrome WebDriver pool (max 3 drivers) for concurrent web scraping
- **Stealth Crawling**: Uses `undetected-chromedriver` with extensive anti-detection measures
- **Multi-tool Agent Integration**: Uses Google ADK agents for weather/time queries in development

### AI Analysis (`multi_tool_agent/agent.py`)
- **Gemini Integration**: Uses `gemini-2.5-pro` model for Vietnamese stock analysis
- **Stock Sentiment Analysis**: Extracts stock symbols, sentiment, and summaries from Vietnamese financial news
- **JSON Response Processing**: Handles Gemini API responses with robust error handling

### Web Interface (`static/index.html`)
- **Multi-source Configuration**: Dynamic form for adding multiple crawling sources
- **Stock-level Results**: Aggregates analysis across all sources by stock symbol
- **Real-time UI Updates**: Shows crawling progress and comprehensive results

## Common Development Commands

### Running the Application
```bash
# Start the FastAPI server
python main.py

# Access the web interface at http://localhost:8000
```

### Testing
```bash
# Run unit tests
python unittest.py

# Test Gemini integration individually
python multi_tool_agent/agent.py

# Test database integration
python test_database.py
```

### Environment Setup
- Create `.env` file with `GEMINI_API_KEY=your_api_key`
- Create `.env` file with `SUPABASE_URL=your_supabase_url`
- Create `.env` file with `SUPABASE_KEY=your_supabase_key`
- Create `.env` file with `SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key`
- Chrome/Chromium browser required for web scraping
- Dependencies: FastAPI, Selenium, undetected-chromedriver, Google Generative AI, lxml, BeautifulSoup

## API Endpoints

### Core Endpoints
- `POST /crawl` - Single source crawling and analysis (with database integration)
- `POST /crawl-multiple` - Multi-source aggregated analysis (primary endpoint)
- `GET /` - Web interface
- `GET /health` - Health check

### Database Management Endpoints
- `POST /sources` - Save source configuration to database
- `GET /sources` - Retrieve all active sources from database
- `GET /dashboard/stats` - Get dashboard statistics from database views

## Data Flow (Database-Integrated)

1. **Daily VN30 Update**:
   - At the start of each analysis task, system fetches current VN30 stocks using vnstock
   - Updates `isvn30` column in stocks table to reflect current VN30 membership
   - Ensures VN30 status is always current for analysis and reporting

2. **Source Configuration**: 
   - Users define XPath selectors for post links, content, and dates
   - Source configurations are saved to `sources` table in Supabase
   
3. **Smart Crawling with Deduplication**:
   - System checks database before crawling each post URL
   - If post exists: retrieves existing analysis from database (no re-crawling)
   - If post is new: crawls content using Selenium with anti-detection measures
   
4. **Content Processing**:
   - XPath-based extraction with text cleaning for LLM processing
   - Only new posts are sent to Gemini for analysis
   
5. **AI Analysis & Database Storage**:
   - Gemini analyzes new posts for Vietnamese stock mentions and sentiment
   - Results saved to database tables: `posts`, `post_mentioned_stocks`, `stocks`, `stock_daily_sentiment`
   - Automatic stock creation for new symbols discovered
   - Daily sentiment aggregation per stock

6. **Automatic Stock Price Updates**:
   - After AI analysis identifies mentioned stocks, system automatically fetches their price history
   - Optimized queries: only fetches data from latest date in database to today
   - Saves price data (OHLCV) to `stock_prices` table with upsert handling
   - Ensures price data is current for all mentioned stocks
   
7. **Response Generation**:
   - Combines existing database data with new analysis results
   - Returns JSON response with both post-level and stock-level analysis
   - Stock price data is available for further analysis and charting

##Other documentation
1. Database schema: We use Supabase as our database. The schema can be found in `schema.md'
2. Available supabase views: We have some views in supabase to help us analyze the data. The views can be found in `views.md'. You can update this document when you add new or adjust existing views.
## Vietnamese Stock Analysis

The system is specifically designed for Vietnamese financial markets:
- Targets Vietnamese stock symbols (HPG, ACB, LDG, etc.)
- Uses Vietnamese-language prompts for Gemini
- Handles Vietnamese date formats (DD/MM/YYYY)
- Provides sentiment analysis in Vietnamese context

## WebDriver Configuration

The application uses sophisticated anti-detection measures:
- Headless Chrome with randomized user agents and window sizes
- Disabled automation indicators and webdriver properties  
- Memory optimization for server deployment
- Automatic driver pool management with cleanup

## Test Configuration

The `test_helper.txt` file contains JavaScript snippets for configuring crawling sources like ABS and ACBS financial websites, including their specific XPath selectors for posts, content, and dates.

### VNSTOCK library

Whenever we need functions related to stock info like getting company profile, prices, etc. we will use VNStock. Refer to vnstock.md to use pre-defined functions there 