# Database Schema Documentation: Vietnamese Stock Market Analysis System

This PostgreSQL database schema is designed for a comprehensive Vietnamese stock market analysis platform that combines news sentiment analysis with financial data tracking. The system processes content from various sources, analyzes sentiment related to stocks, industries, and macro themes, and maintains detailed market data.

## Core Architecture

The database follows a hub-and-spoke design with stocks and posts as central entities, connected through various relationship tables that track mentions, sentiment, and market events. The schema supports multi-source analysis with enhanced contextual intelligence.

## Table Structures and Relationships

### 1. Sources Table
**Purpose**: Manages news and content sources for web scraping with multi-source type support

- `id` (UUID, Primary Key): Unique identifier (default: uuid_generate_v4())
- `name` (TEXT, NOT NULL): Display name of the source
- `url` (TEXT): Base URL of the source
- `xpath_title` (TEXT): XPath selectors for extracting post titles
- `xpath_content` (TEXT): XPath selectors for extracting post content
- `xpath_date` (TEXT): XPath selectors for extracting post dates
- `source_type` (TEXT): Source classification ('Company', 'Industry', 'Macro_Economy') (default: 'Company')
- `pagination_rule` (TEXT): Pagination pattern for multi-page crawling
- `content_type` (TEXT): Type of content extraction (default: 'text')
- `status` (TEXT): Source status (default: 'active')
- `created_at` (TIMESTAMP WITH TIME ZONE): Creation timestamp (default: now())

### 2. Industries Table
**Purpose**: Reference table for Vietnamese stock market sectors using ICB classification

- `icb_code` (TEXT, Primary Key): ICB industry classification code
- `icb_name` (TEXT, NOT NULL): Industry name in Vietnamese
- `en_icb_name` (TEXT, NOT NULL): Industry name in English
- `level` (INTEGER, NOT NULL): ICB classification level (1-4)
- `created_at` (TIMESTAMP WITH TIME ZONE): Creation timestamp (default: now())
- `updated_at` (TIMESTAMP WITH TIME ZONE): Record modification time (default: now())

### 3. Macro Categories Table
**Purpose**: High-level macro economic categories for analysis

- `id` (TEXT, Primary Key): Category identifier
- `name` (TEXT, NOT NULL): Category name in Vietnamese
- `name_en` (TEXT, NOT NULL): Category name in English
- `description` (TEXT): Detailed description of the category
- `created_at` (TIMESTAMP WITH TIME ZONE): Creation timestamp (default: now())

### 4. Macro Themes Table
**Purpose**: Specific themes within macro economic categories

- `id` (TEXT, Primary Key): Theme identifier
- `category_id` (TEXT): Foreign key to macro_categories table
- `name` (TEXT, NOT NULL): Theme name in Vietnamese
- `name_en` (TEXT, NOT NULL): Theme name in English
- `description` (TEXT): Detailed description of the theme
- `created_at` (TIMESTAMP WITH TIME ZONE): Creation timestamp (default: now())

### 5. Macro Indicators Table
**Purpose**: Measurable economic indicators within themes

- `id` (TEXT, Primary Key): Indicator identifier
- `theme_id` (TEXT): Foreign key to macro_themes table
- `name` (TEXT, NOT NULL): Indicator name in Vietnamese
- `name_en` (TEXT, NOT NULL): Indicator name in English
- `unit` (TEXT): Unit of measurement
- `data_type` (TEXT): Type of data (numeric, text, etc.)
- `description` (TEXT): Detailed description of the indicator
- `created_at` (TIMESTAMP WITH TIME ZONE): Creation timestamp (default: now())

### 6. Stocks Table
**Purpose**: Master registry of Vietnamese stocks with enhanced ICB classification

