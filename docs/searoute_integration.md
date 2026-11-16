# SeaRoute Integration Guide

This guide explains how to integrate the SeaRoute API with your PostgreSQL/PostGIS database to calculate and cache shipping routes between ports.

## Overview

SeaRoute is a service that calculates optimal shipping routes over a curated global shipping-lane network using Dijkstra's algorithm. It returns GeoJSON LineString/MultiLineString features with route properties.

### Features

- **Network Resolution**: Choose from 5/10/20/50/100 km network resolutions
- **Passage Avoidance**: Option to avoid passages like Suez, Panama, Malacca, Gibraltar
- **Route Caching**: Cache calculated routes in PostgreSQL with PostGIS
- **Snap-to-Network**: Reports `dFromKM` and `dToKM` for port proximity validation

## Prerequisites

1. **PostgreSQL with PostGIS extension**
   ```sql
   CREATE EXTENSION postgis;
   ```

2. **SeaRoute Service**
   - Clone and build the searoute repository (see `searoute/README.md`)
   - Deploy the WAR file to Tomcat
   - Service should be accessible at `http://localhost:8080/searoute/route`

3. **Python Dependencies**
   ```bash
   pip install psycopg2-binary requests python-dotenv
   ```

## Setup

### 1. Database Schema

Create the PostgreSQL schema:

```bash
psql -U postgres -d wind_propulsion -f databases/postgresql_schema.sql
```

Or run the SQL file manually in your PostgreSQL client.

### 2. Migrate Port Data

If you're migrating from SQLite:

```bash
# Set environment variables in .env file
POSTGRES_DB=wind_propulsion
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# Run migration
python scripts/migrate_to_postgresql.py
```

### 3. Configure SeaRoute API

Add to your `.env` file:

```bash
SEAROUTE_API_URL=http://localhost:8080/searoute/route
SEAROUTE_RESOLUTION=10  # Network resolution in km: 5/10/20/50/100
SEAROUTE_AVOID_SUEZ=false
SEAROUTE_AVOID_PANAMA=false
SEAROUTE_AVOID_MALACCA=false
SEAROUTE_AVOID_GIBRALTAR=false
```

## Usage

### Basic Route Calculation

```python
from scripts.searoute_integration import calculate_route, DB_CONFIG
import psycopg2

conn = psycopg2.connect(**DB_CONFIG)

# Get port IDs by UN/LOCODE
cur = conn.cursor()
cur.execute("SELECT id FROM ports WHERE unlocode = %s", ("NLRTM",))  # Rotterdam
origin_id = cur.fetchone()[0]

cur.execute("SELECT id FROM ports WHERE unlocode = %s", ("CNSHA",))  # Shanghai
dest_id = cur.fetchone()[0]

# Calculate route (automatically caches)
route = calculate_route(conn, origin_id, dest_id)
print(f"Distance: {route['dist_km']:.2f} km")
print(f"Snap distances: from={route['d_from_km']:.2f}km, to={route['d_to_km']:.2f}km")

conn.close()
```

### Batch Route Calculation

```python
from scripts.searoute_integration import batch_calculate_routes, DB_CONFIG
import psycopg2

conn = psycopg2.connect(**DB_CONFIG)

# Define port pairs to calculate
port_pairs = [
    (origin_id_1, dest_id_1),
    (origin_id_2, dest_id_2),
    # ... more pairs
]

# Calculate routes with caching and rate limiting
results = batch_calculate_routes(
    conn, 
    port_pairs, 
    use_cache=True,  # Check cache first
    delay=0.1  # 0.1 second delay between API calls
)

conn.close()
```

### Query Cached Routes

```python
from scripts.searoute_integration import query_routes, DB_CONFIG
import psycopg2

conn = psycopg2.connect(**DB_CONFIG)

# Query all routes
routes = query_routes(conn)

# Query routes from specific origin
routes = query_routes(conn, origin_unlocode="NLRTM")

# Query routes to specific destination
routes = query_routes(conn, dest_unlocode="CNSHA")

for route in routes:
    origin_name, origin_code, dest_name, dest_code, dist_km, d_from, d_to, geojson, created = route
    print(f"{origin_name} ({origin_code}) -> {dest_name} ({dest_code}): {dist_km:.2f} km")

conn.close()
```

