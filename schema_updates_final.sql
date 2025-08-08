-- Final Database Schema Updates for Industries and Macro Economy Analysis
-- Handles existing data properly

-- 1. ADD ICB CODES TO STOCKS TABLE (safe to run multiple times)
ALTER TABLE stocks ADD COLUMN IF NOT EXISTS icb_code1 text;
ALTER TABLE stocks ADD COLUMN IF NOT EXISTS icb_code2 text;
ALTER TABLE stocks ADD COLUMN IF NOT EXISTS icb_code3 text;
ALTER TABLE stocks ADD COLUMN IF NOT EXISTS icb_code4 text;
ALTER TABLE stocks ADD COLUMN IF NOT EXISTS com_type_code text;

-- 2. FIX EXISTING SOURCE_TYPE VALUES AND ADD CONSTRAINT
-- First, update existing 'Company' to 'company' to match our constraint
UPDATE sources SET source_type = 'company' WHERE source_type = 'Company';
UPDATE sources SET source_type = 'industry' WHERE source_type = 'Industry';  
UPDATE sources SET source_type = 'macro_economy' WHERE source_type = 'Macro Economy';

-- Set default for any NULL values
UPDATE sources SET source_type = 'company' WHERE source_type IS NULL;

-- Now add the CHECK constraint safely
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'sources_source_type_check'
    ) THEN
        ALTER TABLE sources ADD CONSTRAINT sources_source_type_check CHECK (source_type IN ('company', 'industry', 'macro_economy'));
    END IF;
END $$;

-- 3. DROP AND RECREATE INDUSTRIES TABLE (to ensure correct structure)
DROP TABLE IF EXISTS post_mentioned_industries CASCADE;
DROP TABLE IF EXISTS industry_daily_sentiment CASCADE;
DROP TABLE IF EXISTS industries CASCADE;

CREATE TABLE industries (
  icb_code text PRIMARY KEY,
  icb_name text NOT NULL,
  en_icb_name text NOT NULL,
  level integer NOT NULL,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now()
);

-- 4. CREATE POST_MENTIONED_INDUSTRIES TABLE
CREATE TABLE post_mentioned_industries (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  post_id uuid NOT NULL,
  icb_code text NOT NULL,
  sentiment text CHECK (sentiment IN ('positive', 'negative', 'neutral')),
  summary text,
  confidence_score decimal(3,2) CHECK (confidence_score >= 0 AND confidence_score <= 1),
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT post_mentioned_industries_post_id_icb_code_key UNIQUE(post_id, icb_code),
  CONSTRAINT post_mentioned_industries_post_id_fkey FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,
  CONSTRAINT post_mentioned_industries_icb_code_fkey FOREIGN KEY (icb_code) REFERENCES industries(icb_code) ON DELETE CASCADE
);

-- 5. DROP AND RECREATE MACRO ECONOMY TABLES
DROP TABLE IF EXISTS post_macro_indicators CASCADE;
DROP TABLE IF EXISTS macro_indicators CASCADE;
DROP TABLE IF EXISTS post_mentioned_macro_themes CASCADE;
DROP TABLE IF EXISTS macro_theme_daily_sentiment CASCADE;
DROP TABLE IF EXISTS macro_themes CASCADE;
DROP TABLE IF EXISTS macro_categories CASCADE;

-- Macro Categories
CREATE TABLE macro_categories (
  id text PRIMARY KEY,
  name text NOT NULL,
  name_en text NOT NULL,
  description text,
  created_at timestamp with time zone DEFAULT now()
);

-- Macro Themes
CREATE TABLE macro_themes (
  id text PRIMARY KEY,
  category_id text,
  name text NOT NULL,
  name_en text NOT NULL,
  description text,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT macro_themes_category_id_fkey FOREIGN KEY (category_id) REFERENCES macro_categories(id) ON DELETE CASCADE
);

-- Post Mentioned Macro Themes
CREATE TABLE post_mentioned_macro_themes (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  post_id uuid NOT NULL,
  macro_theme_id text NOT NULL,
  sentiment text CHECK (sentiment IN ('positive', 'negative', 'neutral')),
  summary text,
  confidence_score decimal(3,2) CHECK (confidence_score >= 0 AND confidence_score <= 1),
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT post_mentioned_macro_themes_post_id_macro_theme_id_key UNIQUE(post_id, macro_theme_id),
  CONSTRAINT post_mentioned_macro_themes_post_id_fkey FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,
  CONSTRAINT post_mentioned_macro_themes_macro_theme_id_fkey FOREIGN KEY (macro_theme_id) REFERENCES macro_themes(id) ON DELETE CASCADE
);

-- Macro Indicators
CREATE TABLE macro_indicators (
  id text PRIMARY KEY,
  theme_id text,
  name text NOT NULL,
  name_en text NOT NULL,
  unit text, -- '%', 'points', 'billion_vnd', etc.
  data_type text, -- 'percentage', 'range', 'absolute_value'
  description text,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT macro_indicators_theme_id_fkey FOREIGN KEY (theme_id) REFERENCES macro_themes(id) ON DELETE CASCADE
);

