# Step-by-Step Guide: Starting the World Ports Map Application

## Prerequisites Check

Before starting, make sure you have:
- ✅ Python 3 installed
- ✅ SQLite database file exists (`databases/port_data.db`)
- ✅ Required Python packages installed

## Step 1: Install Required Dependencies

Open a terminal and navigate to the project directory:

```bash
cd "/Users/uliwintersperger/Desktop/uni/cssci/semester-03/group-project_econowind/group_jan-econowind-winds4change"
```

Install Python dependencies (if not already installed):

```bash
pip3 install folium
```

Or install all dependencies from requirements.txt:

```bash
pip3 install -r requirements.txt
```

## Step 2: Generate/Update the Map

The map is generated from the port database. To create or update it:

```bash
python3 visualization/maps/prototype_map_001.py
```

**Expected output:**
```
Connecting to database: /path/to/databases/port_data.db
Found X ports with valid coordinates
Map saved to: /path/to/visualization/maps/world_ports_map.html
Open the HTML file in a web browser to view the interactive map.

✓ Successfully created interactive map with X ports!
```

## Step 3: Open the Map in Your Browser

You have two options:

### Option A: Open Directly (Simple Method)
1. Navigate to the maps folder:
   ```bash
   open visualization/maps/world_ports_map.html
   ```
   
   Or on macOS, you can also:
   - Find the file in Finder: `visualization/maps/world_ports_map.html`
   - Double-click it to open in your default browser

### Option B: Use a Local Web Server (Recommended - Avoids CORS Issues)

If you plan to load routes or encounter any loading issues:

```bash
cd visualization/maps
python3 -m http.server 8000
```

Then open in your browser:
```
http://localhost:8000/world_ports_map.html
```

**Note:** Keep the server running while viewing the map. Press `Ctrl+C` to stop it.

## Step 4: Using the Map

Once the map is open in your browser:

- **Zoom**: Use mouse wheel or +/- buttons
- **Pan**: Click and drag the map
- **View Port Details**: Click on any blue port marker to see the port name
- **Hover**: Hover over markers to see tooltips

## Troubleshooting

### Error: "Error loading route: Load failed"
✅ **This has been fixed!** The error handling code has been added to suppress this error. If you still see it:
- Refresh the page (F5 or Cmd+R)
- Check the browser console (F12 → Console) for details
- The error is now handled gracefully and won't block the map

### Error: "No module named 'folium'"
**Solution:**
```bash
pip3 install folium
```

### Error: "Database not found"
**Solution:**
Make sure the database exists:
```bash
ls -la databases/port_data.db
```

If it doesn't exist, you may need to create it first (check other scripts in the project).

### Map shows but is empty
**Solution:**
1. Regenerate the map:
   ```bash
   python3 visualization/maps/prototype_map_001.py
   ```
2. Check if the database has port data:
   ```bash
   sqlite3 databases/port_data.db "SELECT COUNT(*) FROM ports WHERE Latitude IS NOT NULL AND Longitude IS NOT NULL;"
   ```

### Routes not loading
- The map is designed to show ports only. Route loading is optional.
- If you want to add routes, see `searoute/VISUALIZATION_README.md`
- The error handling now prevents route loading errors from blocking the map

## Quick Reference

```bash
# 1. Install dependencies
pip3 install folium

# 2. Generate map
python3 visualization/maps/prototype_map_001.py

# 3. Open map (simple)
open visualization/maps/world_ports_map.html

# OR use web server
cd visualization/maps && python3 -m http.server 8000
# Then visit: http://localhost:8000/world_ports_map.html
```

## Next Steps (Optional)

If you want to add shipping routes to the map:

1. **Generate a route:**
   ```bash
   python3 searoute/map_route.py Shanghai "New York"
   ```

2. **Visualize routes:**
   ```bash
   python3 searoute/visualize_routes.py Shanghai-New-York-City
   ```

3. **Use the route visualizer:**
   ```bash
   cd searoute
   python3 route_api_server.py
   # Then open: http://localhost:5000/route_visualizer.html
   ```

## Summary

The simplest way to start:
1. ✅ Install folium: `pip3 install folium`
2. ✅ Generate map: `python3 visualization/maps/prototype_map_001.py`
3. ✅ Open map: `open visualization/maps/world_ports_map.html`

That's it! The map should now display all ports from your database.

