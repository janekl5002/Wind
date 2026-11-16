"""
Fuel Price API Integration for ABM Model

Fetches current fuel prices from USDA AgTransport API and calculates monthly changes.
"""
import os
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from pathlib import Path

# Try to load environment variables from .env file (optional)
# This allows colleagues to run without setting environment variables
try:
    from dotenv import load_dotenv
    # Load from project root .env file (parent directory)
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
    else:
        # Try current directory
        load_dotenv()
except ImportError:
    pass  # dotenv not installed, will use default token or environment variables

# USDA API Configuration
USDA_BASE_URL = "https://agtransport.usda.gov/api/v3/views/4v3x-mj86"
# Default token - can be overridden by environment variable or .env file
USDA_APP_TOKEN = os.getenv("USDA_APP_TOKEN", "ssRAyiMzZsGl4OFTpDYInis6F")


def fetch_fuel_prices(
    limit: int = 1000,
    order_by: str = "day DESC, month DESC, year DESC"
) -> Optional[Dict]:
    """
    Fetch fuel price data from USDA AgTransport API.
    
    Args:
        limit: Maximum number of records to fetch
        order_by: Sort order for results
        
    Returns:
        Dictionary with API response data or None if error
    """
    if not USDA_APP_TOKEN:
        print("Warning: USDA_APP_TOKEN not set. Using default fuel prices.")
        return None
    
    url = f"{USDA_BASE_URL}/query.json"
    
    params = {
        "$limit": limit,
        "$order": order_by,
        "$$app_token": USDA_APP_TOKEN
    }
    
    headers = {
        "X-App-Token": USDA_APP_TOKEN
    }
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        # API returns either a list directly or a dict with 'data' key
        if isinstance(data, list):
            return {"data": data}
        return data
    except requests.exceptions.RequestException as e:
        print(f"Error fetching fuel prices: {e}")
        return None


def get_latest_fuel_price() -> Optional[float]:
    """
    Get the latest available fuel price (VLSFO - IMO 2020 Grade 0.5%).
    
    Returns:
        Latest fuel price in USD per metric tonne, or None if unavailable
    """
    data = fetch_fuel_prices(limit=100)
    
    if not data:
        return None
    
    # Handle both list and dict responses
    if isinstance(data, list):
        records = data
    elif isinstance(data, dict) and "data" in data:
        records = data["data"]
    else:
        return None
    
    if len(records) == 0:
        return None
    
    # Sort by date (most recent first)
    # Handle various date formats
    def parse_date(record):
        year = record.get("year", 0)
        month = record.get("month", 0)
        day = record.get("day", 0)
        
        # Handle year
        try:
            if isinstance(year, str):
                year = int(year.split('-')[0]) if '-' in year else int(year)
            else:
                year = int(year)
        except (ValueError, TypeError):
            year = 0
        
        # Handle month
        if isinstance(month, int):
            month_num = month
        elif isinstance(month, str):
            month_names = ["january", "february", "march", "april", "may", "june",
                          "july", "august", "september", "october", "november", "december"]
            try:
                month_num = month_names.index(month.lower()) + 1
            except ValueError:
                try:
                    month_num = int(month)
                except ValueError:
                    month_num = 0
        else:
            month_num = 0
        
        # Handle day (might be a date string)
        try:
            if isinstance(day, str):
                # Try to parse date string like "2019-01-29T00:00:00.000"
                if 'T' in day:
                    day = day.split('T')[0].split('-')[-1]
                elif '-' in day:
                    day = day.split('-')[-1]
                day_num = int(day)
            else:
                day_num = int(day)
        except (ValueError, TypeError):
            day_num = 0
        
        return (year, month_num, day_num)
    
    records = sorted(records, key=parse_date, reverse=True)
    
    # Try to get VLSFO price (preferred) or fallback to other fuel types
    # Note: API may have typos in field names (e.g., "intermdiate" instead of "intermediate")
    for record in records:
        # Try VLSFO first (various possible field names)
        for vlsfo_field in [
            "vlsfo_fuel_oil_imo_2020_grade_0_5",
            "vlsfo",
            "vlsfo_fuel_oil"
        ]:
            vlsfo = record.get(vlsfo_field)
            if vlsfo is not None and vlsfo != "":
                try:
                    val = float(vlsfo)
                    if val > 0:
                        return val
                except (ValueError, TypeError):
                    continue
        
        # Fallback to Marine Gas Oil
        for mgo_field in ["marine_gas_oil", "mgo", "marine_gas_oil_price"]:
            mgo = record.get(mgo_field)
            if mgo is not None and mgo != "":
                try:
                    val = float(mgo)
                    if val > 0:
                        return val
                except (ValueError, TypeError):
                    continue
        
        # Fallback to IFO 380cst (check for typos)
        for ifo_field in [
            "intermediate_fuel_oil_380cst",
            "intermdiate_fuel_oil_380cst",  # Common typo in API
            "ifo_380cst",
            "intermdiate_fuel_oil_380cst"
        ]:
            ifo380 = record.get(ifo_field)
            if ifo380 is not None and ifo380 != "":
                try:
                    val = float(ifo380)
                    if val > 0:
                        return val
                except (ValueError, TypeError):
                    continue
    
    return None


