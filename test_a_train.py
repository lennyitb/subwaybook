#!/usr/bin/env python3
"""
Minimalist test script: A train travel time matrix.
"""
import gtfs_kit as gk
import travel_times as tt
import pandas as pd

# Set pandas display options to prevent truncation
pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', None)
pd.set_option('display.width', None)
pd.set_option('display.max_colwidth', None)

# Load GTFS feed
feed = gk.read_feed("gtfs_subway.zip", dist_units="m")

# Calculate A train travel times
route_id = 'A'
service_id = 'Weekday'

# Get station order from both directions to include all stops
station_order = tt.get_bidirectional_station_order(feed, route_id, service_id)

# Calculate and combine bidirectional matrix
# Filter to 7-9 AM hour range for morning rush hour analysis
combined = tt.display_bidirectional_matrix(feed, route_id, service_id, station_order, hour=(7, 9))

# Get direction names
direction_name_0 = tt.get_direction_name(feed, route_id, 0, service_id)
direction_name_1 = tt.get_direction_name(feed, route_id, 1, service_id)

# Write to text file instead of printing
output_txt = f'{route_id}_{service_id}_travel_times.txt'
with open(output_txt, 'w') as f:
    f.write(f"{'='*80}\n")
    f.write(f"{route_id} Train - {service_id} - Combined Directions\n")
    f.write(f"Travel Times (minutes)\n")
    f.write(f"{'='*80}\n\n")
    f.write(f"Upper triangle (above diagonal): {direction_name_0}\n")
    f.write(f"Lower triangle (below diagonal): {direction_name_1}\n")
    f.write(f"Diagonal: Same station = 0 minutes\n\n")
    f.write(combined.to_string())
    f.write("\n")

print(f"Matrix written to {output_txt}")

# Export CSV
combined.to_csv(f'{route_id}_{service_id}_travel_times.csv')
print(f"CSV exported to {route_id}_{service_id}_travel_times.csv")