-- Post Macro Indicators
CREATE TABLE post_macro_indicators (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  post_id uuid NOT NULL,
  macro_indicator_id text NOT NULL,
  current_value text,
  projected_value text,
  time_period text,
  mentioned_context text,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT post_macro_indicators_post_id_macro_indicator_id_key UNIQUE(post_id, macro_indicator_id),
  CONSTRAINT post_macro_indicators_post_id_fkey FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,
  CONSTRAINT post_macro_indicators_macro_indicator_id_fkey FOREIGN KEY (macro_indicator_id) REFERENCES macro_indicators(id) ON DELETE CASCADE
);

-- 6. CREATE DAILY SENTIMENT AGGREGATION TABLES
-- Industry Daily Sentiment
CREATE TABLE industry_daily_sentiment (
  icb_code text,
  date date NOT NULL,
  positive_mentions integer DEFAULT 0,
  negative_mentions integer DEFAULT 0,
  neutral_mentions integer DEFAULT 0,
  overall_sentiment decimal(3,2),
  post_count integer DEFAULT 0,
  summary text,
  created_at timestamp with time zone DEFAULT now(),
  PRIMARY KEY (icb_code, date),
  CONSTRAINT industry_daily_sentiment_icb_code_fkey FOREIGN KEY (icb_code) REFERENCES industries(icb_code) ON DELETE CASCADE
);

-- Macro Theme Daily Sentiment
CREATE TABLE macro_theme_daily_sentiment (
  macro_theme_id text,
  date date NOT NULL,
  positive_mentions integer DEFAULT 0,
  negative_mentions integer DEFAULT 0,
  neutral_mentions integer DEFAULT 0,
  overall_sentiment decimal(3,2),
  post_count integer DEFAULT 0,
  summary text,
  created_at timestamp with time zone DEFAULT now(),
  PRIMARY KEY (macro_theme_id, date),
  CONSTRAINT macro_theme_daily_sentiment_macro_theme_id_fkey FOREIGN KEY (macro_theme_id) REFERENCES macro_themes(id) ON DELETE CASCADE
);

-- 7. INSERT SAMPLE MACRO DATA
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

-- Insert macro indicators (using correct theme_ids from macro_themes table)
INSERT INTO macro_indicators (id, theme_id, name, name_en, unit, data_type, description) VALUES
('vn_index_forecast', 'market_liquidity', 'Dự báo VN Index', 'VN Index Forecast', 'points', 'range', 'Forecasted VN Index trading range'),
('vn_index_current', 'market_liquidity', 'VN Index Hiện tại', 'Current VN Index', 'points', 'absolute_value', 'Current VN Index level'),
('corporate_profit_growth_rate', 'corporate_profit_growth', 'Tỷ lệ Tăng trưởng Lợi nhuận', 'Corporate Profit Growth Rate', '%', 'percentage', 'Year-over-year corporate profit growth'),
('market_pe_ratio', 'market_valuation', 'Tỷ lệ P/E Thị trường', 'Market P/E Ratio', 'ratio', 'absolute_value', 'Market price-to-earnings ratio'),
('market_pe_deviation', 'market_valuation', 'Độ lệch P/E so với TB', 'P/E Deviation from Average', 'standard deviation', 'absolute_value', 'Market P/E deviation from historical average'),
('base_interest_rate', 'interest_rate_trends', 'Lãi suất Cơ bản', 'Base Interest Rate', '%', 'percentage', 'Central bank base interest rate'),
('market_liquidity_growth', 'market_liquidity', 'Tăng trưởng Thanh khoản', 'Market Liquidity Growth', '%', 'percentage', 'Growth in market trading liquidity'),
('gdp_growth_rate', 'global_uncertainty', 'Tỷ lệ Tăng trưởng GDP', 'GDP Growth Rate', '%', 'percentage', 'Economic growth rate'),
('inflation_rate', 'monetary_tightening', 'Tỷ lệ Lạm phát', 'Inflation Rate', '%', 'percentage', 'Consumer price inflation rate')
ON CONFLICT (id) DO NOTHING;

-- 8. CREATE INDEXES FOR PERFORMANCE
CREATE INDEX IF NOT EXISTS idx_post_mentioned_industries_post_id ON post_mentioned_industries(post_id);
CREATE INDEX IF NOT EXISTS idx_post_mentioned_industries_icb_code ON post_mentioned_industries(icb_code);
CREATE INDEX IF NOT EXISTS idx_post_mentioned_macro_themes_post_id ON post_mentioned_macro_themes(post_id);
CREATE INDEX IF NOT EXISTS idx_post_mentioned_macro_themes_theme_id ON post_mentioned_macro_themes(macro_theme_id);
CREATE INDEX IF NOT EXISTS idx_post_macro_indicators_post_id ON post_macro_indicators(post_id);
CREATE INDEX IF NOT EXISTS idx_industry_daily_sentiment_date ON industry_daily_sentiment(date);
CREATE INDEX IF NOT EXISTS idx_macro_theme_daily_sentiment_date ON macro_theme_daily_sentiment(date);
CREATE INDEX IF NOT EXISTS idx_stocks_icb_codes ON stocks(icb_code1, icb_code2, icb_code3, icb_code4);

-- 9. VERIFY THE SETUP
SELECT 'Database schema updates completed successfully!' as status;