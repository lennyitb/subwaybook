#!/usr/bin/env python3
"""
Test for analyzing Far Rockaway branch headways in both directions.
"""
import gtfs_kit as gk
import combined_headways as ch

# Load GTFS feed
print("Loading GTFS feed...")
feed = gk.read_feed("gtfs_subway.zip", dist_units="m")

print("\n" + "="*80)
print("A TRAIN - FAR ROCKAWAY BRANCH ANALYSIS")
print("="*80)

# Direction 1: Trains going TO Far Rockaway
print("\n" + "="*80)
print("Direction 1: Trains TO Far Rockaway")
print("="*80)
df_to_far_rockaway = ch.get_headway_dist_branch(feed, 'A', 1, 'Far Rockaway', service_id='Weekday')
ch.print_headway_dist(df_to_far_rockaway)

# Direction 0: Trains coming FROM Far Rockaway
print("\n" + "="*80)
print("Direction 0: Trains FROM Far Rockaway")
print("="*80)
df_from_far_rockaway = ch.get_headway_dist_branch(feed, 'A', 0, 'Far Rockaway', service_id='Weekday')
ch.print_headway_dist(df_from_far_rockaway)

# Summary comparison
import pandas as pd

print("\n" + "="*80)
print("COMPARISON SUMMARY")
print("="*80)

print("\nMorning Rush Hour (8 AM):")
to_8am = df_to_far_rockaway[df_to_far_rockaway['hour'] == 8].iloc[0]
from_8am = df_from_far_rockaway[df_from_far_rockaway['hour'] == 8].iloc[0]

print(f"  TO Far Rockaway:    {to_8am['avg_headway']:6.2f} min avg, {int(to_8am['num_trains']):3d} trains")
print(f"  FROM Far Rockaway:  {from_8am['avg_headway']:6.2f} min avg, {int(from_8am['num_trains']):3d} trains")

print("\nEvening Rush Hour (6 PM / 18:00):")
to_18 = df_to_far_rockaway[df_to_far_rockaway['hour'] == 18].iloc[0]
from_18 = df_from_far_rockaway[df_from_far_rockaway['hour'] == 18].iloc[0]

print(f"  TO Far Rockaway:    {to_18['avg_headway']:6.2f} min avg, {int(to_18['num_trains']):3d} trains")
print(f"  FROM Far Rockaway:  {from_18['avg_headway']:6.2f} min avg, {int(from_18['num_trains']):3d} trains")

print("\nMidnight (12 AM / 00:00):")
to_0 = df_to_far_rockaway[df_to_far_rockaway['hour'] == 0].iloc[0]
from_0 = df_from_far_rockaway[df_from_far_rockaway['hour'] == 0].iloc[0]

to_0_hw = to_0['avg_headway']
from_0_hw = from_0['avg_headway']
to_0_display = f"{to_0_hw:6.2f}" if pd.notna(to_0_hw) else "   N/A"
from_0_display = f"{from_0_hw:6.2f}" if pd.notna(from_0_hw) else "   N/A"

print(f"  TO Far Rockaway:    {to_0_display} min avg, {int(to_0['num_trains']):3d} trains")
print(f"  FROM Far Rockaway:  {from_0_display} min avg, {int(from_0['num_trains']):3d} trains")

print("\nTest completed successfully!")
