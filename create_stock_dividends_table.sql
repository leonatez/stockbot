-- Create stock_dividends table to track company dividend information
CREATE TABLE IF NOT EXISTS stock_dividends (
    id SERIAL PRIMARY KEY,
    stock_id INTEGER REFERENCES stocks(id) ON DELETE CASCADE,
    exercise_date DATE,
    cash_year INTEGER,
    cash_dividend_percentage DECIMAL(10,4),
    issue_method TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Unique constraint to prevent duplicate dividend records
    UNIQUE(stock_id, exercise_date, cash_year)
);

-- Create index for better query performance
CREATE INDEX IF NOT EXISTS idx_stock_dividends_stock_id ON stock_dividends(stock_id);
CREATE INDEX IF NOT EXISTS idx_stock_dividends_exercise_date ON stock_dividends(exercise_date);

-- Add RLS (Row Level Security) if needed
-- ALTER TABLE stock_dividends ENABLE ROW LEVEL SECURITY;