- `id` (UUID, Primary Key): Unique identifier (default: uuid_generate_v4())
- `symbol` (TEXT, NOT NULL): Stock ticker symbol
- `organ_name` (TEXT, NOT NULL): Official company full name
- `exchange` (TEXT): Trading exchange (HOSE, HNX, or UPCOM)
- `description` (TEXT): Company description
- `organ_short_name` (TEXT): Short company name
- `isvn30` (BOOLEAN): Whether stock is in VN30 index (default: false)
- `icb_name1` (TEXT): ICB sector classification level 1 name
- `icb_name2` (TEXT): ICB sector classification level 2 name
- `icb_name3` (TEXT): ICB sector classification level 3 name
- `icb_name4` (TEXT): ICB sector classification level 4 name
- `icb_code1` (TEXT): ICB sector classification level 1 code
- `icb_code2` (TEXT): ICB sector classification level 2 code
- `icb_code3` (TEXT): ICB sector classification level 3 code
- `icb_code4` (TEXT): ICB sector classification level 4 code
- `com_type_code` (TEXT): Company type classification code
- `charter_capital` (NUMERIC): Company charter capital
- `issue_share` (BIGINT): Number of issued shares
- `created_at` (TIMESTAMP WITH TIME ZONE): Creation timestamp (default: now())
- `updated_at` (TIMESTAMP WITH TIME ZONE): Record modification time (default: now())

### 7. Posts Table
**Purpose**: Stores scraped news articles and content with type classification

- `id` (UUID, Primary Key): Unique identifier (default: uuid_generate_v4())
- `url` (TEXT): Source URL of the article
- `source_id` (UUID): Foreign key to sources table
- `type` (TEXT, NOT NULL): Content category - 'Company', 'Industry', or 'Macro'
- `created_date` (DATE, NOT NULL): Publication date of the content
- `content` (TEXT): Full article content
- `summary` (TEXT): Article summary
- `created_at` (TIMESTAMP WITH TIME ZONE): Record creation timestamp (default: now())

### 8. Post Mentioned Stocks Table
**Purpose**: Links posts to stocks they mention with enhanced sentiment analysis

- `id` (UUID, Primary Key): Unique identifier (default: uuid_generate_v4())
- `post_id` (UUID): Foreign key to posts table
- `stock_id` (UUID): Foreign key to stocks table
- `sentiment` (TEXT): Sentiment classification ('positive', 'neutral', 'negative')
- `summary` (TEXT): Context of how the stock was mentioned
- `structured_analysis` (JSONB): Detailed structured analysis data
- `ket_qua_kinh_doanh_quy` (JSONB): Quarterly business results analysis
- `luy_ke_6t_nam` (JSONB): Cumulative 6-month/year analysis
- `phan_tich_mang_kinh_doanh` (JSONB): Business segment analysis
- `tai_chinh_dong_tien` (JSONB): Financial and cash flow analysis
- `trien_vong` (JSONB): Outlook and prospects analysis
- `rui_ro` (JSONB): Risk analysis
- `dinh_gia_khuyen_nghi` (JSONB): Valuation and recommendations
- `created_at` (TIMESTAMP WITH TIME ZONE): Record creation timestamp (default: now())

### 9. Post Mentioned Industries Table
**Purpose**: Links posts to industries they discuss with sentiment analysis

- `id` (UUID, Primary Key): Unique identifier (default: gen_random_uuid())
- `post_id` (UUID, NOT NULL): Foreign key to posts table
- `icb_code` (TEXT, NOT NULL): Foreign key to industries table
- `sentiment` (TEXT): Sentiment classification ('positive', 'neutral', 'negative')
- `summary` (TEXT): Context of industry mention
- `confidence_score` (NUMERIC): Confidence level of the analysis
- `created_at` (TIMESTAMP WITH TIME ZONE): Record creation timestamp (default: now())

### 10. Post Mentioned Macro Themes Table
**Purpose**: Links posts to macro themes they discuss with sentiment analysis

- `id` (UUID, Primary Key): Unique identifier (default: gen_random_uuid())
- `post_id` (UUID, NOT NULL): Foreign key to posts table
- `macro_theme_id` (TEXT, NOT NULL): Foreign key to macro_themes table
- `sentiment` (TEXT): Sentiment classification ('positive', 'neutral', 'negative')
- `summary` (TEXT): Context of macro theme mention
- `confidence_score` (NUMERIC): Confidence level of the analysis
- `created_at` (TIMESTAMP WITH TIME ZONE): Record creation timestamp (default: now())

### 11. Post Macro Indicators Table
**Purpose**: Captures specific macro indicator values mentioned in posts

