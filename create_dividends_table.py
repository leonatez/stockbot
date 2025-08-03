"""
Script to create the stock_dividends table in Supabase
"""

import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

def create_dividends_table():
    """Create the stock_dividends table in Supabase"""
    url = os.getenv("SUPABASE_URL")
    service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    if not url or not service_role_key:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
    
    supabase = create_client(url, service_role_key)
    
    # Read the SQL file
    with open('create_stock_dividends_table.sql', 'r') as f:
        sql_commands = f.read()
    
    try:
        # Execute the SQL commands
        result = supabase.rpc('exec_sql', {'sql': sql_commands}).execute()
        print("✓ Successfully created stock_dividends table")
        return True
    except Exception as e:
        print(f"Error creating table: {e}")
        print("You may need to manually execute the SQL in Supabase dashboard")
        return False

if __name__ == "__main__":
    create_dividends_table()