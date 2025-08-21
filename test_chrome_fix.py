#!/usr/bin/env python3
"""
Test script for Chrome driver fixes
"""

import sys
import os
import time

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from chrome_driver_fix import ChromeDriverManager, get_chrome_driver, return_chrome_driver

def test_chrome_driver_detection():
    """Test Chrome version detection"""
    print("=== Testing Chrome Driver Detection ===\n")
    
    manager = ChromeDriverManager()
    
    # Test 1: Detect Chrome version
    print("1. Testing Chrome version detection...")
    version = manager.detect_chrome_version()
    if version:
        print(f"✓ Detected Chrome version: {version}")
        print(f"✓ Chrome binary path: {manager.chrome_binary_path}")
    else:
        print("✗ Could not detect Chrome version")
        return False
    
    return True

def test_chrome_driver_creation():
    """Test Chrome driver creation"""
    print("\n=== Testing Chrome Driver Creation ===\n")
    
    # Test 2: Create Chrome driver
    print("2. Testing Chrome driver creation...")
    driver = get_chrome_driver()
    
    if driver:
        print("✓ Chrome driver created successfully")
        
        # Test 3: Basic functionality
        print("3. Testing basic driver functionality...")
        try:
            driver.get("data:text/html,<html><body><h1>Test Page</h1></body></html>")
            title = driver.title
            print(f"✓ Driver can load pages. Page title: '{title}'")
            
            # Test 4: JavaScript execution
            print("4. Testing JavaScript execution...")
            result = driver.execute_script("return document.title;")
            print(f"✓ JavaScript execution works. Result: '{result}'")
            
            # Test 5: Element finding
            print("5. Testing element finding...")
            h1_element = driver.find_element("tag name", "h1")
            h1_text = h1_element.text
            print(f"✓ Element finding works. H1 text: '{h1_text}'")
            
        except Exception as e:
            print(f"✗ Driver functionality test failed: {e}")
            return False
        
        # Test 6: Return driver to pool
        print("6. Testing driver return to pool...")
        return_chrome_driver(driver)
        print("✓ Driver returned to pool successfully")
        
        return True
    else:
        print("✗ Failed to create Chrome driver")
        return False

def test_multiple_drivers():
    """Test multiple driver creation and management"""
    print("\n=== Testing Multiple Driver Management ===\n")
    
    drivers = []
    
    # Test 7: Create multiple drivers
    print("7. Testing multiple driver creation...")
    for i in range(3):
        print(f"   Creating driver {i+1}/3...")
        driver = get_chrome_driver()
        if driver:
            drivers.append(driver)
            print(f"   ✓ Driver {i+1} created successfully")
        else:
            print(f"   ✗ Failed to create driver {i+1}")
            break
    
    if len(drivers) == 3:
        print("✓ All 3 drivers created successfully")
    else:
        print(f"✗ Only {len(drivers)}/3 drivers created")
    
    # Test 8: Test each driver
    print("8. Testing each driver independently...")
    for i, driver in enumerate(drivers):
        try:
            driver.get(f"data:text/html,<html><body><h1>Driver {i+1}</h1></body></html>")
            title = driver.execute_script("return document.querySelector('h1').textContent;")
            print(f"   ✓ Driver {i+1} works. Page content: '{title}'")
        except Exception as e:
            print(f"   ✗ Driver {i+1} failed: {e}")
    
    # Test 9: Return all drivers
    print("9. Returning all drivers to pool...")
    for i, driver in enumerate(drivers):
        return_chrome_driver(driver)
        print(f"   ✓ Driver {i+1} returned to pool")
    
    print("✓ All drivers returned successfully")
    return True

def test_error_handling():
    """Test error handling and recovery"""
    print("\n=== Testing Error Handling ===\n")
    
    # Test 10: Handle driver crashes
    print("10. Testing driver crash recovery...")
    driver = get_chrome_driver()
    
    if driver:
        try:
            # Force close the driver to simulate a crash
            driver.quit()
            print("   ✓ Simulated driver crash")
            
            # Try to use the crashed driver (should fail gracefully)
            try:
                driver.get("http://example.com")
                print("   ✗ Crashed driver should not work")
                return False
            except:
                print("   ✓ Crashed driver properly detected as unusable")
            
            # Get a new driver (should work)
            new_driver = get_chrome_driver()
            if new_driver:
                print("   ✓ New driver created after crash")
                new_driver.get("data:text/html,<html><body>Recovery test</body></html>")
                print("   ✓ New driver works properly")
                return_chrome_driver(new_driver)
                return True
            else:
                print("   ✗ Failed to create new driver after crash")
                return False
                
        except Exception as e:
            print(f"   ✗ Error handling test failed: {e}")
            return False
    else:
        print("   ✗ Could not create initial driver for crash test")
        return False

def main():
    """Run all tests"""
    print("🚀 Starting Chrome Driver Fix Tests\n")
    
    test_results = []
    
    # Run tests
    test_results.append(("Chrome Detection", test_chrome_driver_detection()))
    test_results.append(("Driver Creation", test_chrome_driver_creation()))
    test_results.append(("Multiple Drivers", test_multiple_drivers()))
    test_results.append(("Error Handling", test_error_handling()))
    
    # Summary
    print("\n" + "="*50)
    print("🏁 TEST RESULTS SUMMARY")
    print("="*50)
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:20} {status}")
        if result:
            passed += 1
    
    print("-" * 50)
    print(f"Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Chrome driver fixes are working correctly.")
        return True
    else:
        print(f"\n💥 {total - passed} test(s) failed. Chrome driver needs further investigation.")
        return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⏹️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n💥 Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)