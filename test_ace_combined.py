#!/usr/bin/env python3
"""
Test script showing combined headway analysis for A, C, and E trains.
These three routes share the 8th Avenue corridor in Manhattan.
"""
import gtfs_kit as gk
import combined_headways as ch

# Load GTFS feed
print("Loading GTFS feed...")
feed = gk.read_feed("gtfs_subway.zip", dist_units="m")

print("\n" + "="*80)
print("COMBINED HEADWAY ANALYSIS: A + C + E TRAINS")
print("8th Avenue Line - Manhattan")
print("="*80)

# Combined headways for all three routes
print("\n" + "="*80)
print("Direction 1: Trains heading toward Manhattan/Uptown")
print("="*80)

df_combined = ch.get_headway_dist_combined(
    feed, 1, 'A', 'C', 'E',
    service_id='Weekday'
)

ch.print_headway_dist(df_combined)

# Morning rush hour detail
print("\n" + "="*80)
print("MORNING RUSH HOUR (7-9 AM)")
print("="*80)

df_rush = ch.get_headway_dist_combined(
    feed, 1, 'A', 'C', 'E',
    service_id='Weekday',
    hour_range=(7, 9)
)

ch.print_headway_dist(df_rush)

# Midday comparison
print("\n" + "="*80)
print("MIDDAY (10 AM - 2 PM)")
print("="*80)

df_midday = ch.get_headway_dist_combined(
    feed, 1, 'A', 'C', 'E',
    service_id='Weekday',
    hour_range=(10, 14)
)

ch.print_headway_dist(df_midday)

# Individual route comparison during rush hour
print("\n" + "="*80)
print("INDIVIDUAL ROUTE HEADWAYS - MORNING RUSH (7-9 AM)")
print("="*80)

print("\nA Train only:")
df_a = ch.get_headway_dist_combined(feed, 1, 'A', service_id='Weekday', hour_range=(7, 9))
ch.print_headway_dist(df_a)

print("\nC Train only:")
df_c = ch.get_headway_dist_combined(feed, 1, 'C', service_id='Weekday', hour_range=(7, 9))
ch.print_headway_dist(df_c)

print("\nE Train only:")
df_e = ch.get_headway_dist_combined(feed, 1, 'E', service_id='Weekday', hour_range=(7, 9))
ch.print_headway_dist(df_e)

print("\n" + "="*80)
print("SUMMARY")
print("="*80)

# Calculate average headways for morning rush
ace_avg = df_rush['avg_headway'].mean()
a_avg = df_a['avg_headway'].mean()
c_avg = df_c['avg_headway'].mean()
e_avg = df_e['avg_headway'].mean()

print(f"\nMorning Rush Hour (7-9 AM) Average Headways:")
print(f"  A+C+E Combined: {ace_avg:.2f} minutes")
print(f"  A Train alone:  {a_avg:.2f} minutes")
print(f"  C Train alone:  {c_avg:.2f} minutes")
print(f"  E Train alone:  {e_avg:.2f} minutes")

print(f"\nService Improvement:")
print(f"  Combined service is {a_avg/ace_avg:.1f}x more frequent than A alone")
print(f"  Combined service is {c_avg/ace_avg:.1f}x more frequent than C alone")
print(f"  Combined service is {e_avg/ace_avg:.1f}x more frequent than E alone")

print("\nTest completed successfully!")
