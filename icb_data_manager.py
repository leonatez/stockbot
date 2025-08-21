"""
ICB Data Manager for Holistic Analysis
Handles preparation and formatting of ICB data for Gemini analysis
"""

import json
from typing import Dict, List, Any, Optional
from vnstock import Listing
import pandas as pd
from holistic_analysis_logger import get_analysis_logger


class ICBDataManager:
    def __init__(self):
        self.logger = get_analysis_logger()
        self._icb_cache = None
        self._stock_mapping_cache = None
    
    async def prepare_icb_context(self) -> Dict[str, Any]:
        """Prepare comprehensive ICB mapping and industry data for Gemini"""
        
        self.logger.log_phase_start("icb_preparation", "Loading ICB data from VNStock")
        
        try:
            # Get all ICB industries data
            listing = Listing()
            
            self.logger.logger.info("Fetching ICB industries data...")
            industries_df = listing.industries_icb()
            
            if industries_df is None or industries_df.empty:
                raise Exception("Failed to fetch ICB industries data from VNStock")
            
            self.logger.logger.info(f"Loaded {len(industries_df)} ICB industries")
            
            self.logger.logger.info("Fetching stock-to-ICB mapping data...")
            stocks_df = listing.symbols_by_industries()
            
            if stocks_df is None or stocks_df.empty:
                raise Exception("Failed to fetch stock-to-ICB mapping from VNStock")
            
            self.logger.logger.info(f"Loaded ICB mapping for {len(stocks_df)} stocks")
            
            # Create comprehensive ICB mapping
            icb_mapping = {
                "industries": self._format_industries_data(industries_df),
                "stock_to_icb": self._format_stock_mapping(stocks_df),
                "icb_hierarchy": self._build_icb_hierarchy(industries_df)
            }
            
            # Cache the data
            self._icb_cache = icb_mapping
            
            self.logger.log_phase_complete("icb_preparation", 0, {
                "industries_count": len(icb_mapping["industries"]),
                "stocks_mapped": len(icb_mapping["stock_to_icb"]),
                "hierarchy_levels": len(icb_mapping["icb_hierarchy"])
            })
            
            return icb_mapping
            
        except Exception as e:
            self.logger.log_phase_error("icb_preparation", e)
            raise
    
    def _format_industries_data(self, industries_df: pd.DataFrame) -> List[Dict]:
        """Format ICB industries data for Gemini prompt"""
        industries = []
        
        for _, row in industries_df.iterrows():
            industry = {
                "icb_code": str(row['icb_code']),
                "icb_name": row['icb_name'],
                "en_icb_name": row['en_icb_name'],
                "level": int(row['level'])
            }
            industries.append(industry)
        
        # Sort by level and code for better organization
        industries.sort(key=lambda x: (x['level'], x['icb_code']))
        
        return industries
    
    def _format_stock_mapping(self, stocks_df: pd.DataFrame) -> Dict[str, Dict]:
        """Format stock-to-ICB mapping for Gemini prompt"""
        stock_mapping = {}
        
        for _, row in stocks_df.iterrows():
            symbol = row['symbol']
            
            # Get ICB codes (filter out NaN/None values)
            icb_codes = []
            icb_names = []
            
            for level in [1, 2, 3, 4]:
                code = row.get(f'icb_code{level}')
                name = row.get(f'icb_name{level}')
                
                if pd.notna(code) and str(code).strip():
                    icb_codes.append(str(code))
                    icb_names.append(str(name) if pd.notna(name) else "")
            
            if icb_codes:  # Only include stocks with valid ICB data
                stock_mapping[symbol] = {
                    'icb_codes': icb_codes,
                    'icb_names': icb_names,
                    'company_name': row.get('organ_name', ''),
                    'com_type_code': row.get('com_type_code', '')
                }
        
        return stock_mapping
    
    def _build_icb_hierarchy(self, industries_df: pd.DataFrame) -> Dict[int, List[Dict]]:
        """Build ICB hierarchy by levels for better understanding"""
        hierarchy = {}
        
        for level in [1, 2, 3, 4]:
            level_industries = industries_df[industries_df['level'] == level]
            hierarchy[level] = [
                {
                    "icb_code": str(row['icb_code']),
                    "icb_name": row['icb_name'],
                    "en_icb_name": row['en_icb_name']
                }
                for _, row in level_industries.iterrows()
            ]
        
        return hierarchy
    
    def format_icb_industries_for_prompt(self, industries: List[Dict], max_items: int = 50) -> str:
        """Format ICB industries data for inclusion in Gemini prompt"""
        
        # Group by level for better readability
        by_level = {}
        for industry in industries:
            level = industry['level']
            if level not in by_level:
                by_level[level] = []
            by_level[level].append(industry)
        
        formatted_text = "Available Vietnamese ICB Industry Classifications:\n"
        
        for level in sorted(by_level.keys()):
            level_industries = by_level[level][:max_items]  # Limit per level
            formatted_text += f"\nLevel {level} Industries:\n"
            
            for industry in level_industries:
                formatted_text += f"- {industry['icb_code']}: {industry['icb_name']} ({industry['en_icb_name']})\n"
            
            if len(by_level[level]) > max_items:
                formatted_text += f"... and {len(by_level[level]) - max_items} more Level {level} industries\n"
        
        return formatted_text
    
    def format_stock_icb_mapping_for_prompt(self, stock_mapping: Dict[str, Dict], 
                                          symbols_filter: Optional[List[str]] = None,
                                          max_stocks: int = 100) -> str:
        """Format stock-to-ICB mapping for inclusion in Gemini prompt"""
        
        # Filter stocks if symbols provided
        if symbols_filter:
            filtered_mapping = {
                symbol: data for symbol, data in stock_mapping.items() 
                if symbol in symbols_filter
            }
        else:
            # Limit to most common stocks if no filter
            filtered_mapping = dict(list(stock_mapping.items())[:max_stocks])
        
        formatted_text = "Stock to ICB Classification Mapping:\n"
        formatted_text += "(Format: SYMBOL - Company Name - ICB Codes [Level1, Level2, Level3, Level4])\n\n"
        
        for symbol, data in filtered_mapping.items():
            company_name = data['company_name'][:50] + "..." if len(data['company_name']) > 50 else data['company_name']
            icb_codes_str = " -> ".join(data['icb_codes'])
            
            formatted_text += f"- {symbol}: {company_name}\n"
            formatted_text += f"  ICB: {icb_codes_str}\n"
            formatted_text += f"  Industries: {' -> '.join(data['icb_names'])}\n\n"
        
        if len(stock_mapping) > len(filtered_mapping):
            remaining = len(stock_mapping) - len(filtered_mapping)
            formatted_text += f"... and {remaining} more stocks available in mapping\n"
        
        return formatted_text
    
    def get_relevant_stocks_for_prompt(self, mentioned_symbols: List[str]) -> str:
        """Get relevant stock mappings for mentioned symbols"""
        if not self._stock_mapping_cache:
            return "No stock mapping data available."
        
        relevant_mapping = {
            symbol: data for symbol, data in self._stock_mapping_cache.items()
            if symbol in mentioned_symbols
        }
        
        if not relevant_mapping:
            return f"No ICB mapping found for mentioned stocks: {', '.join(mentioned_symbols)}"
        
        return self.format_stock_icb_mapping_for_prompt(relevant_mapping)
    
    def get_industry_context_by_icb_codes(self, icb_codes: List[str]) -> List[Dict]:
        """Get industry information for specific ICB codes"""
        if not self._icb_cache:
            return []
        
        relevant_industries = []
        for industry in self._icb_cache["industries"]:
            if industry["icb_code"] in icb_codes:
                relevant_industries.append(industry)
        
        return relevant_industries
    
    def estimate_token_usage_for_icb_data(self, include_stock_mapping: bool = True, 
                                        stock_count: int = 100) -> int:
        """Estimate token usage for ICB data in prompts"""
        base_industries_tokens = 3000  # Estimated for full ICB industries list
        
        if include_stock_mapping:
            stock_mapping_tokens = stock_count * 15  # Rough estimate per stock
            return base_industries_tokens + stock_mapping_tokens
        
        return base_industries_tokens


# Global ICB manager instance
icb_manager = ICBDataManager()

async def get_icb_context() -> Dict[str, Any]:
    """Convenience function to get ICB context"""
    return await icb_manager.prepare_icb_context()

def format_icb_for_prompt(industries: List[Dict], stock_mapping: Dict[str, Dict], 
                         mentioned_symbols: Optional[List[str]] = None) -> str:
    """Convenience function to format ICB data for prompts"""
    
    # Format industries (limit to essential ones)
    industries_text = icb_manager.format_icb_industries_for_prompt(industries, max_items=30)
    
    # Format stock mapping (focus on mentioned symbols if provided)
    if mentioned_symbols:
        stock_text = icb_manager.format_stock_icb_mapping_for_prompt(
            stock_mapping, symbols_filter=mentioned_symbols
        )
    else:
        stock_text = icb_manager.format_stock_icb_mapping_for_prompt(
            stock_mapping, max_stocks=50
        )
    
    return f"{industries_text}\n\n{stock_text}"