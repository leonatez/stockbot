-- Database Schema Updates for Industries and Macro Economy Analysis
-- To be executed on Supabase

-- 1. ADD ICB CODES TO STOCKS TABLE
ALTER TABLE stocks ADD COLUMN IF NOT EXISTS icb_code1 text;
ALTER TABLE stocks ADD COLUMN IF NOT EXISTS icb_code2 text;
ALTER TABLE stocks ADD COLUMN IF NOT EXISTS icb_code3 text;
ALTER TABLE stocks ADD COLUMN IF NOT EXISTS icb_code4 text;
ALTER TABLE stocks ADD COLUMN IF NOT EXISTS com_type_code text;

-- 2. UPDATE SOURCES TABLE to include source_type
ALTER TABLE sources ADD COLUMN IF NOT EXISTS source_type text DEFAULT 'company' CHECK (source_type IN ('company', 'industry', 'macro_economy'));

-- 3. CREATE INDUSTRIES TABLE (based on VNStock industries_icb())
CREATE TABLE IF NOT EXISTS industries (
  icb_code text PRIMARY KEY,
  icb_name text NOT NULL,
  en_icb_name text NOT NULL,
  level integer NOT NULL,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now()
);

-- 4. CREATE POST_MENTIONED_INDUSTRIES TABLE
-- First create without foreign key constraints
CREATE TABLE IF NOT EXISTS post_mentioned_industries (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  post_id uuid NOT NULL,
  icb_code text NOT NULL,
  sentiment text CHECK (sentiment IN ('positive', 'negative', 'neutral')),
  summary text,
  confidence_score decimal(3,2) CHECK (confidence_score >= 0 AND confidence_score <= 1),
  created_at timestamp with time zone DEFAULT now()
);

-- Add unique constraint if table was just created
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'post_mentioned_industries_post_id_icb_code_key'
    ) THEN
        ALTER TABLE post_mentioned_industries ADD CONSTRAINT post_mentioned_industries_post_id_icb_code_key UNIQUE(post_id, icb_code);
    END IF;
END $$;

-- Add foreign key constraints separately
DO $$
BEGIN
    -- Add foreign key to posts table
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'post_mentioned_industries_post_id_fkey'
    ) THEN
        ALTER TABLE post_mentioned_industries 
        ADD CONSTRAINT post_mentioned_industries_post_id_fkey 
        FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE;
    END IF;
    
    -- Add foreign key to industries table
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'post_mentioned_industries_icb_code_fkey'
    ) THEN
        ALTER TABLE post_mentioned_industries 
        ADD CONSTRAINT post_mentioned_industries_icb_code_fkey 
        FOREIGN KEY (icb_code) REFERENCES industries(icb_code) ON DELETE CASCADE;
    END IF;
END $$;

-- 5. CREATE MACRO ECONOMY TABLES
-- Macro Categories
CREATE TABLE IF NOT EXISTS macro_categories (
  id text PRIMARY KEY,
  name text NOT NULL,
  name_en text NOT NULL,
  description text,
  created_at timestamp with time zone DEFAULT now()
);

-- Macro Themes  
CREATE TABLE IF NOT EXISTS macro_themes (
  id text PRIMARY KEY,
  category_id text,
  name text NOT NULL,
  name_en text NOT NULL,
  description text,
  created_at timestamp with time zone DEFAULT now()
);

-- Add foreign key constraint for macro_themes separately
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'macro_themes_category_id_fkey'
    ) THEN
        ALTER TABLE macro_themes 
        ADD CONSTRAINT macro_themes_category_id_fkey 
        FOREIGN KEY (category_id) REFERENCES macro_categories(id) ON DELETE CASCADE;
    END IF;
END $$;

-- Post Mentioned Macro Themes
CREATE TABLE IF NOT EXISTS post_mentioned_macro_themes (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  post_id uuid NOT NULL,
  macro_theme_id text NOT NULL,
  sentiment text CHECK (sentiment IN ('positive', 'negative', 'neutral')),
  summary text,
  confidence_score decimal(3,2) CHECK (confidence_score >= 0 AND confidence_score <= 1),
  created_at timestamp with time zone DEFAULT now()
);

-- Add constraints for post_mentioned_macro_themes
DO $$
BEGIN
    -- Add unique constraint
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'post_mentioned_macro_themes_post_id_macro_theme_id_key'
    ) THEN
        ALTER TABLE post_mentioned_macro_themes ADD CONSTRAINT post_mentioned_macro_themes_post_id_macro_theme_id_key UNIQUE(post_id, macro_theme_id);
    END IF;
    
    -- Add foreign key to posts
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'post_mentioned_macro_themes_post_id_fkey'
    ) THEN
        ALTER TABLE post_mentioned_macro_themes 
        ADD CONSTRAINT post_mentioned_macro_themes_post_id_fkey 
        FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE;
    END IF;
    
    -- Add foreign key to macro_themes
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'post_mentioned_macro_themes_macro_theme_id_fkey'
    ) THEN
        ALTER TABLE post_mentioned_macro_themes 
        ADD CONSTRAINT post_mentioned_macro_themes_macro_theme_id_fkey 
        FOREIGN KEY (macro_theme_id) REFERENCES macro_themes(id) ON DELETE CASCADE;
    END IF;
