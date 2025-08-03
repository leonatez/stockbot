#!/usr/bin/env python3
"""
Script to update the stocks table schema via Supabase Python client.
This script will execute the SQL schema changes.
"""

import os
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_supabase_client() -> Client:
    """Initialize Supabase client"""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in environment")
    
    return create_client(url, key)

def update_schema():
    """Update the stocks table schema"""
    
    print("Connecting to Supabase...")
    supabase = get_supabase_client()
    print("✓ Connected to Supabase")
    
    # Read the SQL file
    with open('/home/linh-nguyen/AI_lab/stockbot/update_stocks_schema.sql', 'r') as f:
        sql_content = f.read()
    
    print("Executing schema update...")
    try:
        # Execute the SQL via RPC call
        result = supabase.rpc('exec_sql', {'sql_query': sql_content}).execute()
        print("✓ Schema update completed successfully")
        return True
    except Exception as e:
        print(f"✗ Error executing schema update: {e}")
        print("This might be expected if the RPC function doesn't exist.")
        print("The schema changes need to be applied manually in Supabase dashboard.")
        return False

if __name__ == "__main__":
    print("Starting schema update...")
    update_schema()