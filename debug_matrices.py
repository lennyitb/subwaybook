#!/usr/bin/env python3
"""
Debug script to check what's happening with the travel time matrices.
"""
import gtfs_kit as gk
import travel_times as tt
import pandas as pd

# Set pandas to show all columns
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
pd.set_option('display.max_colwidth', None)

# Load GTFS feed
feed = gk.read_feed("gtfs_subway.zip", dist_units="m")

route_id = 'A'
service_id = 'Weekday'

# Get canonical station order
canonical_order = tt.get_station_order(feed, route_id, 0, service_id)

# Just use first 5 stations for debugging
test_order = canonical_order[:5]
print("Test stations:")
for stop_id, stop_name in test_order:
    print(f"  {stop_id}: {stop_name}")

# Calculate matrix for direction 0
print("\n" + "="*80)
print("Direction 0 (to Manhattan)")
print("="*80)
matrix_dir0 = tt.calculate_travel_time_matrix(feed, route_id, 0, service_id, test_order)
print("\nMatrix shape:", matrix_dir0.shape)
print("\nMatrix (before combine):")
print(matrix_dir0)

# Calculate matrix for direction 1
print("\n" + "="*80)
print("Direction 1 (to Queens)")
print("="*80)
matrix_dir1 = tt.calculate_travel_time_matrix(feed, route_id, 1, service_id, test_order)
print("\nMatrix shape:", matrix_dir1.shape)
print("\nMatrix (before combine):")
print(matrix_dir1)