END $$;

-- Macro Indicators
CREATE TABLE IF NOT EXISTS macro_indicators (
  id text PRIMARY KEY,
  theme_id text,
  name text NOT NULL,
  name_en text NOT NULL,
  unit text, -- '%', 'points', 'billion_vnd', etc.
  data_type text, -- 'percentage', 'range', 'absolute_value'
  description text,
  created_at timestamp with time zone DEFAULT now()
);

-- Add foreign key constraint for macro_indicators
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'macro_indicators_theme_id_fkey'
    ) THEN
        ALTER TABLE macro_indicators 
        ADD CONSTRAINT macro_indicators_theme_id_fkey 
        FOREIGN KEY (theme_id) REFERENCES macro_themes(id) ON DELETE CASCADE;
    END IF;
END $$;

-- Post Macro Indicators (actual values mentioned in posts)
CREATE TABLE IF NOT EXISTS post_macro_indicators (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  post_id uuid NOT NULL,
  macro_indicator_id text NOT NULL,
  current_value text, -- Can store ranges like "1,350-1,500" or single values
  projected_value text,
  time_period text, -- "Q1 2025", "2H2025", "2025", etc.
  mentioned_context text,
  created_at timestamp with time zone DEFAULT now()
);

-- Add constraints for post_macro_indicators
DO $$
BEGIN
    -- Add unique constraint
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'post_macro_indicators_post_id_macro_indicator_id_key'
    ) THEN
        ALTER TABLE post_macro_indicators ADD CONSTRAINT post_macro_indicators_post_id_macro_indicator_id_key UNIQUE(post_id, macro_indicator_id);
    END IF;
    
    -- Add foreign key to posts
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'post_macro_indicators_post_id_fkey'
    ) THEN
        ALTER TABLE post_macro_indicators 
        ADD CONSTRAINT post_macro_indicators_post_id_fkey 
        FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE;
    END IF;
    
    -- Add foreign key to macro_indicators
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'post_macro_indicators_macro_indicator_id_fkey'
    ) THEN
        ALTER TABLE post_macro_indicators 
        ADD CONSTRAINT post_macro_indicators_macro_indicator_id_fkey 
        FOREIGN KEY (macro_indicator_id) REFERENCES macro_indicators(id) ON DELETE CASCADE;
    END IF;
END $$;

-- 6. CREATE INDUSTRY DAILY SENTIMENT AGGREGATION
CREATE TABLE IF NOT EXISTS industry_daily_sentiment (
  icb_code text,
  date date NOT NULL,
  positive_mentions integer DEFAULT 0,
  negative_mentions integer DEFAULT 0,
  neutral_mentions integer DEFAULT 0,
  overall_sentiment decimal(3,2),
  post_count integer DEFAULT 0,
  summary text,
  created_at timestamp with time zone DEFAULT now(),
  PRIMARY KEY (icb_code, date)
);

-- Add foreign key constraint for industry_daily_sentiment
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'industry_daily_sentiment_icb_code_fkey'
    ) THEN
        ALTER TABLE industry_daily_sentiment 
        ADD CONSTRAINT industry_daily_sentiment_icb_code_fkey 
        FOREIGN KEY (icb_code) REFERENCES industries(icb_code) ON DELETE CASCADE;
    END IF;
END $$;

-- 7. CREATE MACRO THEME DAILY SENTIMENT AGGREGATION  
CREATE TABLE IF NOT EXISTS macro_theme_daily_sentiment (
  macro_theme_id text,
  date date NOT NULL,
  positive_mentions integer DEFAULT 0,
  negative_mentions integer DEFAULT 0,
  neutral_mentions integer DEFAULT 0,
  overall_sentiment decimal(3,2),
  post_count integer DEFAULT 0,
  summary text,
  created_at timestamp with time zone DEFAULT now(),
  PRIMARY KEY (macro_theme_id, date)
);

-- Add foreign key constraint for macro_theme_daily_sentiment
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'macro_theme_daily_sentiment_macro_theme_id_fkey'
    ) THEN
        ALTER TABLE macro_theme_daily_sentiment 
        ADD CONSTRAINT macro_theme_daily_sentiment_macro_theme_id_fkey 
        FOREIGN KEY (macro_theme_id) REFERENCES macro_themes(id) ON DELETE CASCADE;
    END IF;
END $$;

-- 8. INSERT SAMPLE MACRO DATA
-- Insert macro categories
INSERT INTO macro_categories (id, name, name_en, description) VALUES
('global_economy', 'Kinh tế Toàn cầu', 'Global Economy', 'Conditions and trends in the global economy'),
('monetary_policy', 'Chính sách Tiền tệ', 'Monetary Policy', 'Central bank policies and interest rate decisions'),
('market_conditions', 'Điều kiện Thị trường', 'Market Conditions', 'Stock market liquidity and trading conditions'),
('corporate_sector', 'Khu vực Doanh nghiệp', 'Corporate Sector', 'Overall corporate performance and trends'),
('fiscal_policy', 'Chính sách Tài khóa', 'Fiscal Policy', 'Government spending and taxation policies'),
('geopolitical_risk', 'Rủi ro Địa chính trị', 'Geopolitical Risk', 'Political and geopolitical risk factors')
ON CONFLICT (id) DO NOTHING;

