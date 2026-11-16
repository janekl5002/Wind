#!/usr/bin/env python3
"""
Query Open-Meteo API for weather/wind data along shipping route waypoints.

This module demonstrates how to use extracted waypoints to query Open-Meteo
for wind speed, wind direction, and other meteorological data along a route.
"""

import requests
import json
import math
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime, timedelta


def fetch_wind_data(
    latitude: float,
    longitude: float,
    timezone: str = "auto",
    past_days: int = 0,
    forecast_days: int = 7
) -> Dict:
    """
    Query Open-Meteo API for wind speed and direction.
    
    Args:
        latitude: Latitude in decimal degrees
        longitude: Longitude in decimal degrees
        timezone: Timezone (default: "auto")
        past_days: Number of past days to include (default: 0)
        forecast_days: Number of days to forecast (default: 7)
        
    Returns:
        Dictionary with wind data (speed and direction)
    """
    base_url = "https://api.open-meteo.com/v1/forecast"
    
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": "wind_speed_10m,wind_direction_10m",
        "timezone": timezone,
        "forecast_days": forecast_days,
        "past_days": past_days,
    }
    
    try:
        response = requests.get(base_url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error querying Open-Meteo for wind data: {e}")
        return None


def fetch_marine_weather(
    latitude: float,
    longitude: float,
    variables: List[str] = None,
    timezone: str = "auto",
    past_days: int = 0,
    forecast_days: int = 1
) -> Dict:
    """
    Query Open-Meteo Marine API for marine weather data.
    
    Args:
        latitude: Latitude in decimal degrees
        longitude: Longitude in decimal degrees
        variables: List of hourly marine variables to retrieve
                  Default: wind_wave_height, wind_wave_direction, 
                           ocean_current_velocity, ocean_current_direction
        timezone: Timezone (default: "auto")
        past_days: Number of past days to include (default: 0)
        forecast_days: Number of days to forecast (default: 1)
        
    Returns:
        Dictionary with marine weather data
    """
    if variables is None:
        variables = [
            "wind_wave_height",
            "wind_wave_direction",
            "ocean_current_velocity",
            "ocean_current_direction"
        ]
    
    base_url = "https://marine-api.open-meteo.com/v1/marine"
    
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": ",".join(variables),
        "timezone": timezone,
        "forecast_days": forecast_days,
        "past_days": past_days,
    }
    
    try:
        response = requests.get(base_url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error querying Open-Meteo Marine API: {e}")
        return None


def query_open_meteo_single(
    latitude: float,
    longitude: float,
    hourly_params: List[str] = None,
    forecast_days: int = 7,
    use_marine_api: bool = False,
    wind_only: bool = True
) -> Dict:
    """
    Query Open-Meteo API for a single location.
    
    Args:
        latitude: Latitude in decimal degrees
        longitude: Longitude in decimal degrees
        hourly_params: List of hourly parameters to retrieve
                      Default: wind_speed_10m, wind_direction_10m (wind_only=True)
        forecast_days: Number of days to forecast (default: 7)
        use_marine_api: If True, use Marine API; otherwise use regular forecast API
        wind_only: If True (default), only fetch wind speed and direction
        
    Returns:
        Dictionary with weather data
    """
    if wind_only:
        # Fetch only wind data (speed and direction)
        return fetch_wind_data(latitude, longitude, forecast_days=forecast_days)
    
    if use_marine_api:
        # Use Marine API
        if hourly_params is None:
            hourly_params = [
                "wind_wave_height",
                "wind_wave_direction",
                "ocean_current_velocity",
                "ocean_current_direction"
            ]
        return fetch_marine_weather(
            latitude, longitude, hourly_params, 
            forecast_days=forecast_days
        )
    else:
        # Use regular forecast API
        if hourly_params is None:
            hourly_params = ['wind_speed_10m', 'wind_direction_10m']
        
        base_url = "https://api.open-meteo.com/v1/forecast"
        
        params = {
            'latitude': latitude,
            'longitude': longitude,
            'hourly': ','.join(hourly_params),
            'forecast_days': forecast_days,
            'timezone': 'UTC'
        }
        
        try:
            response = requests.get(base_url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Error querying Open-Meteo: {e}")
            return None


def calculate_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the bearing (route direction angle) from point 1 to point 2.
    
    Args:
        lat1, lon1: Coordinates of first point (in degrees)
        lat2, lon2: Coordinates of second point (in degrees)
        
    Returns:
        Bearing in degrees (0-360), where 0° is North, 90° is East, etc.
    """
    # Convert to radians
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lon = math.radians(lon2 - lon1)
    
    # Calculate bearing using the formula
    y = math.sin(delta_lon) * math.cos(lat2_rad)
    x = (math.cos(lat1_rad) * math.sin(lat2_rad) - 
         math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(delta_lon))
    
    # Calculate bearing in radians, then convert to degrees
    bearing_rad = math.atan2(y, x)
    bearing_deg = math.degrees(bearing_rad)
    
    # Normalize to 0-360 degrees
    bearing_deg = (bearing_deg + 360) % 360
    
    return bearing_deg


def extract_first_valid_wind_sample(weather_data: Dict) -> Optional[Dict]:
    """Return the first hourly wind sample with both speed and direction."""
    if not weather_data or 'hourly' not in weather_data:
        return None
    hourly = weather_data['hourly']
    times = hourly.get('time', [])
    wind_speeds = hourly.get('wind_speed_10m', [])
    wind_directions = hourly.get('wind_direction_10m', [])

    for time_iso, speed, direction in zip(times, wind_speeds, wind_directions):
        if speed is not None and direction is not None:
            direction_to = (direction + 180) % 360
            return {
                'time': time_iso,
                'wind_speed_10m': speed,
                'wind_direction_10m': direction,
                'wind_direction_to_10m': direction_to
            }
    return None


def query_open_meteo_batch(
    waypoints: List[Dict[str, float]],
    hourly_params: List[str] = None,
    forecast_days: int = 7,
    max_points: int = 100,
    use_marine_api: bool = False,
    wind_only: bool = True
) -> List[Dict]:
    """
    Query Open-Meteo API for multiple waypoints.
    
    Note: Open-Meteo API has rate limits. For many waypoints, consider
    querying in batches or using a delay between requests.
    
    Args:
        waypoints: List of waypoint dictionaries with 'lat' and 'lon' keys
        hourly_params: List of hourly parameters to retrieve
        forecast_days: Number of days to forecast
        max_points: Maximum number of points to query (to avoid rate limits)
        
    Returns:
        List of weather data dictionaries for each waypoint
    """
    if hourly_params is None:
        hourly_params = ['wind_speed_10m', 'wind_direction_10m']
    
    results = []
    
    # Limit number of queries to avoid rate limits
    waypoints_to_query = waypoints[:max_points] if len(waypoints) > max_points else waypoints
    
    print(f"Querying Open-Meteo for {len(waypoints_to_query)} waypoints...")
    
    for i, waypoint in enumerate(waypoints_to_query):
        lat = waypoint['lat']
        lon = waypoint['lon']
        
        # Use existing route direction if available, otherwise calculate it
        if 'route_direction_deg' in waypoint and waypoint['route_direction_deg'] is not None:
            route_direction = waypoint['route_direction_deg']
        else:
            # Calculate route direction angle
            if i < len(waypoints_to_query) - 1:
                # Calculate bearing to next waypoint
                next_waypoint = waypoints_to_query[i + 1]
                route_direction = calculate_bearing(lat, lon, next_waypoint['lat'], next_waypoint['lon'])
            elif i > 0:
                # For last waypoint, use bearing from previous to current
                prev_waypoint = waypoints_to_query[i - 1]
                route_direction = calculate_bearing(prev_waypoint['lat'], prev_waypoint['lon'], lat, lon)
            else:
                # Only one waypoint, can't calculate direction
                route_direction = None
        
        # Print with route direction angle
        if route_direction is not None:
            print(f"  Querying waypoint {i+1}/{len(waypoints_to_query)}: {lat:.4f}, {lon:.4f} | Route direction: {route_direction:.1f}°")
        else:
            print(f"  Querying waypoint {i+1}/{len(waypoints_to_query)}: {lat:.4f}, {lon:.4f} | Route direction: N/A")
        
        # Store route direction in waypoint data
        waypoint_with_direction = waypoint.copy()
        if route_direction is not None:
            waypoint_with_direction['route_direction_deg'] = route_direction
        
        weather_data = query_open_meteo_single(
            lat, lon, hourly_params, forecast_days, use_marine_api, wind_only
        )
        
        if weather_data:
            wind_sample = extract_first_valid_wind_sample(weather_data)
            if wind_sample:
                print(
                    f"    Wind: {wind_sample['wind_speed_10m']:.1f} m/s @ "
                    f"{wind_sample['wind_direction_10m']:.1f}° (time {wind_sample['time']})"
                )
            else:
                print("    Wind: No wind data available in response")

            results.append({
                'waypoint': waypoint_with_direction,
                'weather': weather_data
            })
        else:
            print("    Wind: Failed to fetch weather data")
            results.append({
                'waypoint': waypoint_with_direction,
                'weather': None,
                'error': 'Failed to fetch weather data'
            })
        
        # Small delay to avoid rate limiting (adjust as needed)
        import time
        time.sleep(0.1)
    
    return results


def extract_marine_data(weather_data: Dict) -> Dict:
    """
    Extract marine weather data from Open-Meteo Marine API response.
    
    Args:
        weather_data: Open-Meteo Marine API response
        
    Returns:
        Dictionary with processed marine data
    """
    if not weather_data or 'hourly' not in weather_data:
        return None
    
    hourly = weather_data['hourly']
    times = hourly.get('time', [])
    
    # Extract marine variables
    wave_heights = hourly.get('wind_wave_height', [])
    wave_directions = hourly.get('wind_wave_direction', [])
    current_velocities = hourly.get('ocean_current_velocity', [])
    current_directions = hourly.get('ocean_current_direction', [])
    
    # Calculate statistics
    stats = {}
    
    # Filter out None values before processing
    wave_heights_clean = [h for h in wave_heights if h is not None] if wave_heights else []
    if wave_heights_clean:
        stats['avg_wave_height_m'] = round(sum(wave_heights_clean) / len(wave_heights_clean), 3)
        stats['max_wave_height_m'] = round(max(wave_heights_clean), 3)
        stats['min_wave_height_m'] = round(min(wave_heights_clean), 3)
    else:
        stats['avg_wave_height_m'] = stats['max_wave_height_m'] = stats['min_wave_height_m'] = None
    
    if wave_directions:
        import math
        sin_sum = sum(math.sin(math.radians(d)) for d in wave_directions if d is not None)
        cos_sum = sum(math.cos(math.radians(d)) for d in wave_directions if d is not None)
        stats['avg_wave_direction_deg'] = round(math.degrees(math.atan2(sin_sum, cos_sum)) % 360, 1)
    else:
        stats['avg_wave_direction_deg'] = None
    
    # Filter out None values before processing
    current_velocities_clean = [v for v in current_velocities if v is not None] if current_velocities else []
    if current_velocities_clean:
        stats['avg_current_velocity_ms'] = round(sum(current_velocities_clean) / len(current_velocities_clean), 3)
        stats['max_current_velocity_ms'] = round(max(current_velocities_clean), 3)
    else:
        stats['avg_current_velocity_ms'] = stats['max_current_velocity_ms'] = None
    
    if current_directions:
        import math
        sin_sum = sum(math.sin(math.radians(d)) for d in current_directions if d is not None)
        cos_sum = sum(math.cos(math.radians(d)) for d in current_directions if d is not None)
        stats['avg_current_direction_deg'] = round(math.degrees(math.atan2(sin_sum, cos_sum)) % 360, 1)
    else:
        stats['avg_current_direction_deg'] = None
    
    return {
        'location': {
            'latitude': weather_data.get('latitude'),
            'longitude': weather_data.get('longitude')
        },
        'statistics': stats,
        'hourly_data': {
            'times': times[:24] if len(times) > 24 else times,  # First 24 hours
            'wave_heights': wave_heights[:24] if len(wave_heights) > 24 else wave_heights,
            'wave_directions': wave_directions[:24] if len(wave_directions) > 24 else wave_directions,
            'current_velocities': current_velocities[:24] if len(current_velocities) > 24 else current_velocities,
            'current_directions': current_directions[:24] if len(current_directions) > 24 else current_directions
        },
        'forecast_period': {
            'start': times[0] if times else None,
            'end': times[-1] if times else None,
            'hours': len(times)
        }
    }


def extract_wind_data(weather_data: Dict) -> Dict:
    """
    Extract wind speed and direction from Open-Meteo response.
    
    Args:
        weather_data: Open-Meteo API response
        
    Returns:
        Dictionary with processed wind data
    """
    if not weather_data or 'hourly' not in weather_data:
        return None
    
    hourly = weather_data['hourly']
    
    # Get time, wind speed, and wind direction
    times = hourly.get('time', [])
    wind_speeds = hourly.get('wind_speed_10m', [])
    wind_directions = hourly.get('wind_direction_10m', [])
    
    # Calculate statistics
    # Filter out None values before processing
    wind_speeds_clean = [s for s in wind_speeds if s is not None] if wind_speeds else []
    if wind_speeds_clean:
        avg_wind_speed = sum(wind_speeds_clean) / len(wind_speeds_clean)
        max_wind_speed = max(wind_speeds_clean)
        min_wind_speed = min(wind_speeds_clean)
    else:
        avg_wind_speed = max_wind_speed = min_wind_speed = None
    
    wind_directions_clean = [d for d in wind_directions if d is not None] if wind_directions else []
    if wind_directions_clean:
        # Calculate average wind direction (circular mean)
        import math
        sin_sum = sum(math.sin(math.radians(d)) for d in wind_directions_clean)
        cos_sum = sum(math.cos(math.radians(d)) for d in wind_directions_clean)
        avg_direction = math.degrees(math.atan2(sin_sum, cos_sum)) % 360
    else:
        avg_direction = None
    avg_direction_to = (avg_direction + 180) % 360 if avg_direction is not None else None

    representative_sample = extract_first_valid_wind_sample(weather_data)
    representative_time = representative_sample['time'] if representative_sample else (times[0] if times else None)

    return {
        'location': {
            'latitude': weather_data.get('latitude'),
            'longitude': weather_data.get('longitude')
        },
        'statistics': {
            'avg_wind_speed_ms': round(avg_wind_speed, 2) if avg_wind_speed else None,
            'max_wind_speed_ms': round(max_wind_speed, 2) if max_wind_speed else None,
            'min_wind_speed_ms': round(min_wind_speed, 2) if min_wind_speed else None,
            'avg_wind_direction_deg': round(avg_direction, 1) if avg_direction is not None else None,
            'avg_wind_direction_from_deg': round(avg_direction, 1) if avg_direction is not None else None,
            'avg_wind_direction_to_deg': round(avg_direction_to, 1) if avg_direction_to is not None else None
        },
        'representative_time': representative_time,
        'representative_sample': representative_sample,
        'hourly_data': {
            'times': times[:24] if len(times) > 24 else times,  # First 24 hours
            'wind_speeds': wind_speeds[:24] if len(wind_speeds) > 24 else wind_speeds,
            'wind_directions': wind_directions[:24] if len(wind_directions) > 24 else wind_directions
        },
        'forecast_period': {
            'start': times[0] if times else None,
            'end': times[-1] if times else None,
            'hours': len(times)
        }
    }


def process_route_weather(
    waypoints_file: Path, 
    output_file: Optional[Path] = None,
    use_marine_api: bool = False,
    wind_only: bool = True
) -> Dict:
    """
    Process weather data for all waypoints in a route.
    
    Args:
        waypoints_file: Path to JSON file with waypoints
        output_file: Optional path to save processed weather data
        
    Returns:
        Dictionary with weather data for entire route
    """
    if not waypoints_file.exists():
        raise FileNotFoundError(f"Waypoints file not found: {waypoints_file}")
    
    with open(waypoints_file, 'r') as f:
        waypoints_data = json.load(f)
    
    waypoints = waypoints_data.get('waypoints', [])
    
    if not waypoints:
        raise ValueError("No waypoints found in file")
    
    # Query weather for waypoints
    weather_results = query_open_meteo_batch(
        waypoints, 
        max_points=50,  # Limit to 50 for demo
        use_marine_api=use_marine_api,
        wind_only=wind_only
    )
    
    # Process weather data
    processed_data = []
    for result in weather_results:
        waypoint = result['waypoint']
        weather = result.get('weather')
        
        # Ensure waypoint includes all original data (route_direction_deg, distance_km, etc.)
        waypoint_data = waypoint.copy() if isinstance(waypoint, dict) else waypoint
        
        if weather:
            # Always extract wind data (wind_only mode)
            wind_data = extract_wind_data(weather)
            processed_data.append({
                'waypoint': waypoint_data,
                'wind_data': wind_data
            })
        else:
            processed_data.append({
                'waypoint': waypoint_data,
                'wind_data': None,
                'error': result.get('error', 'Unknown error')
            })
    
    # Calculate route summary (wind data only)
    wind_data_list = [p['wind_data'] for p in processed_data if p.get('wind_data')]
    
    if wind_data_list:
        avg_speeds = [w['statistics']['avg_wind_speed_ms'] 
                     for w in wind_data_list 
                     if w['statistics'].get('avg_wind_speed_ms') is not None]
        avg_directions = [w['statistics']['avg_wind_direction_deg'] 
                         for w in wind_data_list 
                         if w['statistics'].get('avg_wind_direction_deg') is not None]
        avg_directions_from = [w['statistics'].get('avg_wind_direction_from_deg')
                               for w in wind_data_list
                               if w['statistics'].get('avg_wind_direction_from_deg') is not None]
        avg_directions_to = [w['statistics'].get('avg_wind_direction_to_deg')
                             for w in wind_data_list
                             if w['statistics'].get('avg_wind_direction_to_deg') is not None]
        
        max_wind_speeds = [w['statistics']['max_wind_speed_ms'] 
                          for w in wind_data_list 
                          if w['statistics'].get('max_wind_speed_ms') is not None]
        
        route_summary = {
            'total_waypoints': len(waypoints),
            'queried_waypoints': len(wind_data_list),
            'route_avg_wind_speed_ms': round(sum(avg_speeds) / len(avg_speeds), 2) if avg_speeds else None,
            'route_max_wind_speed_ms': round(max(max_wind_speeds), 2) if max_wind_speeds else None,
            'route_avg_wind_direction_from_deg': round(sum(avg_directions_from) / len(avg_directions_from), 1) if avg_directions_from else None,
            'route_avg_wind_direction_to_deg': round(sum(avg_directions_to) / len(avg_directions_to), 1) if avg_directions_to else None,
            'route_avg_wind_direction_deg': round(sum(avg_directions_from) / len(avg_directions_from), 1) if avg_directions_from else None,
        }
    else:
        route_summary = {
            'total_waypoints': len(waypoints),
            'queried_waypoints': 0,
            'error': 'No wind data retrieved'
        }
    
    
    result = {
        'source_file': str(waypoints_file),
        'api_type': 'wind' if wind_only else ('marine' if use_marine_api else 'forecast'),
        'route_summary': route_summary,
        'waypoints_weather': processed_data
    }
    
    # Save to file if requested
    if output_file:
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"\n✓ Weather data saved to: {output_file}")
    
    return result


def main():
    """Command-line interface for querying Open-Meteo."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python query_open_meteo.py <waypoints_file> [output_file]")
        print("\nExample:")
        print("  python query_open_meteo.py output/Shanghai-New-York-City_output_waypoints.json")
        print("  python query_open_meteo.py output/Shanghai-New-York-City_output_waypoints.json weather_data.json")
        sys.exit(1)
    
    waypoints_file = Path(sys.argv[1])
    output_file = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    
    try:
        # Use wind-only mode by default
        result = process_route_weather(waypoints_file, output_file, wind_only=True)
        
        # Print summary
        summary = result['route_summary']
        api_type = result.get('api_type', 'wind')
        print(f"\nRoute Wind Data Summary:")
        print(f"  Total waypoints: {summary['total_waypoints']}")
        print(f"  Queried waypoints: {summary['queried_waypoints']}")
        
        if summary.get('route_avg_wind_speed_ms'):
            print(f"  Average wind speed: {summary['route_avg_wind_speed_ms']} m/s")
            print(f"  Maximum wind speed: {summary['route_max_wind_speed_ms']} m/s")
        if summary.get('route_avg_wind_direction_to_deg'):
            print(f"  Average wind direction (to): {summary['route_avg_wind_direction_to_deg']}°")
        if summary.get('route_avg_wind_direction_from_deg'):
            print(f"  Average wind direction (from): {summary['route_avg_wind_direction_from_deg']}°")
        
        # Show first few waypoints
        print(f"\nFirst 5 waypoints with wind data:")
        for wp_data in result['waypoints_weather'][:5]:
            wp = wp_data['waypoint']
            wind = wp_data.get('wind_data')
            if wind:
                stats = wind['statistics']
                print(f"  {wp['lon']:.4f}, {wp['lat']:.4f} - "
                      f"Speed: {stats['avg_wind_speed_ms']} m/s, "
                      f"Direction: {stats['avg_wind_direction_deg']}°")
            else:
                print(f"  {wp['lon']:.4f}, {wp['lat']:.4f} - No data")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

