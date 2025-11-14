#!/usr/bin/env python3
"""
Test comparing 7 (local) vs 7X (express) travel times.
"""
import gtfs_kit as gk
import compare_lines as cl

# Load GTFS feed
print("Loading GTFS feed...")
feed = gk.read_feed("gtfs_subway.zip", dist_units="m")

# Compare 7 (local) vs 7X (express)
print("\n" + "="*80)
print("7 TRAIN (LOCAL) VS 7X TRAIN (EXPRESS) COMPARISON")
print("="*80)

difference = cl.compare_lines(
    feed,
    local_route='7',
    express_route='7X',
    direction_id=1,
    service_id='Weekday',
    export=True,
    verbose=True
)

print("\nTest completed successfully!")
