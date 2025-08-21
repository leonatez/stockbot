"""
Market Context Generation with ICB Integration
Generates comprehensive market context from industry and macro posts
"""

import json
import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import google.generativeai as genai
from holistic_analysis_logger import get_analysis_logger
from icb_data_manager import icb_manager


class MarketContextGenerator:
    def __init__(self):
        self.logger = get_analysis_logger()
        self._context_cache = {}
    
    async def generate_market_context_with_icb(self, posts_by_type: Dict[str, List[Dict]], 
                                             icb_mapping: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive market context with ICB intelligence"""
        
        self.logger.log_phase_start("market_context_generation", 
                                   "Analyzing industry and macro posts for market context")
        
        phase_start_time = time.time()
        
        try:
            # Combine industry + macro posts for context analysis
            context_posts = posts_by_type.get('industry', []) + posts_by_type.get('macro_economy', [])
            
            if not context_posts:
                self.logger.logger.warning("No industry or macro posts found for context generation")
                return self._create_empty_context()
            
            self.logger.logger.info(f"Analyzing {len(context_posts)} posts for market context")
            self.logger.logger.info(f"  - Industry posts: {len(posts_by_type.get('industry', []))}")
            self.logger.logger.info(f"  - Macro economy posts: {len(posts_by_type.get('macro_economy', []))}")
            
            # Check cache first
            cache_key = self._generate_cache_key(context_posts)
            if cache_key in self._context_cache:
                self.logger.logger.info("Using cached market context")
                cached_context = self._context_cache[cache_key]
                
                phase_duration = time.time() - phase_start_time
                self.logger.log_phase_complete("market_context_generation", phase_duration, {
                    "source": "cache",
                    "posts_analyzed": len(context_posts),
                    "icb_sectors_found": len(cached_context.get('icb_analysis', [])),
                    "macro_factors_found": len(cached_context.get('macro_factors', []))
                })
                
                return cached_context
            
            # Create enhanced prompt with ICB data
            context_prompt = self._create_market_context_prompt(context_posts, icb_mapping)
            
            # Log Gemini call
            call_id = self.logger.log_gemini_call(
                "market_context", 
                context_prompt, 
                post_urls=[post['url'] for post in context_posts]
            )
            
            # Call Gemini for market context analysis
            market_context = await self._call_gemini_for_context(context_prompt)
            
            # Log response
            self.logger.log_gemini_response("market_context", market_context)
            
            # Validate and enhance the response
            validated_context = self._validate_and_enhance_context(market_context, icb_mapping)
            
            # Cache the result
            self._context_cache[cache_key] = validated_context
            
            phase_duration = time.time() - phase_start_time
            self.logger.log_phase_complete("market_context_generation", phase_duration, {
                "source": "fresh_analysis",
                "posts_analyzed": len(context_posts),
                "icb_sectors_found": len(validated_context.get('icb_analysis', [])),
                "macro_factors_found": len(validated_context.get('macro_factors', [])),
                "gemini_call_id": call_id
            })
            
            return validated_context
            
        except Exception as e:
            self.logger.log_phase_error("market_context_generation", e)
            # Return empty context instead of failing completely
            return self._create_empty_context()
    
    def _create_market_context_prompt(self, context_posts: List[Dict], 
                                    icb_mapping: Dict[str, Any]) -> str:
        """Create enhanced prompt with ICB data for market context analysis"""
        
        # Format ICB industries for prompt
        industries_text = icb_manager.format_icb_industries_for_prompt(
            icb_mapping["industries"], max_items=40
        )
        
        # Format posts for analysis
        posts_text = self._format_posts_for_context_analysis(context_posts)
        
        prompt = f"""
Analyze Vietnamese financial market context from industry and macro economy posts.
You are an expert Vietnamese financial analyst. Provide comprehensive market intelligence.

AVAILABLE VIETNAMESE ICB INDUSTRIES:
{industries_text}

POSTS TO ANALYZE:
{posts_text}

ANALYSIS REQUIREMENTS:
1. Identify which ICB sectors/industries are mentioned or affected
2. Determine sentiment and key drivers for each affected industry
3. Extract macro economic factors and their market impact
4. Provide cross-sector analysis and market outlook

Please provide structured analysis in JSON format:
{{
    "analysis_date": "{datetime.now().strftime('%Y-%m-%d')}",
    "posts_analyzed": {len(context_posts)},
    "icb_analysis": [
        {{
            "icb_code": "0530",
            "icb_name": "Sản xuất Dầu khí",
            "en_icb_name": "Oil & Gas Producers", 
            "sentiment": "positive|negative|neutral",
            "confidence": "high|medium|low",
            "key_drivers": ["Giá dầu tăng", "Kết quả kinh doanh mạnh"],
            "risk_factors": ["Quy định môi trường", "Biến động giá nguyên liệu"],
            "outlook": "Chi tiết phân tích triển vọng ngành",
            "timeline": "short_term|medium_term|long_term",
            "related_stocks_mentioned": ["PVS", "GAS", "PVD"]
        }}
    ],
    "macro_factors": [
        {{
            "factor": "interest_rates|inflation|currency|global_market|government_policy|trade|gdp_growth",
            "trend": "rising|falling|stable|volatile", 
            "market_impact": "positive|negative|neutral",
            "affected_icb_codes": ["0530", "1350"],
            "impact_description": "Mô tả chi tiết tác động đến thị trường",
            "timeline": "short_term|medium_term|long_term",
            "confidence": "high|medium|low"
        }}
    ],
    "cross_sector_themes": ["Chuyển đổi số", "ESG", "Tái cơ cấu ngành"],
    "market_sentiment": "bullish|bearish|neutral|mixed",
    "volatility_outlook": "low|moderate|high",
    "key_risks": ["Rủi ro 1", "Rủi ro 2"],
    "opportunities": ["Cơ hội 1", "Cơ hội 2"],
    "market_outlook": "Tổng quan triển vọng thị trường tổng thể",
    "investor_sentiment": "risk_on|risk_off|cautious|optimistic"
}}

IMPORTANT NOTES:
- Focus on Vietnamese market context and terminology
- Use actual ICB codes from the provided list
- Provide specific, actionable insights
- Consider both short-term and long-term implications
- Include confidence levels for all assessments
"""
        
        return prompt
    
    def _format_posts_for_context_analysis(self, posts: List[Dict]) -> str:
        """Format posts for context analysis prompt"""
        
        formatted_posts = []
        
        for i, post in enumerate(posts, 1):
            post_text = f"""
POST {i}:
Source: {post.get('source_name', 'Unknown')} ({post.get('source_type', 'unknown')})
Date: {post.get('date', 'Unknown')}
URL: {post.get('url', 'No URL')}
Content: {post.get('content', '')[:1500]}{"..." if len(post.get('content', '')) > 1500 else ""}
"""
            formatted_posts.append(post_text)
        
        return "\n".join(formatted_posts)
    
    async def _call_gemini_for_context(self, prompt: str) -> Dict[str, Any]:
        """Call Gemini API for market context analysis"""
        
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
            self.logger.log_gemini_error("market_context", e)
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
            return self._create_empty_context()
    
    def _validate_and_enhance_context(self, context: Dict[str, Any], 
                                    icb_mapping: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and enhance the market context response"""
        
        # Ensure required fields exist
        validated = {
            "analysis_date": context.get("analysis_date", datetime.now().strftime('%Y-%m-%d')),
            "posts_analyzed": context.get("posts_analyzed", 0),
            "icb_analysis": context.get("icb_analysis", []),
            "macro_factors": context.get("macro_factors", []),
            "cross_sector_themes": context.get("cross_sector_themes", []),
            "market_sentiment": context.get("market_sentiment", "neutral"),
            "volatility_outlook": context.get("volatility_outlook", "moderate"),
            "key_risks": context.get("key_risks", []),
            "opportunities": context.get("opportunities", []),
            "market_outlook": context.get("market_outlook", ""),
            "investor_sentiment": context.get("investor_sentiment", "cautious")
        }
        
        # Validate ICB codes in icb_analysis
        valid_icb_codes = {industry["icb_code"] for industry in icb_mapping["industries"]}
        
        validated_icb_analysis = []
        for icb_item in validated["icb_analysis"]:
            if isinstance(icb_item, dict) and icb_item.get("icb_code") in valid_icb_codes:
                validated_icb_analysis.append(icb_item)
            else:
                self.logger.logger.warning(f"Invalid ICB analysis item: {icb_item}")
        
        validated["icb_analysis"] = validated_icb_analysis
        
        # Log validation results
        self.logger.logger.info(f"Context validation complete:")
        self.logger.logger.info(f"  - Valid ICB sectors: {len(validated['icb_analysis'])}")
        self.logger.logger.info(f"  - Macro factors: {len(validated['macro_factors'])}")
        self.logger.logger.info(f"  - Market sentiment: {validated['market_sentiment']}")
        
        return validated
    
    def _create_empty_context(self) -> Dict[str, Any]:
        """Create empty market context for fallback"""
        return {
            "analysis_date": datetime.now().strftime('%Y-%m-%d'),
            "posts_analyzed": 0,
            "icb_analysis": [],
            "macro_factors": [],
            "cross_sector_themes": [],
            "market_sentiment": "neutral",
            "volatility_outlook": "moderate",
            "key_risks": [],
            "opportunities": [],
            "market_outlook": "No market context available",
            "investor_sentiment": "cautious"
        }
    
    def _generate_cache_key(self, posts: List[Dict]) -> str:
        """Generate cache key for market context"""
        # Use URLs and dates to create unique cache key
        urls = sorted([post.get('url', '') for post in posts])
        dates = sorted([post.get('date', '') for post in posts])
        
        # Create hash of content for cache key
        import hashlib
        content_hash = hashlib.md5(
            (str(urls) + str(dates)).encode('utf-8')
        ).hexdigest()
        
        return f"market_context_{content_hash}"
    
    def get_cached_context(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached market context if available"""
        return self._context_cache.get(cache_key)
    
    def cache_context(self, cache_key: str, context: Dict[str, Any]):
        """Cache market context"""
        self._context_cache[cache_key] = context
        
        # Log cache operation
        self.logger.logger.info(f"Market context cached with key: {cache_key}")


# Global market context generator instance
market_context_generator = MarketContextGenerator()

async def generate_market_context(posts_by_type: Dict[str, List[Dict]], 
                                icb_mapping: Dict[str, Any]) -> Dict[str, Any]:
    """Convenience function to generate market context"""
    return await market_context_generator.generate_market_context_with_icb(posts_by_type, icb_mapping)