- `id` (UUID, Primary Key): Unique identifier (default: gen_random_uuid())
- `post_id` (UUID, NOT NULL): Foreign key to posts table
- `macro_indicator_id` (TEXT, NOT NULL): Foreign key to macro_indicators table
- `current_value` (TEXT): Current value of the indicator mentioned
- `projected_value` (TEXT): Projected or forecast value mentioned
- `time_period` (TEXT): Time period for the indicator value
- `mentioned_context` (TEXT): Context in which the indicator was mentioned
- `created_at` (TIMESTAMP WITH TIME ZONE): Record creation timestamp (default: now())

### 12. Stock Daily Sentiment Table
**Purpose**: Aggregated daily sentiment scores for each stock

- `id` (UUID, Primary Key): Unique identifier (default: uuid_generate_v4())
- `stock_id` (UUID): Foreign key to stocks table
- `date` (DATE, NOT NULL): Date of sentiment aggregation
- `sentiment` (TEXT): Overall daily sentiment
- `summary` (TEXT): Summary of sentiment drivers
- `post_ids` (JSONB): Array of post IDs contributing to sentiment (default: '[]')
- `signals` (JSONB): Trading signals or insights derived from sentiment (default: '[]')
- `created_at` (TIMESTAMP WITH TIME ZONE): Record creation timestamp (default: now())

**Unique constraint**: (stock_id, date) - one record per stock per day

### 13. Industry Daily Sentiment Table
**Purpose**: Aggregated daily sentiment scores for each industry

- `icb_code` (TEXT, NOT NULL): Primary key, foreign key to industries table
- `date` (DATE, NOT NULL): Date of sentiment aggregation
- `positive_mentions` (INTEGER): Count of positive mentions (default: 0)
- `negative_mentions` (INTEGER): Count of negative mentions (default: 0)
- `neutral_mentions` (INTEGER): Count of neutral mentions (default: 0)
- `overall_sentiment` (NUMERIC): Calculated overall sentiment score
- `post_count` (INTEGER): Total number of posts analyzed (default: 0)
- `summary` (TEXT): Summary of industry sentiment drivers
- `created_at` (TIMESTAMP WITH TIME ZONE): Record creation timestamp (default: now())

**Primary Key**: (icb_code, date)

### 14. Macro Theme Daily Sentiment Table
**Purpose**: Aggregated daily sentiment scores for each macro theme

- `macro_theme_id` (TEXT, NOT NULL): Primary key, foreign key to macro_themes table
- `date` (DATE, NOT NULL): Date of sentiment aggregation
- `positive_mentions` (INTEGER): Count of positive mentions (default: 0)
- `negative_mentions` (INTEGER): Count of negative mentions (default: 0)
- `neutral_mentions` (INTEGER): Count of neutral mentions (default: 0)
- `overall_sentiment` (NUMERIC): Calculated overall sentiment score
- `post_count` (INTEGER): Total number of posts analyzed (default: 0)
- `summary` (TEXT): Summary of macro theme sentiment drivers
- `created_at` (TIMESTAMP WITH TIME ZONE): Record creation timestamp (default: now())

**Primary Key**: (macro_theme_id, date)

### 15. Stock Prices Table
**Purpose**: Daily OHLCV price data for stocks

- `id` (UUID, Primary Key): Unique identifier (default: uuid_generate_v4())
- `stock_id` (UUID): Foreign key to stocks table
- `date` (DATE, NOT NULL): Trading date
- `open` (NUMERIC): Opening price
- `high` (NUMERIC): Highest price
- `low` (NUMERIC): Lowest price
- `close` (NUMERIC): Closing price
- `volume` (BIGINT): Trading volume
- `created_at` (TIMESTAMP WITH TIME ZONE): Record creation timestamp (default: now())

**Unique constraint**: (stock_id, date) - one record per stock per day

### 16. Stock Prices Hourly Table
**Purpose**: Hourly OHLCV price data for stocks with enhanced granularity

- `id` (UUID, Primary Key): Unique identifier (default: gen_random_uuid())
- `stock_id` (UUID): Foreign key to stocks table
- `date` (DATE, NOT NULL): Trading date
- `hour` (TIME, NOT NULL): Hour of the trading data (format: HH:MM:SS)
- `open` (NUMERIC): Opening price for the hour
- `high` (NUMERIC): Highest price for the hour
- `low` (NUMERIC): Lowest price for the hour
- `close` (NUMERIC): Closing price for the hour
- `volume` (BIGINT): Trading volume for the hour
- `created_at` (TIMESTAMP WITH TIME ZONE): Record creation timestamp (default: now())