### Using SQL Directly

```sql
-- Get all routes with port names
SELECT 
    p1.main_port_name AS origin,
    p2.main_port_name AS dest,
    r.dist_km,
    r.d_from_km,
    r.d_to_km,
    ST_AsGeoJSON(r.geom) AS geojson
FROM port_routes r
JOIN ports p1 ON p1.id = r.origin_id
JOIN ports p2 ON p2.id = r.dest_id
WHERE r.dist_km < 5000  -- Routes shorter than 5000 km
ORDER BY r.dist_km;

-- Or use the view
SELECT * FROM port_routes_view 
WHERE origin_unlocode = 'NLRTM' 
ORDER BY dist_km;
```

## API Response Format

SeaRoute returns GeoJSON with the following structure:

```json
{
  "type": "Feature",
  "geometry": {
    "type": "LineString" | "MultiLineString",
    "coordinates": [[lon, lat], ...]
  },
  "properties": {
    "distKM": 12345.67,      // Total route distance in km
    "dFromKM": 2.34,         // Distance from origin to network (snap distance)
    "dToKM": 1.56            // Distance from network to destination (snap distance)
  }
}
```

### Interpreting Snap Distances

- **Small values (< 10 km)**: Port is close to shipping network - route is reliable
- **Large values (> 100 km)**: Port may be far from network or near land - route may need manual review
- **Very large values (> 500 km)**: Likely an error or port location issue

## Route Caching Strategy

The `port_routes` table caches routes with:
- **Unique constraint** on `(origin_id, dest_id, params)` to prevent duplicates
- **Params JSONB** stores resolution and avoid settings for cache key
- **Automatic caching** when routes are calculated via the integration script

### Cache Key

Routes are cached based on:
- Origin port ID
- Destination port ID  
- Route parameters (resolution, avoid passages)

Changing resolution or avoid settings will create a new cached route.

## Performance Tips

1. **Batch Processing**: Use `batch_calculate_routes()` for multiple routes
2. **Cache First**: Always use `use_cache=True` to avoid redundant API calls
3. **Rate Limiting**: Add delays between API calls to avoid overwhelming the service
4. **Spatial Indexes**: The schema includes GIST indexes on geometry for fast spatial queries
5. **Connection Pooling**: Consider using connection pooling for production use

## Troubleshooting

### SeaRoute API Not Responding

- Check if Tomcat is running: `http://localhost:8080/searoute/route`
- Verify the WAR file is deployed correctly
- Check Tomcat logs for errors

### Large Snap Distances

- Verify port coordinates are correct
- Check if port is near land or in a restricted area
- Consider using a different network resolution

### Database Connection Issues

- Verify PostgreSQL is running
- Check `.env` file has correct database credentials
- Ensure PostGIS extension is installed: `CREATE EXTENSION postgis;`

## Example: Complete Workflow

```python
import psycopg2
from scripts.searoute_integration import (
    calculate_route, query_routes, DB_CONFIG
)

# Connect to database
conn = psycopg2.connect(**DB_CONFIG)

# 1. Find ports by UN/LOCODE
cur = conn.cursor()
cur.execute("SELECT id, main_port_name, lon, lat FROM ports WHERE unlocode = 'NLRTM'")
rotterdam = cur.fetchone()

cur.execute("SELECT id, main_port_name, lon, lat FROM ports WHERE unlocode = 'CNSHA'")
shanghai = cur.fetchone()

print(f"Calculating route: {rotterdam[1]} -> {shanghai[1]}")

# 2. Calculate route (cached automatically)
route = calculate_route(conn, rotterdam[0], shanghai[0])

if route:
    print(f"Distance: {route['dist_km']:.2f} km")
    print(f"Route geometry: {route['geojson']}")

# 3. Query cached routes
print("\nAll routes from Rotterdam:")
routes = query_routes(conn, origin_unlocode="NLRTM")
for r in routes:
    print(f"  -> {r[2]} ({r[3]}): {r[4]:.2f} km")

conn.close()
```

## Next Steps

- **Visualization**: Add routes to your Folium map using the GeoJSON from cached routes
- **Analysis**: Analyze route distances, identify common shipping corridors
- **Optimization**: Use route data to optimize shipping operations




