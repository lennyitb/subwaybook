#!/usr/bin/env python3
"""
Debug script to see the exact order before and after filtering/reversal.
"""
import gtfs_kit as gk
import travel_times as tt

# Load GTFS feed
feed = gk.read_feed("gtfs_subway.zip", dist_units="m")

route_id = 'A'
service_id = 'Weekday'

# Get station order for direction 1 (this is what we filter and then reverse)
canonical_order = tt.get_station_order(feed, route_id, 1, service_id)

print("Direction 1 canonical order (last 20 stations):")
for i, (stop_id, stop_name) in enumerate(canonical_order[-20:]):
    print(f"  {i+46}. {stop_name}")

# Filter to express stops
filtered_order = tt.filter_station_order_express(
    feed, canonical_order, route_id, 0, service_id,
    express_boroughs=['Manhattan', 'Brooklyn'],
    all_stops_boroughs=['Queens']
)

print(f"\nFiltered order (last 15 stations):")
for i, (stop_id, stop_name) in enumerate(filtered_order[-15:]):
    print(f"  {len(filtered_order)-15+i}. {stop_name}")

# Now reverse it (this is what display_bidirectional_matrix does)
inverted_order = list(reversed(filtered_order))

print(f"\nInverted order (first 15 stations - these become the rightmost columns):")
for i, (stop_id, stop_name) in enumerate(inverted_order[:15]):
    print(f"  {i}. {stop_name}")
