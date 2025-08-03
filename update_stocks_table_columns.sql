-- Add missing columns to stocks table for company information
-- These columns are needed for the new company information features

-- Add issue_share column if it doesn't exist
DO $$ 
BEGIN 
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'stocks' AND column_name = 'issue_share') THEN
        ALTER TABLE stocks ADD COLUMN issue_share BIGINT;
        COMMENT ON COLUMN stocks.issue_share IS 'Number of issued shares';
    END IF;
END $$;

-- Add charter_capital column if it doesn't exist
DO $$ 
BEGIN 
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'stocks' AND column_name = 'charter_capital') THEN
        ALTER TABLE stocks ADD COLUMN charter_capital DECIMAL(20,2);
        COMMENT ON COLUMN stocks.charter_capital IS 'Company charter capital';
    END IF;
END $$;

-- Add organ_name column if it doesn't exist (official company name)
DO $$ 
BEGIN 
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'stocks' AND column_name = 'organ_name') THEN
        ALTER TABLE stocks ADD COLUMN organ_name TEXT;
        COMMENT ON COLUMN stocks.organ_name IS 'Official company name';
    END IF;
END $$;

-- Add isvn30 column if it doesn't exist
DO $$ 
BEGIN 
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'stocks' AND column_name = 'isvn30') THEN
        ALTER TABLE stocks ADD COLUMN isvn30 BOOLEAN DEFAULT FALSE;
        COMMENT ON COLUMN stocks.isvn30 IS 'Whether stock is in VN30 index';
    END IF;
END $$;

-- Add created_at column if it doesn't exist
DO $$ 
BEGIN 
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'stocks' AND column_name = 'created_at') THEN
        ALTER TABLE stocks ADD COLUMN created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();
        COMMENT ON COLUMN stocks.created_at IS 'Record creation timestamp';
    END IF;
END $$;

-- Add updated_at column if it doesn't exist
DO $$ 
BEGIN 
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'stocks' AND column_name = 'updated_at') THEN
        ALTER TABLE stocks ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();
        COMMENT ON COLUMN stocks.updated_at IS 'Record last update timestamp';
    END IF;
END $$;

-- Create or update the trigger for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Drop trigger if exists and recreate
DROP TRIGGER IF EXISTS update_stocks_updated_at ON stocks;
CREATE TRIGGER update_stocks_updated_at 
    BEFORE UPDATE ON stocks 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();