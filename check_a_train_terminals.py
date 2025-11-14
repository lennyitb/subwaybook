#!/usr/bin/env python3
"""
Quick script to check A train terminals for both directions.
"""
import gtfs_kit as gk
import pandas as pd

feed = gk.read_feed("gtfs_subway.zip", dist_units="m")

# Get A train trips
a_trips = feed.trips[feed.trips['route_id'] == 'A'].copy()

print("A train terminals by direction:\n")

for direction in [0, 1]:
    print(f"\nDirection {direction}:")
    dir_trips = a_trips[a_trips['direction_id'] == direction]

    if dir_trips.empty:
        print("  No trips found")
        continue

    # Get terminal stops
    stop_times = feed.stop_times[feed.stop_times['trip_id'].isin(dir_trips['trip_id'])].copy()
    stop_times = stop_times.sort_values(['trip_id', 'stop_sequence'])
    terminals = stop_times.groupby('trip_id').last().reset_index()

    # Count terminals
    terminal_counts = terminals['stop_id'].value_counts()

    for terminal_id, count in terminal_counts.items():
        terminal_name = feed.stops[feed.stops['stop_id'] == terminal_id]['stop_name'].values[0]
        print(f"  {terminal_name}: {count} trips")
