# How to Open Route Visualizer

## Method 1: Simple File Open (Quick Start)

1. **Navigate to the searoute folder**:
   ```
   /Users/uliwintersperger/Desktop/uni/cssci/semester-03/group-project_econowind/group_jan-econowind-winds4change/searoute
   ```

2. **Double-click** `route_visualizer.html` in Finder, or:
   - Right-click → Open With → Your preferred browser (Chrome, Firefox, Safari, etc.)

**Note**: This method works, but if you need to load files from the `output/` directory, you may encounter CORS (Cross-Origin Resource Sharing) issues. Use Method 2 for best results.

---

## Method 2: Using a Local Web Server (Recommended)

This method avoids CORS issues and allows loading files from the `output/` directory.

### Option A: Python's Built-in Server

```bash
# Navigate to the searoute directory
cd searoute

# Start a simple HTTP server (Python 3)
python3 -m http.server 8000

# Or if that doesn't work:
python3 -m http.server 8000 --bind 127.0.0.1
```

Then open in your browser:
```
http://localhost:8000/route_visualizer.html
```

### Option B: Using the API Server (Best for Route Generation)

If you want to generate routes and see wind data:

```bash
# Terminal 1: Start the API server
cd searoute
python3 route_api_server.py
```

Then open in your browser:
```
http://localhost:5000/route_visualizer.html
```

Or if the file is in the searoute directory:
```
http://localhost:5000/route_visualizer.html
```

---

## Method 3: Command Line (macOS)

```bash
# Open directly in default browser
cd searoute
open route_visualizer.html

# Or open in a specific browser
open -a "Google Chrome" route_visualizer.html
open -a "Firefox" route_visualizer.html
open -a "Safari" route_visualizer.html
```

---

## Quick Start Guide

### Step 1: Start the API Server (if generating routes)

```bash
cd searoute
python3 route_api_server.py
```

Keep this terminal running.

### Step 2: Open the Visualizer

**Option A**: Double-click `route_visualizer.html` in Finder

**Option B**: Start a web server:
```bash
cd searoute
python3 -m http.server 8000
```
Then visit: `http://localhost:8000/route_visualizer.html`

### Step 3: Use the Visualizer

1. **Generate a new route**:
   - Enter origin port (e.g., "Shanghai")
   - Enter destination port (e.g., "New York")
   - Click "Generate Route"
   - Wind data will load automatically if available

2. **Load existing route**:
   - Click "Load Shanghai-New York" to load a default route
   - Or use "Load from File" to upload a GeoJSON file

3. **View wind data**:
   - Check "Show Wind Data" checkbox (enabled by default)
   - Colored circles show wind speed at waypoints
   - Arrows show wind direction
   - Click any waypoint to see details

---

## Troubleshooting

### "Failed to fetch" or CORS errors
- Use Method 2 (local web server) instead of double-clicking

### Wind data not showing
- Make sure the weather JSON file exists in `output/` directory
- Check browser console for errors (F12 → Console)
- Verify the route name matches the wind data filename

### API server not responding
- Make sure `route_api_server.py` is running
- Check that port 5000 is not in use by another application
- Verify the server started successfully

### Can't see the map
- Check browser console for JavaScript errors
- Make sure you have an internet connection (for map tiles)
- Try a different browser

---

## File Locations

- **Route Visualizer**: `searoute/route_visualizer.html`
- **Route Files**: `searoute/output/*.geojson`
- **Wind Data**: `searoute/output/*_weather.json`
- **API Server**: `searoute/route_api_server.py`

