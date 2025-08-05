#!/bin/bash
# Start script for Render deployment

echo "Starting FastAPI application..."
echo "PORT: $PORT"
echo "Environment check..."

# Check if required environment variables are set
if [ -z "$SUPABASE_URL" ]; then
    echo "ERROR: SUPABASE_URL not set"
    exit 1
fi

if [ -z "$SUPABASE_SERVICE_ROLE_KEY" ]; then
    echo "ERROR: SUPABASE_SERVICE_ROLE_KEY not set"
    exit 1
fi

if [ -z "$GEMINI_API_KEY" ]; then
    echo "ERROR: GEMINI_API_KEY not set"
    exit 1
fi

echo "All environment variables are set"

# Start the application
python main.py