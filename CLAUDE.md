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

### Company Data Management Endpoints
- `POST /company-info/update` - Manual Company Info Update: Updates stock records with ICB codes and company information from VNStock
- `POST /company-events/update` - Delete all stock events and update with fresh data from vnstock for stocks mentioned in last 30 days
- `POST /company-dividends/update` - Delete all stock dividends and update with fresh data from vnstock for stocks mentioned in last 30 days
- `POST /industries/update` - Update industries table with data from VNStock industries_icb() function

## Data Flow (Enhanced Multi-Source Analysis)

### Core Analysis Flow

1. **Daily VN30 Update**:
   - At the start of each analysis task, system fetches current VN30 stocks using vnstock
   - Updates `isvn30` column in stocks table to reflect current VN30 membership
   - Ensures VN30 status is always current for analysis and reporting

2. **Multi-Source Configuration**: 
   - Users configure three types of sources: Company, Industry, and Macro Economy
   - Source configurations saved to `sources` table with `source_type` field
   - Each source type requires different XPath selectors for content extraction
   
3. **Smart Crawling with Deduplication**:
   - System checks database before crawling each post URL
   - If post exists: retrieves existing analysis from database (no re-crawling)
   - If post is new: crawls content using Selenium with anti-detection measures
   
4. **Content Processing by Source Type**:
   - **Company Posts**: Analyzed for individual stock mentions and sentiment
   - **Industry Posts**: Analyzed for industry trends and sentiment using ICB codes
   - **Macro Posts**: Analyzed for macro economic themes and indicators
   - XPath-based extraction with text cleaning for LLM processing

5. **Enhanced AI Analysis & Database Storage**:
   - **Stock Analysis**: Gemini analyzes company posts for Vietnamese stock mentions and sentiment
   - **Industry Analysis**: Gemini extracts mentioned industries (using VNStock ICB codes) with sentiment
   - **Macro Analysis**: Gemini identifies macro themes and extracts economic indicators
   - Results saved to respective tables: `posts`, `post_mentioned_stocks`, `post_mentioned_industries`, `post_mentioned_macro_themes`, `post_macro_indicators`
   - Automatic stock/industry/theme creation for new symbols discovered
   - Daily sentiment aggregation per stock, industry, and macro theme

### Contextual Enhancement Flow

6. **Industry Context Integration**:
   - For each mentioned stock, system maps to relevant industries using ICB codes
   - Searches industry posts from last 7 days for contextual sentiment
   - Combines industry trends with direct stock mentions for holistic analysis

7. **Macro Economic Context**:
   - For analysis dates, system searches macro economy posts from last 3 days
   - Extracts macro themes (market liquidity, global uncertainty, etc.) and indicators
   - Provides macro economic backdrop for stock analysis decisions

8. **Automatic Stock Price & Company Updates**:
   - After AI analysis identifies mentioned stocks, system automatically fetches their price history
   - Updates company information including ICB codes from VNStock
   - Optimized queries: only fetches data from latest date in database to today
   - Saves data to `stock_prices`, updates `stocks` table with company info
   - Ensures price data is current for all mentioned stocks
   
9. **Comprehensive Response Generation**:
   - **Stock-Level Analysis**: Direct mentions + industry context + macro context
   - **Contextual Factors**: Related industry sentiment and macro environment
   - **Progress Tracking**: Real-time progress updates during analysis
   - Returns enhanced JSON response with multi-dimensional analysis results

## Enhanced Database Schema

### New Tables for Multi-Source Analysis

1. **Industries Management**:
   - `industries` - ICB industry codes and names from VNStock
   - `post_mentioned_industries` - Links posts to industries with sentiment analysis
   - `industry_daily_sentiment` - Daily aggregation of industry sentiment

2. **Macro Economy Analysis**:
   - `macro_categories` - High-level macro categories (monetary policy, global economy, etc.)
   - `macro_themes` - Specific themes within categories (interest rates, market liquidity, etc.)
   - `post_mentioned_macro_themes` - Links posts to macro themes with sentiment
   - `macro_indicators` - Specific measurable indicators (VN Index forecast, GDP growth, etc.)
   - `post_macro_indicators` - Actual indicator values mentioned in posts
   - `macro_theme_daily_sentiment` - Daily aggregation of macro theme sentiment

3. **Enhanced Stocks Table**:
   - Added ICB codes (`icb_code1`, `icb_code2`, `icb_code3`, `icb_code4`)
   - Added company type code (`com_type_code`)
   - Enables automatic stock-industry mapping for contextual analysis

4. **Source Type Management**:
   - `sources` table enhanced with `source_type` field ('company', 'industry', 'macro_economy')
   - Enables different analysis workflows per source type

### Progress Tracking System

- **Real-time Progress Updates**: `analysis_progress.py` provides step-by-step progress tracking
- **10-Step Analysis Process**: From initialization through contextual enhancement to final results
- **Error Tracking**: Captures and reports any issues during analysis
- **Frontend Integration**: Progress bars and status updates for user experience

##Other documentation
1. Database schema: We use Supabase as our database. The schema can be found in `schema.md'
2. Available supabase views: We have some views in supabase to help us analyze the data. The views can be found in `views.md'. You can update this document when you add new or adjust existing views.
3. Database updates: Execute `schema_updates.sql` to add new tables for industries and macro economy analysis

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

## System Workflow

For detailed information about how the system works when users click "Start Analysis", including the complete step-by-step process and sequence diagrams, refer to `workflow.md`. This includes:
- Frontend to backend communication flow
- Database integration and smart deduplication 
- Multi-source crawling and AI analysis process
- Stock price and company data updates
- Error handling and performance optimizations

If there are any requests to adjust or understand the workflow, always refer to and update the workflow.md file accordingly. 
- Always update schema.md for the project once making any update to the supabase database
- before calling any API to the fastapi, check if it offer Debug mode first, this is the mode where the app fully function on just 1 stock, not all, to save time and token