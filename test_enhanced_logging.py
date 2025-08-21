#!/usr/bin/env python3
"""
Test enhanced logging to verify full prompt and response content is logged
"""

import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from holistic_analysis_logger import HolisticAnalysisLogger

def test_enhanced_logging():
    """Test that full prompt and response content is logged"""
    print("=== Testing Enhanced Logging ===\n")
    
    # Create logger instance
    logger = HolisticAnalysisLogger()
    
    # Test data
    test_prompt = """
    Bạn là chuyên gia phân tích tài chính Việt Nam. Hãy phân tích bài viết sau và trích xuất thông tin về các cổ phiếu được đề cập:

    === BÀI VIẾT ===
    VIC Group vừa công bố kết quả kinh doanh quý 2/2025 với doanh thu đạt 15,000 tỷ đồng, tăng 12% so với cùng kỳ năm trước. 
    Lợi nhuận sau thuế đạt 2,500 tỷ đồng, tăng mạnh 18% so với cùng kỳ.
    
    Trong khi đó, HPG cũng ghi nhận kết quả tích cực với doanh thu 8,500 tỷ đồng và lợi nhuận 1,200 tỷ đồng.
    
    Chỉ trả lời theo format JSON:
    {
        "mentioned_stocks": [
            {
                "stock_symbol": "SYMBOL",
                "sentiment": "positive/negative/neutral", 
                "summary": "Tóm tắt phân tích"
            }
        ],
        "post_summary": "Tóm tắt bài viết"
    }
    """
    
    test_response = {
        "mentioned_stocks": [
            {
                "stock_symbol": "VIC",
                "sentiment": "positive",
                "summary": "VIC Group có kết quả kinh doanh tích cực Q2/2025 với doanh thu tăng 12% và lợi nhuận tăng 18%"
            },
            {
                "stock_symbol": "HPG", 
                "sentiment": "positive",
                "summary": "HPG ghi nhận kết quả tích cực với doanh thu 8,500 tỷ và lợi nhuận 1,200 tỷ đồng"
            }
        ],
        "post_summary": "Báo cáo kết quả kinh doanh Q2/2025 của VIC và HPG đều cho thấy tăng trưởng tích cực"
    }
    
    # Test logging
    print("1. Testing Gemini call logging...")
    call_id = logger.log_gemini_call(
        call_type="company_analysis",
        prompt=test_prompt,
        post_urls=["https://example.com/test-post"]
    )
    print(f"✓ Logged Gemini call #{call_id}")
    
    print("\n2. Testing Gemini response logging...")
    logger.log_gemini_response(
        call_type="company_analysis", 
        response=test_response,
        identifier="https://example.com/test-post"
    )
    print("✓ Logged Gemini response")
    
    print("\n3. Finalizing logging session...")
    json_file = logger.finalize_session([])
    print(f"✓ Session finalized. JSON log: {json_file}")
    
    # Verify the logs contain full content
    print("\n4. Verifying log content...")
    
    # Check log file
    log_file = logger.log_dir / f"analysis_{logger.analysis_session['session_id']}.log"
    if log_file.exists():
        with open(log_file, 'r', encoding='utf-8') as f:
            log_content = f.read()
        
        # Check if full prompt is in log
        if "VIC Group vừa công bố kết quả" in log_content:
            print("✓ Full prompt content found in log file")
        else:
            print("✗ Full prompt content NOT found in log file")
            return False
            
        # Check if full response is in log (could be dict format or JSON format)
        if ("mentioned_stocks" in log_content and "VIC" in log_content) or ('"mentioned_stocks"' in log_content and '"stock_symbol": "VIC"' in log_content):
            print("✓ Full response content found in log file")
        else:
            print("✗ Full response content NOT found in log file")
            return False
    else:
        print("✗ Log file not found")
        return False
    
    # Check JSON file
    if json_file.exists():
        import json
        with open(json_file, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
        
        # Check if full prompt is in JSON
        gemini_calls = json_data.get('gemini_calls', [])
        if gemini_calls and 'prompt_full' in gemini_calls[0]:
            if "VIC Group vừa công bố kết quả" in gemini_calls[0]['prompt_full']:
                print("✓ Full prompt content found in JSON file")
            else:
                print("✗ Full prompt content NOT found in JSON file")
                return False
        else:
            print("✗ prompt_full field not found in JSON file")
            return False
            
        # Check if full response is in JSON (could be dict format or JSON format)
        if gemini_calls and 'response_full' in gemini_calls[0]:
            response_full = gemini_calls[0]['response_full']
            if ("'stock_symbol': 'VIC'" in response_full) or ('"stock_symbol": "VIC"' in response_full):
                print("✓ Full response content found in JSON file")
            else:
                print("✗ Full response content NOT found in JSON file")
                return False
        else:
            print("✗ response_full field not found in JSON file")
            return False
    else:
        print("✗ JSON file not found")
        return False
    
    print("\n✅ All enhanced logging tests passed!")
    print(f"\nLog files created:")
    print(f"  - Text log: {log_file}")
    print(f"  - JSON log: {json_file}")
    
    return True

if __name__ == "__main__":
    try:
        success = test_enhanced_logging()
        if success:
            print("\n🎉 Enhanced logging is working correctly!")
            sys.exit(0)
        else:
            print("\n❌ Enhanced logging tests failed!")
            sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)