"""
New Holistic Crawl Multiple Implementation
Replaces the existing crawl-multiple endpoint with enhanced holistic analysis
"""

import time
from typing import List, Dict, Any
from datetime import datetime
from collections import defaultdict
from fastapi import HTTPException
from fastapi.responses import JSONResponse

# Import holistic analysis modules
from holistic_analysis_logger import get_analysis_logger, reset_analysis_logger
from icb_data_manager import get_icb_context
from holistic_market_context import generate_market_context
from holistic_company_analyzer import analyze_companies_with_context
from holistic_stock_consolidator import consolidate_stocks_with_price_context

# Import existing modules
from database import DatabaseService
from daily_vn30_update import daily_vn30_update
from stock_price_updater import update_mentioned_stocks_prices
from company_info_updater import update_company_information


async def holistic_crawl_multiple_endpoints(request, db_service: DatabaseService):
    """
    New holistic approach to crawl-multiple analysis
    
    Flow:
    1. Collect all posts from all sources (existing or crawled)
    2. Generate market context from industry + macro posts
    3. Analyze company posts with full market context
    4. Consolidate stock analysis with price context
    """
    
    # Reset logger for new session
    reset_analysis_logger()
    logger = get_analysis_logger()
    
    # Start analysis session
    logger.log_analysis_start([s.dict() for s in request.sources], request.days)
    
    start_time = time.time()
    
    try:
        logger.logger.info(f"=== HOLISTIC MULTI-SOURCE ANALYSIS START ===")
        logger.logger.info(f"Sources: {len(request.sources)}, Days: {request.days}")
        if request.debug:
            logger.logger.info(f"🐛 DEBUG MODE: Limited analysis for testing")
        
        # Phase 0: Daily VN30 Update
        logger.log_phase_start("vn30_update", "Updating VN30 stock list")
        vn30_success = daily_vn30_update()
        if vn30_success:
            logger.logger.info("✓ VN30 update completed successfully")
        else:
            logger.logger.warning("⚠️ VN30 update had issues, continuing with analysis...")
        
        # Phase 1: ICB Data Preparation
        icb_mapping = await get_icb_context()
        logger.logger.info(f"✓ ICB context prepared: {len(icb_mapping['industries'])} industries, {len(icb_mapping['stock_to_icb'])} stocks mapped")
        
        # Phase 2: Content Collection and Preprocessing
        posts_by_type = await collect_and_preprocess_content(request, db_service, logger)
        
        # Check if we have any content to analyze
        total_posts = sum(len(posts) for posts in posts_by_type.values())
        if total_posts == 0:
            logger.logger.warning("No posts found for analysis")
            return create_empty_response(logger)
        
        logger.logger.info(f"Content collection complete: {total_posts} total posts")
        for post_type, posts in posts_by_type.items():
            logger.logger.info(f"  - {post_type}: {len(posts)} posts")
        
        # Phase 3: Market Context Generation
        market_context = await generate_market_context(posts_by_type, icb_mapping)
        logger.logger.info(f"✓ Market context generated: {len(market_context.get('icb_analysis', []))} ICB sectors, {len(market_context.get('macro_factors', []))} macro factors")
        
        # Phase 4: Company Analysis with Context
        company_analyses = await analyze_companies_with_context(posts_by_type, market_context, icb_mapping)
        
        total_stocks_found = sum(len(a['analysis'].get('mentioned_stocks', [])) for a in company_analyses)
        logger.logger.info(f"✓ Company analysis complete: {len(company_analyses)} posts analyzed, {total_stocks_found} stock mentions found")
        
        # Phase 5: Stock Consolidation with Price Context
        final_stock_insights = await consolidate_stocks_with_price_context(company_analyses, market_context)
        logger.logger.info(f"✓ Stock consolidation complete: {len(final_stock_insights)} final stock insights")
        
        # Phase 6: Post-Analysis Updates
        await perform_post_analysis_updates(final_stock_insights, logger)
        
        # Create comprehensive response
        response_data = create_holistic_response(
            final_stock_insights, 
            market_context, 
            posts_by_type, 
            company_analyses,
            request,
            start_time
        )
        
        # Finalize logging
        log_file = logger.finalize_session(final_stock_insights)
        
        logger.logger.info(f"=== HOLISTIC ANALYSIS COMPLETE ===")
        logger.logger.info(f"Analysis log saved: {log_file}")
        
        return JSONResponse(content=response_data)
        
    except Exception as e:
        logger.log_error("holistic_analysis_failure", str(e), {
            "sources_count": len(request.sources),
            "days": request.days,
            "debug_mode": request.debug
        })
        
        # Finalize logging even on failure
        if logger:
            log_file = logger.finalize_session([])
            
        # Provide detailed error information
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Holistic analysis failed", 
                "message": str(e),
                "log_file": str(log_file) if 'log_file' in locals() else "No log file generated",
                "troubleshooting": "Check the analysis log for detailed failure information",
                "analysis_type": "holistic_multi_source"
            }
        )


