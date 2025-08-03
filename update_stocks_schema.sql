-- Update stocks table schema to match all_stocks function output
-- This script will modify the existing stocks table and populate it with fresh data

BEGIN;

-- Step 1: Remove unused columns (listed_date and sector)
ALTER TABLE stocks DROP COLUMN IF EXISTS listed_date;
ALTER TABLE stocks DROP COLUMN IF EXISTS sector;

-- Step 2: Remove industry_id column since we'll use ICB classification instead
ALTER TABLE stocks DROP COLUMN IF EXISTS industry_id;

-- Step 3: Rename and modify existing columns to match new schema
-- Rename 'name' to 'organ_name' (full legal name)
ALTER TABLE stocks RENAME COLUMN name TO organ_name;

-- Step 4: Add new columns for vnstock data
ALTER TABLE stocks ADD COLUMN IF NOT EXISTS organ_short_name TEXT;
ALTER TABLE stocks ADD COLUMN IF NOT EXISTS isVN30 BOOLEAN DEFAULT FALSE;
ALTER TABLE stocks ADD COLUMN IF NOT EXISTS icb_name1 TEXT; -- General sector
ALTER TABLE stocks ADD COLUMN IF NOT EXISTS icb_name2 TEXT; -- Industry
ALTER TABLE stocks ADD COLUMN IF NOT EXISTS icb_name3 TEXT; -- Sub-industry  
ALTER TABLE stocks ADD COLUMN IF NOT EXISTS icb_name4 TEXT; -- Specific sector

-- Step 5: Update description column to be nullable (in case we don't have descriptions for all stocks)
ALTER TABLE stocks ALTER COLUMN description DROP NOT NULL;

-- The final schema will be:
-- id (UUID, Primary Key): Unique identifier
-- symbol (TEXT, UNIQUE): Stock ticker symbol  
-- organ_name (TEXT): Full legal name of the company
-- exchange (TEXT): Trading exchange (HSX, HNX, UPCOM)
-- organ_short_name (TEXT): Short name of the company
-- isVN30 (BOOLEAN): Whether stock is in VN30 index
-- icb_name1 (TEXT): ICB Level 1 classification
-- icb_name2 (TEXT): ICB Level 2 classification  
-- icb_name3 (TEXT): ICB Level 3 classification
-- icb_name4 (TEXT): ICB Level 4 classification
-- description (TEXT): Company description (optional)

COMMIT;