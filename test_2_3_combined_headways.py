#!/usr/bin/env python3
"""
Test script for combined headways of 2 and 3 trains.

The 2 and 3 trains share the same corridor on the West Side IRT line
(7th Avenue Line in Manhattan and into Brooklyn). This demonstrates how
passengers can take either train when traveling along the shared corridor.
"""
import gtfs_kit as gk
import combined_headways as ch

# Load GTFS feed
print("Loading GTFS feed...")
feed = gk.read_feed("gtfs_subway.zip", dist_units="m")

print("\n" + "=" * 100)
print("2 and 3 Trains - Combined Headway Analysis")
print("West Side IRT Line (7th Avenue Line)")
print("=" * 100)

# First, analyze the service pattern to understand when trains run
print("\n" + "=" * 100)
print("Service Pattern - Northbound (Direction 0)")
print("=" * 100)

ch.analyze_combined_service_pattern(
    feed,
    route_ids=['2', '3'],
    direction_id=0,  # Northbound (to The Bronx)
    service_id='Weekday'
)

# Calculate individual and combined headways - Northbound
print("\n" + "=" * 100)
print("Headway Analysis - Northbound (Direction 0)")
print("=" * 100)

headways_data_nb = ch.get_individual_and_combined_headways(
    feed,
    route_ids=['2', '3'],
    direction_id=0,
    service_id='Weekday'
)

ch.display_combined_headway_summary(headways_data_nb, ['2', '3'])

# Now do the same for Southbound
print("\n\n" + "=" * 100)
print("Service Pattern - Southbound (Direction 1)")
print("=" * 100)

ch.analyze_combined_service_pattern(
    feed,
    route_ids=['2', '3'],
    direction_id=1,  # Southbound (to Brooklyn)
    service_id='Weekday'
)

# Calculate individual and combined headways - Southbound
print("\n" + "=" * 100)
print("Headway Analysis - Southbound (Direction 1)")
print("=" * 100)

headways_data_sb = ch.get_individual_and_combined_headways(
    feed,
    route_ids=['2', '3'],
    direction_id=1,
    service_id='Weekday'
)

ch.display_combined_headway_summary(headways_data_sb, ['2', '3'])

# Also show a simple combined headway table for southbound
print("\n" + "=" * 100)
print("Simple Combined Headway Table - Southbound")
print("=" * 100)

ch.display_simple_combined_headways(
    headways_data_sb['combined'],
    ['2', '3'],
    title="2/3 Combined Headways - Southbound to Brooklyn (Weekday)"
)
