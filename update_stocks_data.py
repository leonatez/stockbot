#!/usr/bin/env python3
"""
Script to update stocks table with fresh data from vnstock all_stocks function.
This script will:
1. Fetch all stock data using vnstock
2. Update existing stocks with new information
3. Insert new stocks that don't exist in the database
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
    """
    Get all stock data using vnstock library.
    Returns DataFrame with columns: symbol, exchange, organ_short_name, organ_name, 
    isVN30, icb_name1, icb_name2, icb_name3, icb_name4
    """
    listing = Listing()
    
    # Get base data
    by_exchange = listing.symbols_by_exchange()
    by_industries = listing.symbols_by_industries()
    
    # Clean industries data
    columns_to_drop = ['organ_name', 'icb_name3','icb_name2','icb_name4','com_type_code']
    by_industries.drop(columns=[col for col in columns_to_drop if col in by_industries.columns], inplace=True)
    
    # Get VN30 list
    try:
        vn30_list = listing.symbols_by_group('VN30')
        vn30_symbols = set(vn30_list.tolist()) if vn30_list is not None else set()
    except Exception as e:
        print(f"Warning: Could not fetch VN30 list: {e}")
        vn30_symbols = set()
    
    # Merge data
    merged_data = pd.merge(by_exchange, by_industries, on='symbol', how='inner')
    merged_data['isVN30'] = merged_data['symbol'].apply(lambda x: x in vn30_symbols)
    
    # Get ICB mapping for industry names
    try:
        icb_mapping = listing.industries_icb()
        icb_dict = {}
        for level in [1, 2, 3, 4]:
            level_data = icb_mapping[icb_mapping['level'] == level]
            icb_dict[level] = dict(zip(level_data['icb_code'], level_data['icb_name']))
        
        # Map ICB codes to names
        result_df = merged_data.copy()
        for level in [1, 2, 3, 4]:
            code_col = f'icb_code{level}'
            name_col = f'icb_name{level}'
            
            if code_col in result_df.columns:
                result_df[name_col] = result_df[code_col].map(icb_dict[level]).fillna('Unknown')
            else:
                print(f"Warning: {code_col} not found in dataframe")
                result_df[name_col] = 'Unknown'
        
        # Drop ICB codes and other unnecessary columns
        columns_to_drop = ['icb_code1', 'icb_code2', 'icb_code3','icb_code4','type','product_grp_id']
        result_df.drop(columns=[col for col in columns_to_drop if col in result_df.columns], inplace=True)
        
    except Exception as e:
        print(f"Warning: Could not process ICB mapping: {e}")
        result_df = merged_data.copy()
        # Add empty ICB columns
        for level in [1, 2, 3, 4]:
            result_df[f'icb_name{level}'] = 'Unknown'
    
    return result_df

def update_stocks_table():
    """Update the stocks table with fresh vnstock data"""
    
    print("Fetching stock data from vnstock...")
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
    
    print("Updating stocks table...")
    success_count = 0
    error_count = 0
    
    for _, row in stocks_df.iterrows():
        try:
            # Prepare data for upsert
            stock_data = {
                'symbol': row['symbol'],
                'organ_name': row['organ_name'],
                'exchange': row['exchange'], 
                'organ_short_name': row['organ_short_name'],
                'isvn30': bool(row['isVN30']),
                'icb_name1': row['icb_name1'],
                'icb_name2': row['icb_name2'],
                'icb_name3': row['icb_name3'], 
                'icb_name4': row['icb_name4']
            }
            
            # Upsert (insert or update) the stock
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
    
    print(f"\n✓ Stock update completed:")
    print(f"  Successfully updated: {success_count} stocks")
    print(f"  Errors: {error_count} stocks")
    
    return error_count == 0

if __name__ == "__main__":
    print("Starting stocks table update...")
    success = update_stocks_table()
    
    if success:
        print("\n🎉 Stocks table update completed successfully!")
    else:
        print("\n⚠️  Stocks table update completed with some errors.")
        sys.exit(1)