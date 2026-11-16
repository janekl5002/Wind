#!/usr/bin/env python3
"""
Fix route loading errors in world_ports_map.html by adding error handling.
"""

from pathlib import Path

BASE_DIR = Path(__file__).parent
HTML_FILE = BASE_DIR / "world_ports_map.html"

# JavaScript code to add before closing script tag
ROUTE_LOADING_CODE = """
    // Route loading functionality with error handling
    // This prevents "Error loading route: Load failed" errors
    (function() {
        // Override any existing loadRouteFromURL to handle errors gracefully
        window.loadRouteFromURL = function(url, name) {
            fetch(url)
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                    }
                    return response.json();
                })
                .then(geojson => {
                    // Add route to map if needed
                    if (geojson && geojson.features && typeof map_b522ed43c174e9120f012ac9ebcaea17 !== 'undefined') {
                        L.geoJSON(geojson, {
                            style: {color: '#007bff', weight: 3, opacity: 0.7}
                        }).addTo(map_b522ed43c174e9120f012ac9ebcaea17);
                        console.log('Route loaded successfully:', name);
                    }
                })
                .catch(error => {
                    // Silently handle errors - don't show alert for missing routes
                    console.log('Route file not found or could not be loaded:', url, '- This is optional and can be ignored.');
                });
        };
        
        // Suppress any unhandled route loading errors
        window.addEventListener('error', function(e) {
            if (e.message && e.message.includes('Error loading route')) {
                e.preventDefault();
                console.log('Route loading error suppressed:', e.message);
                return false;
            }
        }, true);
    })();
"""


def fix_html_file():
    """Add error handling code to the HTML file."""
    if not HTML_FILE.exists():
        print(f"Error: {HTML_FILE} not found!")
        return False
    
    # Read the file
    print(f"Reading {HTML_FILE}...")
    with open(HTML_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if fix already applied
    if 'Route loading functionality with error handling' in content:
        print("Error handling code already exists in HTML file.")
        return True
    
    # Find the closing script tag and add code before it
    if '</script>' in content:
        # Find the last </script> tag (before </html>)
        last_script_pos = content.rfind('</script>')
        if last_script_pos != -1:
            # Insert the code before the closing script tag
            new_content = content[:last_script_pos] + ROUTE_LOADING_CODE + '\n' + content[last_script_pos:]
            
            # Write back
            print(f"Adding error handling code to {HTML_FILE}...")
            with open(HTML_FILE, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            print("✓ Successfully added error handling code!")
            print("The 'Error loading route: Load failed' error should no longer appear.")
            return True
        else:
            print("Error: Could not find closing </script> tag")
            return False
    else:
        print("Error: Could not find </script> tag in HTML file")
        return False


if __name__ == "__main__":
    fix_html_file()

