-- Database Schema Updates for PDF Content Type Support
-- Add content_type column to sources table to support PDF processing

-- 1. ADD CONTENT_TYPE COLUMN TO SOURCES TABLE (safe to run multiple times)
ALTER TABLE sources ADD COLUMN IF NOT EXISTS content_type text DEFAULT 'text';

-- 2. ADD COLUMNS FOR PDF PROCESSING TO POSTS TABLE
ALTER TABLE posts ADD COLUMN IF NOT EXISTS content_type text DEFAULT 'text';
ALTER TABLE posts ADD COLUMN IF NOT EXISTS pdf_url text;
ALTER TABLE posts ADD COLUMN IF NOT EXISTS markdown_file_path text;

-- 3. ADD CHECK CONSTRAINT FOR CONTENT_TYPE (safe to run multiple times)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'sources_content_type_check'
    ) THEN
        ALTER TABLE sources ADD CONSTRAINT sources_content_type_check CHECK (content_type IN ('text', 'pdf'));
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'posts_content_type_check'
    ) THEN
        ALTER TABLE posts ADD CONSTRAINT posts_content_type_check CHECK (content_type IN ('text', 'pdf'));
    END IF;
END $$;

-- 4. CREATE INDEX FOR CONTENT_TYPE FILTERING
CREATE INDEX IF NOT EXISTS idx_sources_content_type ON sources(content_type);
CREATE INDEX IF NOT EXISTS idx_posts_content_type ON posts(content_type);

-- 5. UPDATE EXISTING SOURCES TO HAVE DEFAULT CONTENT_TYPE
UPDATE sources SET content_type = 'text' WHERE content_type IS NULL;
UPDATE posts SET content_type = 'text' WHERE content_type IS NULL;

-- 6. VERIFY THE SETUP
SELECT 'PDF content type schema updates completed successfully!' as status;