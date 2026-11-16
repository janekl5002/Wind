#!/usr/bin/env python3
"""
Simple Flask API server for generating shipping routes.

Run this server to enable the HTML visualizer to generate routes on demand.
"""

from flask import Flask, request, jsonify, send_file, send_from_directory
import json
import sys
from pathlib import Path
from typing import List, Dict, Tuple

# Try to import flask_cors, fall back to manual CORS if not available
try:
    from flask_cors import CORS
    cors_available = True
except ImportError:
    cors_available = False
    print("Warning: flask-cors not installed. Install with: pip install flask-cors")

# Import the route mapping functions
from map_route import map_route, find_port_by_name, search_ports
from extract_waypoints import extract_waypoints_from_file, format_for_open_meteo
from query_open_meteo import (
    query_open_meteo_batch,
    extract_wind_data,
    extract_first_valid_wind_sample
)

app = Flask(__name__, static_folder='.', static_url_path='')
if cors_available:
    CORS(app)  # Enable CORS for local development
else:
    # Manual CORS headers
    @app.after_request
    def after_request(response):
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
        return response

BASE_DIR = Path(__file__).parent.parent
OUTPUT_DIR = BASE_DIR / "searoute" / "output"
DB_PATH = BASE_DIR / "databases" / "port_data.db"
SEAROUTE_JAR = BASE_DIR / "searoute" / "searoute.jar"


def check_setup():
    """Check if all required files and directories exist."""
    errors = []
    warnings = []
    
    # Check database
    if not DB_PATH.exists():
        errors.append(f"Port database not found at {DB_PATH}. Please ensure databases/port_data.db exists.")
    
    # Check searoute.jar
    if not SEAROUTE_JAR.exists():
        warnings.append(f"searoute.jar not found at {SEAROUTE_JAR}. Route generation will not work.")
    
    # Create output directory if it doesn't exist
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    return errors, warnings


# Check setup on import
_setup_errors, _setup_warnings = check_setup()
if _setup_errors:
    print("=" * 60)
    print("ERROR: Setup issues detected!")
    print("=" * 60)
    for error in _setup_errors:
        print(f"  ❌ {error}")
    print("=" * 60)
    print("\nPlease fix these issues before starting the server.\n")

if _setup_warnings:
    print("=" * 60)
    print("WARNING: Some optional components are missing:")
    print("=" * 60)
    for warning in _setup_warnings:
        print(f"  ⚠️  {warning}")
    print("=" * 60)
    print()


def _normalize_waypoints_for_wind(waypoints: List[Dict]) -> List[Dict[str, float]]:
    """Ensure we have dictionaries with lat and lon for wind queries."""
    normalized: List[Dict[str, float]] = []
    for wp in waypoints:
        if isinstance(wp, dict):
            lat = wp.get('lat')
            lon = wp.get('lon')
            if lat is None or lon is None:
                continue
            normalized_wp = {'lat': lat, 'lon': lon}
            if 'route_direction_deg' in wp:
                normalized_wp['route_direction_deg'] = wp['route_direction_deg']
            normalized.append(normalized_wp)
        elif isinstance(wp, (list, tuple)) and len(wp) >= 2:
            normalized.append({'lat': wp[1], 'lon': wp[0]})
    return normalized


def _compute_route_summary(processed_data: List[Dict]) -> Dict:
    wind_data_list = [p['wind_data'] for p in processed_data if p.get('wind_data')]
    if not wind_data_list:
        return {
            'total_waypoints': len(processed_data),
            'queried_waypoints': 0,
            'error': 'No wind data retrieved'
        }

    avg_speeds = [w['statistics'].get('avg_wind_speed_ms')
                  for w in wind_data_list
                  if w['statistics'].get('avg_wind_speed_ms') is not None]
    avg_dirs_from = [w['statistics'].get('avg_wind_direction_from_deg')
                     for w in wind_data_list
                     if w['statistics'].get('avg_wind_direction_from_deg') is not None]
    avg_dirs_to = [w['statistics'].get('avg_wind_direction_to_deg')
                   for w in wind_data_list
                   if w['statistics'].get('avg_wind_direction_to_deg') is not None]
    max_speeds = [w['statistics'].get('max_wind_speed_ms')
                  for w in wind_data_list
                  if w['statistics'].get('max_wind_speed_ms') is not None]

    return {
        'total_waypoints': len(processed_data),
        'queried_waypoints': len(wind_data_list),
        'route_avg_wind_speed_ms': round(sum(avg_speeds) / len(avg_speeds), 2) if avg_speeds else None,
        'route_max_wind_speed_ms': round(max(max_speeds), 2) if max_speeds else None,
        'route_avg_wind_direction_from_deg': round(sum(avg_dirs_from) / len(avg_dirs_from), 1) if avg_dirs_from else None,
        'route_avg_wind_direction_to_deg': round(sum(avg_dirs_to) / len(avg_dirs_to), 1) if avg_dirs_to else None,
        'route_avg_wind_direction_deg': round(sum(avg_dirs_from) / len(avg_dirs_from), 1) if avg_dirs_from else None,
    }


