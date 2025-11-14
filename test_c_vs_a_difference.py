#!/usr/bin/env python3
"""
Generate a travel time difference matrix comparing C train vs A train.

Shows how much longer (or shorter) the C train takes compared to the A train
for the same origin-destination pairs, using only the express stops they both serve.

Result: C train time minus A train time (positive = C is slower, negative = C is faster)
"""
import gtfs_kit as gk
import travel_times as tt
import pandas as pd
import numpy as np

# Load GTFS feed
feed = gk.read_feed("gtfs_subway.zip", dist_units="m")

service_id = 'Weekday'

print("Generating C vs A travel time difference matrix")
print("="*80)

# Define the A train express stops that C also serves (21 stations)
# These are the stops from Euclid Av to 168 St (C's northern terminal)
shared_express_stops = [
    ('A55', 'Euclid Av'),
    ('A54', 'Shepherd Av'),
    ('A53', 'Van Siclen Av'),
    ('A52', 'Liberty Av'),
    ('A51', 'Broadway Junction'),
    ('A46', 'Utica Av'),
    ('A44', 'Nostrand Av'),
    ('A42', 'Hoyt-Schermerhorn Sts'),
    ('A41', 'Jay St-MetroTech'),
    ('A40', 'High St'),
    ('A38', 'Fulton St'),
    ('A36', 'Chambers St'),
    ('A34', 'Canal St'),
    ('A32', 'W 4 St-Wash Sq'),
    ('A31', '14 St'),
    ('A28', '34 St-Penn Station'),
    ('A27', '42 St-Port Authority Bus Terminal'),
    ('A24', '59 St-Columbus Circle'),
    ('A15', '125 St'),
    ('A12', '145 St'),
    ('A09', '168 St')
]

print(f"\nUsing {len(shared_express_stops)} shared express stops")
print("\nStations:")
for i, (stop_id, stop_name) in enumerate(shared_express_stops):
    print(f"  {i+1}. {stop_name}")

# Calculate A train matrices
print("\n" + "="*80)
print("Calculating A train travel times...")
print("="*80)

a_matrix_dir0 = tt.calculate_travel_time_matrix(feed, 'A', 0, service_id, shared_express_stops)
a_matrix_dir1 = tt.calculate_travel_time_matrix(feed, 'A', 1, service_id, shared_express_stops)
a_combined = tt.combine_bidirectional_matrix(a_matrix_dir0, a_matrix_dir1)

print("A train matrix calculated")

# Calculate C train matrices
print("\n" + "="*80)
print("Calculating C train travel times...")
print("="*80)

c_matrix_dir0 = tt.calculate_travel_time_matrix(feed, 'C', 0, service_id, shared_express_stops)
c_matrix_dir1 = tt.calculate_travel_time_matrix(feed, 'C', 1, service_id, shared_express_stops)
c_combined = tt.combine_bidirectional_matrix(c_matrix_dir0, c_matrix_dir1)

print("C train matrix calculated")

# Calculate difference: C minus A
print("\n" + "="*80)
print("Calculating difference (C - A)...")
print("="*80)

difference_matrix = c_combined - a_combined

# Print the difference matrix
print("\n" + "="*80)
print("C Train vs A Train - Travel Time Difference (minutes)")
print("="*80)
print("\nPositive values = C train is SLOWER")
print("Negative values = C train is FASTER")
print("Zero/NaN = Same time or no data")
print()

# Set pandas display options
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
pd.set_option('display.max_colwidth', None)
pd.set_option('display.float_format', lambda x: f'{x:6.1f}')

print(difference_matrix)

# Export to CSV
csv_filename = 'C_vs_A_difference_Weekday.csv'
difference_matrix.to_csv(csv_filename)
print(f"\nExported to {csv_filename}")

# Print some interesting statistics
print("\n" + "="*80)
print("Statistics")
print("="*80)

# Flatten the matrix and remove diagonal (0 values) and NaN
values = difference_matrix.values.flatten()
values = values[~np.isnan(values)]
values = values[values != 0]  # Remove same-station (diagonal) values

if len(values) > 0:
    print(f"\nTotal origin-destination pairs analyzed: {len(values)}")
    print(f"Average difference: {np.mean(values):.2f} minutes")
    print(f"Maximum difference (C slower): {np.max(values):.2f} minutes")
    print(f"Minimum difference (C faster): {np.min(values):.2f} minutes")
    print(f"Median difference: {np.median(values):.2f} minutes")

    # Count how many times C is faster/slower
    c_slower = np.sum(values > 0)
    c_faster = np.sum(values < 0)
    same_time = np.sum(values == 0)

    print(f"\nC train is slower: {c_slower} pairs ({100*c_slower/len(values):.1f}%)")
    print(f"C train is faster: {c_faster} pairs ({100*c_faster/len(values):.1f}%)")
    if same_time > 0:
        print(f"Same time: {same_time} pairs ({100*same_time/len(values):.1f}%)")