-- Insert macro themes
INSERT INTO macro_themes (id, category_id, name, name_en, description) VALUES
('global_uncertainty', 'global_economy', 'Bất ổn Kinh tế Toàn cầu', 'Global Economic Uncertainty', 'Uncertainties in global economic conditions'),
('trade_war_impact', 'global_economy', 'Tác động Chiến tranh Thương mại', 'Trade War Impact', 'Effects of international trade conflicts'),
('interest_rate_trends', 'monetary_policy', 'Xu hướng Lãi suất', 'Interest Rate Trends', 'Changes in interest rate levels'),
('monetary_tightening', 'monetary_policy', 'Thắt chặt Tiền tệ', 'Monetary Tightening', 'Restrictive monetary policy measures'),
('market_liquidity', 'market_conditions', 'Thanh khoản Thị trường', 'Market Liquidity', 'Stock market trading liquidity levels'),
('market_valuation', 'market_conditions', 'Định giá Thị trường', 'Market Valuation', 'Overall market valuation metrics'),
('corporate_performance', 'corporate_sector', 'Hiệu suất Doanh nghiệp', 'Corporate Performance', 'Overall corporate earnings and performance'),
('corporate_profit_growth', 'corporate_sector', 'Tăng trưởng Lợi nhuận', 'Corporate Profit Growth', 'Growth in corporate profits'),
('tax_policy', 'fiscal_policy', 'Chính sách Thuế', 'Tax Policy', 'Government tax policy changes'),
('government_spending', 'fiscal_policy', 'Chi tiêu Chính phủ', 'Government Spending', 'Public investment and spending levels'),
('geopolitical_conflict', 'geopolitical_risk', 'Xung đột Địa chính trị', 'Geopolitical Conflict', 'Political conflicts and their economic impact')
ON CONFLICT (id) DO NOTHING;

-- Insert macro indicators
INSERT INTO macro_indicators (id, theme_id, name, name_en, unit, data_type, description) VALUES
('vn_index_forecast', 'market_liquidity', 'Dự báo VN Index', 'VN Index Forecast', 'points', 'range', 'Forecasted VN Index trading range'),
('vn_index_current', 'market_liquidity', 'VN Index Hiện tại', 'Current VN Index', 'points', 'absolute_value', 'Current VN Index level'),
('corporate_profit_growth_rate', 'corporate_profit_growth', 'Tỷ lệ Tăng trưởng Lợi nhuận', 'Corporate Profit Growth Rate', '%', 'percentage', 'Year-over-year corporate profit growth'),
('market_pe_ratio', 'market_valuation', 'Tỷ lệ P/E Thị trường', 'Market P/E Ratio', 'ratio', 'absolute_value', 'Market price-to-earnings ratio'),
('market_pe_deviation', 'market_valuation', 'Độ lệch P/E so với TB', 'P/E Deviation from Average', 'standard deviation', 'absolute_value', 'Market P/E deviation from historical average'),
('base_interest_rate', 'interest_rate_trends', 'Lãi suất Cơ bản', 'Base Interest Rate', '%', 'percentage', 'Central bank base interest rate'),
('market_liquidity_growth', 'market_liquidity', 'Tăng trưởng Thanh khoản', 'Market Liquidity Growth', '%', 'percentage', 'Growth in market trading liquidity'),
('gdp_growth_rate', 'global_economy', 'Tỷ lệ Tăng trưởng GDP', 'GDP Growth Rate', '%', 'percentage', 'Economic growth rate'),
('inflation_rate', 'monetary_policy', 'Tỷ lệ Lạm phát', 'Inflation Rate', '%', 'percentage', 'Consumer price inflation rate')
ON CONFLICT (id) DO NOTHING;

-- 9. CREATE INDEXES FOR PERFORMANCE
CREATE INDEX IF NOT EXISTS idx_post_mentioned_industries_post_id ON post_mentioned_industries(post_id);
CREATE INDEX IF NOT EXISTS idx_post_mentioned_industries_icb_code ON post_mentioned_industries(icb_code);
CREATE INDEX IF NOT EXISTS idx_post_mentioned_macro_themes_post_id ON post_mentioned_macro_themes(post_id);
CREATE INDEX IF NOT EXISTS idx_post_mentioned_macro_themes_theme_id ON post_mentioned_macro_themes(macro_theme_id);
CREATE INDEX IF NOT EXISTS idx_post_macro_indicators_post_id ON post_macro_indicators(post_id);
CREATE INDEX IF NOT EXISTS idx_industry_daily_sentiment_date ON industry_daily_sentiment(date);
CREATE INDEX IF NOT EXISTS idx_macro_theme_daily_sentiment_date ON macro_theme_daily_sentiment(date);
CREATE INDEX IF NOT EXISTS idx_stocks_icb_codes ON stocks(icb_code1, icb_code2, icb_code3, icb_code4);