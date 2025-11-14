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
feed = gk.read_feed("/Users/lennyphelan/Downloads/gtfs_subway.zip", dist_units="m")

# Calculate A train travel times
route_id = 'A'
service_id = 'Weekday'

# Get station order from direction 1 (will be inverted for display)
canonical_order = tt.get_station_order(feed, route_id, 1, service_id)

# Filter to express stops only in Manhattan/Brooklyn
filtered_order = tt.filter_station_order_express(
    feed, canonical_order, route_id, 0, service_id,
    express_boroughs=['Manhattan', 'Brooklyn'],
    all_stops_boroughs=['Queens']
)

# Calculate and combine bidirectional matrix (inverted station order)
# Filter to 7-9 AM hour range for morning rush hour analysis
combined = tt.display_bidirectional_matrix(feed, route_id, service_id, filtered_order, hour=(7, 9))

# Get direction names
direction_name_0 = tt.get_direction_name(feed, route_id, 0, service_id)
direction_name_1 = tt.get_direction_name(feed, route_id, 1, service_id)

# Print
tt.print_combined_travel_time_matrix(combined, route_id, service_id,
                                    direction_name_0, direction_name_1)

# Export
combined.to_csv(f'{route_id}_{service_id}_travel_times.csv')
print(f"\nExported to {route_id}_{service_id}_travel_times.csv")
