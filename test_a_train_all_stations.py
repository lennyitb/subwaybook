#!/usr/bin/env python3
"""
Test script to verify that all A train stations are included across all branches.
"""
import gtfs_kit as gk
import travel_times as tt

# Load GTFS feed
feed = gk.read_feed("gtfs_subway.zip", dist_units="m")

route_id = 'A'
service_id = 'Weekday'
direction_id = 1

print(f"Getting station order for {route_id} train (direction {direction_id}, {service_id})")
print("="*80)

# First, check what branches exist
branch_point, branches_info = tt.identify_branches(feed, route_id, direction_id, service_id)

if branches_info:
    print(f"\nBranches for {route_id} train:")
    for i, branch in enumerate(branches_info):
        print(f"  {i+1}. {branch['terminal_name']}: {branch['trip_count']} trips, {branch['stop_count']} stops")
    if branch_point:
        branch_name = feed.stops[feed.stops['stop_id'] == branch_point]['stop_name'].values
        print(f"\nBranch point: {branch_name[0] if len(branch_name) > 0 else branch_point}")
    print()

# Get canonical station order
canonical_order = tt.get_station_order(feed, route_id, direction_id, service_id)

print(f"\nTotal stations: {len(canonical_order)}")
print("\nStation order:")
print("-"*80)
for i, (stop_id, stop_name) in enumerate(canonical_order):
    print(f"{i+1:3d}. {stop_name}")

# Expected stations for A train (approximate, based on your description):
# Trunk: Inwood-207 St through Rockaway Blvd (about 38 stops)
# Lefferts branch: 104 St, 111 St, Ozone Park-Lefferts Blvd (3 stops)
# Far Rockaway branch: Aqueduct Racetrack, Howard Beach, Broad Channel, Beach 67 St through Far Rockaway-Mott Av (about 8 stops)
# Rockaway Park branch (part-time): Beach 90 St through Rockaway Park Beach 116 St (about 4 stops)
# Total: ~53 stations

print("\n" + "="*80)
print(f"Expected approximately 53 stations total for A train with all branches")
print(f"Got {len(canonical_order)} stations")
