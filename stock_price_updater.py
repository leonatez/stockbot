#!/usr/bin/env python3
"""
Stock Price History Updater
This module handles fetching and updating stock price history for mentioned stocks.
It optimizes queries by only fetching data from the latest date in database to today.
"""

import os
import sys
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import pandas as pd
from vnstock import Vnstock
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

def get_latest_price_date(symbol: str, supabase: Client) -> Optional[str]:
    """
    Get the latest date for which we have price data for a stock.
    
    Args:
        symbol: Stock symbol
        supabase: Supabase client
        
    Returns:
        Latest date as string (YYYY-MM-DD) or None if no data exists
    """
    try:
        # Get stock_id first
        stock_result = supabase.table("stocks").select("id").eq("symbol", symbol).execute()
        
        if not stock_result.data:
            print(f"⚠️  Stock {symbol} not found in database")
            return None
        
        stock_id = stock_result.data[0]["id"]
        
        # Get latest price date
        price_result = supabase.table("stock_prices").select("date").eq("stock_id", stock_id).order("date", desc=True).limit(1).execute()
        
        if price_result.data:
            latest_date = price_result.data[0]["date"]
            print(f"  Latest price data for {symbol}: {latest_date}")
            return latest_date
        else:
            print(f"  No existing price data for {symbol}")
            return None
            
    except Exception as e:
        print(f"✗ Error getting latest price date for {symbol}: {e}")
        return None

