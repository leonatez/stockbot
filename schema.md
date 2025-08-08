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
source_type (TEXT): Source classification (Company, Industry, Macro)
pagination_rule (TEXT): Pagination pattern for multi-page crawling
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
organ_name (TEXT): Official company full name
exchange (TEXT): Trading exchange (HOSE, HNX, or UPCOM)
description (TEXT): Company description
created_at (TIMESTAMP WITH TIME ZONE): Creation timestamp
organ_short_name (TEXT): Short company name
isvn30 (BOOLEAN): Whether stock is in VN30 index
icb_name1 (TEXT): ICB sector classification level 1
icb_name2 (TEXT): ICB sector classification level 2
icb_name3 (TEXT): ICB sector classification level 3
icb_name4 (TEXT): ICB sector classification level 4
charter_capital (NUMERIC): Company charter capital
issue_share (BIGINT): Number of issued shares
updated_at (TIMESTAMP WITH TIME ZONE): Record modification time

4. Posts Table
Purpose: Stores scraped news articles and content

id (UUID, Primary Key): Unique identifier
url (TEXT): Source URL of the article
source_id (UUID): Foreign key to sources table
type (TEXT): Content category - 'Company', 'Industry', or 'Macro'
created_date (DATE): Publication date of the content
content (TEXT): Full article content
summary (TEXT): Article summary
created_at (TIMESTAMP WITH TIME ZONE): Record creation timestamp

5. Post Mentioned Stocks Table
Purpose: Links posts to stocks they mention with sentiment analysis

id (UUID, Primary Key): Unique identifier
post_id (UUID): Foreign key to posts table
stock_id (UUID): Foreign key to stocks table
sentiment (TEXT): Sentiment classification ('positive', 'neutral', 'negative')
summary (TEXT): Context of how the stock was mentioned
created_at (TIMESTAMP WITH TIME ZONE): Record creation timestamp

6. Post Mentioned Industries Table
Purpose: Links posts to industries they discuss with sentiment analysis

id (UUID, Primary Key): Unique identifier
post_id (UUID): Foreign key to posts table
industry_id (UUID): Foreign key to industries table
sentiment (TEXT): Sentiment classification ('positive', 'neutral', 'negative')
summary (TEXT): Context of industry mention
created_at (TIMESTAMP WITH TIME ZONE): Record creation timestamp

7. Stock Daily Sentiment Table
Purpose: Aggregated daily sentiment scores for each stock

id (UUID, Primary Key): Unique identifier
stock_id (UUID): Foreign key to stocks table
date (DATE): Date of sentiment aggregation
sentiment (TEXT): Overall daily sentiment
summary (TEXT): Summary of sentiment drivers
post_ids (JSONB): Array of post IDs contributing to sentiment
signals (JSONB): Trading signals or insights derived from sentiment
created_at (TIMESTAMP WITH TIME ZONE): Record creation timestamp
Unique constraint: (stock_id, date) - one record per stock per day

8. Stock Prices Table
Purpose: Daily OHLCV price data for stocks

id (UUID, Primary Key): Unique identifier
stock_id (UUID): Foreign key to stocks table
date (DATE): Trading date
open (NUMERIC): Opening price
high (NUMERIC): Highest price
low (NUMERIC): Lowest price
close (NUMERIC): Closing price
volume (BIGINT): Trading volume
created_at (TIMESTAMP WITH TIME ZONE): Record creation timestamp
Unique constraint: (stock_id, date) - one record per stock per day

9. Stock Ticks Table
Purpose: High-frequency tick-by-tick trading data

id (UUID, Primary Key): Unique identifier
stock_id (UUID): Foreign key to stocks table
time (TIMESTAMP WITH TIME ZONE): Exact timestamp of trade
price (NUMERIC): Trade price
volume (BIGINT): Trade volume
match_type (TEXT): Type of trade execution
created_at (TIMESTAMP WITH TIME ZONE): Record creation timestamp

10. Stock Events Table
Purpose: Corporate events and announcements

id (UUID, Primary Key): Unique identifier
stock_id (UUID): Foreign key to stocks table
event_title (TEXT): Event title in Vietnamese
en__event_title (TEXT): Event title in English (note: double underscore)
public_date (DATE): Event announcement date
issue_date (DATE): Event issue date
source_url (TEXT): Link to official announcement
event_list_code (TEXT): Event classification code
ratio (TEXT): Event ratio parameters
value (TEXT): Event value parameters
record_date (DATE): Record date for shareholders
exright_date (DATE): Ex-rights date
event_list_name (TEXT): Event type name in Vietnamese
en__event_list_name (TEXT): Event type name in English (note: double underscore)
created_at (TIMESTAMP WITH TIME ZONE): Record creation timestamp
description (TEXT): Additional event description
event_type (TEXT): Type classification of the event
event_name (TEXT): Alternative event name field
event_date (DATE): Primary event date
ex_date (DATE): Ex-dividend/rights date
place (TEXT): Location or venue for the event

11. Stock Dividends Table
Purpose: Tracks company dividend payments and distributions

id (INTEGER, Primary Key): Unique identifier (auto-incrementing)
stock_id (UUID): Foreign key to stocks table
exercise_date (DATE): Date when dividend is exercised/paid
cash_year (INTEGER): Year of the dividend payment
cash_dividend_percentage (NUMERIC): Dividend percentage rate
issue_method (TEXT): Method of dividend issuance
created_at (TIMESTAMP WITH TIME ZONE): Record creation timestamp
updated_at (TIMESTAMP WITH TIME ZONE): Record modification timestamp
Unique constraint: (stock_id, exercise_date, cash_year) - prevents duplicate dividend records

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