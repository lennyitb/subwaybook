#!/usr/bin/env python3
"""
Simple test comparing A (express) vs C (local) trains.
"""
import gtfs_kit as gk
import compare_lines as cl

# Load GTFS feed
print("Loading GTFS feed...")
feed = gk.read_feed("gtfs_subway.zip", dist_units="m")

print("\n" + "="*80)
print("A TRAIN (EXPRESS) VS C TRAIN (LOCAL)")
print("="*80)

# Compare A vs C for all hours
diff = cl.compare_lines(
    feed,
    local_route='C',
    express_route='A',
    direction_id=1,
    service_id='Weekday',
    export=True,
    verbose=True
)

print("\nTest completed successfully!")
print("CSV exported to: C_vs_A_difference_Weekday.csv")
