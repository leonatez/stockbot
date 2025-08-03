#!/usr/bin/env python3
"""
Test script to verify the date comparison fix
"""
from datetime import datetime, timedelta

def test_date_logic():
    print("🧪 Testing Date Comparison Fix...")
    
    # Today is August 2nd, 2025
    today = datetime.now().date()
    print(f"Today: {today}")
    
    # Test scenarios
    test_cases = [
        {"days": 1, "post_date": datetime(2025, 8, 1, 14, 30), "expected": True},   # Aug 1st should be included for "last 1 days"
        {"days": 1, "post_date": datetime(2025, 7, 31, 23, 59), "expected": False}, # July 31st should be excluded for "last 1 days"
        {"days": 2, "post_date": datetime(2025, 7, 31, 14, 30), "expected": True},  # July 31st should be included for "last 2 days"
        {"days": 3, "post_date": datetime(2025, 7, 30, 14, 30), "expected": True},  # July 30th should be included for "last 3 days"
    ]
    
    print(f"\n📋 Testing {len(test_cases)} scenarios:")
    
    all_passed = True
    for i, case in enumerate(test_cases, 1):
        days = case["days"]
        post_date = case["post_date"]
        expected = case["expected"]
        
        # Apply the fixed logic
        target_date_ago = today - timedelta(days=days)
        actual = post_date.date() >= target_date_ago
        
        status = "✅ PASS" if actual == expected else "❌ FAIL"
        print(f"  {i}. {days} days, post from {post_date.date()}: {status}")
        print(f"     Expected: {expected}, Got: {actual}")
        print(f"     Cutoff date: {target_date_ago}")
        
        if actual != expected:
            all_passed = False
    
    print(f"\n🎯 Overall result: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")
    
    if all_passed:
        print("\n✅ The date comparison fix is working correctly!")
        print("Posts from August 1st will now be included when crawling 'the last 1 days' on August 2nd.")
    else:
        print("\n❌ The date comparison logic still has issues.")
    
    return all_passed

if __name__ == "__main__":
    test_date_logic()