def fetch_stock_quotes(symbol: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
    """
    Fetch stock quote history from vnstock.
    
    Args:
        symbol: Stock symbol
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        
    Returns:
        DataFrame with price data or None if error
    """
    try:
        stock = Vnstock().stock(symbol=symbol, source='VCI')
        df = stock.quote.history(start=start_date, end=end_date, interval='1D')
        
        if df is not None and not df.empty:
            print(f"  ✓ Fetched {len(df)} price records for {symbol} ({start_date} to {end_date})")
            return df
        else:
            print(f"  ⚠️  No price data available for {symbol}")
            return None
            
    except Exception as e:
        print(f"  ✗ Error fetching quotes for {symbol}: {e}")
        return None

def save_stock_prices(symbol: str, price_df: pd.DataFrame, supabase: Client) -> bool:
    """
    Save stock price data to database.
    
    Args:
        symbol: Stock symbol
        price_df: DataFrame with price data
        supabase: Supabase client
        
    Returns:
        True if successful
    """
    try:
        # Get stock_id
        stock_result = supabase.table("stocks").select("id").eq("symbol", symbol).execute()
        
        if not stock_result.data:
            print(f"  ✗ Stock {symbol} not found in database")
            return False
        
        stock_id = stock_result.data[0]["id"]
        
        # Prepare price data for insertion
        price_records = []
        for _, row in price_df.iterrows():
            # Use the 'time' column for date
            if 'time' in row and pd.notna(row['time']):
                # Parse the time column to get date string
                try:
                    if isinstance(row['time'], str):
                        date_str = pd.to_datetime(row['time']).strftime('%Y-%m-%d')
                    else:
                        date_str = row['time'].strftime('%Y-%m-%d')
                except:
                    print(f"  ⚠️  Could not parse time value: {row['time']}")
                    continue
            else:
                print(f"  ⚠️  No time column found in row")
                continue
            
            price_record = {
                "stock_id": stock_id,
                "date": date_str,
                "open": float(row['open']) if pd.notna(row['open']) else None,
                "high": float(row['high']) if pd.notna(row['high']) else None,
                "low": float(row['low']) if pd.notna(row['low']) else None,
                "close": float(row['close']) if pd.notna(row['close']) else None,
                "volume": int(row['volume']) if pd.notna(row['volume']) else None
            }
            price_records.append(price_record)
        
        # Insert price data (handle duplicates by inserting one by one)
        if price_records:
            saved_count = 0
            for record in price_records:
                try:
                    result = supabase.table("stock_prices").upsert(
                        record,
                        on_conflict='stock_id,date'
                    ).execute()
                    saved_count += 1
                except Exception as record_error:
                    # Skip duplicates or other errors for individual records
                    print(f"    ⚠️  Skipped record for {record['date']}: {record_error}")
                    continue
            
            print(f"  ✓ Saved {saved_count}/{len(price_records)} price records for {symbol}")
            return saved_count > 0
        else:
            print(f"  ⚠️  No valid price records to save for {symbol}")
            return False
            
    except Exception as e:
        print(f"  ✗ Error saving prices for {symbol}: {e}")
        return False

def update_stock_prices_for_symbols(stock_symbols: List[str]) -> Dict[str, bool]:
    """
    Update stock price history for a list of stock symbols.
    Only fetches data from the latest date in database to today.
    
    Args:
        stock_symbols: List of stock symbols to update
        
    Returns:
        Dictionary mapping symbol to success status
    """
    print(f"\n🔄 Starting price update for {len(stock_symbols)} stocks...")
    
    supabase = get_supabase_client()
    today = datetime.now().strftime('%Y-%m-%d')
    results = {}
    
    for symbol in stock_symbols:
        print(f"\n📊 Processing {symbol}:")
        
        try:
            # Get latest date we have data for
            latest_date = get_latest_price_date(symbol, supabase)
            
            # Determine start date for fetching
            if latest_date:
                # Start from day after latest date
                latest_dt = datetime.strptime(latest_date, '%Y-%m-%d')
                start_date = (latest_dt + timedelta(days=1)).strftime('%Y-%m-%d')
                
                # Skip if we're already up to date
                if start_date > today:
                    print(f"  ✓ {symbol} is already up to date")
                    results[symbol] = True
                    continue
            else:
                # No existing data, fetch from January 1, 2024
                start_date = '2024-01-01'
            
            print(f"  Fetching from {start_date} to {today}")
            
            # Fetch quote data
            price_df = fetch_stock_quotes(symbol, start_date, today)
            
            if price_df is not None:
                # Save to database
                success = save_stock_prices(symbol, price_df, supabase)
                results[symbol] = success
            else:
                results[symbol] = False
                
        except Exception as e:
            print(f"  ✗ Error processing {symbol}: {e}")
            results[symbol] = False
    
    # Summary
    successful = sum(1 for success in results.values() if success)
    print(f"\n📈 Price update summary:")
    print(f"  Successfully updated: {successful}/{len(stock_symbols)} stocks")
    
    for symbol, success in results.items():
        status = "✓" if success else "✗"
        print(f"  {status} {symbol}")
    
    return results

def update_mentioned_stocks_prices(mentioned_stocks_data: List[Dict[str, Any]]) -> Dict[str, bool]:
    """
    Extract stock symbols from AI analysis results and update their price history.
    
    Args:
        mentioned_stocks_data: List of stock mentions from AI analysis
        
    Returns:
        Dictionary mapping symbol to update success status
    """
    # Extract unique stock symbols
    stock_symbols = set()
    
    for stock_mention in mentioned_stocks_data:
        if 'stock_symbol' in stock_mention:
            stock_symbols.add(stock_mention['stock_symbol'])
        elif 'symbol' in stock_mention:
            stock_symbols.add(stock_mention['symbol'])
    
    stock_symbols = list(stock_symbols)
    
    if not stock_symbols:
        print("⚠️  No stock symbols found in mentioned stocks data")
        return {}
    
    print(f"📊 Found {len(stock_symbols)} unique stocks to update: {', '.join(stock_symbols)}")
    
    return update_stock_prices_for_symbols(stock_symbols)

if __name__ == "__main__":
    # Test with sample symbols
    test_symbols = ["ACB", "HPG", "VPB"]
    results = update_stock_prices_for_symbols(test_symbols)
    print(f"\nTest results: {results}")