**Unique constraint**: (stock_id, date, hour) - one record per stock per hour
**Indexes**: 
- idx_stock_prices_hourly_stock_date on (stock_id, date)
- idx_stock_prices_hourly_date_hour on (date, hour)
- idx_stock_prices_hourly_stock_id on (stock_id)

### 17. Stock Ticks Table
**Purpose**: High-frequency tick-by-tick trading data

- `id` (UUID, Primary Key): Unique identifier (default: uuid_generate_v4())
- `stock_id` (UUID): Foreign key to stocks table
- `time` (TIMESTAMP WITH TIME ZONE, NOT NULL): Exact timestamp of trade
- `price` (NUMERIC, NOT NULL): Trade price
- `volume` (BIGINT, NOT NULL): Trade volume
- `match_type` (TEXT): Type of trade execution
- `created_at` (TIMESTAMP WITH TIME ZONE): Record creation timestamp (default: now())

### 18. Stock Events Table
**Purpose**: Corporate events and announcements

- `id` (UUID, Primary Key): Unique identifier (default: uuid_generate_v4())
- `stock_id` (UUID): Foreign key to stocks table
- `event_title` (TEXT): Event title in Vietnamese
- `en__event_title` (TEXT): Event title in English (note: double underscore)
- `public_date` (DATE): Event announcement date
- `issue_date` (DATE): Event issue date
- `source_url` (TEXT): Link to official announcement
- `event_list_code` (TEXT): Event classification code
- `ratio` (TEXT): Event ratio parameters
- `value` (TEXT): Event value parameters
- `record_date` (DATE): Record date for shareholders
- `exright_date` (DATE): Ex-rights date
- `event_list_name` (TEXT): Event type name in Vietnamese
- `en__event_list_name` (TEXT): Event type name in English (note: double underscore)
- `description` (TEXT): Additional event description
- `event_type` (TEXT): Type classification of the event
- `event_name` (TEXT): Alternative event name field
- `event_date` (DATE): Primary event date
- `ex_date` (DATE): Ex-dividend/rights date
- `place` (TEXT): Location or venue for the event
- `created_at` (TIMESTAMP WITH TIME ZONE): Record creation timestamp (default: now())

### 19. Stock Dividends Table
**Purpose**: Tracks company dividend payments and distributions

- `id` (INTEGER, Primary Key): Unique identifier (auto-incrementing)
- `stock_id` (UUID): Foreign key to stocks table
- `exercise_date` (DATE): Date when dividend is exercised/paid
- `cash_year` (INTEGER): Year of the dividend payment
- `cash_dividend_percentage` (NUMERIC): Dividend percentage rate
- `issue_method` (TEXT): Method of dividend issuance
- `created_at` (TIMESTAMP WITH TIME ZONE): Record creation timestamp (default: now())
- `updated_at` (TIMESTAMP WITH TIME ZONE): Record modification timestamp (default: now())

**Unique constraint**: (stock_id, exercise_date, cash_year) - prevents duplicate dividend records

### 20. Company Finance Table
**Purpose**: Comprehensive financial data for companies

