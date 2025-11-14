#!/usr/bin/env python3
"""
Test comparing 7 (local) vs 7X (express) with hour range filtering.
Demonstrates morning rush vs evening rush comparisons.
"""
import gtfs_kit as gk
import compare_lines as cl

# Load GTFS feed
print("Loading GTFS feed...")
feed = gk.read_feed("gtfs_subway.zip", dist_units="m")

print("\n" + "="*80)
print("7 TRAIN (LOCAL) VS 7X TRAIN (EXPRESS) - TIME-FILTERED COMPARISON")
print("="*80)

# Example 1: All hours (baseline)
print("\n" + "="*80)
print("Example 1: All Hours (Baseline)")
print("="*80)
diff_all = cl.compare_lines(
    feed,
    local_route='7',
    express_route='7X',
    direction_id=1,
    service_id='Weekday',
    export=True,
    verbose=True
)

# Example 2: Morning rush hour only (7-9 AM)
print("\n\n" + "="*80)
print("Example 2: Morning Rush Hour (7-9 AM)")
print("="*80)
diff_morning = cl.compare_lines(
    feed,
    local_route='7',
    express_route='7X',
    direction_id=1,
    service_id='Weekday',
    hour_range=(7, 9),
    export=True,
    verbose=True
)

# Example 3: Evening rush hour only (5-7 PM / 17-19)
print("\n\n" + "="*80)
print("Example 3: Evening Rush Hour (5-7 PM)")
print("="*80)
diff_evening = cl.compare_lines(
    feed,
    local_route='7',
    express_route='7X',
    direction_id=1,
    service_id='Weekday',
    hour_range=(17, 19),
    export=True,
    verbose=True
)

# Example 4: Single hour - Peak morning (8 AM)
print("\n\n" + "="*80)
print("Example 4: Single Hour - 8 AM")
print("="*80)
diff_8am = cl.compare_lines(
    feed,
    local_route='7',
    express_route='7X',
    direction_id=1,
    service_id='Weekday',
    hour_range=8,
    export=True,
    verbose=True
)

print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print("\nGenerated comparison files:")
print("  - 7_vs_7X_difference_Weekday.csv (all hours)")
print("  - 7_vs_7X_difference_Weekday_hours_7-9.csv (morning rush)")
print("  - 7_vs_7X_difference_Weekday_hours_17-19.csv (evening rush)")
print("  - 7_vs_7X_difference_Weekday_hour_8.csv (8 AM only)")

print("\nTest completed successfully!")
