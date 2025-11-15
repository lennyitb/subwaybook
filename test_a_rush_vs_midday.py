#!/usr/bin/env python3
"""
Compare A train travel times between midday (10 AM - 3 PM) and late night (midnight - 6 AM).
"""
import gtfs_kit as gk
import travel_times as tt
import pandas as pd
import numpy as np

# Load GTFS feed
print("Loading GTFS feed...")
feed = gk.read_feed("gtfs_subway.zip", dist_units="m")

route_id = 'A'
service_id = 'Weekday'
direction_id = 1  # Typical display direction

print("\n" + "="*80)
print(f"A Train - Midday (10 AM - 3 PM) vs Late Night (Midnight - 6 AM)")
print("="*80)

# Get station order with express filtering
canonical_order = tt.get_station_order(feed, route_id, direction_id, service_id)
filtered_order = tt.filter_station_order_express(
    feed, canonical_order, route_id, 0, service_id,
    express_boroughs=['Manhattan', 'Brooklyn'],
    all_stops_boroughs=['Queens']
)

print(f"\nAnalyzing {len(filtered_order)} express stops...")

# Calculate travel times for midday (10 AM - 3 PM)
print("\nCalculating midday travel times (10 AM - 3 PM)...")
matrix_midday = tt.display_bidirectional_matrix(
    feed, route_id, service_id, filtered_order, hour=(10, 15)
)

# Calculate travel times for late night (midnight - 6 AM)
print("Calculating late night travel times (Midnight - 6 AM)...")
matrix_late_night = tt.display_bidirectional_matrix(
    feed, route_id, service_id, filtered_order, hour=(0, 6)
)

# Calculate the difference (midday - late_night)
# Positive values mean midday is slower (late night is faster)
print("\nCalculating differences...")

# Preserve the original station order from filtered_order
station_names = [name for _, name in filtered_order]

# Reindex matrices to preserve the route order (not alphabetical)
matrix_midday = matrix_midday.reindex(index=station_names, columns=station_names)
matrix_late_night = matrix_late_night.reindex(index=station_names, columns=station_names)

diff_matrix = matrix_midday - matrix_late_night

# Print summary statistics
print("\n" + "="*80)
print("SUMMARY STATISTICS")
print("="*80)

# Get non-zero, non-NaN differences
valid_diffs = diff_matrix.values[~np.isnan(diff_matrix.values) & (diff_matrix.values != 0)]

if len(valid_diffs) > 0:
    print(f"\nTotal station pairs analyzed: {len(valid_diffs)}")
    print(f"\nAverage difference: {valid_diffs.mean():.2f} minutes")
    print(f"Maximum midday delay (vs late night): {valid_diffs.max():.2f} minutes")
    print(f"Maximum late night delay (vs midday): {valid_diffs.min():.2f} minutes")
    print(f"Median difference: {np.median(valid_diffs):.2f} minutes")

    # Count how many trips are slower/faster during midday vs late night
    slower_midday = np.sum(valid_diffs > 0)
    faster_midday = np.sum(valid_diffs < 0)
    print(f"\nStation pairs slower during midday: {slower_midday} ({100*slower_midday/len(valid_diffs):.1f}%)")
    print(f"Station pairs faster during midday (slower late night): {faster_midday} ({100*faster_midday/len(valid_diffs):.1f}%)")

# Display the difference matrix
print("\n" + "="*80)
print("TRAVEL TIME DIFFERENCE MATRIX")
print("="*80)
print("Midday (10 AM - 3 PM) - Late Night (Midnight - 6 AM)")
print("Positive values = slower during midday (faster late night)")
print("Negative values = faster during midday (slower late night)")
print("="*80 + "\n")

pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
pd.set_option('display.float_format', '{:+.1f}'.format)

print(diff_matrix.to_string())

# Export all three matrices
midday_filename = f'{route_id}_midday_10am-3pm_{service_id}.csv'
late_night_filename = f'{route_id}_late_night_midnight-6am_{service_id}.csv'
diff_filename = f'{route_id}_midday_vs_late_night_difference_{service_id}.csv'

matrix_midday.to_csv(midday_filename)
matrix_late_night.to_csv(late_night_filename)
diff_matrix.to_csv(diff_filename)

print("\n" + "="*80)
print("EXPORTED FILES")
print("="*80)
print(f"Midday matrix: {midday_filename}")
print(f"Late night matrix: {late_night_filename}")
print(f"Difference matrix: {diff_filename}")
print("\nTest completed successfully!")
