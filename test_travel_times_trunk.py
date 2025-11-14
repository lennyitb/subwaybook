#!/usr/bin/env python3
"""
Test script for generating travel time matrix up to the branch point (Euclid Av).

This creates a compact matrix that only includes:
- All stops from the terminal branches up to and including Euclid Av
- Express stops only in Manhattan and Brooklyn
- All the trunk stops through Manhattan
"""
import gtfs_kit as gk
import travel_times as tt

# Load GTFS feed
feed = gk.read_feed("gtfs_subway.zip", dist_units="m")

route_id = 'A'
service_id = 'Weekday'

print(f"Generating travel time matrix for {route_id} train - trunk only (up to Euclid Av)")
print("="*80)

# Get canonical station order
canonical_order = tt.get_station_order(feed, route_id, 0, service_id)

print(f"\nOriginal station count: {len(canonical_order)}")

# Find Euclid Av in the station order
euclid_idx = None
for i, (stop_id, stop_name) in enumerate(canonical_order):
    if 'Euclid' in stop_name:
        euclid_idx = i
        print(f"Found Euclid Av at index {i}: {stop_name} ({stop_id})")
        break

if euclid_idx is None:
    print("ERROR: Could not find Euclid Av in station order")
    exit(1)

# Truncate station order at Euclid Av (include Euclid Av and everything after)
trunk_order = canonical_order[euclid_idx:]

print(f"Trunk station count (from Euclid Av onwards): {len(trunk_order)}")
print("\nStations included:")
for i, (stop_id, stop_name) in enumerate(trunk_order):
    print(f"  {i+1}. {stop_name}")

# Now apply express filtering to Manhattan and Brooklyn
print("\n" + "="*80)
print("Applying express filtering (Manhattan/Brooklyn express only)")
print("="*80)

filtered_trunk_order = tt.filter_station_order_express(
    feed, trunk_order, route_id, 0, service_id,
    express_boroughs=['Manhattan', 'Brooklyn'],
    all_stops_boroughs=[]  # No boroughs with all stops - we already filtered to trunk
)

print(f"\nFiltered to {len(filtered_trunk_order)} stations")
print("\nFiltered stations:")
for i, (stop_id, stop_name) in enumerate(filtered_trunk_order):
    print(f"  {i+1}. {stop_name}")

# Calculate matrices for both directions
print("\n" + "="*80)
print("Calculating travel time matrices...")
print("="*80)

matrix_dir0 = tt.calculate_travel_time_matrix(feed, route_id, 0, service_id, filtered_trunk_order)
matrix_dir1 = tt.calculate_travel_time_matrix(feed, route_id, 1, service_id, filtered_trunk_order)

if not matrix_dir0.empty and not matrix_dir1.empty:
    # Get direction names
    direction_name_0 = tt.get_direction_name(feed, route_id, 0, service_id)
    direction_name_1 = tt.get_direction_name(feed, route_id, 1, service_id)

    # Combine the matrices
    combined_matrix = tt.combine_bidirectional_matrix(matrix_dir0, matrix_dir1)

    # Print combined matrix
    tt.print_combined_travel_time_matrix(combined_matrix, route_id, service_id,
                                        direction_name_0, direction_name_1)

    # Export to CSV
    csv_filename = f'{route_id}_{service_id}_trunk_express_travel_times.csv'
    combined_matrix.to_csv(csv_filename)
    print(f"\nExported to {csv_filename}")
else:
    print(f"Could not generate travel time matrix for {route_id} train")
