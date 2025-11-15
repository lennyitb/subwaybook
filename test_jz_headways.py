#!/usr/bin/env python3
"""
Test script showing headway analysis for J and Z trains.
"""
import gtfs_kit as gk
import combined_headways as ch

# Load GTFS feed
print("Loading GTFS feed...")
feed = gk.read_feed("gtfs_subway.zip", dist_units="m")

print("\n" + "="*80)
print("J/Z TRAIN HEADWAY ANALYSIS - WEEKDAY SERVICE")
print("="*80)

# Direction 0: to Queens
print("\n" + "="*80)
print("DIRECTION 0: TO QUEENS")
print("="*80)

print("\nJ Train only:")
df_j_dir0 = ch.get_headway_dist_combined(feed, 0, 'J', service_id='Weekday')
ch.print_headway_dist(df_j_dir0)

print("\nZ Train only:")
df_z_dir0 = ch.get_headway_dist_combined(feed, 0, 'Z', service_id='Weekday')
ch.print_headway_dist(df_z_dir0)

print("\nJ+Z Combined:")
df_jz_dir0 = ch.get_headway_dist_combined(feed, 0, 'J', 'Z', service_id='Weekday')
ch.print_headway_dist(df_jz_dir0)

# Direction 1: to Manhattan
print("\n" + "="*80)
print("DIRECTION 1: TO MANHATTAN")
print("="*80)

print("\nJ Train only:")
df_j_dir1 = ch.get_headway_dist_combined(feed, 1, 'J', service_id='Weekday')
ch.print_headway_dist(df_j_dir1)

print("\nZ Train only:")
df_z_dir1 = ch.get_headway_dist_combined(feed, 1, 'Z', service_id='Weekday')
ch.print_headway_dist(df_z_dir1)

print("\nJ+Z Combined:")
df_jz_dir1 = ch.get_headway_dist_combined(feed, 1, 'J', 'Z', service_id='Weekday')
ch.print_headway_dist(df_jz_dir1)

print("\n" + "="*80)
print("Test completed successfully!")
print("="*80)
