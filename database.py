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
        self.key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")  # Using service role key for server operations
        
        if not self.url or not self.key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in environment variables")
        
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
                "id": str(uuid.uuid4()),
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
                "organ_name": f"{symbol} Company",  # Default name, can be updated later
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
                    "id": str(uuid.uuid4()),
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
            # Use fallback method that includes detailed post information
            return await self._get_recent_stocks_fallback(days)
            
        except Exception as e:
            print(f"Error fetching recent stocks: {e}")
            return []

    async def _get_recent_stocks_fallback(self, days: int) -> List[Dict[str, Any]]:
        """Fallback method to get recent stocks with detailed post information"""
        try:
            cutoff_date = (datetime.now().date() - timedelta(days=days)).isoformat()
            
            # Step 1: Get all post mentions with stock info
            mentions_result = self.supabase.table("post_mentioned_stocks").select(
                "post_id, sentiment, summary, stocks(id, symbol, organ_name, exchange, isvn30)"
            ).execute()
            
            if not mentions_result.data:
                return []
            
            # Step 2: Get all posts within date range
            posts_result = self.supabase.table("posts").select(
                "id, url, summary, created_date, sources(name)"
            ).gte("created_date", cutoff_date).execute()
            
            if not posts_result.data:
                return []
            
            # Create lookup dict for posts
            posts_dict = {post["id"]: post for post in posts_result.data}
            
            # Step 3: Aggregate stocks data with detailed post information
            stocks_data = {}
            
            for mention in mentions_result.data:
                post_id = mention["post_id"]
                stock = mention.get("stocks")
                
                # Check if post exists and is within date range
                if post_id not in posts_dict or not stock:
                    continue
                
                post = posts_dict[post_id]
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
            
            # Step 4: Calculate overall sentiment and get latest daily sentiment
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
            import traceback
            traceback.print_exc()
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

    # ===== COMPANY INFORMATION UPDATES =====
    
    async def update_company_overview(self, stock_symbol: str, overview_data: Dict[str, Any]) -> bool:
        """
        Update stock table with company overview information (issue_share, charter_capital)
        
        Args:
            stock_symbol: Stock symbol (e.g., 'ACB')
            overview_data: Dictionary containing overview data with 'issue_share' and 'charter_capital'
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get stock ID
            stock_result = self.supabase.table("stocks").select("id").eq("symbol", stock_symbol).execute()
            
            if not stock_result.data:
                print(f"Stock {stock_symbol} not found for overview update")
                return False
            
            stock_id = stock_result.data[0]["id"]
            
            # Update stocks table with issue_share and charter_capital
            update_data = {}
            if 'issue_share' in overview_data and overview_data['issue_share'] is not None:
                update_data['issue_share'] = int(overview_data['issue_share'])
            if 'charter_capital' in overview_data and overview_data['charter_capital'] is not None:
                update_data['charter_capital'] = float(overview_data['charter_capital'])
            
            if update_data:
                update_data['updated_at'] = datetime.now().isoformat()
                
                result = self.supabase.table("stocks").update(update_data).eq("id", stock_id).execute()
                
                if result.data:
                    print(f"✓ Company overview updated for {stock_symbol}: {update_data}")
                    return True
                else:
                    print(f"✗ Failed to update company overview for {stock_symbol}")
                    return False
            else:
                print(f"No valid overview data to update for {stock_symbol}")
                return True
            
        except Exception as e:
            print(f"✗ Error updating company overview for {stock_symbol}: {e}")
            return False

    async def update_company_events(self, stock_symbol: str, events_data: List[Dict[str, Any]]) -> bool:
        """
        Update stock_events table with company events
        
        Args:
            stock_symbol: Stock symbol (e.g., 'ACB')
            events_data: List of dictionaries containing event data
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get stock ID
            stock_result = self.supabase.table("stocks").select("id").eq("symbol", stock_symbol).execute()
            
            if not stock_result.data:
                print(f"Stock {stock_symbol} not found for events update")
                return False
            
            stock_id = stock_result.data[0]["id"]
            
            # Process each event
            updated_count = 0
            if events_data:
                print(f"Debug: First event data keys: {list(events_data[0].keys())}")
            
            for event in events_data:
                try:
                    # Prepare event data for database
                    db_event = {
                        "stock_id": stock_id,
                        "event_type": event.get("event_type", ""),
                        "event_name": event.get("event_name", ""),
                        "event_date": event.get("event_date"),
                        "ex_date": event.get("ex_date"),
                        "record_date": event.get("record_date"),
                        "issue_date": event.get("issue_date"),
                        "ratio": event.get("ratio"),
                        "value": event.get("value"),
                        "place": event.get("place", ""),
                        "description": event.get("description", ""),
                        "created_at": datetime.now().isoformat()
                    }
                    
                    # Use upsert to avoid duplicates (if event_name and event_date are unique)
                    result = self.supabase.table("stock_events").upsert(db_event).execute()
                    
                    if result.data:
                        updated_count += 1
                        # Try different possible field names for event title
                        event_title = (event.get('event_name') or 
                                     event.get('event_title') or 
                                     event.get('event_list_name') or 
                                     event.get('en__event_title') or 
                                     event.get('title') or 
                                     'Unknown event')
                        print(f"✓ Event updated for {stock_symbol}: {event_title}")
                    
                except Exception as event_error:
                    print(f"✗ Error processing event for {stock_symbol}: {event_error}")
                    continue
            
            print(f"✓ Updated {updated_count} events for {stock_symbol}")
            return updated_count > 0
            
        except Exception as e:
            print(f"✗ Error updating company events for {stock_symbol}: {e}")
            return False

    async def update_company_dividends(self, stock_symbol: str, dividends_data: List[Dict[str, Any]]) -> bool:
        """
        Update stock_dividends table with company dividend information
        
        Args:
            stock_symbol: Stock symbol (e.g., 'ACB')
            dividends_data: List of dictionaries containing dividend data with 
                          'exercise_date', 'cash_year', 'cash_dividend_percentage', 'issue_method'
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get stock ID
            stock_result = self.supabase.table("stocks").select("id").eq("symbol", stock_symbol).execute()
            
            if not stock_result.data:
                print(f"Stock {stock_symbol} not found for dividends update")
                return False
            
            stock_id = stock_result.data[0]["id"]
            
            # Process each dividend record
            updated_count = 0
            for dividend in dividends_data:
                try:
                    # Prepare dividend data for database
                    db_dividend = {
                        "stock_id": stock_id,
                        "exercise_date": dividend.get("exercise_date"),
                        "cash_year": int(dividend.get("cash_year")) if dividend.get("cash_year") else None,
                        "cash_dividend_percentage": float(dividend.get("cash_dividend_percentage")) if dividend.get("cash_dividend_percentage") else None,
                        "issue_method": dividend.get("issue_method", ""),
                        "created_at": datetime.now().isoformat(),
                        "updated_at": datetime.now().isoformat()
                    }
                    
                    # Use upsert to avoid duplicates based on unique constraint (stock_id, exercise_date, cash_year)
                    # Specify on_conflict parameter to ensure proper upsert behavior
                    result = self.supabase.table("stock_dividends").upsert(
                        db_dividend, 
                        on_conflict="stock_id,exercise_date,cash_year"
                    ).execute()
                    
                    if result.data:
                        updated_count += 1
                        print(f"✓ Dividend updated for {stock_symbol}: {dividend.get('exercise_date', 'Unknown date')}")
                    
                except Exception as dividend_error:
                    print(f"✗ Error processing dividend for {stock_symbol}: {dividend_error}")
                    continue
            
            print(f"✓ Updated {updated_count} dividends for {stock_symbol}")
            return updated_count > 0
            
        except Exception as e:
            print(f"✗ Error updating company dividends for {stock_symbol}: {e}")
            return False

    async def get_company_additional_info(self, stock_symbol: str) -> Dict[str, Any]:
        """
        Get additional company information (overview, events, dividends) for frontend display
        
        Args:
            stock_symbol: Stock symbol (e.g., 'ACB')
            
        Returns:
            Dictionary containing company overview, recent events, and recent dividends
        """
        try:
            # Get stock ID and basic info
            stock_result = self.supabase.table("stocks").select(
                "id, symbol, organ_name, exchange, issue_share, charter_capital"
            ).eq("symbol", stock_symbol).execute()
            
            if not stock_result.data:
                return {}
            
            stock_data = stock_result.data[0]
            stock_id = stock_data["id"]
            
            # Get recent events (last 10) - order by created_at since event_date can be None
            events_result = self.supabase.table("stock_events").select(
                "event_type, event_name, event_date, ex_date, record_date, ratio, value, description"
            ).eq("stock_id", stock_id).order("created_at", desc=True).limit(10).execute()
            
            # Get recent dividends (last 5)
            dividends_result = self.supabase.table("stock_dividends").select(
                "exercise_date, cash_year, cash_dividend_percentage, issue_method"
            ).eq("stock_id", stock_id).order("exercise_date", desc=True).limit(5).execute()
            
            return {
                "overview": {
                    "symbol": stock_data["symbol"],
                    "name": stock_data["organ_name"],
                    "exchange": stock_data["exchange"],
                    "issue_share": stock_data.get("issue_share"),
                    "charter_capital": stock_data.get("charter_capital")
                },
                "recent_events": events_result.data if events_result.data else [],
                "recent_dividends": dividends_result.data if dividends_result.data else []
            }
            
        except Exception as e:
            print(f"✗ Error getting company additional info for {stock_symbol}: {e}")
            return {}

# Global database service instance
db_service = DatabaseService()