def fetch_wind_for_waypoints(
    route_name: str,
    waypoints: List[Dict],
    save_to_file: bool = True
) -> Tuple[List[Dict], List[Dict], Dict]:
    """Query Open-Meteo for provided waypoints and optionally persist results."""
    normalized = _normalize_waypoints_for_wind(waypoints)
    if not normalized:
        return [], [], {
            'total_waypoints': len(waypoints),
            'queried_waypoints': 0,
            'error': 'No valid waypoints for wind query'
        }

    weather_results = query_open_meteo_batch(
        normalized,
        max_points=len(normalized),
        wind_only=True
    )

    processed_data: List[Dict] = []
    wind_samples: List[Dict] = []

    for idx, result in enumerate(weather_results):
        original_wp = waypoints[idx] if idx < len(waypoints) else result.get('waypoint', {})
        waypoint_copy = original_wp.copy() if isinstance(original_wp, dict) else {
            'lat': original_wp[1],
            'lon': original_wp[0]
        }

        weather = result.get('weather')
        if weather:
            wind_data = extract_wind_data(weather)
            sample = extract_first_valid_wind_sample(weather)

            route_dir = waypoint_copy.get('route_direction_deg')
            if wind_data and route_dir is not None:
                stats = wind_data.setdefault('statistics', {})
                wind_to = stats.get('avg_wind_direction_to_deg')
                if wind_to is None:
                    wind_from = stats.get('avg_wind_direction_from_deg')
                    if wind_from is not None:
                        wind_to = (wind_from + 180) % 360
                if wind_to is not None:
                    relative = ((wind_to - route_dir + 540) % 360) - 180
                    stats['wind_relative_to_route_deg'] = round(relative, 1)

            if sample and route_dir is not None:
                sample_to = sample.get('wind_direction_to_10m')
                if sample_to is None and sample.get('wind_direction_10m') is not None:
                    sample_to = (sample['wind_direction_10m'] + 180) % 360
                if sample_to is not None:
                    sample_relative = ((sample_to - route_dir + 540) % 360) - 180
                    sample['wind_relative_to_route_deg'] = round(sample_relative, 1)
        else:
            wind_data = None
            sample = None

        entry = {'waypoint': waypoint_copy, 'wind_data': wind_data}
        if not weather:
            entry['error'] = result.get('error', 'Failed to fetch weather data')

        processed_data.append(entry)
        wind_samples.append(sample)

    route_summary = _compute_route_summary(processed_data)

    if save_to_file and route_name:
        payload = {
            'route_name': route_name,
            'api_type': 'wind',
            'route_summary': route_summary,
            'waypoints_weather': processed_data
        }
        weather_file = OUTPUT_DIR / f"{route_name}_weather.json"
        with open(weather_file, 'w') as f:
            json.dump(payload, f, indent=2)

    return processed_data, wind_samples, route_summary


@app.route('/api/search-ports', methods=['GET'])
def search_ports_api():
    """Search for ports by name."""
    if not DB_PATH.exists():
        return jsonify({'error': 'Port database not found. Please ensure databases/port_data.db exists.'}), 500
    
    query = request.args.get('q', '')
    limit = int(request.args.get('limit', 10))
    
    if not query:
        return jsonify([])
    
    try:
        ports = search_ports(query, limit=limit)
    except Exception as e:
        return jsonify({'error': f'Error searching ports: {str(e)}'}), 500
    # Convert to JSON-serializable format
    result = []
    for port in ports:
        result.append({
            'name': port.get('Main Port Name', ''),
            'alternate': port.get('Alternate Port Name', ''),
            'country': port.get('Country Code', ''),
            'lon': port.get('Longitude', 0),
            'lat': port.get('Latitude', 0)
        })
    
    return jsonify(result)


