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
        # Split SQL commands and execute them one by one
        commands = [cmd.strip() for cmd in sql_commands.split(';') if cmd.strip()]
        
        for command in commands:
            if command.upper().startswith(('CREATE', 'ALTER')):
                # Use postrest client to execute DDL
                result = supabase.postgrest.rpc('exec', {'query': command}).execute()
                print(f"✓ Executed: {command[:50]}...")
        
        print("✓ Successfully created stock_dividends table and indexes")
        return True
    except Exception as e:
        print(f"Error creating table: {e}")
        print("Let me try manual table creation...")
        
        # Try creating table manually using the supabase client
        try:
            # Create the table using a simple insert operation to test connection
            # then create table using raw SQL
            import requests
            
            headers = {
                'apikey': service_role_key,
                'Authorization': f'Bearer {service_role_key}',
                'Content-Type': 'application/json'
            }
            
            # Use the REST API to execute SQL
            sql_url = f"{url}/rest/v1/rpc/exec"
            response = requests.post(sql_url, headers=headers, json={'sql': sql_commands})
            
            if response.status_code == 200:
                print("✓ Successfully created stock_dividends table via REST API")
                return True
            else:
                print(f"REST API failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e2:
            print(f"Manual creation also failed: {e2}")
            print("Please manually execute the SQL in Supabase dashboard")
            return False

if __name__ == "__main__":
    create_dividends_table()