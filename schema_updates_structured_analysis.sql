-- Schema updates for structured analysis in post_mentioned_stocks table
-- This adds columns to store the detailed structured analysis from Gemini

-- Add structured analysis columns to post_mentioned_stocks table
ALTER TABLE post_mentioned_stocks 
ADD COLUMN IF NOT EXISTS structured_analysis JSONB,
ADD COLUMN IF NOT EXISTS ket_qua_kinh_doanh_quy JSONB,
ADD COLUMN IF NOT EXISTS luy_ke_6t_nam JSONB,
ADD COLUMN IF NOT EXISTS phan_tich_mang_kinh_doanh JSONB,
ADD COLUMN IF NOT EXISTS tai_chinh_dong_tien JSONB,
ADD COLUMN IF NOT EXISTS trien_vong JSONB,
ADD COLUMN IF NOT EXISTS rui_ro JSONB,
ADD COLUMN IF NOT EXISTS dinh_gia_khuyen_nghi JSONB;

-- Create index for efficient structured analysis queries
CREATE INDEX IF NOT EXISTS idx_post_mentioned_stocks_structured_analysis 
ON post_mentioned_stocks USING GIN (structured_analysis);

-- Update comment for table documentation
COMMENT ON TABLE post_mentioned_stocks IS 'Links posts to stocks they mention with sentiment analysis and structured financial analysis';
COMMENT ON COLUMN post_mentioned_stocks.structured_analysis IS 'Complete structured analysis from Gemini in JSON format';
COMMENT ON COLUMN post_mentioned_stocks.ket_qua_kinh_doanh_quy IS 'Quarterly business results analysis';
COMMENT ON COLUMN post_mentioned_stocks.luy_ke_6t_nam IS 'Cumulative 6-month/year performance analysis';
COMMENT ON COLUMN post_mentioned_stocks.phan_tich_mang_kinh_doanh IS 'Business segment analysis';
COMMENT ON COLUMN post_mentioned_stocks.tai_chinh_dong_tien IS 'Financial and cash flow analysis';
COMMENT ON COLUMN post_mentioned_stocks.trien_vong IS 'Outlook and forecasts';
COMMENT ON COLUMN post_mentioned_stocks.rui_ro IS 'Risk factors analysis';
COMMENT ON COLUMN post_mentioned_stocks.dinh_gia_khuyen_nghi IS 'Valuation and recommendations';