async def collect_and_preprocess_content(request, db_service: DatabaseService, logger) -> Dict[str, List[Dict]]:
    """Collect all posts from all sources and categorize by type"""
    
    logger.log_phase_start("content_collection", "Collecting posts from all sources")
    phase_start_time = time.time()
    
    posts_by_type = {
        'company': [],
        'industry': [],
        'macro_economy': []
    }
    
    successful_sources = 0
    failed_sources = []
    
    # Import the existing crawl_posts function
    from main import crawl_posts
    
    try:
        for i, source_request in enumerate(request.sources, 1):
            logger.logger.info(f"Processing source {i}/{len(request.sources)}: {source_request.sourceName}")
            
            try:
                # Get or create source in database
                source_in_db = await db_service.get_source_by_url(source_request.url)
                if not source_in_db:
                    logger.logger.info(f"Creating new source: {source_request.sourceName}")
                    source_id = await db_service.save_source(source_request.dict())
                else:
                    source_id = source_in_db['id']
                    logger.logger.info(f"Using existing source: {source_in_db['name']}")
                
                # Crawl posts from this source
                collected_posts, total_posts_found = await crawl_posts(source_request, days=request.days, debug=request.debug)
                
                logger.logger.info(f"Source {i}: {total_posts_found} posts found, {len(collected_posts)} within {request.days} days")
                
                # Categorize posts by source type
                source_type = source_request.sourceType
                if source_type in posts_by_type:
                    # Add source metadata to each post
                    for post in collected_posts:
                        post['source_name'] = source_request.sourceName
                        post['source_type'] = source_type
                        post['source_id'] = source_id
                    
                    posts_by_type[source_type].extend(collected_posts)
                else:
                    logger.logger.warning(f"Unknown source type: {source_type}, treating as company")
                    for post in collected_posts:
                        post['source_name'] = source_request.sourceName
                        post['source_type'] = 'company'
                        post['source_id'] = source_id
                    posts_by_type['company'].extend(collected_posts)
                
                successful_sources += 1
                
                # In debug mode, break after first successful source
                if request.debug and collected_posts:
                    logger.logger.info("🐛 DEBUG MODE: Stopping after first successful source")
                    break
                    
            except Exception as source_error:
                logger.log_error("source_processing_error", 
                               f"Failed to process source {source_request.sourceName}: {str(source_error)}")
                failed_sources.append({
                    'source_name': source_request.sourceName,
                    'error': str(source_error)
                })
                continue
        
        # Remove duplicates based on URL
        posts_by_type = deduplicate_posts_by_type(posts_by_type, logger)
        
        phase_duration = time.time() - phase_start_time
        total_posts = sum(len(posts) for posts in posts_by_type.values())
        
        logger.log_phase_complete("content_collection", phase_duration, {
            "successful_sources": successful_sources,
            "failed_sources": len(failed_sources),
            "total_posts_collected": total_posts,
            "company_posts": len(posts_by_type['company']),
            "industry_posts": len(posts_by_type['industry']),
            "macro_posts": len(posts_by_type['macro_economy'])
        })
        
        return posts_by_type
        
    except Exception as e:
        logger.log_phase_error("content_collection", e)
        raise


def deduplicate_posts_by_type(posts_by_type: Dict[str, List[Dict]], logger) -> Dict[str, List[Dict]]:
    """Remove duplicate posts based on URL"""
    
    deduplicated = {}
    
    for post_type, posts in posts_by_type.items():
        seen_urls = set()
        unique_posts = []
        
        for post in posts:
            url = post.get('url', '')
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_posts.append(post)
            elif url:
                logger.logger.debug(f"Duplicate post removed: {url}")
        
        deduplicated[post_type] = unique_posts
        
        if len(posts) != len(unique_posts):
            logger.logger.info(f"Deduplicated {post_type}: {len(posts)} -> {len(unique_posts)} posts")
    
    return deduplicated


