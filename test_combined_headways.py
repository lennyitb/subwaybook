#!/usr/bin/env python3
"""
Test script for combined headways module.

Demonstrates calculating effective headways when multiple services share a corridor.
Uses the Lexington Avenue Line (4/5/6 trains) as an example.
"""
import gtfs_kit as gk
import combined_headways as ch

# Load GTFS feed
print("Loading GTFS feed...")
feed = gk.read_feed("gtfs_subway.zip", dist_units="m")

# Test 1: Lexington Avenue Line (4/5/6 trains)
print("\n" + "=" * 100)
print("TEST 1: Lexington Avenue Line (4/5/6 trains) - Southbound to Manhattan")
print("=" * 100)

# First, analyze the service pattern to understand when trains run
ch.analyze_combined_service_pattern(
    feed,
    route_ids=['4', '5', '6'],
    direction_id=1,  # Southbound (to Manhattan)
    service_id='Weekday'
)

# Calculate individual and combined headways
print("\n" + "=" * 100)
print("Calculating headways...")
print("=" * 100)

headways_data = ch.get_individual_and_combined_headways(
    feed,
    route_ids=['4', '5', '6'],
    direction_id=1,
    service_id='Weekday'
)

# Display the comparison
ch.display_combined_headway_summary(headways_data, ['4', '5', '6'])


# Test 2: 8th Avenue Line in Manhattan (A/C/E trains)
print("\n\n" + "=" * 100)
print("TEST 2: 8th Avenue Line (A/C/E trains) - Northbound")
print("=" * 100)

ch.analyze_combined_service_pattern(
    feed,
    route_ids=['A', 'C', 'E'],
    direction_id=0,  # Northbound (to Manhattan)
    service_id='Weekday'
)

headways_data_ace = ch.get_individual_and_combined_headways(
    feed,
    route_ids=['A', 'C', 'E'],
    direction_id=0,
    service_id='Weekday'
)

ch.display_combined_headway_summary(headways_data_ace, ['A', 'C', 'E'])
