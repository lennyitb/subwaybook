#!/usr/bin/env python3
"""
Test for analyzing 5 train Nereid Av branch headways in both directions.
"""
import gtfs_kit as gk
import combined_headways as ch

# Load GTFS feed
print("Loading GTFS feed...")
feed = gk.read_feed("gtfs_subway.zip", dist_units="m")

print("\n" + "="*80)
print("5 TRAIN - NEREID AV BRANCH ANALYSIS")
print("="*80)

# Direction 0: Trains TO Nereid Av
print("\n" + "="*80)
print("Direction 0: Trains TO Nereid Av")
print("="*80)
df_to_nereid = ch.get_headway_dist_branch(feed, '5', 0, 'Nereid', service_id='Weekday')
ch.print_headway_dist(df_to_nereid)

# Direction 1: Trains FROM Nereid Av
print("\n" + "="*80)
print("Direction 1: Trains FROM Nereid Av")
print("="*80)
df_from_nereid = ch.get_headway_dist_branch(feed, '5', 1, 'Nereid', service_id='Weekday')
ch.print_headway_dist(df_from_nereid)

# Summary comparison
import pandas as pd

print("\n" + "="*80)
print("COMPARISON SUMMARY")
print("="*80)

print("\nMorning Rush Hour (8 AM):")
to_8am = df_to_nereid[df_to_nereid['hour'] == 8].iloc[0]
from_8am = df_from_nereid[df_from_nereid['hour'] == 8].iloc[0]

to_8_hw = to_8am['avg_headway']
from_8_hw = from_8am['avg_headway']
to_8_display = f"{to_8_hw:6.2f}" if pd.notna(to_8_hw) else "   N/A"
from_8_display = f"{from_8_hw:6.2f}" if pd.notna(from_8_hw) else "   N/A"

print(f"  TO Nereid Av:    {to_8_display} min avg, {int(to_8am['num_trains']):3d} trains")
print(f"  FROM Nereid Av:  {from_8_display} min avg, {int(from_8am['num_trains']):3d} trains")

print("\nEvening Rush Hour (6 PM / 18:00):")
to_18 = df_to_nereid[df_to_nereid['hour'] == 18].iloc[0]
from_18 = df_from_nereid[df_from_nereid['hour'] == 18].iloc[0]

to_18_hw = to_18['avg_headway']
from_18_hw = from_18['avg_headway']
to_18_display = f"{to_18_hw:6.2f}" if pd.notna(to_18_hw) else "   N/A"
from_18_display = f"{from_18_hw:6.2f}" if pd.notna(from_18_hw) else "   N/A"

print(f"  TO Nereid Av:    {to_18_display} min avg, {int(to_18['num_trains']):3d} trains")
print(f"  FROM Nereid Av:  {from_18_display} min avg, {int(from_18['num_trains']):3d} trains")

print("\nMidday (12 PM / 12:00):")
to_12 = df_to_nereid[df_to_nereid['hour'] == 12].iloc[0]
from_12 = df_from_nereid[df_from_nereid['hour'] == 12].iloc[0]

to_12_hw = to_12['avg_headway']
from_12_hw = from_12['avg_headway']
to_12_display = f"{to_12_hw:6.2f}" if pd.notna(to_12_hw) else "   N/A"
from_12_display = f"{from_12_hw:6.2f}" if pd.notna(from_12_hw) else "   N/A"

print(f"  TO Nereid Av:    {to_12_display} min avg, {int(to_12['num_trains']):3d} trains")
print(f"  FROM Nereid Av:  {from_12_display} min avg, {int(from_12['num_trains']):3d} trains")

print("\nTest completed successfully!")
