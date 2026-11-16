#!/usr/bin/env bash
# Example script to map routes between ports

echo "Example 1: Shanghai to New York"
python3 map_route.py Shanghai "New York"

echo ""
echo "Example 2: Rotterdam to Hamburg"
python3 map_route.py Rotterdam Hamburg

echo ""
echo "Example 3: Shanghai to Rotterdam (with Panama canal)"
python3 map_route.py Shanghai Rotterdam -panama 1

