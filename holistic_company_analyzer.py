"""
Enhanced Company Analysis with Full Market and ICB Context
Analyzes company posts with comprehensive market intelligence
"""

import json
import time
from typing import Dict, List, Any, Optional
from datetime import datetime
import google.generativeai as genai
from holistic_analysis_logger import get_analysis_logger
from icb_data_manager import icb_manager


class CompanyAnalyzer:
    def __init__(self):
        self.logger = get_analysis_logger()
    
    async def analyze_companies_with_full_context(self, posts_by_type: Dict[str, List[Dict]], 
                                                market_context: Dict[str, Any], 
                                                icb_mapping: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze each company post with full market and ICB context"""
        
        self.logger.log_phase_start("company_analysis", 
                                   "Analyzing company posts with market context")
        
        phase_start_time = time.time()
        company_posts = posts_by_type.get('company', [])
        
        if not company_posts:
            self.logger.logger.warning("No company posts found for analysis")
            self.logger.log_phase_complete("company_analysis", 0, {
                "posts_analyzed": 0,
                "stocks_found": 0
            })
            return []
        
        self.logger.logger.info(f"Starting analysis of {len(company_posts)} company posts")
        
        company_analyses = []
        total_stocks_found = 0
        
        try:
            for i, company_post in enumerate(company_posts, 1):
                self.logger.log_company_analysis_start(i, len(company_posts), company_post['url'])
                
                try:
                    # Analyze individual company post
                    analysis_result = await self._analyze_single_company_post(
                        company_post, market_context, icb_mapping, i
                    )
                    
                    stocks_in_post = len(analysis_result['analysis'].get('mentioned_stocks', []))
                    total_stocks_found += stocks_in_post
                    
                    company_analyses.append(analysis_result)
                    
                    self.logger.log_company_analysis_complete(i, stocks_in_post)
                    
                    # Log stocks found in this post
                    for stock in analysis_result['analysis'].get('mentioned_stocks', []):
                        self.logger.logger.info(f"  Found stock: {stock.get('stock_symbol')} - {stock.get('sentiment')}")
                    
                except Exception as post_error:
                    self.logger.log_error("company_post_analysis_error", 
                                        f"Failed to analyze post {i}: {str(post_error)}", 
                                        {"post_url": company_post.get('url')})
                    
                    # Create failed analysis entry
                    failed_analysis = {
                        'post': company_post,
                        'analysis': {
                            'post_summary': 'Analysis failed',
                            'mentioned_stocks': [],
                            'overall_market_implications': 'Unable to analyze due to error',
                            'error': str(post_error)
                        }
                    }
                    company_analyses.append(failed_analysis)
                    continue
            
            phase_duration = time.time() - phase_start_time
            self.logger.log_phase_complete("company_analysis", phase_duration, {
                "posts_analyzed": len(company_posts),
                "successful_analyses": len([a for a in company_analyses if 'error' not in a['analysis']]),
                "failed_analyses": len([a for a in company_analyses if 'error' in a['analysis']]),
                "total_stocks_found": total_stocks_found
            })
            
            return company_analyses
            
        except Exception as e:
            self.logger.log_phase_error("company_analysis", e)
            raise
    
    async def _analyze_single_company_post(self, company_post: Dict[str, Any], 
                                         market_context: Dict[str, Any], 
                                         icb_mapping: Dict[str, Any],
                                         post_index: int) -> Dict[str, Any]:
        """Analyze a single company post with full context"""
        
        # Create enhanced prompt with all available context
        analysis_prompt = self._create_company_analysis_prompt(
            company_post, market_context, icb_mapping
        )
        
        # Log Gemini call
        call_id = self.logger.log_gemini_call(
            "company_analysis", 
            analysis_prompt, 
            post_urls=[company_post['url']]
        )
        
        try:
            # Call Gemini for analysis
            analysis_result = await self._call_gemini_for_company_analysis(analysis_prompt)
            
            # Log successful response
            self.logger.log_gemini_response("company_analysis", analysis_result, company_post['url'])
            
            # Validate and enhance the response
            validated_analysis = self._validate_company_analysis(analysis_result, icb_mapping)
            
            return {
                'post': company_post,
                'analysis': validated_analysis,
                'gemini_call_id': call_id
            }
            
        except Exception as e:
            self.logger.log_gemini_error("company_analysis", e, company_post['url'])
            raise
    
    def _create_company_analysis_prompt(self, company_post: Dict[str, Any], 
                                      market_context: Dict[str, Any], 
                                      icb_mapping: Dict[str, Any]) -> str:
        """Create enhanced prompt with ICB and market context for company analysis"""
        
        # Get relevant stock mapping for the prompt (limit size)
        stock_mapping_text = icb_manager.format_stock_icb_mapping_for_prompt(
            icb_mapping["stock_to_icb"], max_stocks=100
        )
        
        # Format market context for prompt
        market_context_text = self._format_market_context_for_prompt(market_context)
        
        prompt = f"""
Analyze this Vietnamese company post with comprehensive market intelligence.
You are an expert Vietnamese stock analyst with deep understanding of Vietnamese markets.

STOCK-ICB MAPPING REFERENCE:
{stock_mapping_text}

CURRENT MARKET CONTEXT:
{market_context_text}

COMPANY POST TO ANALYZE:
Source: {company_post.get('source_name', 'Unknown')} ({company_post.get('source_type', 'company')})
Date: {company_post.get('date', 'Unknown')}
URL: {company_post['url']}
Content: {company_post['content']}

ANALYSIS INSTRUCTIONS:
1. Identify ALL Vietnamese stock symbols mentioned (e.g., VIC, HPG, ACB, VIN, etc.)
2. For each stock, use the ICB mapping to understand its industry classification
3. Consider current industry sentiment from market context for each stock's ICB sector
4. Factor in relevant macro economic impacts on each stock's industry
5. Provide holistic analysis considering company + industry + macro context
6. Assess confidence levels based on information quality and market context alignment

Return analysis in JSON format:
{{
    "post_summary": "Comprehensive summary of the post content and key insights",
    "mentioned_stocks": [
        {{
            "stock_symbol": "VIC",
            "company_name": "Exact company name from ICB mapping",
            "icb_codes": ["8000", "8600", "8670", "8671"],
            "icb_names": ["Financials", "Real Estate", "Real Estate Investment & Services", "Real Estate Investment Trusts"],
            "sentiment": "positive|negative|neutral",
            "confidence": "high|medium|low",
            "summary": "Detailed stock-specific analysis incorporating post content",
            "industry_context": "How current industry trends and sentiment affect this specific stock",
            "macro_context": "How macro economic factors specifically impact this stock",
            "key_factors": ["Yếu tố tích cực 1", "Yếu tố tích cực 2"],
            "risks": ["Rủi ro 1", "Rủi ro 2"],
            "opportunities": ["Cơ hội 1", "Cơ hội 2"],
            "price_catalyst": "Factors that could drive stock price movement",
            "time_horizon": "short_term|medium_term|long_term"
        }}
    ],
    "overall_market_implications": "How this post affects broader market view and themes",
    "cross_references": "Connections to other market context or industry trends",
    "analyst_notes": "Additional insights and observations"
}}

IMPORTANT GUIDELINES:
- Only include stocks that are actually mentioned in the post content
- Use exact ICB codes and names from the provided mapping
- Provide Vietnamese market-specific insights
- Consider both direct mentions and implied impacts
- Include confidence levels for all assessments
- Be specific about timeframes and catalysts
- Factor in current market sentiment and industry context
"""
        
        return prompt
    
    def _format_market_context_for_prompt(self, market_context: Dict[str, Any]) -> str:
        """Format market context for inclusion in company analysis prompt"""
        
        context_text = f"Market Analysis Date: {market_context.get('analysis_date', 'Unknown')}\n"
        context_text += f"Overall Market Sentiment: {market_context.get('market_sentiment', 'neutral')}\n"
        context_text += f"Volatility Outlook: {market_context.get('volatility_outlook', 'moderate')}\n\n"
        
        # ICB Analysis
        icb_analysis = market_context.get('icb_analysis', [])
        if icb_analysis:
            context_text += "INDUSTRY SENTIMENT BY ICB SECTOR:\n"
            for icb in icb_analysis:
                context_text += f"- {icb.get('icb_code')} ({icb.get('icb_name')}): {icb.get('sentiment', 'neutral')}\n"
                context_text += f"  Key Drivers: {', '.join(icb.get('key_drivers', []))}\n"
                context_text += f"  Outlook: {icb.get('outlook', 'No outlook provided')}\n"
            context_text += "\n"
        
        # Macro Factors
        macro_factors = market_context.get('macro_factors', [])
        if macro_factors:
            context_text += "MACRO ECONOMIC FACTORS:\n"
            for macro in macro_factors:
                context_text += f"- {macro.get('factor', 'Unknown factor')}: {macro.get('trend', 'stable')} trend\n"
                context_text += f"  Market Impact: {macro.get('market_impact', 'neutral')}\n"
                context_text += f"  Affected ICB Codes: {', '.join(macro.get('affected_icb_codes', []))}\n"
                context_text += f"  Description: {macro.get('impact_description', 'No description')}\n"
            context_text += "\n"
        
        # Key themes and risks
        if market_context.get('cross_sector_themes'):
            context_text += f"Cross-Sector Themes: {', '.join(market_context['cross_sector_themes'])}\n"
        
        if market_context.get('key_risks'):
            context_text += f"Key Market Risks: {', '.join(market_context['key_risks'])}\n"
        
        if market_context.get('opportunities'):
            context_text += f"Market Opportunities: {', '.join(market_context['opportunities'])}\n"
        
        if market_context.get('market_outlook'):
            context_text += f"\nMarket Outlook: {market_context['market_outlook']}\n"
        
        return context_text
    
    async def _call_gemini_for_company_analysis(self, prompt: str) -> Dict[str, Any]:
        """Call Gemini API for company analysis"""
        
        try:
            # Initialize Gemini model
            model = genai.GenerativeModel('gemini-2.5-pro')
            
            # Generate response
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,
                    max_output_tokens=8192,
                    response_mime_type="application/json"
                )
            )
            
            # Parse JSON response
            if response.text:
                try:
                    return json.loads(response.text)
                except json.JSONDecodeError as e:
                    self.logger.log_error("json_parse_error", f"Failed to parse Gemini response: {e}")
                    # Try to extract JSON from response
                    return self._extract_json_from_text(response.text)
            else:
                raise Exception("Empty response from Gemini")
                
        except Exception as e:
            self.logger.log_error("gemini_api_error", f"Gemini API call failed: {e}")
            raise
    
    def _extract_json_from_text(self, text: str) -> Dict[str, Any]:
        """Try to extract JSON from text response"""
        try:
            # Look for JSON content between ```json and ```
            start_marker = "```json"
            end_marker = "```"
            
            start_idx = text.find(start_marker)
            if start_idx != -1:
                start_idx += len(start_marker)
                end_idx = text.find(end_marker, start_idx)
                if end_idx != -1:
                    json_text = text[start_idx:end_idx].strip()
                    return json.loads(json_text)
            
            # If no markers found, try to parse the entire text
            return json.loads(text)
            
        except:
            # Return minimal valid structure if all parsing fails
            return {
                "post_summary": "Failed to parse analysis",
                "mentioned_stocks": [],
                "overall_market_implications": "Analysis parsing failed",
                "analyst_notes": f"Raw response: {text[:500]}..."
            }
    
    def _validate_company_analysis(self, analysis: Dict[str, Any], 
                                 icb_mapping: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and enhance company analysis response"""
        
        # Ensure required fields exist
        validated = {
            "post_summary": analysis.get("post_summary", "No summary provided"),
            "mentioned_stocks": [],
            "overall_market_implications": analysis.get("overall_market_implications", ""),
            "cross_references": analysis.get("cross_references", ""),
            "analyst_notes": analysis.get("analyst_notes", "")
        }
        
        # Validate and enhance mentioned stocks
        valid_stock_symbols = set(icb_mapping["stock_to_icb"].keys())
        
        for stock_data in analysis.get("mentioned_stocks", []):
            if not isinstance(stock_data, dict):
                continue
            
            stock_symbol = stock_data.get("stock_symbol", "").upper()
            
            # Validate stock symbol exists in ICB mapping
            if stock_symbol and stock_symbol in valid_stock_symbols:
                # Enhance with ICB data if missing
                icb_data = icb_mapping["stock_to_icb"][stock_symbol]
                
                validated_stock = {
                    "stock_symbol": stock_symbol,
                    "company_name": stock_data.get("company_name") or icb_data.get("company_name", ""),
                    "icb_codes": stock_data.get("icb_codes") or icb_data.get("icb_codes", []),
                    "icb_names": stock_data.get("icb_names") or icb_data.get("icb_names", []),
                    "sentiment": stock_data.get("sentiment", "neutral"),
                    "confidence": stock_data.get("confidence", "medium"),
                    "summary": stock_data.get("summary", ""),
                    "industry_context": stock_data.get("industry_context", ""),
                    "macro_context": stock_data.get("macro_context", ""),
                    "key_factors": stock_data.get("key_factors", []),
                    "risks": stock_data.get("risks", []),
                    "opportunities": stock_data.get("opportunities", []),
                    "price_catalyst": stock_data.get("price_catalyst", ""),
                    "time_horizon": stock_data.get("time_horizon", "medium_term")
                }
                
                validated["mentioned_stocks"].append(validated_stock)
            else:
                self.logger.logger.warning(f"Invalid or unknown stock symbol: {stock_symbol}")
        
        self.logger.logger.info(f"Validated analysis: {len(validated['mentioned_stocks'])} valid stocks")
        
        return validated


# Global company analyzer instance
company_analyzer = CompanyAnalyzer()

async def analyze_companies_with_context(posts_by_type: Dict[str, List[Dict]], 
                                       market_context: Dict[str, Any], 
                                       icb_mapping: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Convenience function to analyze company posts with context"""
    return await company_analyzer.analyze_companies_with_full_context(
        posts_by_type, market_context, icb_mapping
    )