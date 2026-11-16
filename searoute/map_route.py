#!/usr/bin/env python3
"""
Map shipping routes between two harbors using searoute and port database.

This script:
1. Queries the port database for two ports by name
2. Extracts their coordinates (Longitude, Latitude)
3. Creates a CSV input file for searoute
4. Runs searoute to generate the optimal shipping route
5. Optionally saves the output
"""

import sqlite3
import subprocess
import sys
import json
import csv
from pathlib import Path
from typing import Optional, Tuple, Dict, List


# Paths
BASE_DIR = Path(__file__).parent.parent
DB_PATH = BASE_DIR / "databases" / "port_data.db"
SEAROUTE_DIR = BASE_DIR / "searoute"
SEAROUTE_JAR = SEAROUTE_DIR / "searoute.jar"
MARNET_DIR = SEAROUTE_DIR / "marnet"


def find_port_by_name(port_name: str, db_path: Path = DB_PATH) -> Optional[Dict]:
    """
    Find a port in the database by name (case-insensitive partial match).
    
    Args:
        port_name: Name or partial name of the port to search for
        db_path: Path to the SQLite database
        
    Returns:
        Dictionary with port information or None if not found
    """
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # Search in Main Port Name and Alternate Port Name
        query = """
            SELECT "World Port Index Number", "Main Port Name", 
                   "Alternate Port Name", "UN/LOCODE", "Country Code",
                   "Longitude", "Latitude"
            FROM ports
            WHERE "Main Port Name" LIKE ? 
               OR "Alternate Port Name" LIKE ?
            AND "Longitude" IS NOT NULL 
            AND "Latitude" IS NOT NULL
            LIMIT 1
        """
        
        search_pattern = f"%{port_name}%"
        cursor.execute(query, (search_pattern, search_pattern))
        row = cursor.fetchone()
        
        if row:
            return dict(row)
        else:
            return None
            
    finally:
        conn.close()


def search_ports(port_name: str, db_path: Path = DB_PATH, limit: int = 10) -> List[Dict]:
    """
    Search for ports matching a name pattern.
    
    Args:
        port_name: Name or partial name to search for
        db_path: Path to the SQLite database
        limit: Maximum number of results to return
        
    Returns:
        List of dictionaries with matching port information
    """
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        query = """
            SELECT "World Port Index Number", "Main Port Name", 
                   "Alternate Port Name", "UN/LOCODE", "Country Code",
                   "Longitude", "Latitude"
            FROM ports
            WHERE ("Main Port Name" LIKE ? OR "Alternate Port Name" LIKE ?)
            AND "Longitude" IS NOT NULL 
            AND "Latitude" IS NOT NULL
            LIMIT ?
        """
        
        search_pattern = f"%{port_name}%"
        cursor.execute(query, (search_pattern, search_pattern, limit))
        rows = cursor.fetchall()
        
        return [dict(row) for row in rows]
            
    finally:
        conn.close()


def create_searoute_input(origin_port: Dict, dest_port: Dict, 
                          output_file: Path, route_name: Optional[str] = None) -> Path:
    """
    Create a CSV input file for searoute.
    
    Args:
        origin_port: Dictionary with origin port data (must have 'Longitude' and 'Latitude')
        dest_port: Dictionary with destination port data (must have 'Longitude' and 'Latitude')
        output_file: Path to output CSV file
        route_name: Optional name for the route
        
    Returns:
        Path to the created CSV file
    """
    if route_name is None:
        origin_name = origin_port.get('Main Port Name', 'Origin')
        dest_name = dest_port.get('Main Port Name', 'Destination')
        route_name = f"{origin_name}-{dest_name}"
    
    # searoute expects: route name, olon (origin longitude), olat (origin latitude),
    #                   dlon (destination longitude), dlat (destination latitude)
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['route name', 'olon', 'olat', 'dlon', 'dlat'])
        writer.writerow([
            route_name,
            origin_port['Longitude'],
            origin_port['Latitude'],
            dest_port['Longitude'],
            dest_port['Latitude']
        ])
    
    return output_file


