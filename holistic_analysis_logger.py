"""
Comprehensive logging system for holistic analysis workflow
Tracks every Gemini call, response, and analysis phase for optimization
"""

import logging
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional


class HolisticAnalysisLogger:
    def __init__(self):
        # Create logs directory
        self.log_dir = Path("logs/holistic_analysis")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup main logger
        self.logger = logging.getLogger("holistic_analysis")
        self.logger.setLevel(logging.INFO)
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # Create timestamped log file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = self.log_dir / f"analysis_{timestamp}.log"
        
        handler = logging.FileHandler(log_file, encoding='utf-8')
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        
        # Also log to console
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # Create structured JSON log
        self.json_log_file = self.log_dir / f"analysis_{timestamp}.json"
        self.analysis_session = {
            "session_id": timestamp,
            "start_time": datetime.now().isoformat(),
            "gemini_calls": [],
            "phases": {},
            "errors": [],
            "summary": {},
            "performance_metrics": {}
        }
    
    def log_analysis_start(self, sources: List[Dict], days: int):
        """Log the start of analysis session"""
        self.logger.info(f"=== HOLISTIC ANALYSIS SESSION START ===")
        self.logger.info(f"Sources: {len(sources)}, Days: {days}")
        
        self.analysis_session["sources_count"] = len(sources)
        self.analysis_session["days"] = days
        self.analysis_session["sources"] = [
            {"name": s.get('sourceName'), "type": s.get('sourceType'), "url": s.get('url')} 
            for s in sources
        ]
        
        for i, source in enumerate(sources, 1):
            self.logger.info(f"  Source {i}: {source.get('sourceName')} ({source.get('sourceType')})")
    
    def log_gemini_call(self, call_type: str, prompt: str, post_urls: Optional[List[str]] = None) -> int:
        """Log a Gemini API call"""
        call_id = len(self.analysis_session["gemini_calls"]) + 1
        
        # Log summary with full prompt content for debugging
        if post_urls:
            self.logger.info(f"GEMINI CALL #{call_id} ({call_type}): Analyzing {len(post_urls)} posts")
            for url in post_urls[:3]:  # Log first 3 URLs
                self.logger.info(f"  - Post URL: {url}")
            if len(post_urls) > 3:
                self.logger.info(f"  - ... and {len(post_urls) - 3} more posts")
        else:
            self.logger.info(f"GEMINI CALL #{call_id} ({call_type}): Context generation")
        
        self.logger.info(f"  - Prompt length: {len(prompt)} characters")
        self.logger.info(f"  - Estimated tokens: {len(prompt.split()) * 1.3:.0f}")
        
        # Log full prompt content for debugging
        self.logger.info(f"\n--- FULL PROMPT CONTENT (Call #{call_id}) ---")
        self.logger.info(prompt)
        self.logger.info(f"--- END PROMPT CONTENT (Call #{call_id}) ---\n")
        
        # Store detailed info in JSON
        call_data = {
            "call_id": call_id,
            "call_type": call_type,
            "timestamp": datetime.now().isoformat(),
            "post_urls": post_urls or [],
            "prompt_length": len(prompt),
            "prompt_preview": prompt[:500] + "..." if len(prompt) > 500 else prompt,
            "prompt_full": prompt,  # Store full prompt for complete debugging
            "estimated_tokens": len(prompt.split()) * 1.3  # Rough estimation
        }
        
        self.analysis_session["gemini_calls"].append(call_data)
        
        return call_id
    
    def log_gemini_response(self, call_type: str, response: Any, identifier: Optional[str] = None):
        """Log Gemini API response"""
        call_id = len(self.analysis_session["gemini_calls"])
        
        if identifier:
            self.logger.info(f"GEMINI RESPONSE #{call_id} ({call_type}) for {identifier}: Success")
        else:
            self.logger.info(f"GEMINI RESPONSE #{call_id} ({call_type}): Success")
        
        response_str = str(response)
        self.logger.info(f"  - Response length: {len(response_str)} characters")
        
        # Log full response content for debugging
        self.logger.info(f"\n--- FULL RESPONSE CONTENT (Call #{call_id}) ---")
        self.logger.info(response_str)
        self.logger.info(f"--- END RESPONSE CONTENT (Call #{call_id}) ---\n")
        
        # Update the call data with response info
        if self.analysis_session["gemini_calls"]:
            self.analysis_session["gemini_calls"][-1].update({
                "response_timestamp": datetime.now().isoformat(),
                "response_success": True,
                "response_length": len(response_str),
                "response_preview": response_str[:500] + "..." if len(response_str) > 500 else response_str,
                "response_full": response_str,  # Store full response for complete debugging
                "response_type": type(response).__name__
            })
    
    def log_gemini_error(self, call_type: str, error: Exception, identifier: Optional[str] = None):
        """Log Gemini API error"""
        call_id = len(self.analysis_session["gemini_calls"])
        
        if identifier:
            self.logger.error(f"GEMINI ERROR #{call_id} ({call_type}) for {identifier}: {str(error)}")
        else:
            self.logger.error(f"GEMINI ERROR #{call_id} ({call_type}): {str(error)}")
        
        # Update the call data with error info
        if self.analysis_session["gemini_calls"]:
            self.analysis_session["gemini_calls"][-1].update({
                "response_timestamp": datetime.now().isoformat(),
                "response_success": False,
                "error_message": str(error),
                "error_type": type(error).__name__
            })
        
        self.log_error("gemini_api_error", str(error), {"call_type": call_type, "identifier": identifier})
    
    def log_error(self, error_type: str, error_message: str, context: Optional[Dict] = None):
        """Log general errors"""
        self.logger.error(f"ERROR ({error_type}): {error_message}")
        if context:
            self.logger.error(f"Context: {context}")
        
        self.analysis_session["errors"].append({
            "timestamp": datetime.now().isoformat(),
            "error_type": error_type,
            "error_message": error_message,
            "context": context or {}
        })
    
    def log_phase_start(self, phase_name: str, description: str = ""):
        """Log the start of an analysis phase"""
        self.logger.info(f"\n=== PHASE START: {phase_name} ===")
        if description:
            self.logger.info(f"Description: {description}")
        
        if phase_name not in self.analysis_session["phases"]:
            self.analysis_session["phases"][phase_name] = {}
        
        self.analysis_session["phases"][phase_name]["start_time"] = datetime.now().isoformat()
    
    def log_phase_complete(self, phase_name: str, duration: float, results_summary: Dict):
        """Log completion of an analysis phase"""
        self.logger.info(f"PHASE COMPLETE: {phase_name} ({duration:.2f}s)")
        self.logger.info(f"Results: {results_summary}")
        
        if phase_name in self.analysis_session["phases"]:
            self.analysis_session["phases"][phase_name].update({
                "duration_seconds": duration,
                "results_summary": results_summary,
                "completed_at": datetime.now().isoformat(),
                "success": True
            })
    
    def log_phase_error(self, phase_name: str, error: Exception):
        """Log phase failure"""
        self.logger.error(f"PHASE FAILED: {phase_name} - {str(error)}")
        
        if phase_name in self.analysis_session["phases"]:
            self.analysis_session["phases"][phase_name].update({
                "completed_at": datetime.now().isoformat(),
                "success": False,
                "error_message": str(error),
                "error_type": type(error).__name__
            })
    
    def log_content_collection_summary(self, posts_by_type: Dict, total_tokens: int):
        """Log content collection summary"""
        self.logger.info(f"\n--- Content Collection Summary ---")
        for post_type, posts in posts_by_type.items():
            self.logger.info(f"{post_type}: {len(posts)} posts")
        self.logger.info(f"Estimated total tokens: {total_tokens:,}")
    
    def log_company_analysis_start(self, current: int, total: int, post_url: str):
        """Log start of individual company analysis"""
        self.logger.info(f"\n--- Company Analysis {current}/{total} ---")
        self.logger.info(f"Post URL: {post_url}")
    
    def log_company_analysis_complete(self, post_index: int, stocks_found: int):
        """Log completion of individual company analysis"""
        self.logger.info(f"Company analysis {post_index} complete: {stocks_found} stocks found")
    
    def log_stock_consolidation_start(self, symbol: str, mentions_count: int):
        """Log start of stock consolidation"""
        self.logger.info(f"\n--- Stock Consolidation: {symbol} ---")
        self.logger.info(f"Consolidating {mentions_count} mentions")
    
    def log_stock_consolidation_complete(self, symbol: str):
        """Log completion of stock consolidation"""
        self.logger.info(f"Stock consolidation complete: {symbol}")
    
    def log_performance_metric(self, metric_name: str, value: Any):
        """Log performance metrics"""
        self.analysis_session["performance_metrics"][metric_name] = value
        self.logger.info(f"METRIC: {metric_name} = {value}")
    
    def finalize_session(self, final_results: List[Dict]):
        """Finalize the analysis session and write logs"""
        end_time = datetime.now()
        start_time = datetime.fromisoformat(self.analysis_session["start_time"])
        total_duration = (end_time - start_time).total_seconds()
        
        self.analysis_session["end_time"] = end_time.isoformat()
        self.analysis_session["total_duration_seconds"] = total_duration
        
        # Calculate summary statistics
        total_gemini_calls = len(self.analysis_session["gemini_calls"])
        successful_calls = sum(1 for call in self.analysis_session["gemini_calls"] 
                             if call.get("response_success", False))
        total_errors = len(self.analysis_session["errors"])
        
        self.analysis_session["summary"] = {
            "total_gemini_calls": total_gemini_calls,
            "successful_gemini_calls": successful_calls,
            "failed_gemini_calls": total_gemini_calls - successful_calls,
            "total_errors": total_errors,
            "phases_completed": len([p for p in self.analysis_session["phases"].values() 
                                   if p.get("success", False)]),
            "phases_failed": len([p for p in self.analysis_session["phases"].values() 
                                if p.get("success") is False]),
            "stocks_analyzed": len(final_results),
            "overall_success": total_errors == 0 and successful_calls == total_gemini_calls,
            "total_duration_minutes": total_duration / 60
        }
        
        # Write JSON log
        with open(self.json_log_file, 'w', encoding='utf-8') as f:
            json.dump(self.analysis_session, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"\n=== HOLISTIC ANALYSIS SESSION COMPLETE ===")
        self.logger.info(f"Total duration: {total_duration:.2f}s ({total_duration/60:.1f}m)")
        self.logger.info(f"Gemini calls: {successful_calls}/{total_gemini_calls} successful")
        self.logger.info(f"Stocks analyzed: {len(final_results)}")
        self.logger.info(f"Errors: {total_errors}")
        self.logger.info(f"JSON log saved: {self.json_log_file}")
        
        return self.json_log_file


# Global logger instance - will be created fresh for each analysis session
analysis_logger = None

def get_analysis_logger() -> HolisticAnalysisLogger:
    """Get or create analysis logger for current session"""
    global analysis_logger
    if analysis_logger is None:
        analysis_logger = HolisticAnalysisLogger()
    return analysis_logger

def reset_analysis_logger():
    """Reset logger for new analysis session"""
    global analysis_logger
    analysis_logger = None