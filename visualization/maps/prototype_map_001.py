"""
Interactive map showing all ports from the World Port Index database.

This script creates an interactive map using Folium, displaying all ports
with clickable markers that show the port name when clicked.
"""

import sqlite3
import folium
from pathlib import Path

# Define file paths
BASE_DIR = Path(__file__).parent.parent.parent
DATABASE_PATH = BASE_DIR / "databases" / "port_data.db"
OUTPUT_MAP_PATH = BASE_DIR / "visualization" / "maps" / "world_ports_map.html"
TABLE_NAME = "ports"


def create_ports_map():
    """Create an interactive map show
    ing all ports from the database."""
    
    # Connect to SQLite database
    print(f"Connecting to database: {DATABASE_PATH}")
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Query all ports with location and name
    query = f"""
    SELECT "Main Port Name", Latitude, Longitude
    FROM {TABLE_NAME}
    WHERE Latitude IS NOT NULL 
    AND Longitude IS NOT NULL
    AND Latitude != ''
    AND Longitude != ''
    """
    
    cursor.execute(query)
    ports = cursor.fetchall()
    conn.close()
    
    print(f"Found {len(ports)} ports with valid coordinates")
    
    if len(ports) == 0:
        print("No ports found with valid coordinates. Cannot create map.")
        return None
    
    # Calculate center point for the map (average of all coordinates)
    latitudes = [port[1] for port in ports if port[1] is not None]
    longitudes = [port[2] for port in ports if port[2] is not None]
    
    if latitudes and longitudes:
        center_lat = sum(latitudes) / len(latitudes)
        center_lon = sum(longitudes) / len(longitudes)
    else:
        # Default to world center if no valid coordinates
        center_lat = 0
        center_lon = 0
    
    # Create the map
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=2,
        tiles='OpenStreetMap'
    )
    
    # Add markers for each port
    for port_name, lat, lon in ports:
        if lat is not None and lon is not None:
            # Clean up port name (remove extra whitespace)
            port_name_clean = str(port_name).strip() if port_name else "Unknown Port"
            
            # Create popup with port name
            popup = folium.Popup(
                f"<b>{port_name_clean}</b>",
                max_width=200
            )
            
            # Add marker to map
            folium.Marker(
                location=[lat, lon],
                popup=popup,
                tooltip=port_name_clean,
                icon=folium.Icon(color='blue', icon='info-sign')
            ).add_to(m)
    
    # Save the map
    OUTPUT_MAP_PATH.parent.mkdir(parents=True, exist_ok=True)
    m.save(str(OUTPUT_MAP_PATH))
    
    print(f"Map saved to: {OUTPUT_MAP_PATH}")
    print(f"Open the HTML file in a web browser to view the interactive map.")
    
    return OUTPUT_MAP_PATH, len(ports)


if __name__ == "__main__":
    result = create_ports_map()
    if result:
        map_path, num_ports = result
        print(f"\n✓ Successfully created interactive map with {num_ports} ports!")