def run_searoute(input_file: Path, output_file: Optional[Path] = None,
                resolution: int = 5, panama: int = 0, marnet_file: Optional[str] = None) -> str:
    """
    Run searoute.jar to generate shipping routes.
    
    Args:
        input_file: Path to CSV input file
        output_file: Optional path to save output JSON
        resolution: Resolution parameter (default: 5)
        panama: Panama canal option (0=no, 1=yes)
        marnet_file: Optional marnet GPKG file path
        
    Returns:
        Output from searoute as string
    """
    if not SEAROUTE_JAR.exists():
        raise FileNotFoundError(f"searoute.jar not found at {SEAROUTE_JAR}")
    
    cmd = [
        'java', '-jar', str(SEAROUTE_JAR),
        '-i', str(input_file),
        '-res', str(resolution),
        '-panama', str(panama)
    ]
    
    if marnet_file:
        cmd.extend(['-marnet', marnet_file])
    
    if output_file:
        cmd.extend(['-o', str(output_file)])
    
    # Check if Java is available
    try:
        java_check = subprocess.run(
            ['java', '-version'],
            capture_output=True,
            text=True,
            timeout=5
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        raise RuntimeError(
            "Java not found. Please install Java to use searoute.\n"
            "Windows: Download from https://www.oracle.com/java/technologies/downloads/\n"
            "macOS: brew install openjdk\n"
            "Linux: sudo apt-get install openjdk-11-jdk"
        )
    
    try:
        result = subprocess.run(
            cmd,
            cwd=str(SEAROUTE_DIR),
            capture_output=True,
            text=True,
            check=True,
            timeout=300  # 5 minute timeout
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        error_msg = f"searoute.jar failed with exit code {e.returncode}"
        if e.stderr:
            error_msg += f"\n\nError output:\n{e.stderr}"
        if e.stdout:
            error_msg += f"\n\nStandard output:\n{e.stdout}"
        error_msg += f"\n\nCommand: {' '.join(cmd)}"
        raise RuntimeError(error_msg)
    except subprocess.TimeoutExpired:
        raise RuntimeError(
            "searoute.jar timed out after 5 minutes. "
            "This might indicate an issue with the input data or searoute configuration."
        )


def map_route(origin_name: str, dest_name: str, 
              resolution: int = 5, panama: int = 0,
              output_dir: Optional[Path] = None) -> Dict:
    """
    Main function to map a route between two ports.
    
    Args:
        origin_name: Name of origin port
        dest_name: Name of destination port
        resolution: Resolution parameter for searoute
        panama: Panama canal option (0=no, 1=yes)
        output_dir: Optional directory to save output files
        
    Returns:
        Dictionary with route information and results
    """
    if output_dir is None:
        output_dir = SEAROUTE_DIR / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Find ports
    print(f"Searching for origin port: {origin_name}")
    origin_port = find_port_by_name(origin_name)
    if not origin_port:
        print(f"Error: Could not find origin port matching '{origin_name}'")
        print("Try searching for similar ports:")
        similar = search_ports(origin_name, limit=5)
        for port in similar:
            print(f"  - {port['Main Port Name']} ({port.get('Country Code', 'N/A')})")
        return None
    
    print(f"Found origin: {origin_port['Main Port Name']} "
          f"({origin_port['Longitude']}, {origin_port['Latitude']})")
    
    print(f"\nSearching for destination port: {dest_name}")
    dest_port = find_port_by_name(dest_name)
    if not dest_port:
        print(f"Error: Could not find destination port matching '{dest_name}'")
        print("Try searching for similar ports:")
        similar = search_ports(dest_name, limit=5)
        for port in similar:
            print(f"  - {port['Main Port Name']} ({port.get('Country Code', 'N/A')})")
        return None
    
    print(f"Found destination: {dest_port['Main Port Name']} "
          f"({dest_port['Longitude']}, {dest_port['Latitude']})")
    
    # Create route name
    route_name = f"{origin_port['Main Port Name']}-{dest_port['Main Port Name']}"
    route_name = route_name.replace(' ', '-').replace(',', '')
    
    # Create input file
    input_file = output_dir / f"{route_name}_input.csv"
    print(f"\nCreating searoute input file: {input_file}")
    create_searoute_input(origin_port, dest_port, input_file, route_name)
    
    # Run searoute (output as GeoJSON)
    output_file = output_dir / f"{route_name}_output.geojson"
    print(f"\nRunning searoute...")
    try:
        output = run_searoute(input_file, output_file, resolution, panama)
        print(f"Route generated successfully!")
        
        # Check if output file was created, otherwise look for default out.geojson
        if not output_file.exists():
            default_output = SEAROUTE_DIR / "out.geojson"
            if default_output.exists():
                import shutil
                shutil.copy(default_output, output_file)
                print(f"Output copied from {default_output} to {output_file}")
        
        if output_file.exists():
            with open(output_file, 'r') as f:
                route_data = json.load(f)
        else:
            route_data = {"raw_output": output}
            print(f"Warning: Output file not found at {output_file}")
        
        return {
            "origin": origin_port,
            "destination": dest_port,
            "route_name": route_name,
            "input_file": str(input_file),
            "output_file": str(output_file),
            "route_data": route_data
        }
        
    except RuntimeError as e:
        error_msg = str(e)
        print(f"\nError: {error_msg}", file=sys.stderr)
        # Re-raise with more context for API server
        raise RuntimeError(
            f"Failed to generate route using searoute.jar.\n\n"
            f"{error_msg}\n\n"
            f"Troubleshooting:\n"
            f"1. Ensure Java is installed and in your PATH (run 'java -version' to check)\n"
            f"2. Verify searoute.jar is not corrupted\n"
            f"3. Check that the input CSV file is valid: {input_file}\n"
            f"4. See SETUP.md for more information"
        )
    except Exception as e:
        error_msg = str(e)
        print(f"\nUnexpected error: {error_msg}", file=sys.stderr)
        raise RuntimeError(
            f"Unexpected error while generating route: {error_msg}\n"
            f"See SETUP.md for troubleshooting information"
        )


def main():
    """Command-line interface."""
    if len(sys.argv) < 3:
        print("Usage: python map_route.py <origin_port_name> <destination_port_name> [options]")
        print("\nOptions:")
        print("  -res <number>     Resolution (default: 5)")
        print("  -panama <0|1>     Use Panama canal (default: 0)")
        print("\nExamples:")
        print("  python map_route.py Shanghai New York")
        print("  python map_route.py Rotterdam Hamburg -res 10 -panama 1")
        sys.exit(1)
    
    origin_name = sys.argv[1]
    dest_name = sys.argv[2]
    
    # Parse options
    resolution = 5
    panama = 0
    
    i = 3
    while i < len(sys.argv):
        if sys.argv[i] == '-res' and i + 1 < len(sys.argv):
            resolution = int(sys.argv[i + 1])
            i += 2
        elif sys.argv[i] == '-panama' and i + 1 < len(sys.argv):
            panama = int(sys.argv[i + 1])
            i += 2
        else:
            i += 1
    
    result = map_route(origin_name, dest_name, resolution, panama)
    
    if result:
        print("\n" + "="*60)
        print("Route mapping complete!")
        print("="*60)
        print(f"Route: {result['route_name']}")
        print(f"Distance: Check output file for details")
        print(f"Files saved in: {SEAROUTE_DIR / 'output'}")


if __name__ == "__main__":
    main()
