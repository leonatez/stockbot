"""
Comprehensive debug logging for crawling and AI analysis workflow
Logs every crawl action, Gemini prompt, and response for debugging and tracing
"""

import logging
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import traceback


class DebugLogger:
    def __init__(self):
        # Create debug logs directory
        self.log_dir = Path("logs/debug")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create timestamped session
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Setup file logger
        self.logger = logging.getLogger(f"debug_session_{self.timestamp}")
        self.logger.setLevel(logging.DEBUG)
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # Create detailed log file
        log_file = self.log_dir / f"debug_{self.timestamp}.log"
        handler = logging.FileHandler(log_file, encoding='utf-8')
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - [%(funcName)s:%(lineno)d] - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        
        # Create JSON structured log for machine parsing
        self.json_log_file = self.log_dir / f"debug_{self.timestamp}.json"
        self.session_data = {
            "session_id": self.timestamp,
            "start_time": datetime.now().isoformat(),
            "crawl_operations": [],
            "gemini_interactions": [],
            "database_operations": [],
            "errors": []
        }
        
        # Counter for operations
        self.operation_counter = 0
        
        self.logger.info("=== DEBUG SESSION STARTED ===")
        self.logger.info(f"Session ID: {self.timestamp}")
        self.logger.info(f"Log file: {log_file}")
        self.logger.info(f"JSON log: {self.json_log_file}")
    
    def get_next_operation_id(self) -> int:
        """Get next operation ID"""
        self.operation_counter += 1
        return self.operation_counter
    
    def log_crawl_start(self, request_data: Dict, source_name: str, url: str):
        """Log the start of a crawl operation"""
        op_id = self.get_next_operation_id()
        
        self.logger.info(f"\n{'='*80}")
        self.logger.info(f"CRAWL START - Operation #{op_id}")
        self.logger.info(f"{'='*80}")
        self.logger.info(f"Source: {source_name}")
        self.logger.info(f"URL: {url}")
        self.logger.info(f"Source Type: {request_data.get('sourceType', 'Unknown')}")
        self.logger.info(f"XPath: {request_data.get('xpath', 'N/A')}")
        self.logger.info(f"Content XPath: {request_data.get('contentXpath', 'N/A')}")
        self.logger.info(f"Date XPath: {request_data.get('contentDateXpath', 'N/A')}")
        self.logger.info(f"Days to crawl: {request_data.get('days', 3)}")
        self.logger.info(f"Debug mode: {request_data.get('debug', False)}")
        
        crawl_data = {
            "operation_id": op_id,
            "operation_type": "crawl_start",
            "timestamp": datetime.now().isoformat(),
            "source_name": source_name,
            "url": url,
            "request_data": request_data,
            "posts_found": [],
            "status": "started"
        }
        
        self.session_data["crawl_operations"].append(crawl_data)
        return op_id
    
    def log_page_crawl(self, op_id: int, page_num: int, page_url: str, posts_found: int):
        """Log individual page crawling"""
        self.logger.info(f"\n--- PAGE CRAWL - Operation #{op_id}, Page {page_num} ---")
        self.logger.info(f"Page URL: {page_url}")
        self.logger.info(f"Posts found on page: {posts_found}")
        
        # Update crawl operation
        for crawl_op in self.session_data["crawl_operations"]:
            if crawl_op["operation_id"] == op_id:
                crawl_op.setdefault("pages_crawled", []).append({
                    "page_number": page_num,
                    "page_url": page_url,
                    "posts_found": posts_found,
                    "timestamp": datetime.now().isoformat()
                })
                break
    
    def log_post_extraction(self, op_id: int, post_url: str, post_date: str, content_length: int, 
                          content_preview: str, source_type: str = "web"):
        """Log individual post extraction"""
        self.logger.info(f"\n--- POST EXTRACTION - Operation #{op_id} ---")
        self.logger.info(f"Post URL: {post_url}")
        self.logger.info(f"Post Date: {post_date}")
        self.logger.info(f"Content Length: {content_length} characters")
        self.logger.info(f"Source Type: {source_type}")
        self.logger.info(f"Content Preview (first 300 chars):")
        self.logger.info(f"'''{content_preview[:300]}'''")
        
        post_data = {
            "post_url": post_url,
            "post_date": post_date,
            "content_length": content_length,
            "content_preview": content_preview[:500],
            "source_type": source_type,
            "extraction_timestamp": datetime.now().isoformat()
        }
        
        # Update crawl operation
        for crawl_op in self.session_data["crawl_operations"]:
            if crawl_op["operation_id"] == op_id:
                crawl_op["posts_found"].append(post_data)
                break
    
    def log_gemini_prompt(self, call_type: str, prompt: str, post_urls: Optional[List[str]] = None, 
                         context_info: Optional[Dict] = None) -> int:
        """Log Gemini prompt being sent"""
        call_id = len(self.session_data["gemini_interactions"]) + 1
        
        self.logger.info(f"\n{'='*80}")
        self.logger.info(f"GEMINI PROMPT - Call #{call_id}")
        self.logger.info(f"{'='*80}")
        self.logger.info(f"Call Type: {call_type}")
        self.logger.info(f"Prompt Length: {len(prompt)} characters")
        self.logger.info(f"Estimated Tokens: {len(prompt.split()) * 1.3:.0f}")
        
        if post_urls:
            self.logger.info(f"Analyzing {len(post_urls)} posts:")
            for i, url in enumerate(post_urls[:5], 1):  # Log first 5 URLs
                self.logger.info(f"  {i}. {url}")
            if len(post_urls) > 5:
                self.logger.info(f"  ... and {len(post_urls) - 5} more posts")
        
        if context_info:
            self.logger.info(f"Context Info: {context_info}")
        
        self.logger.info(f"\n--- FULL PROMPT CONTENT ---")
        self.logger.info(prompt)
        self.logger.info(f"--- END PROMPT CONTENT ---\n")
        
        gemini_data = {
            "call_id": call_id,
            "call_type": call_type,
            "timestamp": datetime.now().isoformat(),
            "prompt": prompt,
            "prompt_length": len(prompt),
            "estimated_tokens": len(prompt.split()) * 1.3,
            "post_urls": post_urls or [],
            "context_info": context_info or {},
            "status": "sent"
        }
        
        self.session_data["gemini_interactions"].append(gemini_data)
        return call_id
    
    def log_gemini_response(self, call_id: int, response: Any, processing_time: float = None):
        """Log Gemini response received"""
        self.logger.info(f"\n{'='*80}")
        self.logger.info(f"GEMINI RESPONSE - Call #{call_id}")
        self.logger.info(f"{'='*80}")
        
        if processing_time:
            self.logger.info(f"Processing Time: {processing_time:.2f} seconds")
        
        response_str = str(response)
        self.logger.info(f"Response Length: {len(response_str)} characters")
        self.logger.info(f"Response Type: {type(response).__name__}")
        
        self.logger.info(f"\n--- FULL RESPONSE CONTENT ---")
        self.logger.info(response_str)
        self.logger.info(f"--- END RESPONSE CONTENT ---\n")
        
        # Try to parse as JSON for structured logging
        parsed_response = None
        try:
            if isinstance(response, str):
                # Try to extract JSON from response
                import re
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    parsed_response = json.loads(json_match.group())
                    self.logger.info(f"Parsed JSON Response: {len(parsed_response)} items")
            elif isinstance(response, (dict, list)):
                parsed_response = response
        except Exception as e:
            self.logger.warning(f"Could not parse response as JSON: {e}")
        
        # Update gemini interaction
        for interaction in self.session_data["gemini_interactions"]:
            if interaction["call_id"] == call_id:
                interaction.update({
                    "response": response_str,
                    "response_length": len(response_str),
                    "processing_time": processing_time,
                    "parsed_response": parsed_response,
                    "response_timestamp": datetime.now().isoformat(),
                    "status": "success"
                })
                break
    
    def log_gemini_error(self, call_id: int, error: Exception, error_context: Optional[Dict] = None):
        """Log Gemini API error"""
        self.logger.error(f"\n{'='*80}")
        self.logger.error(f"GEMINI ERROR - Call #{call_id}")
        self.logger.error(f"{'='*80}")
        self.logger.error(f"Error Type: {type(error).__name__}")
        self.logger.error(f"Error Message: {str(error)}")
        
        if error_context:
            self.logger.error(f"Error Context: {error_context}")
        
        self.logger.error(f"Traceback:")
        self.logger.error(traceback.format_exc())
        
        error_data = {
            "timestamp": datetime.now().isoformat(),
            "error_type": "gemini_api_error",
            "call_id": call_id,
            "error_message": str(error),
            "error_class": type(error).__name__,
            "context": error_context or {},
            "traceback": traceback.format_exc()
        }
        
        self.session_data["errors"].append(error_data)
        
        # Update gemini interaction
        for interaction in self.session_data["gemini_interactions"]:
            if interaction["call_id"] == call_id:
                interaction.update({
                    "error_message": str(error),
                    "error_type": type(error).__name__,
                    "error_timestamp": datetime.now().isoformat(),
                    "status": "error"
                })
                break
    
    def log_database_operation(self, operation_type: str, table: str, data: Any, result: Any = None, error: Exception = None):
        """Log database operations"""
        self.logger.info(f"\n--- DATABASE OPERATION ---")
        self.logger.info(f"Operation: {operation_type}")
        self.logger.info(f"Table: {table}")
        
        if error:
            self.logger.error(f"Database Error: {str(error)}")
            self.logger.error(f"Error Type: {type(error).__name__}")
        else:
            self.logger.info(f"Operation Status: Success")
            if result:
                self.logger.info(f"Result: {str(result)[:200]}...")
        
        db_data = {
            "timestamp": datetime.now().isoformat(),
            "operation_type": operation_type,
            "table": table,
            "data_preview": str(data)[:500] if data else None,
            "result_preview": str(result)[:500] if result else None,
            "success": error is None,
            "error_message": str(error) if error else None,
            "error_type": type(error).__name__ if error else None
        }
        
        self.session_data["database_operations"].append(db_data)
        
        if error:
            error_data = {
                "timestamp": datetime.now().isoformat(),
                "error_type": "database_error",
                "operation": operation_type,
                "table": table,
                "error_message": str(error),
                "error_class": type(error).__name__
            }
            self.session_data["errors"].append(error_data)
    
    def log_analysis_result(self, operation_id: int, analysis_type: str, stocks_found: List[Dict], 
                          summary: Dict):
        """Log analysis results"""
        self.logger.info(f"\n{'='*80}")
        self.logger.info(f"ANALYSIS RESULT - Operation #{operation_id}")
        self.logger.info(f"{'='*80}")
        self.logger.info(f"Analysis Type: {analysis_type}")
        self.logger.info(f"Stocks Found: {len(stocks_found)}")
        
        for i, stock in enumerate(stocks_found[:10], 1):  # Log first 10 stocks
            self.logger.info(f"  {i}. {stock.get('stock_symbol', 'Unknown')} - {stock.get('sentiment', 'Unknown')}")
        
        if len(stocks_found) > 10:
            self.logger.info(f"  ... and {len(stocks_found) - 10} more stocks")
        
        self.logger.info(f"Analysis Summary: {summary}")
        
        # Update crawl operation with results
        for crawl_op in self.session_data["crawl_operations"]:
            if crawl_op["operation_id"] == operation_id:
                crawl_op.update({
                    "analysis_type": analysis_type,
                    "stocks_found_count": len(stocks_found),
                    "stocks_found": stocks_found,
                    "analysis_summary": summary,
                    "status": "completed",
                    "completion_timestamp": datetime.now().isoformat()
                })
                break
    
    def log_error(self, error_type: str, error_message: str, context: Optional[Dict] = None):
        """Log general errors"""
        self.logger.error(f"\n--- ERROR ---")
        self.logger.error(f"Type: {error_type}")
        self.logger.error(f"Message: {error_message}")
        if context:
            self.logger.error(f"Context: {context}")
        
        error_data = {
            "timestamp": datetime.now().isoformat(),
            "error_type": error_type,
            "error_message": error_message,
            "context": context or {}
        }
        
        self.session_data["errors"].append(error_data)
    
    def finalize_session(self):
        """Finalize debug session and write JSON log"""
        end_time = datetime.now()
        start_time = datetime.fromisoformat(self.session_data["start_time"])
        total_duration = (end_time - start_time).total_seconds()
        
        self.session_data["end_time"] = end_time.isoformat()
        self.session_data["total_duration_seconds"] = total_duration
        
        # Calculate summary
        summary = {
            "total_crawl_operations": len(self.session_data["crawl_operations"]),
            "total_gemini_calls": len(self.session_data["gemini_interactions"]),
            "successful_gemini_calls": len([g for g in self.session_data["gemini_interactions"] 
                                          if g.get("status") == "success"]),
            "total_database_operations": len(self.session_data["database_operations"]),
            "total_errors": len(self.session_data["errors"]),
            "session_duration_minutes": total_duration / 60
        }
        
        self.session_data["session_summary"] = summary
        
        # Write JSON log
        with open(self.json_log_file, 'w', encoding='utf-8') as f:
            json.dump(self.session_data, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"\n{'='*80}")
        self.logger.info(f"DEBUG SESSION COMPLETED")
        self.logger.info(f"{'='*80}")
        self.logger.info(f"Session Duration: {total_duration:.2f}s ({total_duration/60:.1f}m)")
        self.logger.info(f"Crawl Operations: {summary['total_crawl_operations']}")
        self.logger.info(f"Gemini Calls: {summary['successful_gemini_calls']}/{summary['total_gemini_calls']} successful")
        self.logger.info(f"Database Operations: {summary['total_database_operations']}")
        self.logger.info(f"Errors: {summary['total_errors']}")
        self.logger.info(f"JSON log saved: {self.json_log_file}")
        
        return self.json_log_file


# Global debug logger instance
debug_logger = None

def get_debug_logger() -> DebugLogger:
    """Get or create debug logger for current session"""
    global debug_logger
    if debug_logger is None:
        debug_logger = DebugLogger()
    return debug_logger

def reset_debug_logger():
    """Reset logger for new session"""
    global debug_logger
    if debug_logger:
        debug_logger.finalize_session()
    debug_logger = None

def initialize_debug_session():
    """Initialize new debug session"""
    reset_debug_logger()
    return get_debug_logger()