- `id` (UUID, Primary Key): Unique identifier (default: gen_random_uuid())
- `stock_id` (UUID, NOT NULL): Foreign key to stocks table
- `symbol` (TEXT, NOT NULL): Stock symbol for reference
- `quarter` (TEXT): Financial reporting quarter
- `year` (INTEGER): Financial reporting year
- `total_assets` (NUMERIC): Total company assets
- `current_assets` (NUMERIC): Current assets
- `non_current_assets` (NUMERIC): Non-current assets
- `total_liabilities` (NUMERIC): Total liabilities
- `current_liabilities` (NUMERIC): Current liabilities
- `non_current_liabilities` (NUMERIC): Non-current liabilities
- `shareholders_equity` (NUMERIC): Shareholders' equity
- `revenue` (NUMERIC): Total revenue
- `gross_profit` (NUMERIC): Gross profit
- `operating_profit` (NUMERIC): Operating profit
- `net_profit` (NUMERIC): Net profit
- `ebit` (NUMERIC): Earnings before interest and taxes
- `ebitda` (NUMERIC): Earnings before interest, taxes, depreciation, and amortization
- `operating_cash_flow` (NUMERIC): Operating cash flow
- `investing_cash_flow` (NUMERIC): Investing cash flow
- `financing_cash_flow` (NUMERIC): Financing cash flow
- `net_cash_flow` (NUMERIC): Net cash flow
- `free_cash_flow` (NUMERIC): Free cash flow
- `eps` (NUMERIC): Earnings per share
- `book_value_per_share` (NUMERIC): Book value per share
- `roe` (NUMERIC): Return on equity
- `roa` (NUMERIC): Return on assets
- `current_ratio` (NUMERIC): Current ratio
- `debt_to_equity` (NUMERIC): Debt to equity ratio
- `profit_margin` (NUMERIC): Profit margin
- `revenue_growth` (NUMERIC): Revenue growth rate
- `additional_data` (JSONB): Additional financial metrics
- `created_at` (TIMESTAMP WITH TIME ZONE): Record creation timestamp (default: now())
- `updated_at` (TIMESTAMP WITH TIME ZONE): Record modification timestamp (default: now())

## Database Views

### Core Statistics Views

**v_total_sources**: Count total number of sources
```sql
SELECT COUNT(*) as total_sources FROM sources;
```

**v_active_sources**: Count number of active sources
```sql
SELECT COUNT(*) as active_sources FROM sources WHERE status = 'active';
```

**v_recent_posts**: Count posts from last 7 days
```sql
SELECT COUNT(*) as recent_posts_count FROM posts WHERE created_date >= CURRENT_DATE - INTERVAL '7 days';
```

**v_sources_list**: List all sources with selected fields, sorted by status
```sql
SELECT name, created_at, status FROM sources ORDER BY CASE WHEN status = 'active' THEN 1 ELSE 2 END, created_at DESC;
```

**v_dashboard_stats**: Combined dashboard view with all statistics
```sql
SELECT 
    (SELECT total_sources FROM v_total_sources) as total_sources,
    (SELECT active_sources FROM v_active_sources) as active_sources,
    (SELECT recent_posts_count FROM v_recent_posts) as recent_posts_count;
```

**company_finance_with_stock**: Join view combining company finance data with stock information

## Key Data Flow Patterns

### Enhanced Multi-Source Analysis Flow

1. **Content Ingestion**: Sources (by type) → Posts → AI Analysis → Stock/Industry/Macro Mentions
2. **Price Data**: VNStock API → Stock Prices (daily), Stock Prices Hourly, Stock Ticks tables
3. **Sentiment Aggregation**: Individual post sentiments → Daily sentiment summaries for stocks, industries, and macro themes
4. **Event Tracking**: VNStock API → Stock Events/Dividends tables
5. **Contextual Enhancement**: Industry context + Macro context → Enhanced stock analysis
6. **Company Financial Data**: VNStock API → Company Finance table
7. **Hourly Price Enhancement**: On-demand hourly price fetching for enhanced chart granularity

### Multi-Source Type Processing

- **Company Sources**: Focus on individual stock analysis and sentiment
- **Industry Sources**: Analyze sector trends and industry-wide sentiment
- **Macro Sources**: Track economic indicators and market-wide themes

## Performance Optimizations

The schema includes strategic indexes on:
- Foreign key relationships for join performance
- Date fields for time-series queries
- Stock symbols for quick lookups
- Sentiment analysis queries
- ICB codes for industry classification
- Macro theme IDs for economic analysis

## Security Features

- Row Level Security (RLS) enabled on all tables for Supabase multi-tenancy
- UUID primary keys prevent enumeration attacks
- Check constraints ensure data integrity
- Proper foreign key relationships maintain referential integrity

## Vietnamese Market Context

The schema is specifically designed for Vietnamese exchanges (HOSE, HNX, UPCOM) and supports:
- Bilingual content (Vietnamese/English) for international accessibility
- ICB industry classification system used in Vietnamese markets
- VN30 index tracking for blue-chip stocks
- Vietnamese macro economic indicators and themes
- Corporate events specific to Vietnamese market regulations

This database serves as the foundation for building sentiment-driven trading algorithms, market analysis dashboards, automated news monitoring systems, and comprehensive multi-source analysis for the Vietnamese stock market.