@app.route('/api/generate-route', methods=['POST'])
def generate_route():
    """Generate a route between two ports."""
    if not DB_PATH.exists():
        return jsonify({'error': 'Port database not found. Please ensure databases/port_data.db exists.'}), 500
    
    if not SEAROUTE_JAR.exists():
        return jsonify({'error': 'searoute.jar not found. Route generation requires searoute.jar in the searoute directory.'}), 500
    
    data = request.json
    origin = data.get('origin', '')
    destination = data.get('destination', '')
    resolution = int(data.get('resolution', 5))
    panama = int(data.get('panama', 0))
    
    if not origin or not destination:
        return jsonify({'error': 'Origin and destination are required'}), 400
    
    try:
        # Ensure output directory exists
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        
        # Generate the route
        result = map_route(origin, destination, resolution, panama)
        
        if result is None:
            return jsonify({'error': 'Could not generate route. Check port names.'}), 400
        
        # Read the generated GeoJSON file
        output_file = Path(result['output_file'])
        if not output_file.exists():
            # Try alternative location
            default_output = BASE_DIR / "searoute" / "out.geojson"
            if default_output.exists():
                output_file = default_output
            else:
                return jsonify({'error': 'Route generated but output file not found'}), 500
        
        with open(output_file, 'r') as f:
            geojson_data = json.load(f)
        
        # Extract preview waypoints (uniformly spaced)
        waypoints_preview = extract_waypoints_from_file(
            output_file,
            method='count',
            max_waypoints=50
        )

        # Query wind data for preview waypoints and persist results
        try:
            processed_weather, wind_samples, route_summary = fetch_wind_for_waypoints(
                result['route_name'],
                waypoints_preview,
                save_to_file=True
            )
        except Exception as wind_error:
            print(f"Warning: Failed to fetch wind data for terminal output: {wind_error}")
            processed_weather = []
            wind_samples = []
            route_summary = None

        # Log waypoints (with wind data) in terminal
        def fmt(value, precision=4):
            if value is None:
                return "N/A"
            return f"{value:.{precision}f}"

        def fmt_dir(value):
            if value is None:
                return "N/A"
            return f"{value:.1f}°"

        def fmt_rel(value):
            if value is None:
                return "   N/A"
            return f"{value:+6.1f}°"

        total_wp = len(waypoints_preview)
        print("\n" + "=" * 100)
        print(f"Route generated: {result['route_name']} | Waypoints ({total_wp})")
        if route_summary:
            avg_w = route_summary.get('route_avg_wind_speed_ms')
            avg_dir_to = route_summary.get('route_avg_wind_direction_to_deg')
            print(
                f"Route wind summary -> Avg: {fmt(avg_w, 2)} m/s, "
                f"Avg Dir (to): {fmt_dir(avg_dir_to)}"
            )
        print("Index |   Latitude |  Longitude | Route Dir | Distance km | Wind Avg | Wind Dir→ | Wind Dir← | Wind Max | Wind Min | Wind Δ | Wind Time")
        print("-" * 135)

        for idx, wp in enumerate(waypoints_preview, 1):
            lat = wp.get('lat')
            lon = wp.get('lon')
            route_dir = wp.get('route_direction_deg')
            distance_km = wp.get('distance_km')

            wind_entry = processed_weather[idx - 1]['wind_data'] if idx - 1 < len(processed_weather) else None
            stats = wind_entry.get('statistics') if wind_entry else {}
            avg_wind = stats.get('avg_wind_speed_ms') if stats else None
            avg_dir_to = stats.get('avg_wind_direction_to_deg') if stats else None
            avg_dir_from = stats.get('avg_wind_direction_from_deg') if stats else None
            max_wind = stats.get('max_wind_speed_ms') if stats else None
            min_wind = stats.get('min_wind_speed_ms') if stats else None
            wind_time = wind_entry.get('representative_time') if wind_entry else None
            rel_wind = stats.get('wind_relative_to_route_deg') if stats else None

            print(
                f"{idx:02d}/{total_wp:02d} | {fmt(lat):>9} | {fmt(lon):>10} | {fmt_dir(route_dir):>9} | "
                f"{fmt(distance_km, 1):>11} | {fmt(avg_wind, 2):>8} | {fmt_dir(avg_dir_to):>9} | {fmt_dir(avg_dir_from):>9} | "
                f"{fmt(max_wind, 2):>8} | {fmt(min_wind, 2):>8} | {fmt_rel(rel_wind):>8} | {wind_time or 'N/A'}"
            )

            sample = wind_samples[idx - 1] if idx - 1 < len(wind_samples) else None
            if sample and sample.get('time'):
                dir_to = sample.get('wind_direction_to_10m')
                rel_sample = sample.get('wind_relative_to_route_deg')
                print(
                    f"      Sample -> {sample['time']}: {sample['wind_speed_10m']:.1f} m/s @ "
                    f"{sample['wind_direction_10m']:.1f}° from ({dir_to:.1f}° to) | Δ {fmt_rel(rel_sample).strip()}"
                )
            elif not wind_entry:
                print("      Wind data unavailable")

        print("=" * 100 + "\n")
        
        return jsonify({
            'success': True,
            'geojson': geojson_data,
            'route_name': result['route_name'],
            'origin': result['origin']['Main Port Name'],
            'destination': result['destination']['Main Port Name']
        })
        
    except RuntimeError as e:
        # RuntimeError from map_route contains detailed error messages
        return jsonify({'error': str(e)}), 500
    except Exception as e:
        # Catch any other unexpected errors
        import traceback
        error_details = traceback.format_exc()
        print(f"Unexpected error in generate_route: {error_details}", file=sys.stderr)
        return jsonify({
            'error': f'Unexpected error: {str(e)}\n\nSee server logs for details.'
        }), 500


