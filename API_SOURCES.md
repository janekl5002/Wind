# API Sources Documentation

This document lists all external APIs and data sources used in the Route Visualization and Wind Data Analysis project.

---

## External APIs

### 1. Open-Meteo Weather API

**Purpose**: Fetch wind speed and direction data for route waypoints

**Base URL**: `https://api.open-meteo.com/v1/forecast`

**Endpoint Used**: `/v1/forecast`

**Parameters**:
- `latitude` (float): Latitude in decimal degrees
- `longitude` (float): Longitude in decimal degrees
- `hourly` (string): Comma-separated list of variables
  - `wind_speed_10m`: Wind speed at 10 meters above ground (m/s)
  - `wind_direction_10m`: Wind direction at 10 meters above ground (degrees)
- `timezone` (string): Timezone (default: "auto")
- `forecast_days` (int): Number of forecast days (default: 7)
- `past_days` (int): Number of past days to include (default: 0)

**Example Request**:
```
GET https://api.open-meteo.com/v1/forecast?latitude=40.7&longitude=-74.0&hourly=wind_speed_10m,wind_direction_10m&forecast_days=7
```

**Usage**:
- Location: `searoute/query_open_meteo.py`
- Function: `fetch_wind_data()`
- Purpose: Primary API for wind data queries

**Rate Limits**: 
- Free tier: ~10,000 requests/day
- No API key required
- Rate limiting: ~10 requests/second recommended

**Documentation**: https://open-meteo.com/en/docs

---

### 2. Open-Meteo Marine API

**Purpose**: Fetch marine-specific weather data (wave height, ocean currents)

**Base URL**: `https://marine-api.open-meteo.com/v1/marine`

**Endpoint Used**: `/v1/marine`

**Parameters**:
- `latitude` (float): Latitude in decimal degrees
- `longitude` (float): Longitude in decimal degrees
- `hourly` (string): Comma-separated list of marine variables
  - `wind_wave_height`: Wind wave height (meters)
  - `wind_wave_direction`: Wind wave direction (degrees)
  - `ocean_current_velocity`: Ocean current velocity (m/s)
  - `ocean_current_direction`: Ocean current direction (degrees)
- `timezone` (string): Timezone (default: "auto")
- `forecast_days` (int): Number of forecast days (default: 1)
- `past_days` (int): Number of past days to include (default: 0)

**Example Request**:
```
GET https://marine-api.open-meteo.com/v1/marine?latitude=40.7&longitude=-74.0&hourly=wind_wave_height,wind_wave_direction&forecast_days=1
```

**Usage**:
- Location: `searoute/query_open_meteo.py`
- Function: `fetch_marine_weather()`
- Purpose: Alternative API for marine-specific data (currently not used in wind-only mode)

**Rate Limits**: Same as Open-Meteo Weather API

**Documentation**: https://open-meteo.com/en/docs/marine-api

---

## Map Tile Services

### 3. OpenStreetMap Tiles

**Purpose**: Base map tiles for route visualization

**Base URL**: `https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png`

**Parameters**:
- `{s}`: Subdomain (a, b, c)
- `{z}`: Zoom level
- `{x}`: Tile X coordinate
- `{y}`: Tile Y coordinate

**Usage**:
- Location: `searoute/route_visualizer.html`
- Library: Leaflet.js
- Purpose: Display interactive map background

**Attribution**: © OpenStreetMap contributors

**License**: Open Database License (ODbL)

**Documentation**: https://wiki.openstreetmap.org/wiki/Tiles

---

## CDN Libraries

### 4. Leaflet.js (via jsDelivr CDN)

**Purpose**: Interactive mapping library

**CSS**: `https://cdn.jsdelivr.net/npm/leaflet@1.9.3/dist/leaflet.css`

**JavaScript**: `https://cdn.jsdelivr.net/npm/leaflet@1.9.3/dist/leaflet.js`

**Usage**:
- Location: `searoute/route_visualizer.html`
- Purpose: Interactive map rendering, markers, popups, route visualization

**License**: BSD 2-Clause License

**Documentation**: https://leafletjs.com/

---

### 5. Leaflet Color Markers (via GitHub)

**Purpose**: Colored marker icons for origin/destination ports

**URL**: `https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-{color}.png`

**Colors Used**:
- Green: Origin ports
- Red: Destination ports

**Usage**:
- Location: `searoute/route_visualizer.html`
- Purpose: Visual markers for route start/end points

**License**: MIT License

**Repository**: https://github.com/pointhi/leaflet-color-markers

---

### 6. Leaflet Marker Shadow (via cdnjs)

**Purpose**: Shadow images for map markers

**URL**: `https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.3/images/marker-shadow.png`

**Usage**:
- Location: `searoute/route_visualizer.html`
- Purpose: Marker shadow rendering

**License**: BSD 2-Clause License (part of Leaflet)

---

## Local API Endpoints (Flask Server)

