"""
Company Information Updater using VNStock library
Fetches and updates company overview, events, and dividends for mentioned stocks
"""

import pandas as pd
from datetime import datetime
from typing import List, Dict, Any, Optional
from database import db_service

# Import vnstock components individually to avoid conflicts
try:
    from vnstock import Vnstock
    from vnstock.explorer.vci import Company
    VNSTOCK_AVAILABLE = True
except ImportError as e:
    print(f"VNStock import error: {e}")
    print("Company information features will be disabled until VNStock is properly installed")
    VNSTOCK_AVAILABLE = False


async def update_company_information(stock_symbols: List[str]) -> Dict[str, bool]:
    """
    Update company information for a list of stock symbols
    
    Args:
        stock_symbols: List of stock symbols to update (e.g., ['ACB', 'HPG', 'VPB'])
        
    Returns:
        Dictionary with stock symbols as keys and success status as values
    """
    if not VNSTOCK_AVAILABLE:
        print("VNStock not available - company information update skipped")
        return {symbol: False for symbol in stock_symbols}
    
    results = {}
    
    for symbol in stock_symbols:
        try:
            print(f"\n=== Updating company info for {symbol} ===")
            
            # Update company overview (issue_share, charter_capital)
            overview_success = await update_company_overview(symbol)
            
            # Update company events
            events_success = await update_company_events(symbol)
            
            # Update company dividends
            dividends_success = await update_company_dividends(symbol)
            
            # Consider successful if at least one update worked
            results[symbol] = overview_success or events_success or dividends_success
            
            if results[symbol]:
                print(f"✓ Company info update completed for {symbol}")
            else:
                print(f"⚠️ No company info could be updated for {symbol}")
                
        except Exception as e:
            print(f"✗ Error updating company info for {symbol}: {e}")
            results[symbol] = False
    
    return results


async def update_company_overview(stock_symbol: str) -> bool:
    """
    Update company overview information (issue_share, charter_capital)
    
    Args:
        stock_symbol: Stock symbol (e.g., 'ACB')
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        print(f"Fetching company overview for {stock_symbol}...")
        
        # Create Company instance for overview
        company = Company(stock_symbol)
        
        # Get company overview data
        overview_df = company.overview()
        
        if overview_df is None or overview_df.empty:
            print(f"No overview data available for {stock_symbol}")
            return False
        
        # Extract the first row (should be for our stock symbol)
        overview_data = overview_df.iloc[0].to_dict()
        
        # Prepare data for database update
        db_overview_data = {}
        
        # Extract issue_share
        if 'issue_share' in overview_data and pd.notna(overview_data['issue_share']):
            db_overview_data['issue_share'] = overview_data['issue_share']
        
        # Extract charter_capital
        if 'charter_capital' in overview_data and pd.notna(overview_data['charter_capital']):
            db_overview_data['charter_capital'] = overview_data['charter_capital']
        
        if not db_overview_data:
            print(f"No valid overview data found for {stock_symbol}")
            return False
        
        # Update database
        success = await db_service.update_company_overview(stock_symbol, db_overview_data)
        
        if success:
            print(f"✓ Overview updated for {stock_symbol}: issue_share={db_overview_data.get('issue_share', 'N/A')}, charter_capital={db_overview_data.get('charter_capital', 'N/A')}")
        
        return success
        
    except Exception as e:
        print(f"✗ Error fetching overview for {stock_symbol}: {e}")
        return False


async def update_company_events(stock_symbol: str) -> bool:
    """
    Update company events information
    
    Args:
        stock_symbol: Stock symbol (e.g., 'ACB')
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        print(f"Fetching company events for {stock_symbol}...")
        
        # Create Company instance for events using VCI source (matching Company Update implementation)
        company = Vnstock().stock(symbol=stock_symbol, source='VCI').company
        
        # Get company events data
        events_df = company.events()
        
        if events_df is None or events_df.empty:
            print(f"No events data available for {stock_symbol}")
            return False
        
        # Convert DataFrame to list of dictionaries (matching Company Update implementation)
        events_data = []
        
        for _, row in events_df.iterrows():
            event_dict = row.to_dict()
            
            # Helper function to parse dates from vnstock
            def parse_date(date_str):
                if not date_str or str(date_str).lower() == 'nan':
                    return None
                try:
                    # vnstock returns dates as strings like '2012-05-25'
                    return datetime.strptime(str(date_str), "%Y-%m-%d").date().isoformat()
                except:
                    return None
            
            # Helper function to convert vnstock numeric values  
            def convert_numeric(value):
                if not value or str(value).lower() == 'nan':
                    return None
                return str(value)
            
            # Clean up the data - use exact same structure as Company Update
            cleaned_event = {}
            
            # Map vnstock fields directly (same as database.py update_company_events)
            cleaned_event.update({
                "event_title": event_dict.get("event_title"),
                "en__event_title": event_dict.get("en__event_title"),
                "public_date": parse_date(event_dict.get("public_date")),
                "issue_date": parse_date(event_dict.get("issue_date")),
                "source_url": event_dict.get("source_url"),
                "event_list_code": event_dict.get("event_list_code"),
                "ratio": convert_numeric(event_dict.get("ratio")),
                "value": convert_numeric(event_dict.get("value")),
                "record_date": parse_date(event_dict.get("record_date")),
                "exright_date": parse_date(event_dict.get("exright_date")),
                "event_list_name": event_dict.get("event_list_name"),
                "en__event_list_name": event_dict.get("en__event_list_name"),
                # Additional database fields (matching database.py)
                "description": "",
                "event_type": event_dict.get("event_list_code", ""),  # Use code as type
                "event_name": event_dict.get("event_title", ""),     # Use title as name  
                "event_date": parse_date(event_dict.get("issue_date")),  # Use issue_date as primary event date
                "ex_date": parse_date(event_dict.get("exright_date")),   # Use exright_date as ex_date
                "place": ""
            })
            
            events_data.append(cleaned_event)
        
        # Update database
        success = await db_service.update_company_events(stock_symbol, events_data)
        
        if success:
            print(f"✓ Events updated for {stock_symbol}: {len(events_data)} events processed")
        
        return success
        
    except Exception as e:
        print(f"✗ Error fetching events for {stock_symbol}: {e}")
        return False


