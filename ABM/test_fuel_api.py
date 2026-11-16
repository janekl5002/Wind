

#!/usr/bin/env python3
"""
Test script to verify fuel price API integration
"""
import sys
import os
from pathlib import Path

# Add parent directory to path to load .env
sys.path.insert(0, str(Path(__file__).parent.parent))

from fuel_price_api import (
    get_latest_fuel_price,
    calculate_monthly_change,
    get_fuel_price_with_fallback
)

print("=" * 60)
print("Testing Fuel Price API Integration")
print("=" * 60)
print()

# Check if token is set
usda_token = os.getenv("USDA_APP_TOKEN", "")
if not usda_token:
    print("⚠️  Warning: USDA_APP_TOKEN not found in environment")
    print("   The API will use defaults if unavailable")
    print()
else:
    print(f"✓ USDA_APP_TOKEN found: {usda_token[:10]}...")
    print()

# Test 1: Get latest fuel price
print("Test 1: Fetching latest fuel price...")
try:
    latest_price = get_latest_fuel_price()
    if latest_price:
        print(f"✓ Latest fuel price: ${latest_price:.2f}/tonne")
    else:
        print("✗ Could not fetch latest fuel price (using defaults)")
except Exception as e:
    print(f"✗ Error fetching latest price: {e}")
print()

# Test 2: Calculate monthly change
print("Test 2: Calculating monthly change rate...")
try:
    monthly_change = calculate_monthly_change()
    if monthly_change:
        print(f"✓ Monthly growth rate: {monthly_change*100:.2f}%")
    else:
        print("✗ Could not calculate monthly change (using defaults)")
except Exception as e:
    print(f"✗ Error calculating monthly change: {e}")
print()

# Test 3: Get both with fallback
print("Test 3: Getting fuel price data with fallback...")
try:
    price, growth = get_fuel_price_with_fallback(
        default_price=500.0,
        default_growth=0.005
    )
    print(f"✓ Fuel price: ${price:.2f}/tonne")
    print(f"✓ Monthly growth: {growth*100:.2f}%")
except Exception as e:
    print(f"✗ Error: {e}")
print()

print("=" * 60)
print("API Test Complete")
print("=" * 60)
