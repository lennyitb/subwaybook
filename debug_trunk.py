#!/usr/bin/env python3
"""
Debug trunk matrix generation
"""
import gtfs_kit as gk
import travel_times as tt
import pandas as pd

pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)

feed = gk.read_feed("/Users/lennyphelan/Downloads/gtfs_subway.zip", dist_units="m")

route_id = 'A'
service_id = 'Weekday'

# Get canonical station order
canonical_order = tt.get_station_order(feed, route_id, 0, service_id)

# Find Euclid Av and truncate
euclid_idx = None
for i, (stop_id, stop_name) in enumerate(canonical_order):
    if 'Euclid' in stop_name:
        euclid_idx = i
        break

trunk_order = canonical_order[euclid_idx:]

# Apply express filtering
filtered_trunk_order = tt.filter_station_order_express(
    feed, trunk_order, route_id, 0, service_id,
    express_boroughs=['Manhattan', 'Brooklyn'],
    all_stops_boroughs=[]
)

# Just test with first 5 stations
test_order = filtered_trunk_order[:5]
print("Test stations:")
for stop_id, stop_name in test_order:
    print(f"  {stop_id}: {stop_name}")

print("\nCalculating direction 0 matrix...")
matrix_dir0 = tt.calculate_travel_time_matrix(feed, route_id, 0, service_id, test_order)
print(matrix_dir0)

print("\nCalculating direction 1 matrix...")
matrix_dir1 = tt.calculate_travel_time_matrix(feed, route_id, 1, service_id, test_order)
print(matrix_dir1)

print("\nCombining matrices...")
combined = tt.combine_bidirectional_matrix(matrix_dir0, matrix_dir1)
print(combined)
