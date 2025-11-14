#!/usr/bin/env python3
"""
Compare 6 train (local) vs 4 train (express) travel times.

The 6 train runs local on the Lexington Avenue Line, while the 4 train
runs express. This script compares their travel times on the shared express stops.
"""
import gtfs_kit as gk
import compare_lines as cl

# Load GTFS feed
feed = gk.read_feed("/Users/lennyphelan/Downloads/gtfs_subway.zip", dist_units="m")

# Compare 6 (local) vs 4 (express)
difference = cl.compare_lines(
    feed,
    local_route='6',
    express_route='4',
    service_id='Weekday'
)
