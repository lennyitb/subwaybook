#!/usr/bin/env python3
"""
Test for analyzing 7X (7 Express) headways in both directions.
"""
import gtfs_kit as gk
import combined_headways as ch

# Load GTFS feed
print("Loading GTFS feed...")
feed = gk.read_feed("gtfs_subway.zip", dist_units="m")

print("\n" + "="*80)
print("7X (7 EXPRESS) ANALYSIS")
print("="*80)

# Direction 0
print("\n" + "="*80)
print("Direction 0")
print("="*80)
df_dir0 = ch.get_headway_dist(feed, 0, '7X', service_id='Weekday')
ch.print_headway_dist(df_dir0)

# Direction 1
print("\n" + "="*80)
print("Direction 1")
print("="*80)
df_dir1 = ch.get_headway_dist(feed, 1, '7X', service_id='Weekday')
ch.print_headway_dist(df_dir1)

# Summary comparison
import pandas as pd

print("\n" + "="*80)
print("COMPARISON SUMMARY")
print("="*80)

print("\nMorning Rush Hour (8 AM):")
dir0_8am = df_dir0[df_dir0['hour'] == 8].iloc[0]
dir1_8am = df_dir1[df_dir1['hour'] == 8].iloc[0]

dir0_8_hw = dir0_8am['avg_headway']
dir1_8_hw = dir1_8am['avg_headway']
dir0_8_display = f"{dir0_8_hw:6.2f}" if pd.notna(dir0_8_hw) else "   N/A"
dir1_8_display = f"{dir1_8_hw:6.2f}" if pd.notna(dir1_8_hw) else "   N/A"

print(f"  Direction 0:  {dir0_8_display} min avg, {int(dir0_8am['num_trains']):3d} trains")
print(f"  Direction 1:  {dir1_8_display} min avg, {int(dir1_8am['num_trains']):3d} trains")

print("\nEvening Rush Hour (6 PM / 18:00):")
dir0_18 = df_dir0[df_dir0['hour'] == 18].iloc[0]
dir1_18 = df_dir1[df_dir1['hour'] == 18].iloc[0]

dir0_18_hw = dir0_18['avg_headway']
dir1_18_hw = dir1_18['avg_headway']
dir0_18_display = f"{dir0_18_hw:6.2f}" if pd.notna(dir0_18_hw) else "   N/A"
dir1_18_display = f"{dir1_18_hw:6.2f}" if pd.notna(dir1_18_hw) else "   N/A"

print(f"  Direction 0:  {dir0_18_display} min avg, {int(dir0_18['num_trains']):3d} trains")
print(f"  Direction 1:  {dir1_18_display} min avg, {int(dir1_18['num_trains']):3d} trains")

print("\nMidday (12 PM / 12:00):")
dir0_12 = df_dir0[df_dir0['hour'] == 12].iloc[0]
dir1_12 = df_dir1[df_dir1['hour'] == 12].iloc[0]

dir0_12_hw = dir0_12['avg_headway']
dir1_12_hw = dir1_12['avg_headway']
dir0_12_display = f"{dir0_12_hw:6.2f}" if pd.notna(dir0_12_hw) else "   N/A"
dir1_12_display = f"{dir1_12_hw:6.2f}" if pd.notna(dir1_12_hw) else "   N/A"

print(f"  Direction 0:  {dir0_12_display} min avg, {int(dir0_12['num_trains']):3d} trains")
print(f"  Direction 1:  {dir1_12_display} min avg, {int(dir1_12['num_trains']):3d} trains")

print("\nTest completed successfully!")