async def update_company_dividends(stock_symbol: str) -> bool:
    """
    Update company dividends information
    
    Args:
        stock_symbol: Stock symbol (e.g., 'ACB')
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        print(f"Fetching company dividends for {stock_symbol}...")
        
        # Create different Company instance for dividends (using TCBS source)
        company = Vnstock().stock(symbol=stock_symbol, source='TCBS').company
        
        # Get company dividends data
        dividends_df = company.dividends()
        
        if dividends_df is None or dividends_df.empty:
            print(f"No dividends data available for {stock_symbol}")
            return False
        
        # Convert DataFrame to list of dictionaries
        dividends_data = []
        for _, row in dividends_df.iterrows():
            dividend_dict = row.to_dict()
            
            # Clean up the data - convert NaN to None and handle dates
            cleaned_dividend = {}
            for key, value in dividend_dict.items():
                if pd.isna(value):
                    cleaned_dividend[key] = None
                elif key == 'exercise_date' and value:
                    # Ensure date field is properly formatted
                    try:
                        if isinstance(value, str):
                            cleaned_dividend[key] = value
                        else:
                            cleaned_dividend[key] = str(value)
                    except:
                        cleaned_dividend[key] = None
                else:
                    cleaned_dividend[key] = value
            
            dividends_data.append(cleaned_dividend)
        
        # Update database
        success = await db_service.update_company_dividends(stock_symbol, dividends_data)
        
        if success:
            print(f"✓ Dividends updated for {stock_symbol}: {len(dividends_data)} dividend records processed")
        
        return success
        
    except Exception as e:
        print(f"✗ Error fetching dividends for {stock_symbol}: {e}")
        return False


def get_company_info_for_frontend(stock_symbols: List[str]) -> Dict[str, Dict[str, Any]]:
    """
    Get company additional information for frontend display (synchronous version)
    
    Args:
        stock_symbols: List of stock symbols
        
    Returns:
        Dictionary with stock symbols as keys and company info as values
    """
    import asyncio
    
    async def fetch_all_info():
        results = {}
        for symbol in stock_symbols:
            try:
                info = await db_service.get_company_additional_info(symbol)
                if info:
                    results[symbol] = info
            except Exception as e:
                print(f"Error fetching company info for {symbol}: {e}")
                results[symbol] = {}
        return results
    
    # Run the async function
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If already in an async context, create a new task
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, fetch_all_info())
                return future.result()
        else:
            return asyncio.run(fetch_all_info())
    except Exception as e:
        print(f"Error in get_company_info_for_frontend: {e}")
        return {}