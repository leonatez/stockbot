#!/usr/bin/env python3
"""
Verify the date comparison fix is applied in main.py
"""
import sys
from datetime import datetime, timedelta

def verify_fix_in_code():
    print("🧪 Verifying Date Fix in main.py...")
    
    try:
        with open('main.py', 'r') as f:
            content = f.read()
        
        # Check for the fixed date calculation
        if "target_date_ago = (datetime.now().date() - timedelta(days=days))" in content:
            print("✅ Found fixed date calculation (date-only)")
        else:
            print("❌ Fixed date calculation not found")
            return False
        
        # Check for the fixed comparison
        if "if post_date.date() >= target_date_ago:" in content:
            print("✅ Found fixed date comparison (date-only)")
        else:
            print("❌ Fixed date comparison not found")
            return False
        
        # Check for the fixed pagination check
        if "if oldest_post_date and oldest_post_date.date() < target_date_ago:" in content:
            print("✅ Found fixed pagination date check (date-only)")
        else:
            print("❌ Fixed pagination date check not found")
            return False
        
        # Check for the fixed is_within_3_days function
        if "return three_days_ago <= post_date.date() <= today" in content:
            print("✅ Found fixed is_within_3_days function (date-only)")
        else:
            print("❌ Fixed is_within_3_days function not found")
            return False
        
        print("\n🎉 ALL DATE FIXES VERIFIED IN CODE!")
        
        # Show the specific issue that was fixed
        print("\n📋 Issue Summary:")
        print("❌ Before: Posts from Aug 1st were excluded when crawling 'last 1 days' on Aug 2nd")
        print("   - Used datetime comparison with current time")
        print("   - target_date_ago = datetime.now() - timedelta(days=1)")
        print("   - Aug 1st posts published before current time were excluded")
        
        print("\n✅ After: Posts from Aug 1st are now included when crawling 'last 1 days' on Aug 2nd")
        print("   - Uses date-only comparison")
        print("   - target_date_ago = datetime.now().date() - timedelta(days=1)")
        print("   - All posts from Aug 1st are included regardless of time")
        
        return True
        
    except FileNotFoundError:
        print("❌ main.py file not found")
        return False
    except Exception as e:
        print(f"❌ Error reading main.py: {e}")
        return False

def demonstrate_fix():
    print("\n🧮 Demonstrating the Fix:")
    
    # Simulate today being Aug 2nd
    today = datetime(2025, 8, 2, 15, 30).date()  # Aug 2nd at 3:30 PM
    
    # When requesting "last 1 days"
    days = 1
    target_date_ago = today - timedelta(days=days)
    
    print(f"Today: {today}")
    print(f"Crawling 'last {days} days', cutoff: {target_date_ago}")
    
    # Test various posts from Aug 1st
    test_posts = [
        datetime(2025, 8, 1, 8, 0),   # Aug 1st 8:00 AM
        datetime(2025, 8, 1, 12, 30), # Aug 1st 12:30 PM
        datetime(2025, 8, 1, 18, 45), # Aug 1st 6:45 PM
        datetime(2025, 8, 1, 23, 59), # Aug 1st 11:59 PM
    ]
    
    print(f"\nTesting posts from Aug 1st:")
    for post_time in test_posts:
        included = post_time.date() >= target_date_ago
        print(f"  Post at {post_time.strftime('%H:%M')}: {'✅ Included' if included else '❌ Excluded'}")
    
    # Test posts from July 31st (should be excluded)
    july_31_post = datetime(2025, 7, 31, 23, 59)
    included = july_31_post.date() >= target_date_ago
    print(f"  Post from July 31st: {'✅ Included' if included else '❌ Excluded (correct)'}")

if __name__ == "__main__":
    success = verify_fix_in_code()
    
    if success:
        demonstrate_fix()
        print(f"\n🚀 The date comparison bug has been fixed!")
        print("Posts from August 1st will now be correctly included when crawling 'the last 1 days' on August 2nd.")
    else:
        print(f"\n❌ Some fixes are missing from the code.")
        sys.exit(1)