async def perform_post_analysis_updates(final_stock_insights: List[Dict], logger):
    """Perform stock price and company information updates"""
    
    logger.log_phase_start("post_analysis_updates", "Updating stock prices and company information")
    
    try:
        # Extract mentioned stock symbols
        mentioned_symbols = []
        for insight in final_stock_insights:
            symbol = insight.get('stock_symbol')
            if symbol:
                mentioned_symbols.append(symbol)
        
        if mentioned_symbols:
            logger.logger.info(f"Updating data for {len(mentioned_symbols)} mentioned stocks")
            
            # Update stock prices
            try:
                await update_mentioned_stocks_prices(mentioned_symbols)
                logger.logger.info("✓ Stock prices updated successfully")
            except Exception as price_error:
                logger.log_error("price_update_error", f"Stock price update failed: {price_error}")
            
            # Update company information
            try:
                await update_company_information(mentioned_symbols)
                logger.logger.info("✓ Company information updated successfully")
            except Exception as company_error:
                logger.log_error("company_update_error", f"Company info update failed: {company_error}")
        
        logger.log_phase_complete("post_analysis_updates", 0, {
            "stocks_updated": len(mentioned_symbols)
        })
        
    except Exception as e:
        logger.log_phase_error("post_analysis_updates", e)
        # Don't raise - this is non-critical


def create_holistic_response(final_stock_insights: List[Dict], market_context: Dict, 
                           posts_by_type: Dict, company_analyses: List[Dict],
                           request, start_time: float) -> Dict:
    """Create comprehensive response for holistic analysis"""
    
    # Create posts list for compatibility
    all_posts = []
    for post_type, posts in posts_by_type.items():
        for post in posts:
            # Create post object compatible with existing frontend
            post_object = {
                "url": post['url'],
                "type": post_type,
                "createdDate": post.get('date', ''),
                "content": post.get('content', ''),
                "source_name": post.get('source_name', ''),
                "source_type": post.get('source_type', ''),
                "summary": "Processed in holistic analysis"
            }
            
            # Add mentioned stocks if this was a company post
            mentioned_stocks = []
            for analysis in company_analyses:
                if analysis['post'].get('url') == post['url']:
                    for stock in analysis['analysis'].get('mentioned_stocks', []):
                        mentioned_stocks.append({
                            "stock_symbol": stock.get('stock_symbol', ''),
                            "sentiment": stock.get('sentiment', 'neutral'),
                            "stock_summary": stock.get('summary', '')
                        })
                    break
            
            post_object["mentionedStocks"] = mentioned_stocks
            all_posts.append(post_object)
    
    # Calculate execution time
    execution_duration = f"{time.time() - start_time:.2f}s"
    
    # Create comprehensive response
    response_data = {
        "approach": "holistic_analysis",
        "posts": all_posts,
        "stock_analysis": final_stock_insights,  # This is the main holistic insights
        "market_context": market_context,
        "metadata": {
            "analysis_approach": "holistic_multi_source",
            "sources_requested": len(request.sources),
            "sources_analyzed": len([p for p in posts_by_type.values() if p]),
            "total_posts_analyzed": len(all_posts),
            "unique_stocks_found": len(final_stock_insights),
            "analysis_duration": execution_duration,
            "crawl_timestamp": datetime.now().isoformat(),
            "debug_mode": request.debug,
            "days_analyzed": request.days,
            "analysis_phases": [
                "ICB Data Preparation",
                "Content Collection", 
                "Market Context Generation",
                "Company Analysis with Context",
                "Stock Consolidation with Price Context"
            ],
            "source_breakdown": [
                {
                    "source_name": source.sourceName,
                    "source_type": source.sourceType,
                    "posts_count": len([p for p in all_posts if p.get('source_name') == source.sourceName])
                }
                for source in request.sources
            ]
        }
    }
    
    return response_data


def create_empty_response(logger) -> JSONResponse:
    """Create empty response when no content is found"""
    
    response_data = {
        "approach": "holistic_analysis",
        "posts": [],
        "stock_analysis": [],
        "market_context": {
            "analysis_date": datetime.now().strftime('%Y-%m-%d'),
            "posts_analyzed": 0,
            "icb_analysis": [],
            "macro_factors": [],
            "market_sentiment": "neutral",
            "market_outlook": "No content available for analysis"
        },
        "metadata": {
            "analysis_approach": "holistic_multi_source",
            "unique_stocks_found": 0,
            "total_posts_analyzed": 0,
            "message": "No posts found within the specified date range"
        }
    }
    
    logger.finalize_session([])
    
    return JSONResponse(content=response_data)