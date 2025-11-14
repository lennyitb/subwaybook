#!/usr/bin/env python3
"""
Test for analyzing Rockaway Park branch headways in both directions.
"""
import gtfs_kit as gk
import combined_headways as ch

# Load GTFS feed
print("Loading GTFS feed...")
feed = gk.read_feed("gtfs_subway.zip", dist_units="m")

print("\n" + "="*80)
print("A TRAIN - ROCKAWAY PARK BRANCH ANALYSIS")
print("="*80)

# Direction 1: Trains going TO Rockaway Park
print("\n" + "="*80)
print("Direction 1: Trains TO Rockaway Park")
print("="*80)
df_to_rockaway_park = ch.get_headway_dist_branch(feed, 'A', 1, 'Rockaway Park', service_id='Weekday')
ch.print_headway_dist(df_to_rockaway_park)

# Direction 0: Trains coming FROM Rockaway Park
print("\n" + "="*80)
print("Direction 0: Trains FROM Rockaway Park")
print("="*80)
df_from_rockaway_park = ch.get_headway_dist_branch(feed, 'A', 0, 'Rockaway Park', service_id='Weekday')
ch.print_headway_dist(df_from_rockaway_park)

# Summary comparison
import pandas as pd

print("\n" + "="*80)
print("COMPARISON SUMMARY")
print("="*80)

print("\nMorning Rush Hour (8 AM):")
to_8am = df_to_rockaway_park[df_to_rockaway_park['hour'] == 8].iloc[0]
from_8am = df_from_rockaway_park[df_from_rockaway_park['hour'] == 8].iloc[0]

to_8_hw = to_8am['avg_headway']
from_8_hw = from_8am['avg_headway']
to_8_display = f"{to_8_hw:6.2f}" if pd.notna(to_8_hw) else "   N/A"
from_8_display = f"{from_8_hw:6.2f}" if pd.notna(from_8_hw) else "   N/A"

print(f"  TO Rockaway Park:    {to_8_display} min avg, {int(to_8am['num_trains']):3d} trains")
print(f"  FROM Rockaway Park:  {from_8_display} min avg, {int(from_8am['num_trains']):3d} trains")

print("\nEvening Rush Hour (6 PM / 18:00):")
to_18 = df_to_rockaway_park[df_to_rockaway_park['hour'] == 18].iloc[0]
from_18 = df_from_rockaway_park[df_from_rockaway_park['hour'] == 18].iloc[0]

to_18_hw = to_18['avg_headway']
from_18_hw = from_18['avg_headway']
to_18_display = f"{to_18_hw:6.2f}" if pd.notna(to_18_hw) else "   N/A"
from_18_display = f"{from_18_hw:6.2f}" if pd.notna(from_18_hw) else "   N/A"

print(f"  TO Rockaway Park:    {to_18_display} min avg, {int(to_18['num_trains']):3d} trains")
print(f"  FROM Rockaway Park:  {from_18_display} min avg, {int(from_18['num_trains']):3d} trains")

print("\nAfternoon (4 PM / 16:00):")
to_16 = df_to_rockaway_park[df_to_rockaway_park['hour'] == 16].iloc[0]
from_16 = df_from_rockaway_park[df_from_rockaway_park['hour'] == 16].iloc[0]

to_16_hw = to_16['avg_headway']
from_16_hw = from_16['avg_headway']
to_16_display = f"{to_16_hw:6.2f}" if pd.notna(to_16_hw) else "   N/A"
from_16_display = f"{from_16_hw:6.2f}" if pd.notna(from_16_hw) else "   N/A"

print(f"  TO Rockaway Park:    {to_16_display} min avg, {int(to_16['num_trains']):3d} trains")
print(f"  FROM Rockaway Park:  {from_16_display} min avg, {int(from_16['num_trains']):3d} trains")

print("\nMidnight (12 AM / 00:00):")
to_0 = df_to_rockaway_park[df_to_rockaway_park['hour'] == 0].iloc[0]
from_0 = df_from_rockaway_park[df_from_rockaway_park['hour'] == 0].iloc[0]

to_0_hw = to_0['avg_headway']
from_0_hw = from_0['avg_headway']
to_0_display = f"{to_0_hw:6.2f}" if pd.notna(to_0_hw) else "   N/A"
from_0_display = f"{from_0_hw:6.2f}" if pd.notna(from_0_hw) else "   N/A"

print(f"  TO Rockaway Park:    {to_0_display} min avg, {int(to_0['num_trains']):3d} trains")
print(f"  FROM Rockaway Park:  {from_0_display} min avg, {int(from_0['num_trains']):3d} trains")

print("\nTest completed successfully!")