def calculate_monthly_change() -> Optional[float]:
    """
    Calculate monthly fuel price change rate based on historical data.
    
    Returns:
        Monthly growth rate (as decimal, e.g., 0.005 for 0.5% per month),
        or None if insufficient data
    """
    data = fetch_fuel_prices(limit=500)
    
    if not data or "data" not in data or len(data["data"]) < 2:
        return None
    
    # Handle both list and dict responses
    if isinstance(data, list):
        raw_records = data
    elif isinstance(data, dict) and "data" in data:
        raw_records = data["data"]
    else:
        return None
    
    # Process and sort records by date
    # Handle month as either number or string
    def get_month_num(month_val):
        if isinstance(month_val, int):
            return month_val
        if isinstance(month_val, str):
            month_names = ["january", "february", "march", "april", "may", "june",
                          "july", "august", "september", "october", "november", "december"]
            try:
                return month_names.index(month_val.lower()) + 1
            except ValueError:
                try:
                    return int(month_val)
                except ValueError:
                    return 0
        return 0
    
    records = []
    for record in raw_records:
        try:
            # Parse date fields (handle various formats)
            year_val = record.get("year", 0)
            month_val = record.get("month", 0)
            day_val = record.get("day", 0)
            
            # Parse year
            try:
                if isinstance(year_val, str):
                    year = int(year_val.split('-')[0]) if '-' in year_val else int(year_val)
                else:
                    year = int(year_val)
            except (ValueError, TypeError):
                continue
            
            # Parse month
            if isinstance(month_val, int):
                month = month_val
            elif isinstance(month_val, str):
                month_names = ["january", "february", "march", "april", "may", "june",
                              "july", "august", "september", "october", "november", "december"]
                try:
                    month = month_names.index(month_val.lower()) + 1
                except ValueError:
                    try:
                        month = int(month_val)
                    except ValueError:
                        continue
            else:
                continue
            
            # Parse day
            try:
                if isinstance(day_val, str):
                    if 'T' in day_val:
                        day = int(day_val.split('T')[0].split('-')[-1])
                    elif '-' in day_val:
                        day = int(day_val.split('-')[-1])
                    else:
                        day = int(day_val)
                else:
                    day = int(day_val)
            except (ValueError, TypeError):
                day = 1  # Default to day 1 if can't parse
            
            if year == 0 or month == 0:
                continue
            
            # Try VLSFO first, then fallback to other types
            # Check for various field name variations (including typos)
            price = None
            fuel_fields = [
                "vlsfo_fuel_oil_imo_2020_grade_0_5", "vlsfo", "vlsfo_fuel_oil",
                "marine_gas_oil", "mgo",
                "intermediate_fuel_oil_380cst", "intermdiate_fuel_oil_380cst",  # Typo variant
                "intermediate_fuel_oil_180cst", "intermdiate_fuel_oil_180cst"  # Typo variant
            ]
            for fuel_type in fuel_fields:
                val = record.get(fuel_type)
                if val is not None and val != "":
                    try:
                        price_val = float(val)
                        if price_val > 0:
                            price = price_val
                            break
                    except (ValueError, TypeError):
                        continue
            
            if price is not None:
                records.append({
                    "date": datetime(year, month, day),
                    "price": price
                })
        except (ValueError, TypeError, KeyError):
            continue
    
    if len(records) < 2:
        return None
    
    # Sort by date
    records.sort(key=lambda x: x["date"])
    
    # Group by month and get average price per month
    monthly_prices = {}
    for record in records:
        month_key = (record["date"].year, record["date"].month)
        if month_key not in monthly_prices:
            monthly_prices[month_key] = []
        monthly_prices[month_key].append(record["price"])
    
    # Calculate average price per month
    monthly_avg = {
        month_key: sum(prices) / len(prices)
        for month_key, prices in monthly_prices.items()
    }
    
    if len(monthly_avg) < 2:
        return None
    
    # Calculate monthly growth rate
    months = sorted(monthly_avg.keys())
    growth_rates = []
    
    for i in range(1, len(months)):
        prev_price = monthly_avg[months[i-1]]
        curr_price = monthly_avg[months[i]]
        
        if prev_price > 0:
            growth = (curr_price - prev_price) / prev_price
            growth_rates.append(growth)
    
    if len(growth_rates) == 0:
        return None
    
    # Return average monthly growth rate
    avg_growth = sum(growth_rates) / len(growth_rates)
    return avg_growth


def get_fuel_price_data() -> Tuple[Optional[float], Optional[float]]:
    """
    Get current fuel price and monthly change rate.
    
    Returns:
        Tuple of (current_price, monthly_growth_rate)
        Returns (None, None) if API is unavailable
    """
    current_price = get_latest_fuel_price()
    monthly_growth = calculate_monthly_change()
    
    return current_price, monthly_growth


def get_fuel_price_with_fallback(
    default_price: float = 500.0,
    default_growth: float = 0.005
) -> Tuple[float, float]:
    """
    Get fuel price data with fallback to defaults if API fails.
    
    Args:
        default_price: Default fuel price if API unavailable
        default_growth: Default monthly growth rate if API unavailable
        
    Returns:
        Tuple of (fuel_price, monthly_growth_rate)
    """
    current_price, monthly_growth = get_fuel_price_data()
    
    price = current_price if current_price is not None else default_price
    growth = monthly_growth if monthly_growth is not None else default_growth
    
    if current_price is None:
        print(f"Using default fuel price: ${price:.2f}/tonne")
    else:
        print(f"Current fuel price from API: ${price:.2f}/tonne")
    
    if monthly_growth is None:
        print(f"Using default monthly growth rate: {growth*100:.2f}%")
    else:
        print(f"Calculated monthly growth rate: {growth*100:.2f}%")
    
    return price, growth