The following endpoints are provided by our local Flask API server (`route_api_server.py`):

### 7. Port Search API

**Endpoint**: `GET /api/search-ports`

**Purpose**: Search for ports by name with autocomplete

**Parameters**:
- `q` (string, required): Search query (minimum 2 characters)
- `limit` (int, optional): Maximum number of results (default: 10)

**Example Request**:
```
GET http://localhost:5000/api/search-ports?q=Shanghai&limit=8
```

**Response**:
```json
[
  {
    "name": "Shanghai",
    "alternate": "Shanghai Port",
    "country": "CN",
    "lon": 121.5,
    "lat": 31.2
  }
]
```

**Usage**: Port autocomplete in route visualizer

---

### 8. Route Generation API

**Endpoint**: `POST /api/generate-route`

**Purpose**: Generate a shipping route between two ports

**Request Body**:
```json
{
  "origin": "Shanghai",
  "destination": "New York",
  "resolution": 5,
  "panama": 0
}
```

**Response**:
```json
{
  "success": true,
  "geojson": {...},
  "route_name": "Shanghai-New-York-City",
  "origin": "Shanghai",
  "destination": "New York City"
}
```

**Usage**: Route generation from web interface

---

### 9. Waypoint Extraction API

**Endpoint**: `POST /api/extract-waypoints`

**Purpose**: Extract waypoints from a GeoJSON route for weather data queries

**Request Body**:
```json
{
  "route_name": "Shanghai-New-York-City",
  "method": "distance",
  "interval_km": 200.0,
  "max_waypoints": 50
}
```

**Response**:
```json
{
  "success": true,
  "waypoints": [...],
  "count": 50,
  "method": "distance",
  "open_meteo_format": "..."
}
```

**Usage**: Extract route waypoints for wind data queries

---

### 10. Wind Data Query API

**Endpoint**: `POST /api/query-wind-data`

**Purpose**: Query wind data for route waypoints and return formatted results

**Request Body**:
```json
{
  "route_name": "Shanghai-New-York-City",
  "waypoints": [
    {"lat": 40.7, "lon": -74.0},
    ...
  ]
}
```

**Response**:
```json
{
  "route_name": "Shanghai-New-York-City",
  "api_type": "wind",
  "route_summary": {
    "total_waypoints": 50,
    "queried_waypoints": 50,
    "route_avg_wind_speed_ms": 27.53,
    "route_max_wind_speed_ms": 94.4,
    "route_avg_wind_direction_deg": 266.5
  },
  "waypoints_weather": [...]
}
```

**Usage**: Automatic wind data generation after route creation

---

### 11. Health Check API

**Endpoint**: `GET /api/health`

**Purpose**: Check if the API server is running

**Response**:
```json
{
  "status": "ok"
}
```

**Usage**: Server health monitoring

---

## Data Sources

### 12. Port Database (SQLite)

**Purpose**: Local database of port information

**Location**: `databases/port_data.db`

**Schema**: SQLite database with port names, coordinates, country codes

**Usage**: Port search, route generation

**Source**: Processed from `data/processed/port_data_processed.csv`

---

## API Usage Summary

| API | Type | Purpose | Authentication | Rate Limit |
|-----|------|---------|----------------|------------|
| Open-Meteo Forecast | External | Wind data | None | ~10k/day |
| Open-Meteo Marine | External | Marine data | None | ~10k/day |
| OpenStreetMap | External | Map tiles | None | Fair use |
| Leaflet.js | CDN | Map library | None | N/A |
| Local Flask Server | Local | Route generation | None | None |

---

## Configuration

### Environment Variables

No API keys are required for the current implementation. All external APIs are free and open.

### Rate Limiting Recommendations

1. **Open-Meteo API**: 
   - Limit to 50 waypoints per route
   - Add delays between batch requests (100ms recommended)
   - Cache results when possible

2. **OpenStreetMap Tiles**:
   - Standard tile usage (no special limits)
   - Attribution required

---

## Dependencies

### Python Packages
- `requests`: HTTP requests to Open-Meteo API
- `flask`: Local API server
- `flask-cors`: CORS support for local development

### JavaScript Libraries
- `leaflet`: Interactive mapping (loaded via CDN)

---

## License and Attribution

- **Open-Meteo**: Free, no attribution required
- **OpenStreetMap**: ODbL license, attribution required
- **Leaflet**: BSD 2-Clause License
- **Port Data**: Project-specific database

---

## References

- Open-Meteo Documentation: https://open-meteo.com/en/docs
- OpenStreetMap Wiki: https://wiki.openstreetmap.org/
- Leaflet Documentation: https://leafletjs.com/
- Flask Documentation: https://flask.palletsprojects.com/

---

## Updates

Last updated: 2025-11-05
- Added Open-Meteo Marine API (optional)
- Integrated wind data query API endpoint
- Documented all local API endpoints

