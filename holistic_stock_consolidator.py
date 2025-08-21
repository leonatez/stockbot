"""
Stock Consolidation with Price Context
Final phase of holistic analysis - consolidates all mentions of each stock
"""

import json
import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import google.generativeai as genai
from holistic_analysis_logger import get_analysis_logger
from database import DatabaseService


class StockConsolidator:
    def __init__(self):
        self.logger = get_analysis_logger()
        self.db_service = DatabaseService()
    
    async def consolidate_stock_analysis_with_price_context(self, company_analyses: List[Dict[str, Any]], 
                                                          market_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Final consolidation with price action context"""
        
        self.logger.log_phase_start("stock_consolidation", 
                                   "Consolidating stock analysis with price context")
        
        phase_start_time = time.time()
        
        try:
            # Group analyses by stock symbol
            stock_groups = self._group_analyses_by_stock(company_analyses)
            
            if not stock_groups:
                self.logger.logger.warning("No stocks found in company analyses for consolidation")
                self.logger.log_phase_complete("stock_consolidation", 0, {
                    "stocks_processed": 0,
                    "consolidations_created": 0
                })
                return []
            
            self.logger.logger.info(f"Consolidating analysis for {len(stock_groups)} unique stocks")
            
            # Get recent price context for mentioned stocks
            mentioned_symbols = list(stock_groups.keys())
            price_context = await self._get_recent_price_context(mentioned_symbols, days=7)
            
            final_insights = []
            successful_consolidations = 0
            
            for symbol, analyses in stock_groups.items():
                self.logger.log_stock_consolidation_start(symbol, len(analyses))
                
                try:
                    # Consolidate analysis for this stock
                    consolidated_result = await self._consolidate_single_stock(
                        symbol, analyses, market_context, price_context.get(symbol, {})
                    )
                    
                    final_insights.append(consolidated_result)
                    successful_consolidations += 1
                    
                    self.logger.log_stock_consolidation_complete(symbol)
                    
                except Exception as stock_error:
                    self.logger.log_error("stock_consolidation_error", 
                                        f"Failed to consolidate {symbol}: {str(stock_error)}", 
                                        {"stock_symbol": symbol})
                    
                    # Create failed consolidation entry
                    failed_consolidation = self._create_failed_consolidation(symbol, analyses, str(stock_error))
                    final_insights.append(failed_consolidation)
                    continue
            
            # Sort by confidence and mentions count
            final_insights.sort(key=lambda x: (
                x.get('confidence_score', 0),
                x.get('mentions_count', 0)
            ), reverse=True)
            
            phase_duration = time.time() - phase_start_time
            self.logger.log_phase_complete("stock_consolidation", phase_duration, {
                "stocks_processed": len(stock_groups),
                "successful_consolidations": successful_consolidations,
                "failed_consolidations": len(stock_groups) - successful_consolidations,
                "total_insights_generated": len(final_insights)
            })
            
            return final_insights
            
        except Exception as e:
            self.logger.log_phase_error("stock_consolidation", e)
            raise
    
    def _group_analyses_by_stock(self, company_analyses: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group company analyses by stock symbol"""
        
        stock_groups = defaultdict(list)
        
        for analysis in company_analyses:
            analysis_data = analysis.get('analysis', {})
            post_data = analysis.get('post', {})
            
            for stock in analysis_data.get('mentioned_stocks', []):
                stock_symbol = stock.get('stock_symbol', '').upper()
                if stock_symbol:
                    stock_groups[stock_symbol].append({
                        'analysis': stock,
                        'post': post_data,
                        'gemini_call_id': analysis.get('gemini_call_id')
                    })
        
        return dict(stock_groups)
    
    async def _get_recent_price_context(self, symbols: List[str], days: int = 7) -> Dict[str, Dict[str, Any]]:
        """Get recent price data and context for mentioned stocks"""
        
        self.logger.logger.info(f"Fetching price context for {len(symbols)} stocks (last {days} days)")
        
        price_context = {}
        cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        try:
            for symbol in symbols:
                try:
                    # Get recent price data from database
                    price_result = self.db_service.supabase.table("stock_prices").select(
                        "date, open, high, low, close, volume"
                    ).eq("symbol", symbol).gte("date", cutoff_date).order("date", desc=False).execute()
                    
                    if price_result.data:
                        price_data = price_result.data
                        
                        # Calculate price metrics
                        first_price = price_data[0]['close']
                        last_price = price_data[-1]['close']
                        price_change = ((last_price - first_price) / first_price) * 100
                        
                        # Calculate volatility (simple standard deviation of daily changes)
                        daily_changes = []
                        for i in range(1, len(price_data)):
                            prev_close = price_data[i-1]['close']
                            curr_close = price_data[i]['close']
                            if prev_close > 0:
                                daily_change = ((curr_close - prev_close) / prev_close) * 100
                                daily_changes.append(daily_change)
                        
                        volatility = self._calculate_standard_deviation(daily_changes) if daily_changes else 0
                        
                        # Get trading volume trend
                        avg_volume = sum(d['volume'] for d in price_data) / len(price_data)
                        recent_volume = price_data[-1]['volume']
                        volume_trend = "above_average" if recent_volume > avg_volume * 1.2 else "below_average" if recent_volume < avg_volume * 0.8 else "normal"
                        
                        price_context[symbol] = {
                            "period_start": price_data[0]['date'],
                            "period_end": price_data[-1]['date'],
                            "price_change_percent": round(price_change, 2),
                            "volatility": round(volatility, 2),
                            "current_price": last_price,
                            "price_range": {
                                "high": max(d['high'] for d in price_data),
                                "low": min(d['low'] for d in price_data)
                            },
                            "volume_trend": volume_trend,
                            "avg_volume": avg_volume,
                            "recent_volume": recent_volume,
                            "trading_days": len(price_data)
                        }
                        
                        self.logger.logger.info(f"  {symbol}: {price_change:+.2f}% change, {volatility:.2f}% volatility")
                    
                    else:
                        price_context[symbol] = {
                            "error": "No recent price data available",
                            "trading_days": 0
                        }
                        self.logger.logger.warning(f"  {symbol}: No price data found")
                        
                except Exception as symbol_error:
                    self.logger.logger.warning(f"  {symbol}: Price data error - {symbol_error}")
                    price_context[symbol] = {
                        "error": str(symbol_error),
                        "trading_days": 0
                    }
            
        except Exception as e:
            self.logger.log_error("price_context_error", f"Failed to fetch price context: {e}")
        
        return price_context
    
    def _calculate_standard_deviation(self, values: List[float]) -> float:
        """Calculate standard deviation of a list of values"""
        if not values:
            return 0
        
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance ** 0.5
    
    async def _consolidate_single_stock(self, symbol: str, analyses: List[Dict[str, Any]], 
                                      market_context: Dict[str, Any], 
                                      price_context: Dict[str, Any]) -> Dict[str, Any]:
        """Consolidate all analysis for a single stock"""
        
        # Create comprehensive consolidation prompt
        consolidation_prompt = self._create_consolidation_prompt(
            symbol, analyses, market_context, price_context
        )
        
        # Log Gemini call
        call_id = self.logger.log_gemini_call(
            "stock_consolidation", 
            consolidation_prompt, 
            post_urls=[a['post']['url'] for a in analyses]
        )
        
        try:
            # Call Gemini for final consolidation
            consolidated_result = await self._call_gemini_for_consolidation(consolidation_prompt)
            
            # Log response
            self.logger.log_gemini_response("stock_consolidation", consolidated_result, symbol)
            
            # Validate and enhance the response
            validated_result = self._validate_consolidation_result(consolidated_result, symbol, analyses)
            
            return validated_result
            
        except Exception as e:
            self.logger.log_gemini_error("stock_consolidation", e, symbol)
            raise
    
    def _create_consolidation_prompt(self, symbol: str, analyses: List[Dict[str, Any]], 
                                   market_context: Dict[str, Any], 
                                   price_context: Dict[str, Any]) -> str:
        """Create comprehensive prompt for stock consolidation"""
        
        # Format market context
        market_context_text = self._format_market_context_for_consolidation(market_context)
        
        # Format price context
        price_context_text = self._format_price_context(price_context)
        
        # Format all mentions of this stock
        mentions_text = self._format_stock_mentions_for_consolidation(analyses)
        
        prompt = f"""
Consolidate all analysis for Vietnamese stock {symbol} with comprehensive market intelligence.
You are a senior Vietnamese stock analyst providing final investment research.

CURRENT MARKET CONTEXT:
{market_context_text}

RECENT PRICE DATA FOR {symbol}:
{price_context_text}

ALL MENTIONS AND ANALYSIS OF {symbol}:
{mentions_text}

CONSOLIDATION REQUIREMENTS:
1. Synthesize all mentions into a unified investment thesis
2. Consider price action alignment with sentiment analysis
3. Factor in industry trends and macro environment
4. Provide clear investment recommendation with reasoning
5. Include specific risk factors and opportunities
6. Consider different time horizons and scenarios

Provide final consolidated analysis in JSON format:
{{
    "stock_symbol": "{symbol}",
    "company_name": "Official company name from analysis",
    "icb_classification": {{
        "codes": ["level1", "level2", "level3", "level4"],
        "names": ["name1", "name2", "name3", "name4"]
    }},
    "overall_sentiment": "positive|negative|neutral",
    "confidence_score": 0.85,
    "mentions_count": {len(analyses)},
    "sentiment_distribution": {{
        "positive": 2,
        "negative": 0, 
        "neutral": 1
    }},
    "consolidated_summary": "Comprehensive final analysis integrating all sources and market context",
    "key_drivers": ["Driver 1", "Driver 2", "Driver 3"],
    "risk_factors": ["Risk 1", "Risk 2"], 
    "opportunities": ["Opportunity 1", "Opportunity 2"],
    "industry_context": "How industry trends specifically impact this stock",
    "macro_context": "How macro environment affects this stock",
    "price_context": "How recent price action aligns with fundamental analysis",
    "investment_thesis": "Clear, actionable investment perspective",
    "time_horizon": "short_term|medium_term|long_term",
    "recommendation": "strong_buy|buy|hold|sell|strong_sell",
    "target_scenarios": {{
        "bull_case": "Best case scenario analysis and price target reasoning",
        "bear_case": "Worst case scenario analysis and downside risk",
        "base_case": "Most likely scenario and expected performance"
    }},
    "catalysts": {{
        "positive": ["Positive catalyst 1", "Positive catalyst 2"],
        "negative": ["Negative catalyst 1", "Negative catalyst 2"]
    }},
    "post_details": [
        {{
            "source": "Source name",
            "date": "YYYY-MM-DD",
            "sentiment": "positive",
            "key_points": ["Point 1", "Point 2"],
            "url": "post_url"
        }}
    ],
    "analyst_confidence": "high|medium|low",
    "research_quality": "comprehensive|good|limited",
    "data_freshness": "recent|moderate|outdated"
}}

IMPORTANT GUIDELINES:
- Provide specific, actionable insights for Vietnamese investors
- Consider both technical (price) and fundamental (news) factors
- Be realistic about recommendation confidence
- Include specific timeframes for catalysts and targets
- Consider market context and industry positioning
- Provide clear reasoning for investment recommendation
"""
        
        return prompt
    
    def _format_market_context_for_consolidation(self, market_context: Dict[str, Any]) -> str:
        """Format market context for consolidation prompt"""
        
        context_text = f"Market Sentiment: {market_context.get('market_sentiment', 'neutral')}\n"
        context_text += f"Volatility Outlook: {market_context.get('volatility_outlook', 'moderate')}\n"
        context_text += f"Market Outlook: {market_context.get('market_outlook', 'No outlook available')}\n\n"
        
        # Key market themes
        if market_context.get('cross_sector_themes'):
            context_text += f"Market Themes: {', '.join(market_context['cross_sector_themes'])}\n"
        
        if market_context.get('key_risks'):
            context_text += f"Market Risks: {', '.join(market_context['key_risks'])}\n"
        
        if market_context.get('opportunities'):
            context_text += f"Market Opportunities: {', '.join(market_context['opportunities'])}\n"
        
        return context_text
    
    def _format_price_context(self, price_context: Dict[str, Any]) -> str:
        """Format price context for consolidation prompt"""
        
        if price_context.get('error'):
            return f"Price Data: {price_context['error']}"
        
        if not price_context:
            return "Price Data: No price information available"
        
        price_text = f"Period: {price_context.get('period_start')} to {price_context.get('period_end')}\n"
        price_text += f"Price Change: {price_context.get('price_change_percent', 0):+.2f}%\n"
        price_text += f"Volatility: {price_context.get('volatility', 0):.2f}%\n"
        price_text += f"Current Price: {price_context.get('current_price', 0):,.0f}\n"
        
        price_range = price_context.get('price_range', {})
        if price_range:
            price_text += f"Range: {price_range.get('low', 0):,.0f} - {price_range.get('high', 0):,.0f}\n"
        
        price_text += f"Volume Trend: {price_context.get('volume_trend', 'normal')}\n"
        price_text += f"Trading Days: {price_context.get('trading_days', 0)}\n"
        
        return price_text
    
    def _format_stock_mentions_for_consolidation(self, analyses: List[Dict[str, Any]]) -> str:
        """Format all stock mentions for consolidation prompt"""
        
        mentions_text = ""
        
        for i, analysis in enumerate(analyses, 1):
            stock_analysis = analysis['analysis']
            post_data = analysis['post']
            
            mentions_text += f"\nMENTION {i}:\n"
            mentions_text += f"Source: {post_data.get('source_name', 'Unknown')} ({post_data.get('source_type', 'unknown')})\n"
            mentions_text += f"Date: {post_data.get('date', 'Unknown')}\n"
            mentions_text += f"URL: {post_data.get('url', 'No URL')}\n"
            mentions_text += f"Sentiment: {stock_analysis.get('sentiment', 'neutral')}\n"
            mentions_text += f"Confidence: {stock_analysis.get('confidence', 'medium')}\n"
            mentions_text += f"Summary: {stock_analysis.get('summary', 'No summary')}\n"
            mentions_text += f"Key Factors: {', '.join(stock_analysis.get('key_factors', []))}\n"
            mentions_text += f"Risks: {', '.join(stock_analysis.get('risks', []))}\n"
            mentions_text += f"Opportunities: {', '.join(stock_analysis.get('opportunities', []))}\n"
            mentions_text += f"Industry Context: {stock_analysis.get('industry_context', 'No context')}\n"
            mentions_text += f"Macro Context: {stock_analysis.get('macro_context', 'No context')}\n"
        
        return mentions_text
    
    async def _call_gemini_for_consolidation(self, prompt: str) -> Dict[str, Any]:
        """Call Gemini API for stock consolidation"""
        
        try:
            # Initialize Gemini model
            model = genai.GenerativeModel('gemini-2.5-pro')
            
            # Generate response
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.2,  # Lower temperature for more consistent consolidation
                    max_output_tokens=8192,
                    response_mime_type="application/json"
                )
            )
            
            # Parse JSON response
            if response.text:
                try:
                    return json.loads(response.text)
                except json.JSONDecodeError as e:
                    self.logger.log_error("json_parse_error", f"Failed to parse consolidation response: {e}")
                    # Try to extract JSON from response
                    return self._extract_json_from_text(response.text)
            else:
                raise Exception("Empty response from Gemini")
                
        except Exception as e:
            self.logger.log_error("gemini_consolidation_error", f"Gemini consolidation failed: {e}")
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
                "error": "Failed to parse consolidation response",
                "raw_response": text[:1000] + "..." if len(text) > 1000 else text
            }
    
    def _validate_consolidation_result(self, result: Dict[str, Any], symbol: str, 
                                     analyses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate and enhance consolidation result"""
        
        # Get base information from first analysis
        first_analysis = analyses[0]['analysis'] if analyses else {}
        
        # Ensure required fields exist
        validated = {
            "stock_symbol": symbol,
            "company_name": result.get("company_name") or first_analysis.get("company_name", ""),
            "icb_classification": result.get("icb_classification") or {
                "codes": first_analysis.get("icb_codes", []),
                "names": first_analysis.get("icb_names", [])
            },
            "overall_sentiment": result.get("overall_sentiment", "neutral"),
            "confidence_score": min(max(result.get("confidence_score", 0.5), 0.0), 1.0),
            "mentions_count": len(analyses),
            "sentiment_distribution": self._calculate_sentiment_distribution(analyses),
            "consolidated_summary": result.get("consolidated_summary", "No consolidated summary available"),
            "key_drivers": result.get("key_drivers", []),
            "risk_factors": result.get("risk_factors", []),
            "opportunities": result.get("opportunities", []),
            "industry_context": result.get("industry_context", ""),
            "macro_context": result.get("macro_context", ""),
            "price_context": result.get("price_context", ""),
            "investment_thesis": result.get("investment_thesis", ""),
            "time_horizon": result.get("time_horizon", "medium_term"),
            "recommendation": result.get("recommendation", "hold"),
            "target_scenarios": result.get("target_scenarios", {}),
            "catalysts": result.get("catalysts", {"positive": [], "negative": []}),
            "post_details": self._extract_post_details(analyses),
            "analyst_confidence": result.get("analyst_confidence", "medium"),
            "research_quality": result.get("research_quality", "good"),
            "data_freshness": result.get("data_freshness", "recent")
        }
        
        # Add consolidation metadata
        validated["consolidation_metadata"] = {
            "sources_count": len(set(a['post'].get('source_name', '') for a in analyses)),
            "date_range": self._get_date_range(analyses),
            "consolidation_timestamp": datetime.now().isoformat()
        }
        
        return validated
    
    def _calculate_sentiment_distribution(self, analyses: List[Dict[str, Any]]) -> Dict[str, int]:
        """Calculate sentiment distribution from analyses"""
        distribution = {"positive": 0, "negative": 0, "neutral": 0}
        
        for analysis in analyses:
            sentiment = analysis['analysis'].get('sentiment', 'neutral').lower()
            if sentiment in distribution:
                distribution[sentiment] += 1
        
        return distribution
    
    def _extract_post_details(self, analyses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract post details for final result"""
        post_details = []
        
        for analysis in analyses:
            post_data = analysis['post']
            stock_analysis = analysis['analysis']
            
            detail = {
                "source": post_data.get('source_name', 'Unknown'),
                "date": post_data.get('date', 'Unknown'),
                "sentiment": stock_analysis.get('sentiment', 'neutral'),
                "key_points": stock_analysis.get('key_factors', []),
                "url": post_data.get('url', '')
            }
            post_details.append(detail)
        
        return post_details
    
    def _get_date_range(self, analyses: List[Dict[str, Any]]) -> Dict[str, str]:
        """Get date range from analyses"""
        dates = [a['post'].get('date', '') for a in analyses if a['post'].get('date')]
        
        if dates:
            dates.sort()
            return {
                "earliest": dates[0],
                "latest": dates[-1]
            }
        
        return {"earliest": "Unknown", "latest": "Unknown"}
    
    def _create_failed_consolidation(self, symbol: str, analyses: List[Dict[str, Any]], 
                                   error_message: str) -> Dict[str, Any]:
        """Create a failed consolidation entry"""
        first_analysis = analyses[0]['analysis'] if analyses else {}
        
        return {
            "stock_symbol": symbol,
            "company_name": first_analysis.get("company_name", ""),
            "overall_sentiment": "neutral",
            "confidence_score": 0.0,
            "mentions_count": len(analyses),
            "consolidated_summary": f"Consolidation failed: {error_message}",
            "error": error_message,
            "post_details": self._extract_post_details(analyses)
        }


# Global stock consolidator instance
stock_consolidator = StockConsolidator()

async def consolidate_stocks_with_price_context(company_analyses: List[Dict[str, Any]], 
                                              market_context: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Convenience function to consolidate stock analysis with price context"""
    return await stock_consolidator.consolidate_stock_analysis_with_price_context(
        company_analyses, market_context
    )