#!/usr/bin/env python3
"""
Test script for debug logging functionality
"""

import sys
import os
import asyncio
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from debug_logger import DebugLogger, initialize_debug_session

def test_debug_logger():
    """Test the debug logger functionality"""
    print("=== Testing Debug Logger Functionality ===\n")
    
    # Initialize debug session
    logger = initialize_debug_session()
    
    # Test 1: Log crawl start
    print("1. Testing crawl start logging...")
    request_data = {
        "sourceName": "Test Source",
        "sourceType": "company",
        "url": "https://test.example.com",
        "xpath": "//div[@class='post']",
        "contentXpath": "//div[@class='content']",
        "contentDateXpath": "//span[@class='date']",
        "days": 3,
        "debug": True
    }
    
    op_id = logger.log_crawl_start(
        request_data=request_data,
        source_name="Test Source",
        url="https://test.example.com"
    )
    print(f"✓ Created operation ID: {op_id}")
    
    # Test 2: Log page crawl
    print("\n2. Testing page crawl logging...")
    logger.log_page_crawl(op_id, 1, "https://test.example.com/page/1", 5)
    logger.log_page_crawl(op_id, 2, "https://test.example.com/page/2", 3)
    print("✓ Logged page crawls")
    
    # Test 3: Log post extraction
    print("\n3. Testing post extraction logging...")
    test_content = """
    Này là nội dung bài viết test về cổ phiếu VIC và HPG.
    VIC tăng trưởng mạnh trong quý này với doanh thu đạt 1000 tỷ đồng.
    HPG cũng có kết quả khả quan với lợi nhuận tăng 15% so với cùng kỳ.
    """
    
    logger.log_post_extraction(
        op_id=op_id,
        post_url="https://test.example.com/post/123",
        post_date="20/08/2025",
        content_length=len(test_content),
        content_preview=test_content,
        source_type="company"
    )
    print("✓ Logged post extraction")
    
    # Test 4: Log Gemini prompt
    print("\n4. Testing Gemini prompt logging...")
    test_prompt = """
    Phân tích bài viết sau và tìm các cổ phiếu được đề cập:
    
    """ + test_content
    
    call_id = logger.log_gemini_prompt(
        call_type="individual_post_analysis",
        prompt=test_prompt,
        post_urls=["https://test.example.com/post/123"],
        context_info={"source_type": "company", "post_date": "20/08/2025"}
    )
    print(f"✓ Created Gemini call ID: {call_id}")
    
    # Test 5: Log Gemini response
    print("\n5. Testing Gemini response logging...")
    mock_response = {
        "post_summary": "Bài viết phân tích tình hình kinh doanh của VIC và HPG",
        "mentioned_stocks": [
            {
                "stock_symbol": "VIC",
                "sentiment": "positive",
                "summary": "VIC tăng trưởng mạnh với doanh thu 1000 tỷ đồng"
            },
            {
                "stock_symbol": "HPG",
                "sentiment": "positive",
                "summary": "HPG có lợi nhuận tăng 15% so với cùng kỳ"
            }
        ]
    }
    
    logger.log_gemini_response(call_id, mock_response, processing_time=2.5)
    print("✓ Logged Gemini response")
    
    # Test 6: Log database operation
    print("\n6. Testing database operation logging...")
    logger.log_database_operation(
        operation_type="save_post_with_analysis",
        table="posts",
        data={"post_url": "https://test.example.com/post/123", "stocks_count": 2},
        result="success"
    )
    print("✓ Logged database operation")
    
    # Test 7: Log analysis results
    print("\n7. Testing analysis results logging...")
    analysis_results = [
        {
            "stock_symbol": "VIC",
            "mentioned_count": 1,
            "overall_sentiment": "positive",
            "posts": [
                {
                    "url": "https://test.example.com/post/123",
                    "sentiment": "positive"
                }
            ]
        },
        {
            "stock_symbol": "HPG", 
            "mentioned_count": 1,
            "overall_sentiment": "positive",
            "posts": [
                {
                    "url": "https://test.example.com/post/123",
                    "sentiment": "positive"
                }
            ]
        }
    ]
    
    logger.log_analysis_result(
        operation_id=op_id,
        analysis_type="stock_level_analysis",
        stocks_found=analysis_results,
        summary={
            "total_posts": 1,
            "unique_stocks": 2,
            "source_type": "company"
        }
    )
    print("✓ Logged analysis results")
    
    # Test 8: Test error logging
    print("\n8. Testing error logging...")
    try:
        raise ValueError("This is a test error")
    except Exception as e:
        logger.log_gemini_error(
            call_id=call_id + 1,
            error=e,
            error_context={"test": "error_simulation"}
        )
        
        logger.log_error(
            error_type="test_error",
            error_message="This is a general test error",
            context={"function": "test_debug_logger"}
        )
    print("✓ Logged errors")
    
    # Test 9: Finalize session
    print("\n9. Testing session finalization...")
    json_log_path = logger.finalize_session()
    print(f"✓ Session finalized. JSON log saved to: {json_log_path}")
    
    # Verify files were created
    log_dir = Path("logs/debug")
    log_files = list(log_dir.glob("debug_*.log"))
    json_files = list(log_dir.glob("debug_*.json"))
    
    print(f"\n=== Test Results ===")
    print(f"Log directory: {log_dir}")
    print(f"Log files created: {len(log_files)}")
    print(f"JSON files created: {len(json_files)}")
    
    if log_files:
        latest_log = max(log_files, key=os.path.getctime)
        print(f"Latest log file: {latest_log}")
        
        # Show file size
        file_size = latest_log.stat().st_size
        print(f"Log file size: {file_size} bytes")
        
        # Show first few lines
        print(f"\nFirst few lines of log file:")
        with open(latest_log, 'r', encoding='utf-8') as f:
            lines = f.readlines()[:10]
            for i, line in enumerate(lines, 1):
                print(f"  {i:2}: {line.rstrip()}")
    
    if json_files:
        latest_json = max(json_files, key=os.path.getctime)
        print(f"\nLatest JSON file: {latest_json}")
        
        # Show JSON structure
        import json
        with open(latest_json, 'r', encoding='utf-8') as f:
            data = json.load(f)
            print(f"JSON structure keys: {list(data.keys())}")
            print(f"Total crawl operations: {len(data.get('crawl_operations', []))}")
            print(f"Total Gemini calls: {len(data.get('gemini_interactions', []))}")
            print(f"Total database operations: {len(data.get('database_operations', []))}")
            print(f"Total errors: {len(data.get('errors', []))}")
    
    print(f"\n✅ All tests completed successfully!")
    return True

if __name__ == "__main__":
    try:
        success = test_debug_logger()
        if success:
            print("\n🎉 Debug logging test passed!")
            sys.exit(0)
        else:
            print("\n❌ Debug logging test failed!")
            sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)