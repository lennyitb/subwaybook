#!/usr/bin/env python3
"""
Generate travel time matrix for C train using only A train express stops.

This creates a table showing C train travel times between the stations where
the A train runs express (the 26 stations from Euclid Av to Inwood-207 St).
"""
import gtfs_kit as gk
import travel_times as tt

# Load GTFS feed
feed = gk.read_feed("gtfs_subway.zip", dist_units="m")

route_id = 'C'
service_id = 'Weekday'

print(f"Generating travel time matrix for {route_id} train - using A express stops")
print("="*80)

# Define the A train express stops (from the trunk express list)
# These are the 26 stations from Euclid Av onwards with Manhattan/Brooklyn express filtering
a_express_stops = [
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
    ('A09', '168 St'),
    ('A07', '175 St'),
    ('A06', '181 St'),
    ('A05', '190 St'),
    ('A03', 'Dyckman St'),
    ('A02', 'Inwood-207 St')
]

print(f"\nUsing {len(a_express_stops)} A train express stops")
print("\nStations included:")
for i, (stop_id, stop_name) in enumerate(a_express_stops):
    print(f"  {i+1}. {stop_name}")

# Check which of these stops the C train actually serves
print("\n" + "="*80)
print("Checking which stops C train serves...")
print("="*80)

# Get C train's full station order
c_station_order = tt.get_station_order(feed, route_id, 0, service_id)
c_stop_ids = set([stop_id for stop_id, _ in c_station_order])

# Filter A express stops to only those served by C train
c_filtered_stops = []
for stop_id, stop_name in a_express_stops:
    if stop_id in c_stop_ids:
        c_filtered_stops.append((stop_id, stop_name))
    else:
        print(f"  C train does NOT serve: {stop_name} ({stop_id})")

print(f"\nC train serves {len(c_filtered_stops)} of the {len(a_express_stops)} A express stops")
print("\nC train stations (from A express list):")
for i, (stop_id, stop_name) in enumerate(c_filtered_stops):
    print(f"  {i+1}. {stop_name}")

# Calculate travel time matrices
print("\n" + "="*80)
print("Calculating travel time matrices...")
print("="*80)

matrix_dir0 = tt.calculate_travel_time_matrix(feed, route_id, 0, service_id, c_filtered_stops)
matrix_dir1 = tt.calculate_travel_time_matrix(feed, route_id, 1, service_id, c_filtered_stops)

if not matrix_dir0.empty and not matrix_dir1.empty:
    # Get direction names
    direction_name_0 = tt.get_direction_name(feed, route_id, 0, service_id)
    direction_name_1 = tt.get_direction_name(feed, route_id, 1, service_id)

    # Combine the matrices
    combined_matrix = tt.combine_bidirectional_matrix(matrix_dir0, matrix_dir1)

    # Print combined matrix
    tt.print_combined_travel_time_matrix(combined_matrix, route_id, service_id,
                                        direction_name_0, direction_name_1)

    # Export to CSV
    csv_filename = f'{route_id}_{service_id}_A_express_stops_travel_times.csv'
    combined_matrix.to_csv(csv_filename)
    print(f"\nExported to {csv_filename}")
else:
    print(f"Could not generate travel time matrix for {route_id} train")
