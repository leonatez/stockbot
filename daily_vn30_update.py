#!/usr/bin/env python3
"""
Daily VN30 Update Workflow
This script updates the isVN30 column in the stocks table based on current VN30 membership.
Should be run daily as part of the analysis workflow.
"""

import os
import sys
from typing import List, Set
from vnstock import Listing
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

def get_vn30_symbols() -> Set[str]:
    """
    Fetch current VN30 stock symbols from vnstock.
    Returns a set of stock symbols that are currently in the VN30 index.
    """
    try:
        listing = Listing()
        vn30_list = listing.symbols_by_group('VN30')
        
        if vn30_list is not None:
            vn30_symbols = set(vn30_list.tolist())
            print(f"✓ Retrieved {len(vn30_symbols)} VN30 stocks")
            print(f"  VN30 stocks: {', '.join(sorted(vn30_symbols))}")
            return vn30_symbols
        else:
            print("⚠️  VN30 list is empty or None")
            return set()
            
    except Exception as e:
        print(f"✗ Error fetching VN30 list: {e}")
        return set()

def update_vn30_status(vn30_symbols: Set[str]) -> bool:
    """
    Update the isVN30 column in the stocks table.
    
    Args:
        vn30_symbols: Set of stock symbols that are in VN30
        
    Returns:
        bool: True if update was successful
    """
    try:
        supabase = get_supabase_client()
        print("✓ Connected to Supabase")
        
        # First, set all stocks isVN30 = False
        print("Resetting all stocks isVN30 to False...")
        result = supabase.table("stocks").update({"isvn30": False}).neq("symbol", "").execute()
        
        if not result.data:
            print("⚠️  No stocks found to reset")
        else:
            print(f"✓ Reset isVN30 for all stocks")
        
        # Then, set VN30 stocks isVN30 = True
        if vn30_symbols:
            print(f"Updating {len(vn30_symbols)} VN30 stocks...")
            
            success_count = 0
            error_count = 0
            
            for symbol in vn30_symbols:
                try:
                    result = supabase.table("stocks").update(
                        {"isvn30": True}
                    ).eq("symbol", symbol).execute()
                    
                    if result.data:
                        success_count += 1
                    else:
                        print(f"⚠️  Stock {symbol} not found in database")
                        error_count += 1
                        
                except Exception as e:
                    print(f"✗ Error updating {symbol}: {e}")
                    error_count += 1
            
            print(f"✓ VN30 update completed:")
            print(f"  Successfully updated: {success_count} stocks")
            print(f"  Not found/errors: {error_count} stocks")
            
            return error_count == 0
        else:
            print("⚠️  No VN30 symbols to update")
            return True
            
    except Exception as e:
        print(f"✗ Error updating VN30 status: {e}")
        return False

def daily_vn30_update() -> bool:
    """
    Main function to perform daily VN30 update.
    This should be called at the beginning of daily analysis workflow.
    
    Returns:
        bool: True if update was successful
    """
    print("🔄 Starting daily VN30 update...")
    
    # Step 1: Get current VN30 symbols
    vn30_symbols = get_vn30_symbols()
    
    if not vn30_symbols:
        print("⚠️  No VN30 symbols retrieved, skipping update")
        return False
    
    # Step 2: Update database
    success = update_vn30_status(vn30_symbols)
    
    if success:
        print("🎉 Daily VN30 update completed successfully!")
    else:
        print("⚠️  Daily VN30 update completed with errors")
    
    return success

if __name__ == "__main__":
    print("Running daily VN30 update...")
    success = daily_vn30_update()
    
    if not success:
        sys.exit(1)