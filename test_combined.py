#!/usr/bin/env python3
"""
Test for get_headway_dist_combined() function.
Shows various combinations of routes and branches with hour filtering.
"""
import gtfs_kit as gk
import combined_headways as ch

# Load GTFS feed
print("Loading GTFS feed...")
feed = gk.read_feed("gtfs_subway.zip", dist_units="m")

print("\n" + "="*80)
print("COMBINED HEADWAY ANALYSIS - EXAMPLES")
print("="*80)

# Example 1: Multiple regular routes (classic use case)
print("\n" + "="*80)
print("Example 1: Lexington Ave Line (4/5/6 combined)")
print("="*80)
df1 = ch.get_headway_dist_combined(feed, 1, '4', '5', '6', service_id='Weekday')
ch.print_headway_dist(df1)

# Example 2: Mix of regular route and specific branch
print("\n" + "="*80)
print("Example 2: All 4 trains + 5 trains to Nereid only")
print("="*80)
df2 = ch.get_headway_dist_combined(feed, 1, '4', ('5', 'Nereid'), service_id='Weekday')
ch.print_headway_dist(df2)

# Example 3: Multiple specific branches
print("\n" + "="*80)
print("Example 3: A train Rockaway branches (Far Rockaway + Rockaway Park)")
print("="*80)
df3 = ch.get_headway_dist_combined(feed, 1, ('A', 'Far Rockaway'), ('A', 'Rockaway Park'),
                                    service_id='Weekday')
ch.print_headway_dist(df3)

# Example 4: Morning rush hour only (7-9 AM)
print("\n" + "="*80)
print("Example 4: 4/5/6 trains during morning rush (7-9 AM)")
print("="*80)
df4 = ch.get_headway_dist_combined(feed, 1, '4', '5', '6', service_id='Weekday',
                                    hour_range=(7, 9))
ch.print_headway_dist(df4)

# Example 5: Evening Nereid service only (5-7 PM)
print("\n" + "="*80)
print("Example 5: 5 trains to Nereid during evening rush (17-19)")
print("="*80)
df5 = ch.get_headway_dist_combined(feed, 0, ('5', 'Nereid'), service_id='Weekday',
                                    hour_range=(17, 19))
ch.print_headway_dist(df5)

# Example 6: Compare combined headways
print("\n" + "="*80)
print("COMPARISON: Rush Hour Headways")
print("="*80)

# 8 AM comparisons
import pandas as pd

print("\nMorning Rush (8 AM):")
df1_8am = df1[df1['hour'] == 8].iloc[0]
df2_8am = df2[df2['hour'] == 8].iloc[0]

print(f"  All 4/5/6 trains:      {df1_8am['avg_headway']:6.2f} min avg, {int(df1_8am['num_trains']):3d} trains")
print(f"  4 + 5-to-Nereid:       {df2_8am['avg_headway']:6.2f} min avg, {int(df2_8am['num_trains']):3d} trains")

# Summary for morning rush time range
print("\nMorning Rush Period (7-9 AM) - Average across all hours:")
avg_7_9 = df4['avg_headway'].mean()
total_trains_7_9 = df4['num_trains'].sum()
print(f"  4/5/6 combined:        {avg_7_9:6.2f} min avg headway")
print(f"  Total trains 7-9 AM:   {int(total_trains_7_9):3d} trains")

print("\nTest completed successfully!")
