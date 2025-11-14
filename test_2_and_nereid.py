#!/usr/bin/env python3
"""
Test for combined headway analysis of 2 train and 5 trains to Nereid Av.
"""
import gtfs_kit as gk
import combined_headways as ch
import pandas as pd

# Load GTFS feed
print("Loading GTFS feed...")
feed = gk.read_feed("gtfs_subway.zip", dist_units="m")

print("\n" + "="*80)
print("COMBINED HEADWAY: 2 TRAIN + 5 TRAIN TO NEREID AV")
print("="*80)

# Direction 1: Trains heading to Manhattan
print("\n" + "="*80)
print("Direction 1: Trains to Manhattan")
print("="*80)
df_dir1 = ch.get_headway_dist_combined(feed, 1, '2', ('5', 'Nereid'), service_id='Weekday')
ch.print_headway_dist(df_dir1)

# Direction 0: Trains heading to the Bronx
print("\n" + "="*80)
print("Direction 0: Trains to the Bronx")
print("="*80)
df_dir0 = ch.get_headway_dist_combined(feed, 0, '2', ('5', 'Nereid'), service_id='Weekday')
ch.print_headway_dist(df_dir0)

# Morning rush hour comparison
print("\n" + "="*80)
print("COMPARISON SUMMARY")
print("="*80)

print("\nMorning Rush Hour (8 AM):")
dir1_8am = df_dir1[df_dir1['hour'] == 8].iloc[0]
dir0_8am = df_dir0[df_dir0['hour'] == 8].iloc[0]

dir1_8_hw = dir1_8am['avg_headway']
dir0_8_hw = dir0_8am['avg_headway']

print(f"  To Manhattan (Dir 1):  {dir1_8_hw:6.2f} min avg, {int(dir1_8am['num_trains']):3d} trains")
print(f"  To Bronx (Dir 0):      {dir0_8_hw:6.2f} min avg, {int(dir0_8am['num_trains']):3d} trains")

print("\nEvening Rush Hour (6 PM / 18:00):")
dir1_18 = df_dir1[df_dir1['hour'] == 18].iloc[0]
dir0_18 = df_dir0[df_dir0['hour'] == 18].iloc[0]

dir1_18_hw = dir1_18['avg_headway']
dir0_18_hw = dir0_18['avg_headway']

print(f"  To Manhattan (Dir 1):  {dir1_18_hw:6.2f} min avg, {int(dir1_18['num_trains']):3d} trains")
print(f"  To Bronx (Dir 0):      {dir0_18_hw:6.2f} min avg, {int(dir0_18['num_trains']):3d} trains")

print("\nMidday (12 PM / 12:00):")
dir1_12 = df_dir1[df_dir1['hour'] == 12].iloc[0]
dir0_12 = df_dir0[df_dir0['hour'] == 12].iloc[0]

dir1_12_hw = dir1_12['avg_headway']
dir0_12_hw = dir0_12['avg_headway']

print(f"  To Manhattan (Dir 1):  {dir1_12_hw:6.2f} min avg, {int(dir1_12['num_trains']):3d} trains")
print(f"  To Bronx (Dir 0):      {dir0_12_hw:6.2f} min avg, {int(dir0_12['num_trains']):3d} trains")

# Bonus: Morning rush hour detail (7-9 AM)
print("\n" + "="*80)
print("MORNING RUSH DETAIL (7-9 AM)")
print("="*80)

df_morning_to_manhattan = ch.get_headway_dist_combined(
    feed, 1, '2', ('5', 'Nereid'), service_id='Weekday', hour_range=(7, 9)
)
ch.print_headway_dist(df_morning_to_manhattan)

print("\nTest completed successfully!")
