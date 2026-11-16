# Route Mapping with SeaRoute

This directory contains tools to map optimal shipping routes between ports using the searoute tool and the port database.

## Prerequisites

1. **Java Runtime Environment (JRE)** - Required to run searoute.jar
   - Install on macOS: `brew install openjdk`
   - Or download from: https://www.java.com

2. **Python 3** - Required for the mapping script
   - Should already be installed on macOS

3. **Port Database** - Located at `../databases/port_data.db`
   - Contains port coordinates and information

## Usage

### Basic Usage

Map a route between two ports:

```bash
python3 map_route.py <origin_port> <destination_port>
```

**Examples:**

```bash
# Map route from Shanghai to New York
python3 map_route.py Shanghai "New York"

# Map route from Rotterdam to Hamburg
python3 map_route.py Rotterdam Hamburg

# Use Panama canal and higher resolution
python3 map_route.py Shanghai Rotterdam -res 10 -panama 1
```

### Options

- `-res <number>`: Resolution parameter (default: 5)
  - Higher values = more detailed routes but slower computation
  - Recommended: 5-10
  
- `-panama <0|1>`: Use Panama canal (default: 0)
  - 0 = Do not use Panama canal
  - 1 = Allow Panama canal

### Output

The script will:
1. Search for ports in the database by name
2. Extract coordinates (Longitude, Latitude)
3. Create a CSV input file for searoute
4. Run searoute to generate the optimal route
5. Save results to `output/` directory:
   - `{route_name}_input.csv` - Input file for searoute
   - `{route_name}_output.json` - Route output (JSON format)

### Searching for Ports

If a port name is not found exactly, the script will suggest similar ports. You can also search for ports programmatically:

```python
from map_route import search_ports

# Search for ports matching "New"
ports = search_ports("New", limit=10)
for port in ports:
    print(f"{port['Main Port Name']} ({port['Country Code']})")
```

## How It Works

1. **Port Lookup**: The script queries `port_data.db` to find ports by name (case-insensitive partial match)
2. **Coordinate Extraction**: Extracts Longitude and Latitude from the database
3. **CSV Generation**: Creates a CSV file in the format expected by searoute:
   ```
   route name,olon,olat,dlon,dlat
   Shanghai-New-York,121.5,31.216667,-74.016667,40.7
   ```
4. **Route Calculation**: Runs `searoute.jar` with the generated CSV
5. **Output**: Saves the route as JSON (can be used for visualization)

## Troubleshooting

### Java Not Found

If you get an error about Java:
```bash
# Install Java on macOS
brew install openjdk

# Or install Oracle Java
brew install --cask oracle-jdk
```

### Port Not Found

If a port is not found:
- Try a partial name (e.g., "York" instead of "New York City")
- Use the suggested similar ports
- Check the database directly:
  ```bash
  sqlite3 ../databases/port_data.db "SELECT \"Main Port Name\" FROM ports WHERE \"Main Port Name\" LIKE '%Shanghai%'"
  ```

### Route Generation Fails

- Ensure searoute.jar exists in the searoute directory
- Check that marnet files are available (optional but recommended)
- Verify coordinates are valid (not NULL in database)

## File Structure

```
searoute/
├── map_route.py          # Main Python script for route mapping
├── searoute.jar          # SeaRoute Java application
├── test_input.csv        # Example input file
├── example_route.sh      # Example bash script
├── marnet/               # Marine network data (GPKG files)
│   ├── marnet_plus_5km.gpkg
│   ├── marnet_plus_10km.gpkg
│   └── ...
└── output/               # Generated route files (created automatically)
```

## Integration with Visualization

The output JSON files can be used to visualize routes on maps. The route data includes:
- Route coordinates (linestring/geometry)
- Distance information
- Route metadata

## References

- [SeaRoute GitHub](https://github.com/eurostat/searoute)
- Port database: `../databases/port_data.db`

