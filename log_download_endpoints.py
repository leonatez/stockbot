"""
Add these endpoints to your main.py to download log files via web interface
"""

from fastapi import HTTPException
from fastapi.responses import FileResponse, JSONResponse
import os
import glob
from pathlib import Path
import json
from datetime import datetime

# Add these endpoints to your main.py FastAPI app

@app.get("/logs/list")
async def list_log_files():
    """List all available log files"""
    try:
        logs_data = {
            "debug_logs": [],
            "holistic_analysis_logs": [],
            "log_directories": []
        }
        
        # Check if logs directories exist
        debug_dir = Path("logs/debug")
        holistic_dir = Path("logs/holistic_analysis")
        
        if debug_dir.exists():
            logs_data["log_directories"].append("debug")
            # List debug log files
            for log_file in sorted(debug_dir.glob("*.json"), key=os.path.getmtime, reverse=True):
                file_stats = log_file.stat()
                logs_data["debug_logs"].append({
                    "filename": log_file.name,
                    "path": str(log_file),
                    "size_bytes": file_stats.st_size,
                    "modified": datetime.fromtimestamp(file_stats.st_mtime).isoformat(),
                    "download_url": f"/logs/download/debug/{log_file.name}"
                })
        
        if holistic_dir.exists():
            logs_data["log_directories"].append("holistic_analysis")
            # List holistic analysis log files
            for log_file in sorted(holistic_dir.glob("*.json"), key=os.path.getmtime, reverse=True):
                file_stats = log_file.stat()
                logs_data["holistic_analysis_logs"].append({
                    "filename": log_file.name,
                    "path": str(log_file),
                    "size_bytes": file_stats.st_size,
                    "modified": datetime.fromtimestamp(file_stats.st_mtime).isoformat(),
                    "download_url": f"/logs/download/holistic_analysis/{log_file.name}"
                })
        
        return JSONResponse(content=logs_data)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing log files: {str(e)}")

