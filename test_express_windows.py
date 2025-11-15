#!/usr/bin/env python3
"""
Test script demonstrating express service windows for various routes.
Shows when express service operates throughout the day, broken down by borough.

This script now uses the express_windows module to load pre-generated data
from express_window_data.json instead of computing it live.
"""
import express_windows as ew

print("\n" + "="*80)
print("EXPRESS SERVICE WINDOWS BY BOROUGH - WEEKDAY SERVICE")
print("="*80)
print("(Data loaded from express_window_data.json)")
print("="*80)

# Load all data and print all routes
try:
    data = ew.load_express_windows()

    # Print all routes in order
    all_routes = ['A', 'C', 'E', 'B', 'D', 'F', 'M', 'N', 'Q', 'R', 'W',
                  '1', '2', '3', '4', '5', '6', '7', 'L', 'G',
                  '6X', '7X', 'FX', 'J', 'Z']

    for route_id in all_routes:
        if route_id in data:
            ew.print_express_windows(route_id)

    print("\n" + "="*80)
    print("NOTES:")
    print("  - Data generated from GTFS feed with hardcoded special cases:")
    print("  - A trains are always local in Queens")
    print("  - B trains are always express in Manhattan and Brooklyn (weekdays only)")
    print("  - C, M, R, 1, 6, L, G trains are always local")
    print("  - F trains are never express in Brooklyn")
    print("  - 6X, 7X, FX trains run express in outer boroughs, local in Manhattan")
    print("  - J/Z trains have special skip-stop service patterns")
    print("="*80)

except FileNotFoundError:
    print("\nERROR: express_window_data.json not found!")
    print("Run 'python3 express_windows.py' to generate the data file.")
    print("="*80)
