import os
import uuid
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Any
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

class DatabaseService:
    def __init__(self):
        """Initialize Supabase client"""
        self.url = os.getenv("SUPABASE_URL")
        self.key = os.getenv("SERVICE_ROLE_KEY")  # Using service role key for server operations
        
        if not self.url or not self.key:
            raise ValueError("SUPABASE_URL and SERVICE_ROLE_KEY must be set in environment variables")
        
        self.supabase: Client = create_client(self.url, self.key)
    
    # ===== SOURCE MANAGEMENT =====
    
    async def save_source(self, source_data: Dict[str, Any]) -> str:
        """
        Save a crawling source configuration to database
        
        Args:
            source_data: Dictionary containing source configuration
            
        Returns:
            str: UUID of the created source
        """
        try:
            # Map from frontend fields to database fields
            db_source = {
                "id": str(uuid.uuid4()),
                "name": source_data.get("sourceName"),
                "url": source_data.get("url"),
                "xpath_title": source_data.get("xpath"),  # XPath for finding post links
                "xpath_content": source_data.get("contentXpath"),  # XPath for post content
                "xpath_date": source_data.get("contentDateXpath"),  # XPath for post date
                "status": "active",
                "created_at": datetime.now().isoformat()
            }
            
            print(f"Saving source to database: {db_source['name']} - {db_source['url']}")
            
            # Store pagination rule in a JSON field or as metadata
            # Note: The schema doesn't show a pagination field, so we might need to add it
            # For now, we'll store it in the name or create a separate field
            
            result = self.supabase.table("sources").insert(db_source).execute()
            
            if result.data:
                print(f"✓ Source '{source_data.get('sourceName')}' saved to database with ID: {db_source['id']}")
                return db_source['id']
            else:
                raise Exception(f"Failed to save source: {result}")
                
        except Exception as e:
            print(f"✗ Error saving source to database: {e}")
            raise e

    async def get_source_by_url(self, url: str) -> Optional[Dict[str, Any]]:
        """Get source by URL to avoid duplicates"""
        try:
            result = self.supabase.table("sources").select("*").eq("url", url).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error fetching source by URL: {e}")
            return None

    async def get_all_sources(self) -> List[Dict[str, Any]]:
        """Get all sources (both active and inactive)"""
        try:
            result = self.supabase.table("sources").select("*").order("created_at", desc=True).execute()
            return result.data or []
        except Exception as e:
            print(f"Error fetching sources: {e}")
            return []

    async def update_source_status(self, source_id: str, new_status: str) -> bool:
        """Update source status (active/inactive)"""
        try:
            result = self.supabase.table("sources").update({
                "status": new_status
            }).eq("id", source_id).execute()
            
            if result.data:
                print(f"✓ Source {source_id} status updated to {new_status}")
                return True
            else:
                print(f"✗ Source {source_id} not found")
                return False
                
        except Exception as e:
            print(f"Error updating source status: {e}")
            return False
    
    # ===== POST MANAGEMENT =====
    
    async def check_post_exists(self, url: str) -> bool:
        """
        Check if a post with given URL already exists in database
        
        Args:
            url: Post URL to check
            
        Returns:
            bool: True if post exists, False otherwise
        """
        try:
            result = self.supabase.table("posts").select("id").eq("url", url).execute()
            exists = len(result.data) > 0
            if exists:
                print(f"✓ Post already exists in database: {url}")
            return exists
        except Exception as e:
            print(f"Error checking if post exists: {e}")
            return False

    async def get_existing_post_data(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Get existing post data with stock analysis from database
        
        Args:
            url: Post URL
            
        Returns:
            Dict containing post data with stock mentions, or None if not found
        """
        try:
            # Get post basic data
            post_result = self.supabase.table("posts").select("""
                id, url, source_id, type, created_date, content, summary,
                sources(name, url)
            """).eq("url", url).execute()
            
            if not post_result.data:
                return None
                
            post = post_result.data[0]
            
            # Get stock mentions for this post
            stock_mentions_result = self.supabase.table("post_mentioned_stocks").select("""
                sentiment, summary,
                stocks(symbol, organ_name, isvn30)
            """).eq("post_id", post["id"]).execute()
            
            # Format the response similar to your current structure
            mentioned_stocks = []
            for mention in stock_mentions_result.data or []:
                mentioned_stocks.append({
                    "stock_symbol": mention["stocks"]["symbol"],
                    "sentiment": mention["sentiment"],
                    "stock_summary": mention["summary"]
                })
            
            formatted_post = {
                "url": post["url"],
                "type": post["type"],
                "createdDate": post["created_date"],
                "content": post["content"],
                "summary": post["summary"],
                "mentionedStocks": mentioned_stocks,
                "source_name": post["sources"]["name"] if post["sources"] else "Unknown"
            }
            
            print(f"✓ Retrieved existing post from database: {url}")
            return formatted_post
            
        except Exception as e:
            print(f"Error fetching existing post data: {e}")
            return None

    async def save_post_with_analysis(self, post_data: Dict[str, Any], source_id: str, analysis_data: List[Dict[str, Any]], post_summary: str = "") -> str:
        """
        Save post and its stock analysis to database
        
        Args:
            post_data: Post information (url, content, date, etc.)
            source_id: ID of the source this post came from
            analysis_data: List of stock analysis results from Gemini
            
        Returns:
            str: UUID of the created post
        """
        try:
            post_id = str(uuid.uuid4())
            
            # Parse date from Vietnamese format DD/MM/YYYY
            created_date = datetime.strptime(post_data["date"], "%d/%m/%Y").date()
            
            # Insert post
            db_post = {
                "id": post_id,
                "url": post_data["url"],
                "source_id": source_id,
                "type": post_data.get("type", "Company"),  # Default type
                "created_date": created_date.isoformat(),
                "content": post_data["content"],
                "summary": post_summary
            }
            
            post_result = self.supabase.table("posts").insert(db_post).execute()
            
            if not post_result.data:
                raise Exception("Failed to insert post")
            
            print(f"✓ Post saved to database: {post_data['url']}")
            
            # Process stock mentions
            for stock_analysis in analysis_data:
                await self._save_stock_mention(post_id, stock_analysis, created_date)
            
            return post_id
            
        except Exception as e:
            print(f"✗ Error saving post with analysis: {e}")
            raise e

    async def _save_stock_mention(self, post_id: str, stock_analysis: Dict[str, Any], post_date: date):
        """Save individual stock mention and analysis"""
        try:
            stock_symbol = stock_analysis.get("stock_symbol")
            sentiment = stock_analysis.get("sentiment", "neutral")
            summary = stock_analysis.get("summary", "")
            
            if not stock_symbol:
                return
            
            # Get or create stock
            stock_id = await self._get_or_create_stock(stock_symbol)
            
            # Insert post mention
            mention_data = {
                "post_id": post_id,
                "stock_id": stock_id,
                "sentiment": sentiment,
                "summary": summary
            }
            
            mention_result = self.supabase.table("post_mentioned_stocks").insert(mention_data).execute()
            
            if mention_result.data:
                print(f"✓ Stock mention saved: {stock_symbol} ({sentiment})")
                
                # Update daily sentiment aggregation
                await self._update_daily_sentiment(stock_id, post_date, sentiment, summary, post_id)
            
        except Exception as e:
            print(f"Error saving stock mention: {e}")

    async def _get_or_create_stock(self, symbol: str) -> str:
        """Get existing stock ID or create new stock entry"""
        try:
            # Check if stock exists
            result = self.supabase.table("stocks").select("id").eq("symbol", symbol).execute()
            
            if result.data:
                return result.data[0]["id"]
            
            # Create new stock
            stock_id = str(uuid.uuid4())
            new_stock = {
                "id": stock_id,
                "symbol": symbol,
                "name": f"{symbol} Company",  # Default name, can be updated later
                "exchange": "Unknown"  # Simple default, no constraint issues
            }
            
            create_result = self.supabase.table("stocks").insert(new_stock).execute()
            
            if create_result.data:
                print(f"✓ New stock created: {symbol}")
                return stock_id
            else:
                raise Exception(f"Failed to create stock: {symbol}")
                
        except Exception as e:
            print(f"Error getting/creating stock {symbol}: {e}")
            raise e


    async def _update_daily_sentiment(self, stock_id: str, post_date: date, sentiment: str, summary: str, post_id: str):
        """Update or create daily sentiment aggregation"""
        try:
            # Check if daily sentiment exists
            result = self.supabase.table("stock_daily_sentiment").select("*").eq("stock_id", stock_id).eq("date", post_date.isoformat()).execute()
            
            if result.data:
                # Update existing daily sentiment
                existing = result.data[0]
                post_ids = existing.get("post_ids", [])
                if post_id not in post_ids:
                    post_ids.append(post_id)
                
                # Combine summaries
                existing_summary = existing.get("summary", "")
                combined_summary = f"{existing_summary}. {summary}".strip(". ")
                
                update_data = {
                    "summary": combined_summary[:1000],  # Limit length
                    "post_ids": post_ids,
                    "sentiment": sentiment  # For now, use latest sentiment. Could implement voting logic later
                }
                
                self.supabase.table("stock_daily_sentiment").update(update_data).eq("stock_id", stock_id).eq("date", post_date.isoformat()).execute()
                
            else:
                # Create new daily sentiment
                daily_sentiment = {
                    "stock_id": stock_id,
                    "date": post_date.isoformat(),
                    "sentiment": sentiment,
                    "summary": summary[:1000],  # Limit length
                    "post_ids": [post_id]
                }
                
                self.supabase.table("stock_daily_sentiment").insert(daily_sentiment).execute()
                
            print(f"✓ Daily sentiment updated for stock {stock_id} on {post_date}")
            
        except Exception as e:
            print(f"Error updating daily sentiment: {e}")

    # ===== QUERY METHODS =====
    
    async def get_dashboard_stats(self) -> Dict[str, Any]:
        """Get dashboard statistics using the database views"""
        try:
            # Use the database views you created
            stats_result = self.supabase.table("v_dashboard_stats").select("*").execute()
            
            if stats_result.data:
                return stats_result.data[0]
            else:
                return {
                    "total_sources": 0,
                    "active_sources": 0,
                    "recent_posts_count": 0
                }
        except Exception as e:
            print(f"Error fetching dashboard stats: {e}")
            return {
                "total_sources": 0,
                "active_sources": 0,
                "recent_posts_count": 0
            }

    async def get_recent_stock_analysis(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get recent stock analysis aggregated by stock"""
        try:
            # Get recent daily sentiments with stock info
            result = self.supabase.table("stock_daily_sentiment").select("""
                stock_id, date, sentiment, summary, post_ids,
                stocks(symbol, organ_name, isvn30)
            """).gte("date", (datetime.now().date() - timedelta(days=days)).isoformat()).execute()
            
            return result.data or []
            
        except Exception as e:
            print(f"Error fetching recent stock analysis: {e}")
            return []

    async def get_recent_stocks(self, days: int = 3) -> List[Dict[str, Any]]:
        """Get stocks that have been mentioned in the last N days with aggregated data"""
        try:
            cutoff_date = (datetime.now().date() - timedelta(days=days)).isoformat()
            
            # Get stocks with recent activity, aggregated by stock
            result = self.supabase.rpc('get_recent_stocks_summary', {
                'days_back': days
            }).execute()
            
            if result.data:
                return result.data
            
            # Fallback: manual aggregation if RPC doesn't exist
            return await self._get_recent_stocks_fallback(days)
            
        except Exception as e:
            print(f"Error fetching recent stocks: {e}")
            # Try fallback method
            return await self._get_recent_stocks_fallback(days)

    async def _get_recent_stocks_fallback(self, days: int) -> List[Dict[str, Any]]:
        """Fallback method to get recent stocks with detailed post information"""
        try:
            cutoff_date = (datetime.now().date() - timedelta(days=days)).isoformat()
            
            # Get all stocks that have posts in the last N days with detailed information
            posts_result = self.supabase.table("posts").select("""
                id, url, summary, created_date,
                sources(name),
                post_mentioned_stocks(
                    sentiment, summary,
                    stocks(id, symbol, organ_name, exchange, isvn30)
                )
            """).gte("created_date", cutoff_date).execute()
            
            if not posts_result.data:
                return []
            
            # Aggregate stocks data with detailed post information
            stocks_data = {}
            
            for post in posts_result.data:
                for mention in post.get("post_mentioned_stocks", []):
                    stock = mention.get("stocks")
                    if not stock:
                        continue
                        
                    stock_id = stock["id"]
                    
                    if stock_id not in stocks_data:
                        stocks_data[stock_id] = {
                            "symbol": stock["symbol"],
                            "name": stock["organ_name"],
                            "exchange": stock["exchange"],
                            "isvn30": stock.get("isvn30", False),
                            "posts_count": 0,
                            "sentiments": [],
                            "last_updated": post["created_date"],
                            "posts": []  # Store detailed post information
                        }
                    
                    # Add detailed post information
                    post_info = {
                        "url": post["url"],
                        "summary": post["summary"] or "No summary available",
                        "source_name": post.get("sources", {}).get("name", "Unknown Source") if post.get("sources") else "Unknown Source",
                        "created_date": post["created_date"],
                        "sentiment": mention["sentiment"],
                        "stock_mention_summary": mention.get("summary", "")
                    }
                    
                    stocks_data[stock_id]["posts"].append(post_info)
                    stocks_data[stock_id]["posts_count"] += 1
                    stocks_data[stock_id]["sentiments"].append(mention["sentiment"])
                    
                    # Keep the most recent date
                    if post["created_date"] > stocks_data[stock_id]["last_updated"]:
                        stocks_data[stock_id]["last_updated"] = post["created_date"]
            
            # Calculate overall sentiment and get latest daily sentiment
            result = []
            for stock_id, stock_data in stocks_data.items():
                sentiments = stock_data["sentiments"]
                
                # Count sentiment occurrences
                sentiment_counts = {"positive": 0, "negative": 0, "neutral": 0}
                for sentiment in sentiments:
                    sentiment_counts[sentiment.lower()] = sentiment_counts.get(sentiment.lower(), 0) + 1
                
                # Determine overall sentiment (majority wins)
                overall_sentiment = max(sentiment_counts.items(), key=lambda x: x[1])[0]
                
                # Get latest stock daily sentiment summary
                daily_sentiment_summary = await self._get_latest_daily_sentiment_summary(stock_id)
                
                # Sort posts by date (most recent first)
                stock_data["posts"].sort(key=lambda x: x["created_date"], reverse=True)
                
                result.append({
                    "symbol": stock_data["symbol"],
                    "name": stock_data["name"],
                    "exchange": stock_data["exchange"],
                    "sentiment": overall_sentiment,
                    "posts_count": stock_data["posts_count"],
                    "last_updated": stock_data["last_updated"],
                    "summary": daily_sentiment_summary or f"Recent activity: {overall_sentiment} sentiment from {stock_data['posts_count']} posts",
                    "posts": stock_data["posts"]  # Include detailed post information
                })
            
            # Sort by posts count (most mentioned first)
            result.sort(key=lambda x: x["posts_count"], reverse=True)
            
            return result
            
        except Exception as e:
            print(f"Error in fallback recent stocks query: {e}")
            return []

    async def _get_latest_daily_sentiment_summary(self, stock_id: str) -> str:
        """Get the latest daily sentiment summary for a stock"""
        try:
            result = self.supabase.table("stock_daily_sentiment").select(
                "summary"
            ).eq("stock_id", stock_id).order("date", desc=True).limit(1).execute()
            
            if result.data and result.data[0].get("summary"):
                return result.data[0]["summary"]
            
            return ""
            
        except Exception as e:
            print(f"Error fetching latest daily sentiment summary: {e}")
            return ""

# Global database service instance
db_service = DatabaseService()