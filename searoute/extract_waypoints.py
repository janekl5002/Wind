#!/usr/bin/env python3
"""
Extract route waypoints from GeoJSON routes for Open-Meteo API queries.

This module extracts intermediate waypoints from SeaRoute-generated GeoJSON files
to enable weather/wind data queries along shipping routes.
"""

import json
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import math


def haversine_distance(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """
    Calculate the great circle distance between two points on Earth.
    
    Returns distance in kilometers.
    """
    # Earth radius in kilometers
    R = 6371.0
    
    # Convert to radians
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    # Haversine formula
    a = (math.sin(delta_lat / 2) ** 2 +
         math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c


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


def extract_coordinates_from_geojson(geojson_data: Dict) -> List[Tuple[float, float]]:
    """
    Extract all coordinate pairs from a GeoJSON route.
    
    Args:
        geojson_data: GeoJSON dictionary (FeatureCollection or Feature)
        
    Returns:
        List of (longitude, latitude) tuples
    """
    coordinates = []
    
    # Handle FeatureCollection
    if geojson_data.get('type') == 'FeatureCollection':
        features = geojson_data.get('features', [])
        for feature in features:
            geometry = feature.get('geometry', {})
            coords = extract_coordinates_from_geometry(geometry)
            coordinates.extend(coords)
    # Handle single Feature
    elif geojson_data.get('type') == 'Feature':
        geometry = geojson_data.get('geometry', {})
        coords = extract_coordinates_from_geometry(geometry)
        coordinates.extend(coords)
    # Handle direct Geometry
    elif 'type' in geojson_data and 'coordinates' in geojson_data:
        coords = extract_coordinates_from_geometry(geojson_data)
        coordinates.extend(coords)
    
    return coordinates


def extract_coordinates_from_geometry(geometry: Dict) -> List[Tuple[float, float]]:
    """
    Extract coordinates from a GeoJSON geometry object.
    
    Handles LineString, MultiLineString, and other geometry types.
    """
    coordinates = []
    geom_type = geometry.get('type', '')
    coords = geometry.get('coordinates', [])
    
    if geom_type == 'LineString':
        # LineString: [[lon, lat], [lon, lat], ...]
        coordinates.extend([(lon, lat) for lon, lat in coords])
    elif geom_type == 'MultiLineString':
        # MultiLineString: [[[lon, lat], ...], [[lon, lat], ...], ...]
        for line in coords:
            coordinates.extend([(lon, lat) for lon, lat in line])
    elif geom_type == 'Point':
        # Point: [lon, lat]
        coordinates.append((coords[0], coords[1]))
    elif geom_type == 'MultiPoint':
        # MultiPoint: [[lon, lat], [lon, lat], ...]
        coordinates.extend([(lon, lat) for lon, lat in coords])
    
    return coordinates


def sample_waypoints_by_distance(
    coordinates: List[Tuple[float, float]], 
    interval_km: float = 100.0
) -> List[Dict[str, float]]:
    """
    Sample waypoints at regular distance intervals along the route.
    
    Args:
        coordinates: List of (lon, lat) tuples
        interval_km: Distance interval in kilometers (default: 100km)
        
    Returns:
        List of waypoint dictionaries with 'lon', 'lat', and 'distance_km' keys
    """
    if not coordinates:
        return []
    
    waypoints = []
    accumulated_distance = 0.0
    
    # Always include the first waypoint
    first_waypoint = {
        'lon': coordinates[0][0],
        'lat': coordinates[0][1],
        'distance_km': 0.0,
        'index': 0
    }
    # Calculate route direction for first waypoint (to next coordinate)
    if len(coordinates) > 1:
        first_waypoint['route_direction_deg'] = calculate_bearing(
            coordinates[0][1], coordinates[0][0],
            coordinates[1][1], coordinates[1][0]
        )
    waypoints.append(first_waypoint)
    
    last_waypoint_idx = 0
    
    for i in range(1, len(coordinates)):
        # Calculate distance from last waypoint to current point
        lon1, lat1 = coordinates[last_waypoint_idx]
        lon2, lat2 = coordinates[i]
        
        segment_distance = haversine_distance(lon1, lat1, lon2, lat2)
        accumulated_distance += segment_distance
        
        # If we've traveled enough distance, add a waypoint
        if accumulated_distance >= interval_km:
            waypoint = {
                'lon': lon2,
                'lat': lat2,
                'distance_km': sum(haversine_distance(
                    coordinates[j][0], coordinates[j][1],
                    coordinates[j+1][0], coordinates[j+1][1]
                ) for j in range(i)),
                'index': i
            }
            # Calculate route direction (to next coordinate if available)
            if i < len(coordinates) - 1:
                waypoint['route_direction_deg'] = calculate_bearing(
                    lat2, lon2,
                    coordinates[i+1][1], coordinates[i+1][0]
                )
            else:
                # Last waypoint, use direction from previous
                waypoint['route_direction_deg'] = calculate_bearing(
                    coordinates[i-1][1], coordinates[i-1][0],
                    lat2, lon2
                )
            waypoints.append(waypoint)
            last_waypoint_idx = i
            accumulated_distance = 0.0
    
    # Always include the last waypoint
    if waypoints[-1]['index'] != len(coordinates) - 1:
        total_distance = sum(
            haversine_distance(
                coordinates[i][0], coordinates[i][1],
                coordinates[i+1][0], coordinates[i+1][1]
            ) for i in range(len(coordinates) - 1)
        )
        
        last_waypoint = {
            'lon': coordinates[-1][0],
            'lat': coordinates[-1][1],
            'distance_km': total_distance,
            'index': len(coordinates) - 1
        }
        # Calculate route direction from previous waypoint
        if len(waypoints) > 0:
            prev_wp = waypoints[-1]
            last_waypoint['route_direction_deg'] = calculate_bearing(
                prev_wp['lat'], prev_wp['lon'],
                last_waypoint['lat'], last_waypoint['lon']
            )
        waypoints.append(last_waypoint)
    
    return waypoints


def sample_waypoints_by_count(
    coordinates: List[Tuple[float, float]], 
    max_waypoints: int = 50
) -> List[Dict[str, float]]:
    """
    Sample waypoints evenly distributed along the route by distance.
    
    Args:
        coordinates: List of (lon, lat) tuples
        max_waypoints: Number of waypoints to generate (defaults to 50)
        
    Returns:
        List of waypoint dictionaries with uniform distance spacing
    """
    if not coordinates:
        return []
    
    # If only one coordinate, return duplicates as needed
    if len(coordinates) == 1 or max_waypoints <= 1:
        lon, lat = coordinates[0]
        return [{
            'lon': lon,
            'lat': lat,
            'distance_km': 0.0,
            'index': 0,
            'route_direction_deg': None
        }]
    
    # Calculate cumulative distances along the route
    segment_distances = []
    total_distance = 0.0
    for i in range(len(coordinates) - 1):
        lon1, lat1 = coordinates[i]
        lon2, lat2 = coordinates[i + 1]
        dist = haversine_distance(lon1, lat1, lon2, lat2)
        segment_distances.append(dist)
        total_distance += dist
    
    if total_distance == 0:
        lon, lat = coordinates[0]
        return [{
            'lon': lon,
            'lat': lat,
            'distance_km': 0.0,
            'index': 0,
            'route_direction_deg': None
        }]
    
    waypoint_count = max(2, max_waypoints)
    interval = total_distance / (waypoint_count - 1)
    
    waypoints: List[Dict[str, float]] = []
    current_segment = 0
    distance_at_segment_start = 0.0
    segment_distance = segment_distances[0]
    segment_start_lon, segment_start_lat = coordinates[0]
    segment_end_lon, segment_end_lat = coordinates[1]
    
    for idx in range(waypoint_count):
        target_distance = min(interval * idx, total_distance)
        
        # Advance to the segment containing the target distance
        while (
            current_segment < len(segment_distances) - 1 and
            distance_at_segment_start + segment_distance < target_distance - 1e-6
        ):
            distance_at_segment_start += segment_distance
            current_segment += 1
            segment_start_lon, segment_start_lat = coordinates[current_segment]
            segment_end_lon, segment_end_lat = coordinates[current_segment + 1]
            segment_distance = segment_distances[current_segment]
        
        if segment_distance == 0:
            lon, lat = segment_end_lon, segment_end_lat
        else:
            remaining = max(0.0, target_distance - distance_at_segment_start)
            fraction = min(max(remaining / segment_distance, 0.0), 1.0)
            lon = segment_start_lon + (segment_end_lon - segment_start_lon) * fraction
            lat = segment_start_lat + (segment_end_lat - segment_start_lat) * fraction
        
        waypoint = {
            'lon': lon,
            'lat': lat,
            'distance_km': target_distance,
            'index': idx
        }
        waypoints.append(waypoint)
    
    # Ensure last waypoint exactly matches destination coordinates
    waypoints[-1]['lon'], waypoints[-1]['lat'] = coordinates[-1]
    waypoints[-1]['distance_km'] = total_distance
    
    # Calculate route direction bearings for waypoints
    for i in range(len(waypoints)):
        if i < len(waypoints) - 1:
            waypoints[i]['route_direction_deg'] = calculate_bearing(
                waypoints[i]['lat'], waypoints[i]['lon'],
                waypoints[i + 1]['lat'], waypoints[i + 1]['lon']
            )
        elif i > 0:
            waypoints[i]['route_direction_deg'] = calculate_bearing(
                waypoints[i - 1]['lat'], waypoints[i - 1]['lon'],
                waypoints[i]['lat'], waypoints[i]['lon']
            )
        else:
            waypoints[i]['route_direction_deg'] = None
    
    return waypoints


def ensure_coordinates_ordered_from_origin(
    coordinates: List[Tuple[float, float]],
    geojson_data: Dict
) -> List[Tuple[float, float]]:
    """
    Ensure coordinates are ordered from origin to destination.
    
    Args:
        coordinates: List of (lon, lat) tuples
        geojson_data: GeoJSON dictionary containing properties with origin/destination
        
    Returns:
        List of coordinates ordered from origin to destination
    """
    origin_lon = None
    origin_lat = None
    dest_lon = None
    dest_lat = None

    def safe_float(value: Optional[str]) -> Optional[float]:
        try:
            return float(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    # Try to get from FeatureCollection
    if geojson_data.get('type') == 'FeatureCollection':
        features = geojson_data.get('features', [])
        if features:
            props = features[0].get('properties', {})
            origin_lon = props.get('olon')
            origin_lat = props.get('olat')
            dest_lon = props.get('dlon')
            dest_lat = props.get('dlat')
    # Try to get from single Feature
    elif geojson_data.get('type') == 'Feature':
        props = geojson_data.get('properties', {})
        origin_lon = props.get('olon')
        origin_lat = props.get('olat')
        dest_lon = props.get('dlon')
        dest_lat = props.get('dlat')

    origin_lon_f = safe_float(origin_lon)
    origin_lat_f = safe_float(origin_lat)
    dest_lon_f = safe_float(dest_lon)
    dest_lat_f = safe_float(dest_lat)

    # Check if coordinates need to be reversed
    if (
        origin_lon_f is not None and origin_lat_f is not None and
        dest_lon_f is not None and dest_lat_f is not None
    ):
        first_coord = coordinates[0]
        last_coord = coordinates[-1]

        first_to_origin = haversine_distance(
            first_coord[0], first_coord[1], origin_lon_f, origin_lat_f
        )
        first_to_dest = haversine_distance(
            first_coord[0], first_coord[1], dest_lon_f, dest_lat_f
        )
        last_to_origin = haversine_distance(
            last_coord[0], last_coord[1], origin_lon_f, origin_lat_f
        )
        last_to_dest = haversine_distance(
            last_coord[0], last_coord[1], dest_lon_f, dest_lat_f
        )

        reverse_needed = False
        if first_to_dest < first_to_origin:
            reverse_needed = True
        if last_to_origin < last_to_dest:
            reverse_needed = True

        if reverse_needed:
            return list(reversed(coordinates))

    return coordinates


def extract_waypoints_from_file(
    geojson_file: Path,
    method: str = 'distance',
    interval_km: float = 100.0,
    max_waypoints: int = 50
) -> List[Dict[str, float]]:
    """
    Extract waypoints from a GeoJSON route file.
    
    Args:
        geojson_file: Path to GeoJSON file
        method: 'distance' to sample by distance interval, 'count' to sample by count
        interval_km: Distance interval in kilometers (for method='distance')
        max_waypoints: Maximum number of waypoints (for method='count')
        
    Returns:
        List of waypoint dictionaries with 'lon', 'lat', 'distance_km', and 'index'
    """
    if not geojson_file.exists():
        raise FileNotFoundError(f"GeoJSON file not found: {geojson_file}")
    
    with open(geojson_file, 'r') as f:
        geojson_data = json.load(f)
    
    # Extract all coordinates
    coordinates = extract_coordinates_from_geojson(geojson_data)
    
    if not coordinates:
        raise ValueError("No coordinates found in GeoJSON file")
    
    # Ensure coordinates are ordered from origin to destination
    coordinates = ensure_coordinates_ordered_from_origin(coordinates, geojson_data)
    
    # Sample waypoints based on method
    if method == 'distance':
        waypoints = sample_waypoints_by_distance(coordinates, interval_km)
    elif method == 'count':
        waypoints = sample_waypoints_by_count(coordinates, max_waypoints)
    else:
        raise ValueError(f"Unknown method: {method}. Use 'distance' or 'count'")
    
    return waypoints


def format_for_open_meteo(waypoints: List[Dict[str, float]]) -> Dict:
    """
    Format waypoints for Open-Meteo API query.
    
    Open-Meteo accepts multiple coordinates in the format:
    latitude1,longitude1&latitude2,longitude2&...
    
    Args:
        waypoints: List of waypoint dictionaries
        
    Returns:
        Dictionary with formatted coordinates and metadata
    """
    coordinates_str = '&'.join([
        f"{wp['lat']},{wp['lon']}" for wp in waypoints
    ])
    
    return {
        'coordinates': coordinates_str,
        'count': len(waypoints),
        'waypoints': waypoints,
        'open_meteo_url_format': (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={waypoints[0]['lat']}&longitude={waypoints[0]['lon']}"
            f"&hourly=wind_speed_10m,wind_direction_10m"
            # For multiple points, you'd need to query each separately or use a different endpoint
        )
    }


def main():
    """Command-line interface for extracting waypoints."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python extract_waypoints.py <geojson_file> [method] [options]")
        print("\nMethods:")
        print("  distance - Sample by distance interval (default: 100km)")
        print("  count    - Sample by maximum count (default: 50)")
        print("\nExamples:")
        print("  python extract_waypoints.py output/Shanghai-New-York-City_output.geojson")
        print("  python extract_waypoints.py output/Shanghai-New-York-City_output.geojson distance 50")
        print("  python extract_waypoints.py output/Shanghai-New-York-City_output.geojson count 100")
        sys.exit(1)
    
    geojson_file = Path(sys.argv[1])
    method = sys.argv[2] if len(sys.argv) > 2 else 'distance'
    
    if method == 'distance':
        interval_km = float(sys.argv[3]) if len(sys.argv) > 3 else 100.0
        waypoints = extract_waypoints_from_file(geojson_file, method='distance', interval_km=interval_km)
        print(f"\nExtracted {len(waypoints)} waypoints at {interval_km}km intervals")
    elif method == 'count':
        max_waypoints = int(sys.argv[3]) if len(sys.argv) > 3 else 50
        waypoints = extract_waypoints_from_file(geojson_file, method='count', max_waypoints=max_waypoints)
        print(f"\nExtracted {len(waypoints)} waypoints (max: {max_waypoints})")
    else:
        print(f"Unknown method: {method}")
        sys.exit(1)
    
    # Display first few waypoints
    print("\nFirst 5 waypoints:")
    for wp in waypoints[:5]:
        print(f"  {wp['lon']:.4f}, {wp['lat']:.4f} - {wp['distance_km']:.2f} km")
    
    if len(waypoints) > 5:
        print(f"  ... ({len(waypoints) - 5} more)")
        print(f"\nLast waypoint:")
        print(f"  {waypoints[-1]['lon']:.4f}, {waypoints[-1]['lat']:.4f} - {waypoints[-1]['distance_km']:.2f} km")
    
    # Format for Open-Meteo
    formatted = format_for_open_meteo(waypoints)
    print(f"\nTotal waypoints: {formatted['count']}")
    print(f"\nOpen-Meteo format (first 3 coordinates):")
    coords_list = formatted['coordinates'].split('&')[:3]
    for coord in coords_list:
        print(f"  {coord}")
    if len(coords_list) < len(waypoints):
        print(f"  ... ({len(waypoints) - len(coords_list)} more)")
    
    # Save to JSON file
    output_file = geojson_file.parent / f"{geojson_file.stem}_waypoints.json"
    with open(output_file, 'w') as f:
        json.dump({
            'source_file': str(geojson_file),
            'method': method,
            'waypoints': waypoints,
            'open_meteo_format': formatted
        }, f, indent=2)
    
    print(f"\n✓ Waypoints saved to: {output_file}")


if __name__ == "__main__":
    main()

