Database Schema Documentation: Vietnamese Stock Market Analysis System
This PostgreSQL database schema is designed for a comprehensive Vietnamese stock market analysis platform that combines news sentiment analysis with financial data tracking. The system processes content from various sources, analyzes sentiment related to stocks and industries, and maintains detailed market data.
Core Architecture
The database follows a hub-and-spoke design with stocks and posts as central entities, connected through various relationship tables that track mentions, sentiment, and market events.
Table Structures and Relationships
1. Sources Table
Purpose: Manages news and content sources for web scraping

id (UUID, Primary Key): Unique identifier
name (TEXT): Display name of the source
url (TEXT): Base URL of the source
xpath_title, xpath_content, xpath_date (TEXT): XPath selectors for web scraping
status (TEXT): Source status (default: 'active')
created_at (TIMESTAMP): Creation timestamp

2. Industries Table
Purpose: Reference table for stock market sectors

id (UUID, Primary Key): Unique identifier
code (TEXT, UNIQUE): Industry classification code
name (TEXT): Industry display name

3. Stocks Table
Purpose: Master registry of Vietnamese stocks

id (UUID, Primary Key): Unique identifier
symbol (TEXT, UNIQUE): Stock ticker symbol
name (TEXT): Company full name
exchange (TEXT): Trading exchange (HOSE, HNX, or UPCOM)
industry_id (UUID): Foreign key to industries table
sector (TEXT): Additional sector classification
listed_date (DATE): Stock listing date
description (TEXT): Company description

4. Posts Table
Purpose: Stores scraped news articles and content

id (UUID, Primary Key): Unique identifier
url (TEXT): Source URL of the article
source_id (UUID): Foreign key to sources table
type (TEXT): Content category - 'Company', 'Industry', or 'Macro'
created_date (DATE): Publication date of the content
content (TEXT): Full article content
summary (TEXT): Article summary

5. Post Mentioned Stocks Table
Purpose: Links posts to stocks they mention with sentiment analysis

post_id (UUID): Foreign key to posts table
stock_id (UUID): Foreign key to stocks table
sentiment (TEXT): Sentiment classification ('positive', 'neutral', 'negative')
summary (TEXT): Context of how the stock was mentioned

6. Post Mentioned Industries Table
Purpose: Links posts to industries they discuss with sentiment analysis

post_id (UUID): Foreign key to posts table
industry_id (UUID): Foreign key to industries table
sentiment (TEXT): Sentiment classification ('positive', 'neutral', 'negative')
summary (TEXT): Context of industry mention

7. Stock Daily Sentiment Table
Purpose: Aggregated daily sentiment scores for each stock

stock_id (UUID): Foreign key to stocks table
date (DATE): Date of sentiment aggregation
sentiment (TEXT): Overall daily sentiment
summary (TEXT): Summary of sentiment drivers
post_ids (JSONB): Array of post IDs contributing to sentiment
signals (JSONB): Trading signals or insights derived from sentiment
Unique constraint: (stock_id, date) - one record per stock per day

8. Stock Prices Table
Purpose: Daily OHLCV price data for stocks

stock_id (UUID): Foreign key to stocks table
date (DATE): Trading date
open, high, low, close (DECIMAL): Price points
volume (BIGINT): Trading volume
Unique constraint: (stock_id, date) - one record per stock per day

9. Stock Ticks Table
Purpose: High-frequency tick-by-tick trading data

stock_id (UUID): Foreign key to stocks table
time (TIMESTAMP WITH TIME ZONE): Exact timestamp of trade
price (DECIMAL): Trade price
volume (BIGINT): Trade volume
match_type (TEXT): Type of trade execution

10. Stock Events Table
Purpose: Corporate events and announcements

stock_id (UUID): Foreign key to stocks table
event_title, en__event_title (TEXT): Event titles in Vietnamese and English
public_date, issue_date (DATE): Event announcement and issue dates
source_url (TEXT): Link to official announcement
event_list_code (TEXT): Event classification code
ratio, value (TEXT): Event parameters (dividends, splits, etc.)
record_date, exright_date (DATE): Important dates for shareholders
event_list_name, en__event_list_name (TEXT): Event type names

Key Data Flow Patterns

Content Ingestion: Sources → Posts → Sentiment Analysis → Stock/Industry Mentions
Price Data: External feeds → Stock Prices/Ticks tables
Sentiment Aggregation: Individual post sentiments → Daily sentiment summaries
Event Tracking: Corporate announcements → Stock Events table

Performance Optimizations
The schema includes strategic indexes on:

Foreign key relationships for join performance
Date fields for time-series queries
Stock symbols for quick lookups
Sentiment analysis queries

Security Features

Row Level Security (RLS) enabled on all tables for Supabase multi-tenancy
UUID primary keys prevent enumeration attacks
Check constraints ensure data integrity

Vietnamese Market Context
The schema is specifically designed for Vietnamese exchanges (HOSE, HNX, UPCOM) and supports bilingual content (Vietnamese/English) for international accessibility. The sentiment analysis system can process Vietnamese language content and correlate it with market movements.
This database serves as the foundation for building sentiment-driven trading algorithms, market analysis dashboards, and automated news monitoring systems for the Vietnamese stock market.


#CREATED VIEW
-- 1. View: Count total number of sources
CREATE VIEW v_total_sources AS
SELECT COUNT(*) as total_sources
FROM sources;

-- 2. View: Count number of active sources
CREATE VIEW v_active_sources AS
SELECT COUNT(*) as active_sources
FROM sources
WHERE status = 'active';

-- 3. View: Count posts from last 7 days
CREATE VIEW v_recent_posts AS
SELECT COUNT(*) as recent_posts_count
FROM posts
WHERE created_date >= CURRENT_DATE - INTERVAL '7 days';

-- 4. View: List all sources with selected fields, sorted by status
CREATE VIEW v_sources_list AS
SELECT 
    name,
    created_at,
    status
FROM sources
ORDER BY 
    CASE 
        WHEN status = 'active' THEN 1 
        ELSE 2 
    END,
    created_at DESC;

-- Optional: Combined dashboard view with all statistics
CREATE VIEW v_dashboard_stats AS
SELECT 
    (SELECT total_sources FROM v_total_sources) as total_sources,
    (SELECT active_sources FROM v_active_sources) as active_sources,
    (SELECT recent_posts_count FROM v_recent_posts) as recent_posts_count;