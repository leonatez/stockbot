"""
Analysis Progress Tracker
Provides real-time progress updates during multi-step analysis process
"""

import asyncio
from typing import Dict, Any, Optional
from datetime import datetime

class AnalysisProgressTracker:
    """Track progress for multi-step stock analysis"""
    
    def __init__(self, total_steps: int = 10):
        self.total_steps = total_steps
        self.current_step = 0
        self.progress_data = {
            "progress_percentage": 0,
            "current_phase": "Starting analysis",
            "phase_details": "",
            "start_time": datetime.now().isoformat(),
            "estimated_completion": None,
            "completed_tasks": [],
            "current_task": "",
            "errors": []
        }
    
    def update_progress(self, step_increment: int = 1, phase: str = "", details: str = "", task: str = ""):
        """Update progress with new step information"""
        self.current_step = min(self.current_step + step_increment, self.total_steps)
        
        self.progress_data.update({
            "progress_percentage": int((self.current_step / self.total_steps) * 100),
            "current_phase": phase if phase else self.progress_data["current_phase"],
            "phase_details": details,
            "current_task": task,
            "updated_at": datetime.now().isoformat()
        })
        
        if task and task not in self.progress_data["completed_tasks"]:
            if self.progress_data["current_task"] and self.progress_data["current_task"] != task:
                self.progress_data["completed_tasks"].append(self.progress_data["current_task"])
    
    def add_error(self, error_message: str):
        """Add error to progress tracking"""
        self.progress_data["errors"].append({
            "message": error_message,
            "timestamp": datetime.now().isoformat()
        })
    
    def get_progress(self) -> Dict[str, Any]:
        """Get current progress data"""
        return self.progress_data.copy()
    
    def complete(self, final_message: str = "Analysis completed"):
        """Mark analysis as completed"""
        self.current_step = self.total_steps
        self.progress_data.update({
            "progress_percentage": 100,
            "current_phase": final_message,
            "phase_details": "All analysis steps completed successfully",
            "completed_at": datetime.now().isoformat(),
            "current_task": ""
        })

# Progress step definitions for stock analysis
ANALYSIS_STEPS = {
    1: {"phase": "Initializing", "task": "Setting up analysis environment"},
    2: {"phase": "Crawling Sources", "task": "Fetching posts from configured sources"},  
    3: {"phase": "Content Processing", "task": "Extracting and cleaning post content"},
    4: {"phase": "AI Analysis", "task": "Analyzing content with Gemini for stock mentions"},
    5: {"phase": "Database Updates", "task": "Saving analysis results to database"},
    6: {"phase": "Industry Context", "task": "Gathering industry sentiment for mentioned stocks"},
    7: {"phase": "Macro Context", "task": "Collecting macro economic environment data"},
    8: {"phase": "Price Updates", "task": "Fetching latest stock prices from VNStock"},
    9: {"phase": "Company Info", "task": "Updating company information and events"},
    10: {"phase": "Finalizing", "task": "Preparing comprehensive analysis results"}
}

def create_analysis_progress_tracker() -> AnalysisProgressTracker:
    """Create a progress tracker with predefined analysis steps"""
    return AnalysisProgressTracker(total_steps=len(ANALYSIS_STEPS))

# Progress tracking for different analysis types
INDUSTRY_ANALYSIS_STEPS = {
    1: {"phase": "Initializing", "task": "Setting up industry analysis"},
    2: {"phase": "Content Processing", "task": "Analyzing posts for industry mentions"},
    3: {"phase": "AI Analysis", "task": "Extracting industry sentiment with Gemini"},
    4: {"phase": "Database Storage", "task": "Saving industry analysis results"},
    5: {"phase": "Sentiment Aggregation", "task": "Computing daily industry sentiment"}
}

MACRO_ANALYSIS_STEPS = {
    1: {"phase": "Initializing", "task": "Setting up macro economy analysis"},
    2: {"phase": "Content Processing", "task": "Analyzing posts for macro themes"},
    3: {"phase": "Theme Extraction", "task": "Identifying macro economic themes with AI"},
    4: {"phase": "Indicator Extraction", "task": "Extracting macro economic indicators"},
    5: {"phase": "Database Storage", "task": "Saving macro analysis results"}
}

def create_industry_progress_tracker() -> AnalysisProgressTracker:
    """Create progress tracker for industry analysis"""
    return AnalysisProgressTracker(total_steps=len(INDUSTRY_ANALYSIS_STEPS))

def create_macro_progress_tracker() -> AnalysisProgressTracker:
    """Create progress tracker for macro economy analysis"""  
    return AnalysisProgressTracker(total_steps=len(MACRO_ANALYSIS_STEPS))