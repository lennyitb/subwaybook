#!/usr/bin/env python3
"""
Test comparing A (express) vs C (local) during morning rush and midday.
"""
import gtfs_kit as gk
import compare_lines as cl

# Load GTFS feed
print("Loading GTFS feed...")
feed = gk.read_feed("gtfs_subway.zip", dist_units="m")

print("\n" + "="*80)
print("A TRAIN (EXPRESS) VS C TRAIN (LOCAL) - TIME COMPARISONS")
print("="*80)

# Morning rush hour comparison (7-9 AM)
print("\n" + "="*80)
print("MORNING RUSH HOUR (7-9 AM)")
print("="*80)
diff_morning = cl.compare_lines(
    feed,
    local_route='C',
    express_route='A',
    direction_id=1,
    service_id='Weekday',
    hour_range=(7, 9),
    export=True,
    verbose=True
)

# Midday comparison (9 AM - 4 PM)
print("\n\n" + "="*80)
print("MIDDAY (9 AM - 4 PM)")
print("="*80)
diff_midday = cl.compare_lines(
    feed,
    local_route='C',
    express_route='A',
    direction_id=1,
    service_id='Weekday',
    hour_range=(9, 16),
    export=True,
    verbose=True
)

print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print("\nGenerated comparison files:")
print("  - C_vs_A_difference_Weekday_hours_7-9.csv (morning rush)")
print("  - C_vs_A_difference_Weekday_hours_9-16.csv (midday)")

print("\nTest completed successfully!")
