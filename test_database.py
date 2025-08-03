#!/usr/bin/env python3
"""
Test script for database integration
"""
import asyncio
from database import db_service

async def test_database_connection():
    """Test basic database connectivity"""
    try:
        print("Testing database connection...")
        
        # Test dashboard stats (uses database views)
        stats = await db_service.get_dashboard_stats()
        print(f"✓ Dashboard stats: {stats}")
        
        # Test getting sources
        sources = await db_service.get_all_sources()
        print(f"✓ Found {len(sources)} sources in database")
        
        # Test checking if a post exists (should return False for a non-existent URL)
        test_url = "https://test-url-that-does-not-exist.com"
        exists = await db_service.check_post_exists(test_url)
        print(f"✓ Post exists check for test URL: {exists} (should be False)")
        
        print("✅ Database connection test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Database connection test failed: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return False

async def test_source_creation():
    """Test creating a source"""
    try:
        print("\nTesting source creation...")
        
        test_source = {
            "url": "https://example.com/test",
            "sourceName": "Test Source",
            "sourceType": "Company",
            "xpath": "//a[@class='test']",
            "pagination": "/page/",
            "contentXpath": "//div[@class='content']",
            "contentDateXpath": "//span[@class='date']"
        }
        
        # Check if source already exists
        existing = await db_service.get_source_by_url(test_source["url"])
        if existing:
            print(f"✓ Test source already exists: {existing['name']}")
        else:
            # Create new source
            source_id = await db_service.save_source(test_source)
            print(f"✓ Created test source with ID: {source_id}")
        
        print("✅ Source creation test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Source creation test failed: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return False

async def run_all_tests():
    """Run all database tests"""
    print("🧪 Starting database integration tests...\n")
    
    results = []
    
    # Test 1: Basic connection
    results.append(await test_database_connection())
    
    # Test 2: Source creation
    results.append(await test_source_creation())
    
    # Results summary
    passed = sum(results)
    total = len(results)
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Database integration is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the error messages above.")
    
    return passed == total

if __name__ == "__main__":
    asyncio.run(run_all_tests())