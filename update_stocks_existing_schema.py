#!/usr/bin/env python3
"""
Script to update stocks table with data that matches the current schema.
This version works with the existing schema before schema changes are applied.
"""

import os
import sys
from typing import Dict, Any
import pandas as pd
from vnstock import Vnstock, Listing
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

def all_stocks() -> pd.DataFrame:
    """Get all stock data using vnstock library."""
    listing = Listing()
    
    # Get base data
    by_exchange = listing.symbols_by_exchange()
    print(f"✓ Retrieved {len(by_exchange)} stocks from exchange data")
    
    return by_exchange

def update_stocks_basic():
    """Update the stocks table with basic vnstock data that matches current schema"""
    
    print("Fetching basic stock data from vnstock...")
    try:
        stocks_df = all_stocks()
        print(f"✓ Retrieved {len(stocks_df)} stocks from vnstock")
    except Exception as e:
        print(f"✗ Error fetching stock data: {e}")
        return False
    
    print("Connecting to Supabase...")
    try:
        supabase = get_supabase_client()
        print("✓ Connected to Supabase")
    except Exception as e:
        print(f"✗ Error connecting to Supabase: {e}")
        return False
    
    print("Updating stocks table with basic information...")
    success_count = 0
    error_count = 0
    
    for _, row in stocks_df.iterrows():
        try:
            # Map to current schema: id, symbol, name, exchange, industry_id, sector, listed_date, description
            stock_data = {
                'symbol': row['symbol'],
                'name': row['organ_name'],  # Map organ_name to name
                'exchange': row['exchange']
                # Skip other fields for now as they don't exist in vnstock data
            }
            
            # Upsert the stock
            result = supabase.table("stocks").upsert(
                stock_data,
                on_conflict='symbol'
            ).execute()
            
            success_count += 1
            if success_count % 100 == 0:
                print(f"  Processed {success_count} stocks...")
                
        except Exception as e:
            print(f"✗ Error updating stock {row['symbol']}: {e}")
            error_count += 1
            if error_count > 10:  # Stop after too many errors
                print("Too many errors, stopping...")
                break
    
    print(f"\n✓ Basic stock update completed:")
    print(f"  Successfully updated: {success_count} stocks")
    print(f"  Errors: {error_count} stocks")
    
    return error_count == 0

if __name__ == "__main__":
    print("Starting basic stocks table update...")
    success = update_stocks_basic()
    
    if success:
        print("\n🎉 Basic stocks update completed successfully!")
        print("\nNext steps:")
        print("1. Apply schema changes in Supabase dashboard using update_stocks_schema.sql")
        print("2. Run update_stocks_data.py to populate full vnstock data")
    else:
        print("\n⚠️  Basic stocks update completed with errors.")
        sys.exit(1)