@app.get("/logs/download/{log_type}/{filename}")
async def download_log_file(log_type: str, filename: str):
    """Download a specific log file"""
    try:
        # Validate log_type
        if log_type not in ["debug", "holistic_analysis"]:
            raise HTTPException(status_code=400, detail="Invalid log type. Use 'debug' or 'holistic_analysis'")
        
        # Construct file path
        file_path = Path(f"logs/{log_type}/{filename}")
        
        # Security check - ensure file is within logs directory
        if not str(file_path.resolve()).startswith(str(Path("logs").resolve())):
            raise HTTPException(status_code=400, detail="Invalid file path")
        
        # Check if file exists
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Log file not found")
        
        # Return file
        return FileResponse(
            path=str(file_path),
            filename=filename,
            media_type="application/json"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error downloading log file: {str(e)}")

@app.get("/logs/latest/{log_type}")
async def get_latest_log(log_type: str):
    """Get the content of the latest log file"""
    try:
        # Validate log_type
        if log_type not in ["debug", "holistic_analysis"]:
            raise HTTPException(status_code=400, detail="Invalid log type. Use 'debug' or 'holistic_analysis'")
        
        # Find latest JSON file
        log_dir = Path(f"logs/{log_type}")
        if not log_dir.exists():
            raise HTTPException(status_code=404, detail=f"Log directory '{log_type}' not found")
        
        json_files = list(log_dir.glob("*.json"))
        if not json_files:
            raise HTTPException(status_code=404, detail=f"No JSON log files found in '{log_type}' directory")
        
        # Get latest file by modification time
        latest_file = max(json_files, key=os.path.getmtime)
        
        # Read and return content
        with open(latest_file, 'r', encoding='utf-8') as f:
            content = json.load(f)
        
        return {
            "filename": latest_file.name,
            "file_path": str(latest_file),
            "file_size": latest_file.stat().st_size,
            "modified": datetime.fromtimestamp(latest_file.stat().st_mtime).isoformat(),
            "content": content
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading latest log: {str(e)}")

@app.get("/logs/search")
async def search_logs(log_type: str = "holistic_analysis", search_term: str = "", limit: int = 10):
    """Search through log files for specific content"""
    try:
        # Validate log_type
        if log_type not in ["debug", "holistic_analysis"]:
            raise HTTPException(status_code=400, detail="Invalid log type. Use 'debug' or 'holistic_analysis'")
        
        log_dir = Path(f"logs/{log_type}")
        if not log_dir.exists():
            raise HTTPException(status_code=404, detail=f"Log directory '{log_type}' not found")
        
        results = []
        json_files = sorted(log_dir.glob("*.json"), key=os.path.getmtime, reverse=True)
        
        for log_file in json_files[:limit]:
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # If search term provided, check if it's in the content
                if search_term and search_term.lower() not in content.lower():
                    continue
                
                # Parse JSON and extract relevant info
                data = json.loads(content)
                
                file_info = {
                    "filename": log_file.name,
                    "modified": datetime.fromtimestamp(log_file.stat().st_mtime).isoformat(),
                    "file_size": log_file.stat().st_size,
                    "download_url": f"/logs/download/{log_type}/{log_file.name}"
                }
                
                # Add summary based on log type
                if log_type == "holistic_analysis":
                    file_info["summary"] = {
                        "session_id": data.get("session_id"),
                        "total_gemini_calls": len(data.get("gemini_calls", [])),
                        "total_errors": len(data.get("errors", [])),
                        "duration_minutes": data.get("total_duration_seconds", 0) / 60,
                        "stocks_analyzed": data.get("summary", {}).get("stocks_analyzed", 0)
                    }
                elif log_type == "debug":
                    file_info["summary"] = {
                        "session_id": data.get("session_id"),
                        "crawl_operations": len(data.get("crawl_operations", [])),
                        "gemini_calls": len(data.get("gemini_interactions", [])),
                        "database_operations": len(data.get("database_operations", [])),
                        "total_errors": len(data.get("errors", []))
                    }
                
                results.append(file_info)
                
            except Exception as e:
                # Skip files that can't be parsed
                continue
        
        return {
            "log_type": log_type,
            "search_term": search_term,
            "results_count": len(results),
            "results": results
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching logs: {str(e)}")

# Add a simple HTML interface to browse logs
@app.get("/logs/browser", response_class=HTMLResponse)
async def log_browser():
    """Simple HTML interface to browse and download logs"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Stock Bot - Log Browser</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .log-section { margin-bottom: 30px; border: 1px solid #ddd; padding: 15px; }
            .log-file { margin: 10px 0; padding: 10px; background: #f5f5f5; border-radius: 4px; }
            .download-btn { background: #007bff; color: white; padding: 5px 10px; text-decoration: none; border-radius: 3px; margin-right: 10px; }
            .view-btn { background: #28a745; color: white; padding: 5px 10px; text-decoration: none; border-radius: 3px; }
            .file-info { color: #666; font-size: 0.9em; }
        </style>
    </head>
    <body>
        <h1>Stock Bot - Log Browser</h1>
        <div id="logs-container">Loading logs...</div>
        
        <script>
            async function loadLogs() {
                try {
                    const response = await fetch('/logs/list');
                    const data = await response.json();
                    
                    let html = '';
                    
                    // Debug logs section
                    if (data.debug_logs.length > 0) {
                        html += '<div class="log-section"><h2>Debug Logs</h2>';
                        data.debug_logs.forEach(log => {
                            html += `
                                <div class="log-file">
                                    <strong>${log.filename}</strong>
                                    <div class="file-info">
                                        Size: ${(log.size_bytes / 1024).toFixed(1)} KB | 
                                        Modified: ${new Date(log.modified).toLocaleString()}
                                    </div>
                                    <a href="${log.download_url}" class="download-btn">Download</a>
                                    <a href="/logs/latest/debug" class="view-btn" target="_blank">View Latest</a>
                                </div>
                            `;
                        });
                        html += '</div>';
                    }
                    
                    // Holistic analysis logs section  
                    if (data.holistic_analysis_logs.length > 0) {
                        html += '<div class="log-section"><h2>Holistic Analysis Logs</h2>';
                        data.holistic_analysis_logs.forEach(log => {
                            html += `
                                <div class="log-file">
                                    <strong>${log.filename}</strong>
                                    <div class="file-info">
                                        Size: ${(log.size_bytes / 1024).toFixed(1)} KB | 
                                        Modified: ${new Date(log.modified).toLocaleString()}
                                    </div>
                                    <a href="${log.download_url}" class="download-btn">Download</a>
                                    <a href="/logs/latest/holistic_analysis" class="view-btn" target="_blank">View Latest</a>
                                </div>
                            `;
                        });
                        html += '</div>';
                    }
                    
                    if (data.debug_logs.length === 0 && data.holistic_analysis_logs.length === 0) {
                        html = '<p>No log files found. Run some crawl operations to generate logs.</p>';
                    }
                    
                    document.getElementById('logs-container').innerHTML = html;
                    
                } catch (error) {
                    document.getElementById('logs-container').innerHTML = `<p>Error loading logs: ${error.message}</p>`;
                }
            }
            
            loadLogs();
            
            // Auto-refresh every 30 seconds
            setInterval(loadLogs, 30000);
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)