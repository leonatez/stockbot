-- Company Finance Table Creation Script
-- This table stores comprehensive financial data from VNStock including
-- balance sheet, income statement, cash flow, and financial ratios

CREATE TABLE IF NOT EXISTS company_finance (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    stock_id UUID NOT NULL REFERENCES stocks(id) ON DELETE CASCADE,
    symbol TEXT NOT NULL, -- For easier queries
    quarter TEXT, -- Quarter identifier (e.g., "Q1/2024")
    year INTEGER, -- Year
    
    -- Balance Sheet Data
    total_assets NUMERIC, -- Total assets
    current_assets NUMERIC, -- Current assets
    non_current_assets NUMERIC, -- Non-current assets
    total_liabilities NUMERIC, -- Total liabilities
    current_liabilities NUMERIC, -- Current liabilities
    non_current_liabilities NUMERIC, -- Non-current liabilities
    shareholders_equity NUMERIC, -- Total shareholders equity
    
    -- Income Statement Data
    revenue NUMERIC, -- Total revenue
    gross_profit NUMERIC, -- Gross profit
    operating_profit NUMERIC, -- Operating profit
    net_profit NUMERIC, -- Net profit
    ebit NUMERIC, -- Earnings before interest and tax
    ebitda NUMERIC, -- Earnings before interest, tax, depreciation, amortization
    
    -- Cash Flow Data
    operating_cash_flow NUMERIC, -- Cash flow from operations
    investing_cash_flow NUMERIC, -- Cash flow from investing
    financing_cash_flow NUMERIC, -- Cash flow from financing
    net_cash_flow NUMERIC, -- Net cash flow
    free_cash_flow NUMERIC, -- Free cash flow
    
    -- Financial Ratios
    eps NUMERIC, -- Earnings per share
    book_value_per_share NUMERIC, -- Book value per share
    roe NUMERIC, -- Return on equity (%)
    roa NUMERIC, -- Return on assets (%)
    current_ratio NUMERIC, -- Current ratio
    debt_to_equity NUMERIC, -- Debt to equity ratio
    profit_margin NUMERIC, -- Profit margin (%)
    revenue_growth NUMERIC, -- Revenue growth (%)
    
    -- Additional financial data (JSON for flexibility)
    additional_data JSONB, -- Store any additional columns from VNStock
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    UNIQUE(stock_id, quarter, year) -- Prevent duplicate entries for same stock/quarter
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_company_finance_stock_id ON company_finance(stock_id);
CREATE INDEX IF NOT EXISTS idx_company_finance_symbol ON company_finance(symbol);
CREATE INDEX IF NOT EXISTS idx_company_finance_quarter ON company_finance(quarter);
CREATE INDEX IF NOT EXISTS idx_company_finance_year ON company_finance(year);
CREATE INDEX IF NOT EXISTS idx_company_finance_created_at ON company_finance(created_at);

-- Create a view for easy access to finance data with stock information
CREATE OR REPLACE VIEW company_finance_with_stock AS
SELECT 
    cf.*,
    s.organ_name,
    s.organ_short_name,
    s.exchange,
    s.isvn30
FROM company_finance cf
JOIN stocks s ON cf.stock_id = s.id
ORDER BY cf.symbol, cf.year DESC, cf.quarter DESC;

COMMENT ON TABLE company_finance IS 'Comprehensive financial data for Vietnamese stocks including balance sheet, income statement, cash flow, and ratios';
COMMENT ON COLUMN company_finance.additional_data IS 'JSON storage for additional financial metrics from VNStock that do not fit standard columns';