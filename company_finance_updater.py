"""
Company Finance Data Updater

This module handles fetching and processing company financial data from VNStock,
including balance sheet, income statement, cash flow, and financial ratios.
All data is joined by stock symbol and quarter for comprehensive analysis.
"""

import pandas as pd
from vnstock import Vnstock
from typing import Dict, Any, Optional, List
import logging
import time
import traceback

class CompanyFinanceUpdater:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def get_company_finance_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """
        Get comprehensive financial data for a company including:
        - Balance sheet
        - Income statement 
        - Cash flow
        - Financial ratios
        
        All data is joined by quarter for unified analysis.
        
        Args:
            symbol: Stock symbol (e.g., 'VIN', 'ACB')
            
        Returns:
            DataFrame with all financial data joined by quarter, or None if error
        """
        try:
            # Initialize stock instance
            stock = Vnstock().stock(symbol=symbol, source='VCI')
            
            # Get all financial statements with delays to avoid rate limiting
            print(f"Fetching financial data for {symbol}...")
            
            # Add delay before first call
            time.sleep(2)
            
            balance_sheet = None
            income_statement = None
            cash_flow = None
            ratios = None
            
            # Fetch each dataset with error handling and delays
            try:
                balance_sheet = stock.finance.balance_sheet(period='quarter', lang='vi', dropna=True)
                if balance_sheet is not None and not balance_sheet.empty:
                    print(f"✓ balance_sheet: {len(balance_sheet)} records")
                else:
                    print(f"⚠️ balance_sheet: No data")
                time.sleep(3)  # Wait between API calls
            except Exception as e:
                print(f"⚠️ balance_sheet error: {str(e)}")
            
            try:
                income_statement = stock.finance.income_statement(period='quarter', lang='vi', dropna=True)
                if income_statement is not None and not income_statement.empty:
                    print(f"✓ income_statement: {len(income_statement)} records")
                else:
                    print(f"⚠️ income_statement: No data")
                time.sleep(3)  # Wait between API calls
            except Exception as e:
                print(f"⚠️ income_statement error: {str(e)}")
            
            try:
                cash_flow = stock.finance.cash_flow(period='quarter', dropna=True)
                if cash_flow is not None and not cash_flow.empty:
                    print(f"✓ cash_flow: {len(cash_flow)} records")
                else:
                    print(f"⚠️ cash_flow: No data")
                time.sleep(3)  # Wait between API calls
            except Exception as e:
                print(f"⚠️ cash_flow error: {str(e)}")
            
            try:
                ratios = stock.finance.ratio(period='quarter', lang='vi', dropna=True)
                if ratios is not None and not ratios.empty:
                    print(f"✓ ratios: {len(ratios)} records")
                else:
                    print(f"⚠️ ratios: No data")
            except Exception as e:
                print(f"⚠️ ratios error: {str(e)}")
            
            # Check if any dataframes are empty
            dataframes = {
                'balance_sheet': balance_sheet,
                'income_statement': income_statement, 
                'cash_flow': cash_flow,
                'ratios': ratios
            }
            
            valid_dataframes = {}
            for name, df in dataframes.items():
                if df is not None and not df.empty:
                    valid_dataframes[name] = df
                    print(f"✓ {name}: {len(df)} records")
                else:
                    print(f"⚠️ {name}: No data available")
            
            if not valid_dataframes:
                print(f"No financial data available for {symbol}")
                return None
            
            # Start with the largest dataframe as base
            base_df = None
            base_name = None
            max_records = 0
            
            for name, df in valid_dataframes.items():
                if len(df) > max_records:
                    max_records = len(df)
                    base_df = df.copy()
                    base_name = name
            
            print(f"Using {base_name} as base with {max_records} records")
            
            # Add symbol column to base dataframe
            base_df['symbol'] = symbol
            
            # Join other dataframes
            for name, df in valid_dataframes.items():
                if name != base_name:
                    # Add suffix to avoid column conflicts
                    suffix = f"_{name}"
                    
                    # Identify common columns (usually quarter-related columns)
                    common_cols = []
                    if 'quarter' in df.columns and 'quarter' in base_df.columns:
                        common_cols = ['quarter']
                    elif 'year' in df.columns and 'year' in base_df.columns:
                        common_cols = ['year']
                    
                    if common_cols:
                        # Merge on common columns
                        base_df = pd.merge(base_df, df, on=common_cols, how='outer', suffixes=('', suffix))
                        print(f"✓ Joined {name} on {common_cols}")
                    else:
                        # If no common merge columns, try to join by index
                        df_renamed = df.add_suffix(suffix)
                        base_df = pd.concat([base_df, df_renamed], axis=1, sort=False)
                        print(f"✓ Concatenated {name} by index")
            
            # Clean up the result
            # Handle MultiIndex columns if present
            if isinstance(base_df.columns, pd.MultiIndex):
                # Flatten MultiIndex columns
                base_df.columns = ['_'.join(str(level) for level in col if str(level) != '') for col in base_df.columns]
            
            # Ensure column names are strings
            base_df.columns = [str(col) for col in base_df.columns]
            
            # Remove duplicate symbol columns if any
            symbol_cols = [col for col in base_df.columns if str(col).startswith('symbol')]
            if len(symbol_cols) > 1:
                for col in symbol_cols[1:]:
                    base_df = base_df.drop(columns=[col])
            
            # Sort by quarter/year if available - handle different possible column names
            quarter_cols = [col for col in base_df.columns if 'quarter' in str(col).lower()]
            year_cols = [col for col in base_df.columns if 'year' in str(col).lower()]
            
            if quarter_cols:
                try:
                    base_df = base_df.sort_values(quarter_cols[0], ascending=False)
                except Exception:
                    pass  # Skip sorting if there's an issue
            elif year_cols:
                try:
                    base_df = base_df.sort_values(year_cols[0], ascending=False)
                except Exception:
                    pass  # Skip sorting if there's an issue
            
            print(f"✓ Successfully joined financial data for {symbol}: {len(base_df)} records, {len(base_df.columns)} columns")
            return base_df
            
        except Exception as e:
            print(f"✗ Error fetching financial data for {symbol}: {str(e)}")
            self.logger.error(f"Error in get_company_finance_data for {symbol}: {str(e)}")
            return None
    
    def prepare_finance_data_for_db(self, df: pd.DataFrame, symbol: str) -> List[Dict[str, Any]]:
        """
        Convert finance DataFrame to format suitable for database insertion
        
        Args:
            df: Finance DataFrame from get_company_finance_data
            symbol: Stock symbol
            
        Returns:
            List of dictionaries ready for database insertion
        """
        try:
            records = []
            
            # Create mapping for actual Vietnamese financial terms from vnstock to English fields
            field_mapping = {
                # Common time fields
                'Năm': 'year',
                'năm': 'year',
                'yearReport': 'year',
                'Kỳ': 'quarter',
                'Quarter': 'quarter',
                'lengthReport': 'quarter',
                
                # Balance Sheet - using actual field names from vnstock
                'TỔNG CỘNG TÀI SẢN (đồng)': 'total_assets',
                'TOTAL ASSETS (Bn. VND)': 'total_assets',
                'TÀI SẢN NGẮN HẠN (đồng)': 'current_assets',
                'CURRENT ASSETS (Bn. VND)': 'current_assets',
                'TÀI SẢN DÀI HẠN (đồng)': 'non_current_assets', 
                'LONG-TERM ASSETS (Bn. VND)': 'non_current_assets',
                'NỢ PHẢI TRẢ (đồng)': 'total_liabilities',
                'LIABILITIES (Bn. VND)': 'total_liabilities',
                'Nợ ngắn hạn (đồng)': 'current_liabilities',
                'Current liabilities (Bn. VND)': 'current_liabilities',
                'Nợ dài hạn (đồng)': 'non_current_liabilities',
                'Long-term liabilities (Bn. VND)': 'non_current_liabilities',
                'VỐN CHỦ SỞ HỮU (đồng)': 'shareholders_equity',
                "OWNER'S EQUITY(Bn.VND)": 'shareholders_equity',
                
                # Income Statement - using actual field names from vnstock
                'Doanh thu (đồng)_income_statement': 'revenue',
                'Revenue (Bn. VND)': 'revenue',
                'Doanh thu thuần_income_statement': 'revenue',
                'Net Sales': 'revenue',
                'Lãi gộp_income_statement': 'gross_profit',
                'Gross Profit': 'gross_profit',
                'Lãi/Lỗ từ hoạt động kinh doanh_income_statement': 'operating_profit',
                'Operating Profit/Loss': 'operating_profit',
                'Lợi nhuận thuần_income_statement': 'net_profit',
                'Net Profit For the Year': 'net_profit',
                'Cổ đông của Công ty mẹ_income_statement': 'net_profit',
                'Attributable to parent company': 'net_profit',
                'Cổ đông của Công ty mẹ': 'net_profit',
                
                # Cash Flow - using actual field names from vnstock
                'Net cash inflows/outflows from operating activities_cash_flow': 'operating_cash_flow',
                'Net Cash Flows from Investing Activities_cash_flow': 'investing_cash_flow',
                'Cash flows from financial activities_cash_flow': 'financing_cash_flow',
                'Net increase/decrease in cash and cash equivalents_cash_flow': 'net_cash_flow',
                
                # Financial Ratios - using actual field names from vnstock
                'EPS (VND)_ratios': 'eps',
                'BVPS (VND)_ratios': 'book_value_per_share', 
                'ROE (%)_ratios': 'roe',
                'ROA (%)_ratios': 'roa',
                'Current Ratio_ratios': 'current_ratio',
                'Debt/Equity_ratios': 'debt_to_equity',
                'Net Profit Margin (%)_ratios': 'profit_margin',
                'Revenue YoY (%)_ratios': 'revenue_growth',
                'EBIT (Tỷ đồng)_ratios': 'ebit',
                'EBITDA (Tỷ đồng)_ratios': 'ebitda',
                
                # Handle tuple-style column names from ratios DataFrame with _ratios suffix
                "('Chỉ tiêu khả năng sinh lợi_ratios', 'ROE (%)_ratios')": 'roe',
                "('Chỉ tiêu khả năng sinh lợi_ratios', 'ROA (%)_ratios')": 'roa',
                "('Chỉ tiêu định giá_ratios', 'EPS (VND)_ratios')": 'eps',
                "('Chỉ tiêu khả năng sinh lợi_ratios', 'EBITDA (Tỷ đồng)_ratios')": 'ebitda',
                "('Chỉ tiêu khả năng sinh lợi_ratios', 'EBIT (Tỷ đồng)_ratios')": 'ebit',
                "('Chỉ tiêu khả năng sinh lợi_ratios', 'Biên lợi nhuận ròng (%)_ratios')": 'profit_margin',
                "('Chỉ tiêu thanh khoản_ratios', 'Chỉ số thanh toán hiện thời_ratios')": 'current_ratio',
                "('Chỉ tiêu cơ cấu nguồn vốn_ratios', 'Nợ/VCSH_ratios')": 'debt_to_equity',
                "('Chỉ tiêu định giá_ratios', 'BVPS (VND)_ratios')": 'book_value_per_share'
            }
            
            for _, row in df.iterrows():
                # Convert row to dictionary and handle NaN values
                record = row.to_dict()
                
                # Clean and map the record
                clean_record = {}
                additional_data = {}
                
                for key, value in record.items():
                    # Clean the value
                    if pd.isna(value):
                        clean_value = None
                    elif isinstance(value, (int, float)) and pd.notna(value):
                        clean_value = float(value)
                    else:
                        clean_value = str(value) if value is not None else None
                    
                    # Map Vietnamese fields to English
                    mapped_key = field_mapping.get(key, key)
                    
                    # Check if this is a standard field
                    standard_fields = {
                        'quarter', 'year', 'symbol',
                        'total_assets', 'current_assets', 'non_current_assets',
                        'total_liabilities', 'current_liabilities', 'non_current_liabilities', 'shareholders_equity',
                        'revenue', 'gross_profit', 'operating_profit', 'net_profit', 'ebit', 'ebitda',
                        'operating_cash_flow', 'investing_cash_flow', 'financing_cash_flow', 'net_cash_flow', 'free_cash_flow',
                        'eps', 'book_value_per_share', 'roe', 'roa', 'current_ratio', 'debt_to_equity', 'profit_margin', 'revenue_growth'
                    }
                    
                    if mapped_key in standard_fields:
                        clean_record[mapped_key] = clean_value
                    else:
                        # Store as additional data
                        additional_data[str(key)] = clean_value
                
                # Ensure symbol is set
                clean_record['symbol'] = symbol
                
                # Store additional data if any
                if additional_data:
                    clean_record['additional_data'] = additional_data
                
                records.append(clean_record)
            
            print(f"✓ Prepared {len(records)} finance records for {symbol}")
            if records:
                print(f"Sample fields: {list(records[0].keys())}")
            return records
            
        except Exception as e:
            print(f"✗ Error preparing finance data for {symbol}: {str(e)}")
            print(f"Full error: {traceback.format_exc()}")
            self.logger.error(f"Error in prepare_finance_data_for_db for {symbol}: {str(e)}")
            return []


def test_finance_updater():
    """Test the finance updater with a sample stock"""
    updater = CompanyFinanceUpdater()
    
    # Test with VIN stock
    test_symbol = 'VIN'
    print(f"\n=== Testing Finance Data Fetch for {test_symbol} ===")
    
    finance_df = updater.get_company_finance_data(test_symbol)
    
    if finance_df is not None:
        print(f"\nDataFrame Shape: {finance_df.shape}")
        print(f"Columns: {list(finance_df.columns)}")
        print(f"\nFirst few rows:")
        print(finance_df.head())
        
        # Test data preparation
        db_records = updater.prepare_finance_data_for_db(finance_df, test_symbol)
        print(f"\nPrepared {len(db_records)} records for database")
        if db_records:
            print("Sample record keys:", list(db_records[0].keys()))
    else:
        print(f"Failed to fetch finance data for {test_symbol}")


if __name__ == "__main__":
    test_finance_updater()