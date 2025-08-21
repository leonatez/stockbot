-- Fix for database schema issues
-- This script addresses the "column stock_prices.symbol does not exist" error

-- First, let's check the current structure of stock_prices table
-- and fix the column name issue

-- Option 1: If the column is named differently (e.g., 'stock_symbol' instead of 'symbol')
-- Add alias to make it work with existing code
DO $$
BEGIN
    -- Check if 'symbol' column exists
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'stock_prices' 
        AND column_name = 'symbol'
    ) THEN
        -- Check if 'stock_symbol' column exists instead
        IF EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'stock_prices' 
            AND column_name = 'stock_symbol'
        ) THEN
            -- Add a computed column/view or rename
            ALTER TABLE stock_prices ADD COLUMN symbol TEXT;
            UPDATE stock_prices SET symbol = stock_symbol WHERE symbol IS NULL;
            
            -- Create index for performance
            CREATE INDEX IF NOT EXISTS idx_stock_prices_symbol ON stock_prices(symbol);
            
        ELSE
            -- Create the missing column
            ALTER TABLE stock_prices ADD COLUMN symbol TEXT NOT NULL DEFAULT '';
            ALTER TABLE stock_prices ADD COLUMN stock_symbol TEXT NOT NULL DEFAULT '';
            
            -- Create indexes
            CREATE INDEX IF NOT EXISTS idx_stock_prices_symbol ON stock_prices(symbol);
            CREATE INDEX IF NOT EXISTS idx_stock_prices_stock_symbol ON stock_prices(stock_symbol);
        END IF;
    END IF;
END $$;

-- Option 2: Ensure stock_prices table has the correct structure
CREATE TABLE IF NOT EXISTS stock_prices (
    id BIGSERIAL PRIMARY KEY,
    symbol TEXT NOT NULL,
    stock_symbol TEXT NOT NULL,
    date DATE NOT NULL,
    open DECIMAL(15, 2),
    high DECIMAL(15, 2),
    low DECIMAL(15, 2),
    close DECIMAL(15, 2),
    volume BIGINT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_stock_prices_symbol_date ON stock_prices(symbol, date DESC);
CREATE INDEX IF NOT EXISTS idx_stock_prices_stock_symbol_date ON stock_prices(stock_symbol, date DESC);
CREATE INDEX IF NOT EXISTS idx_stock_prices_date ON stock_prices(date DESC);

-- Update trigger for updated_at
CREATE OR REPLACE FUNCTION update_stock_prices_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER IF NOT EXISTS trigger_update_stock_prices_updated_at
    BEFORE UPDATE ON stock_prices
    FOR EACH ROW
    EXECUTE FUNCTION update_stock_prices_updated_at();

-- Ensure both columns have the same data for compatibility
UPDATE stock_prices 
SET symbol = stock_symbol 
WHERE symbol IS NULL OR symbol = '';

UPDATE stock_prices 
SET stock_symbol = symbol 
WHERE stock_symbol IS NULL OR stock_symbol = '';

-- Add constraints to keep them in sync
CREATE OR REPLACE FUNCTION sync_stock_symbol_columns()
RETURNS TRIGGER AS $$
BEGIN
    -- If symbol is updated, update stock_symbol
    IF NEW.symbol IS DISTINCT FROM OLD.symbol THEN
        NEW.stock_symbol = NEW.symbol;
    END IF;
    
    -- If stock_symbol is updated, update symbol  
    IF NEW.stock_symbol IS DISTINCT FROM OLD.stock_symbol THEN
        NEW.symbol = NEW.stock_symbol;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER IF NOT EXISTS trigger_sync_stock_symbol_columns
    BEFORE UPDATE ON stock_prices
    FOR EACH ROW
    EXECUTE FUNCTION sync_stock_symbol_columns();