@app.route('/api/extract-waypoints', methods=['POST'])
def extract_waypoints_api():
    """Extract waypoints from a GeoJSON route."""
    data = request.json or {}
    
    # Get route_name or geojson data
    route_name = data.get('route_name', '')
    geojson = data.get('geojson')
    
    # Method: 'distance' or 'count'
    method = data.get('method', 'distance')
    interval_km = float(data.get('interval_km', 100.0))
    max_waypoints = int(data.get('max_waypoints', 50))
    
    try:
        if route_name:
            # Load from file
            geojson_file = OUTPUT_DIR / f"{route_name}_output.geojson"
            if not geojson_file.exists():
                return jsonify({'error': f'Route file not found: {route_name}'}), 404
            
            waypoints = extract_waypoints_from_file(
                geojson_file,
                method=method,
                interval_km=interval_km,
                max_waypoints=max_waypoints
            )
        elif geojson:
            # Extract from provided GeoJSON
            from extract_waypoints import (
                extract_coordinates_from_geojson, 
                sample_waypoints_by_distance, 
                sample_waypoints_by_count,
                ensure_coordinates_ordered_from_origin
            )
            
            coordinates = extract_coordinates_from_geojson(geojson)
            if not coordinates:
                return jsonify({'error': 'No coordinates found in GeoJSON'}), 400
            
            # Ensure coordinates are ordered from origin to destination
            coordinates = ensure_coordinates_ordered_from_origin(coordinates, geojson)
            
            if method == 'distance':
                waypoints = sample_waypoints_by_distance(coordinates, interval_km)
            else:
                waypoints = sample_waypoints_by_count(coordinates, max_waypoints)
        else:
            return jsonify({'error': 'Either route_name or geojson must be provided'}), 400
        
        # Format for Open-Meteo
        formatted = format_for_open_meteo(waypoints)
        
        return jsonify({
            'success': True,
            'waypoints': waypoints,
            'count': len(waypoints),
            'method': method,
            'open_meteo_format': formatted
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/query-wind-data', methods=['POST'])
def query_wind_data_api():
    """Query wind data for waypoints."""
    data = request.json or {}
    route_name = data.get('route_name', '')
    waypoints = data.get('waypoints', [])
    
    if not waypoints:
        return jsonify({'error': 'Waypoints are required'}), 400
    
    try:
        processed_data, _, route_summary = fetch_wind_for_waypoints(
            route_name,
            waypoints,
            save_to_file=True
        )

        result = {
            'route_name': route_name,
            'api_type': 'wind',
            'route_summary': route_summary,
            'waypoints_weather': processed_data
        }

        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/health', methods=['GET', 'OPTIONS'])
def health():
    """Health check endpoint."""
    if request.method == 'OPTIONS':
        # Handle CORS preflight
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Methods', 'GET, OPTIONS')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        return response
    return jsonify({'status': 'ok', 'server': 'running'})


@app.route('/')
@app.route('/route_visualizer.html')
def index():
    """Serve the route visualizer HTML."""
    return send_from_directory('.', 'route_visualizer.html')


if __name__ == '__main__':
    print("=" * 60)
    print("Starting Route API Server...")
    print("=" * 60)
    
    # Check setup
    errors, warnings = check_setup()
    
    if errors:
        print("\n❌ Cannot start server due to setup errors:")
        for error in errors:
            print(f"   {error}")
        print("\nPlease fix these issues and try again.")
        sys.exit(1)
    
    if warnings:
        print("\n⚠️  Warnings:")
        for warning in warnings:
            print(f"   {warning}")
        print()
    
    print("✓ Setup check passed")
    print(f"\n🌐 Access the visualizer at: http://localhost:5000/route_visualizer.html")
    print("   Or simply: http://localhost:5000/")
    print("\n⚠️  IMPORTANT: Open the visualizer through the server URL above,")
    print("   NOT by opening the HTML file directly!")
    print("\nAPI endpoints:")
    print("  GET  /api/health - Health check")
    print("  GET  /api/search-ports?q=<query> - Search ports")
    print("  POST /api/generate-route - Generate route")
    print("  POST /api/extract-waypoints - Extract waypoints")
    print("  POST /api/query-wind-data - Query wind data")
    print("\nPress Ctrl+C to stop the server")
    print("=" * 60)
    print()
    
    # Run on port 5000
    # Using 0.0.0.0 to allow connections from other interfaces if needed
    app.run(host='0.0.0.0', port=5000, debug=True)

