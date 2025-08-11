-- Add content_type column to sources table for PDF support
ALTER TABLE sources 
ADD COLUMN IF NOT EXISTS content_type text 
DEFAULT 'text' 
CHECK (content_type IN ('text', 'pdf'));

-- Update any existing sources to have the default content_type
UPDATE sources SET content_type = 'text' WHERE content_type IS NULL;