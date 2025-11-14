#!/usr/bin/env python3
"""
Test script for the get_headway_dist() function.

Demonstrates the refactored interface that returns DataFrames
and uses a separate print function for formatting.
"""
import gtfs_kit as gk
import combined_headways as ch

# Load GTFS feed
print("Loading GTFS feed...")
feed = gk.read_feed("/Users/lennyphelan/Downloads/gtfs_subway.zip", dist_units="m")

# Example 1: Single line - Get DataFrame and print it
print("\n" + "=" * 100)
print("Example 1: Single Line - 4 train southbound")
print("=" * 100)

df_4 = ch.get_headway_dist(feed, 1, '4', service_id='Weekday')
ch.print_headway_dist(df_4)

# Show that we can also work with the DataFrame directly
print("\n" + "=" * 100)
print("Example 1b: Working with the DataFrame directly")
print("=" * 100)
print("\nDataFrame info:")
print(f"  - Route(s): {df_4.attrs['route_ids']}")
print(f"  - Direction: {df_4.attrs['direction_id']} ({df_4.attrs['direction_name']})")
print(f"  - Service: {df_4.attrs['service_id']}")
print(f"\nPeak hour (7 AM) stats:")
peak_hour = df_4[df_4['hour'] == 7].iloc[0]
print(f"  - Trains per hour: {peak_hour['num_trains']}")
print(f"  - Average headway: {peak_hour['avg_headway']:.2f} minutes")

# Example 2: Two lines combined
print("\n\n" + "=" * 100)
print("Example 2: Two Lines Combined - 2 and 3 trains southbound")
print("=" * 100)

df_23 = ch.get_headway_dist(feed, 1, '2', '3', service_id='Weekday')
ch.print_headway_dist(df_23)

# Example 3: Three lines combined
print("\n\n" + "=" * 100)
print("Example 3: Three Lines Combined - 4, 5, and 6 trains southbound")
print("=" * 100)

df_456 = ch.get_headway_dist(feed, 1, '4', '5', '6', service_id='Weekday')
ch.print_headway_dist(df_456)

# Example 4: Demonstrate exporting to CSV
print("\n\n" + "=" * 100)
print("Example 4: Export DataFrame to CSV")
print("=" * 100)

# Export the 4/5/6 combined data
csv_filename = '456_combined_headways_weekday.csv'
df_456.to_csv(csv_filename, index=False)
print(f"\nExported 4/5/6 combined headways to {csv_filename}")
print(f"Columns: {list(df_456.columns)}")
print(f"Metadata preserved in df.attrs: {df_456.attrs}")

# Example 5: Compare rush hour vs off-peak
print("\n\n" + "=" * 100)
print("Example 5: Compare rush hour vs off-peak for 4/5/6")
print("=" * 100)

morning_rush = df_456[df_456['hour'] == 7].iloc[0]
midday = df_456[df_456['hour'] == 12].iloc[0]
evening_rush = df_456[df_456['hour'] == 17].iloc[0]

print("\nHeadway comparison:")
print(f"  Morning rush (7 AM):  {morning_rush['avg_headway']:.2f} min avg ({morning_rush['num_trains']} trains)")
print(f"  Midday (12 PM):       {midday['avg_headway']:.2f} min avg ({midday['num_trains']} trains)")
print(f"  Evening rush (5 PM):  {evening_rush['avg_headway']:.2f} min avg ({evening_rush['num_trains']} trains)")
