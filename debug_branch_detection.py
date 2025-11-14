#!/usr/bin/env python3
"""
Debug script to check branch detection logic.
"""
import gtfs_kit as gk
import pandas as pd

feed = gk.read_feed("gtfs_subway.zip", dist_units="m")

for direction in [0, 1]:
    print(f"\n{'='*80}")
    print(f"DIRECTION {direction}")
    print(f"{'='*80}")

    # Get A train trips
    trips = feed.trips[
        (feed.trips['route_id'] == 'A') &
        (feed.trips['direction_id'] == direction) &
        (feed.trips['service_id'] == 'Weekday')
    ].copy()

    print(f"Found {len(trips)} trips for A train direction {direction}")

    # Get stop times
    stop_times = feed.stop_times[feed.stop_times['trip_id'].isin(trips['trip_id'])].copy()
    stop_times = stop_times.sort_values(['trip_id', 'stop_sequence'])

    # Get first and last stops
    first_stops = stop_times.groupby('trip_id').first().reset_index()
    last_stops = stop_times.groupby('trip_id').last().reset_index()

    # Count unique stops at each end
    first_stop_unique = first_stops['stop_id'].unique()
    last_stop_unique = last_stops['stop_id'].unique()

    print(f"\nFirst stops (where trips start): {len(first_stop_unique)} unique")
    first_stop_counts = first_stops['stop_id'].value_counts()
    for stop_id in first_stop_unique:
        stop_name = feed.stops[feed.stops['stop_id'] == stop_id]['stop_name'].values[0]
        count = len(first_stops[first_stops['stop_id'] == stop_id])
        print(f"  {stop_name}: {count} trips")

    print(f"\nLast stops (where trips end): {len(last_stop_unique)} unique")
    last_stop_counts = last_stops['stop_id'].value_counts()
    for stop_id in last_stop_unique:
        stop_name = feed.stops[feed.stops['stop_id'] == stop_id]['stop_name'].values[0]
        count = len(last_stops[last_stops['stop_id'] == stop_id])
        print(f"  {stop_name}: {count} trips")

    # Test the heuristic
    min_significant_trips = len(trips) * 0.05
    significant_first_stops = sum(first_stop_counts >= min_significant_trips)
    significant_last_stops = sum(last_stop_counts >= min_significant_trips)

    print(f"\nHeuristic Analysis:")
    print(f"  min_significant_trips (5%): {min_significant_trips:.1f}")
    print(f"  significant_first_stops: {significant_first_stops}")
    print(f"  significant_last_stops: {significant_last_stops}")

    if significant_first_stops >= 2 and significant_first_stops >= significant_last_stops:
        print(f"  => Branches are at the START (first stop)")
    else:
        print(f"  => Branches are at the END (last stop)")
