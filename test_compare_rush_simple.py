#!/usr/bin/env python3
"""
Simple test comparing 7 vs 7X during morning rush hour only.
"""
import gtfs_kit as gk
import compare_lines as cl

# Load GTFS feed
print("Loading GTFS feed...")
feed = gk.read_feed("gtfs_subway.zip", dist_units="m")

print("\n" + "="*80)
print("7 vs 7X - MORNING RUSH HOUR ONLY (7-9 AM)")
print("="*80)

# Morning rush hour comparison (7-9 AM)
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

print("\nTest completed successfully!")
print(f"Exported to: 7_vs_7X_difference_Weekday_hours_7-9.csv")
