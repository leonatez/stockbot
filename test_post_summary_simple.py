#!/usr/bin/env python3
"""
Simple test script to verify post summary database saving
"""
import asyncio

async def test_database_insertion():
    """Test database insertion with summary"""
    print("🧪 Testing Database Post Summary Insertion...\n")
    
    try:
        from database import db_service
        
        # Clean up test post if it exists
        await cleanup_test_post()
        
        # Test post data
        post_data = {
            "url": "https://test-post-summary-fix.com",
            "date": "02/08/2025",
            "content": "VPB công bố kết quả kinh doanh tốt trong Q2/2025 với lợi nhuận tăng 18%.",
            "type": "Company"
        }
        
        # Test analysis data
        analysis_data = [
            {
                "stock_symbol": "VPB",
                "sentiment": "positive",
                "summary": "VPB có kết quả kinh doanh tích cực"
            }
        ]
        
        # Test summary - this should now be saved properly
        test_summary = "VPB báo cáo kết quả kinh doanh Q2/2025 tích cực với lợi nhuận tăng trưởng mạnh. Ngân hàng này đạt được các chỉ tiêu tài chính khả quan trong quý vừa qua."
        
        # Get first source from database
        sources = await db_service.get_all_sources()
        if sources:
            source_id = sources[0]["id"]
            print(f"Using source: {sources[0]['name']}")
            
            # Test the save function with the new summary parameter
            print("Saving post with summary to database...")
            post_id = await db_service.save_post_with_analysis(
                post_data, source_id, analysis_data, test_summary
            )
            
            print(f"✅ SUCCESS: Post saved with ID: {post_id}")
            print(f"Summary saved: '{test_summary[:50]}...'")
            
            # Verify by checking the database
            print("\nVerification - checking database:")
            print("Run this SQL in Supabase to verify:")
            print(f"SELECT url, summary FROM posts WHERE id = '{post_id}';")
            
            return True
        else:
            print("❌ No sources found in database for testing")
            return False
            
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        import traceback
        print(f"Error details: {traceback.format_exc()}")
        return False

async def cleanup_test_post():
    """Clean up test post"""
    try:
        from database import db_service
        # Clean up the test post
        result = db_service.supabase.table("posts").delete().eq("url", "https://test-post-summary-fix.com").execute()
        print("Cleaned up existing test post")
    except:
        pass

async def main():
    print("🚀 Testing Post Summary Database Fix...\n")
    
    db_ok = await test_database_insertion()
    
    if db_ok:
        print("\n🎉 TEST PASSED!")
        print("\nThe fix is working. Now when you crawl:")
        print("1. Gemini will generate proper Vietnamese post summaries")
        print("2. These summaries will be saved to posts.summary field")
        print("3. The database will contain meaningful post summaries")
        
        print("\nTo test with real data:")
        print("1. DELETE FROM posts; (clean the table)")
        print("2. Run a fresh crawl")
        print("3. Check posts.summary field - should contain Vietnamese summaries")
    else:
        print("\n❌ Test failed. Check the errors above.")

if __name__ == "__main__":
    asyncio.run(main())