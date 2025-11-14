#!/usr/bin/env python3
"""
Minimal test for get_headway_dist_branch() function.
Tests A train overall service and its three branches in BOTH directions.
"""
import gtfs_kit as gk
import combined_headways as ch

# Load GTFS feed
print("Loading GTFS feed...")
feed = gk.read_feed("gtfs_subway.zip", dist_units="m")

print("\n" + "#"*80)
print("# OUTBOUND DIRECTION (Direction 1 - to Queens)")
print("#"*80)

# Test 1: Overall A train service (all branches combined)
# Direction 1 = outbound from Manhattan (where the branches are)
print("\n" + "="*80)
print("TEST 1: Overall A train service (all branches) - Outbound")
print("="*80)
df_all_out = ch.get_headway_dist(feed, 1, 'A', service_id='Weekday')
ch.print_headway_dist(df_all_out)

# Test 2: Lefferts branch (using "Ozone" as truncated name)
print("\n" + "="*80)
print("TEST 2: A train to Lefferts/Ozone Park branch - Outbound")
print("="*80)
df_ozone_out = ch.get_headway_dist_branch(feed, 'A', 1, 'Ozone', service_id='Weekday')
ch.print_headway_dist(df_ozone_out)

# Test 3: Rockaway Park branch
print("\n" + "="*80)
print("TEST 3: A train to Rockaway Park branch - Outbound")
print("="*80)
df_rockaway_park_out = ch.get_headway_dist_branch(feed, 'A', 1, 'Rockaway Park', service_id='Weekday')
ch.print_headway_dist(df_rockaway_park_out)

# Test 4: Far Rockaway branch
print("\n" + "="*80)
print("TEST 4: A train to Far Rockaway branch - Outbound")
print("="*80)
df_far_rockaway_out = ch.get_headway_dist_branch(feed, 'A', 1, 'Far Rockaway', service_id='Weekday')
ch.print_headway_dist(df_far_rockaway_out)

print("\n\n" + "#"*80)
print("# INBOUND DIRECTION (Direction 0 - to Manhattan)")
print("#"*80)

# Test 5: Overall A train service - Inbound
print("\n" + "="*80)
print("TEST 5: Overall A train service (all branches) - Inbound")
print("="*80)
df_all_in = ch.get_headway_dist(feed, 0, 'A', service_id='Weekday')
ch.print_headway_dist(df_all_in)

# Test 6: Lefferts branch - Inbound (trains FROM Lefferts)
print("\n" + "="*80)
print("TEST 6: A train from Lefferts/Ozone Park branch - Inbound")
print("="*80)
df_ozone_in = ch.get_headway_dist_branch(feed, 'A', 0, 'Ozone', service_id='Weekday')
ch.print_headway_dist(df_ozone_in)

# Test 7: Rockaway Park branch - Inbound
print("\n" + "="*80)
print("TEST 7: A train from Rockaway Park branch - Inbound")
print("="*80)
df_rockaway_park_in = ch.get_headway_dist_branch(feed, 'A', 0, 'Rockaway Park', service_id='Weekday')
ch.print_headway_dist(df_rockaway_park_in)

# Test 8: Far Rockaway branch - Inbound
print("\n" + "="*80)
print("TEST 8: A train from Far Rockaway branch - Inbound")
print("="*80)
df_far_rockaway_in = ch.get_headway_dist_branch(feed, 'A', 0, 'Far Rockaway', service_id='Weekday')
ch.print_headway_dist(df_far_rockaway_in)

# Summary comparison at 8 AM (rush hour)
import pandas as pd

print("\n" + "="*80)
print("SUMMARY: Rush hour comparison (8 AM)")
print("="*80)

# Outbound (to Queens)
all_out_8am = df_all_out[df_all_out['hour'] == 8].iloc[0]
ozone_out_8am = df_ozone_out[df_ozone_out['hour'] == 8].iloc[0]
rockaway_park_out_8am = df_rockaway_park_out[df_rockaway_park_out['hour'] == 8].iloc[0]
far_rockaway_out_8am = df_far_rockaway_out[df_far_rockaway_out['hour'] == 8].iloc[0]

# Inbound (to Manhattan)
all_in_8am = df_all_in[df_all_in['hour'] == 8].iloc[0]
ozone_in_8am = df_ozone_in[df_ozone_in['hour'] == 8].iloc[0]
rockaway_park_in_8am = df_rockaway_park_in[df_rockaway_park_in['hour'] == 8].iloc[0]
far_rockaway_in_8am = df_far_rockaway_in[df_far_rockaway_in['hour'] == 8].iloc[0]

print("\nOUTBOUND (to Queens):")
print(f"  All A trains:        {all_out_8am['avg_headway']:6.2f} min avg, {int(all_out_8am['num_trains']):3d} trains")
print(f"  Lefferts/Ozone:      {ozone_out_8am['avg_headway']:6.2f} min avg, {int(ozone_out_8am['num_trains']):3d} trains")
rp_out_hw = rockaway_park_out_8am['avg_headway']
rp_out_display = f"{rp_out_hw:6.2f}" if pd.notna(rp_out_hw) else "   N/A"
print(f"  Rockaway Park:       {rp_out_display} min avg, {int(rockaway_park_out_8am['num_trains']):3d} trains")
print(f"  Far Rockaway:        {far_rockaway_out_8am['avg_headway']:6.2f} min avg, {int(far_rockaway_out_8am['num_trains']):3d} trains")

print("\nINBOUND (to Manhattan):")
print(f"  All A trains:        {all_in_8am['avg_headway']:6.2f} min avg, {int(all_in_8am['num_trains']):3d} trains")
print(f"  Lefferts/Ozone:      {ozone_in_8am['avg_headway']:6.2f} min avg, {int(ozone_in_8am['num_trains']):3d} trains")
rp_in_hw = rockaway_park_in_8am['avg_headway']
rp_in_display = f"{rp_in_hw:6.2f}" if pd.notna(rp_in_hw) else "   N/A"
print(f"  Rockaway Park:       {rp_in_display} min avg, {int(rockaway_park_in_8am['num_trains']):3d} trains")
print(f"  Far Rockaway:        {far_rockaway_in_8am['avg_headway']:6.2f} min avg, {int(far_rockaway_in_8am['num_trains']):3d} trains")

print("\nTest completed successfully!")
