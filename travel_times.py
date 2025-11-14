#!/usr/bin/env python3
"""
Generate travel time matrices for subway routes.

Creates a table showing travel times between all pairs of stations on a route.
Rows = origin stations, Columns = destination stations, Values = travel time in minutes
"""
import gtfs_kit as gk
import pandas as pd
import numpy as np
from collections import defaultdict
import os


def identify_branches(feed, route_id, direction_id, service_id='Weekday'):
    """
    Identify branches for a multi-branch route.

    Returns information about where the route branches and the terminals.

    Parameters:
    -----------
    feed : gtfs_kit.Feed
        A GTFS feed object loaded with gtfs_kit
    route_id : str
        The route ID
    direction_id : int
        Direction ID (0 or 1)
    service_id : str, default='Weekday'
        Service ID to filter by

    Returns:
    --------
    tuple
        (branch_point_stop_id, branches_info)
        branches_info is a list of dicts with 'terminal_id', 'terminal_name', 'trip_count', 'stop_count'
    """
    trips = feed.trips[
        (feed.trips['route_id'] == route_id) &
        (feed.trips['direction_id'] == direction_id) &
        (feed.trips['service_id'] == service_id)
    ].copy()

    if trips.empty:
        return None, []

    stop_times = feed.stop_times[feed.stop_times['trip_id'].isin(trips['trip_id'])].copy()
    stop_times = stop_times.sort_values(['trip_id', 'stop_sequence'])

    # Get terminal stops for each trip
    terminals = stop_times.groupby('trip_id').last().reset_index()
    terminal_counts = terminals['stop_id'].value_counts()

    # If only one terminal, no branching
    if len(terminal_counts) == 1:
        return None, []

    # Analyze each branch
    branches_info = []
    for terminal_id, trip_count in terminal_counts.items():
        # Get trips going to this terminal
        terminal_trips = terminals[terminals['stop_id'] == terminal_id]['trip_id'].tolist()

        # Get the stop count for the longest trip to this terminal
        terminal_stop_times = stop_times[stop_times['trip_id'].isin(terminal_trips)]
        stop_counts = terminal_stop_times.groupby('trip_id').size()
        max_stops = stop_counts.max()

        # Get terminal name
        terminal_name = feed.stops[feed.stops['stop_id'] == terminal_id]['stop_name'].values
        terminal_name = terminal_name[0] if len(terminal_name) > 0 else terminal_id

        branches_info.append({
            'terminal_id': terminal_id,
            'terminal_name': terminal_name,
            'trip_count': trip_count,
            'stop_count': max_stops
        })

    # Sort branches: by trip count (descending), then by stop count (ascending)
    # This puts full-time branches first, shorter ones before longer ones
    branches_info.sort(key=lambda x: (-x['trip_count'], x['stop_count']))

    # Find branch point (last common stop)
    trips_by_terminal = {}
    for terminal_id in terminal_counts.index:
        terminal_trip_ids = terminals[terminals['stop_id'] == terminal_id]['trip_id'].tolist()
        trips_by_terminal[terminal_id] = terminal_trip_ids

    common_stops = None
    for terminal_id, trip_ids in trips_by_terminal.items():
        sample_trip = trip_ids[0]
        trip_stops = stop_times[stop_times['trip_id'] == sample_trip].sort_values('stop_sequence')
        trip_stop_ids = set(trip_stops['stop_id'].tolist())

        if common_stops is None:
            common_stops = trip_stop_ids
        else:
            common_stops = common_stops.intersection(trip_stop_ids)

    branch_point = None
    if common_stops:
        sample_trip = terminals['trip_id'].iloc[0]
        trip_stops = stop_times[stop_times['trip_id'] == sample_trip].sort_values('stop_sequence')
        common_in_sequence = trip_stops[trip_stops['stop_id'].isin(common_stops)]
        if not common_in_sequence.empty:
            branch_point = common_in_sequence['stop_id'].iloc[-1]

    return branch_point, branches_info


def normalize_stop_id(feed, stop_id):
    """
    Normalize a stop ID to its parent station.

    In GTFS, stops like H11N and H11S are different platforms at the same station H11.
    This function returns the parent station ID if it exists, otherwise the stop ID itself.
    """
    stop_row = feed.stops[feed.stops['stop_id'] == stop_id]
    if stop_row.empty:
        return stop_id

    parent = stop_row['parent_station'].values[0]
    if pd.notna(parent):
        return parent
    return stop_id


def get_station_order(feed, route_id, direction_id, service_id='Weekday'):
    """
    Get the canonical ordering of stations for a route/direction.

    For branched routes, lists the trunk first, then branches in order:
    full-time branches (by ascending length), then part-time branches.

    Parameters:
    -----------
    feed : gtfs_kit.Feed
        A GTFS feed object loaded with gtfs_kit
    route_id : str
        The route ID (e.g., 'A', 'L', '7')
    direction_id : int
        Direction ID (0 or 1)
    service_id : str, default='Weekday'
        Service ID to filter by

    Returns:
    --------
    list
        Ordered list of (stop_id, stop_name) tuples
    """
    trips = feed.trips[
        (feed.trips['route_id'] == route_id) &
        (feed.trips['direction_id'] == direction_id) &
        (feed.trips['service_id'] == service_id)
    ].copy()

    if trips.empty:
        return []

    # Check for branches
    branch_point, branches_info = identify_branches(feed, route_id, direction_id, service_id)

    stop_times = feed.stop_times[feed.stop_times['trip_id'].isin(trips['trip_id'])].copy()
    stop_times = stop_times.sort_values(['trip_id', 'stop_sequence'])

    if not branches_info:
        # No branches - simple case
        stop_counts = stop_times.groupby('trip_id').size()
        max_stops_trip_id = stop_counts.idxmax()
        trip_stops = stop_times[stop_times['trip_id'] == max_stops_trip_id].sort_values('stop_sequence')

        station_order = []
        seen = set()
        for stop_id in trip_stops['stop_id']:
            # Normalize to parent station
            normalized_id = normalize_stop_id(feed, stop_id)
            if normalized_id not in seen:
                stop_name = feed.stops[feed.stops['stop_id'] == normalized_id]['stop_name'].values
                if len(stop_name) > 0:
                    station_order.append((normalized_id, stop_name[0]))
                    seen.add(normalized_id)
        return station_order

    # Multi-branch route
    # Get the trunk (common part) - use first branch's trip up to branch point
    first_branch_terminal = branches_info[0]['terminal_id']
    terminals = stop_times.groupby('trip_id').last().reset_index()
    sample_trip_id = terminals[terminals['stop_id'] == first_branch_terminal]['trip_id'].iloc[0]
    sample_trip_stops = stop_times[stop_times['trip_id'] == sample_trip_id].sort_values('stop_sequence')

    trunk_stops = []
    if branch_point:
        trunk_stops = sample_trip_stops[sample_trip_stops['stop_id'] != branch_point]['stop_id'].tolist()
        # Include branch point in trunk
        branch_point_seq = sample_trip_stops[sample_trip_stops['stop_id'] == branch_point]
        if not branch_point_seq.empty:
            trunk_stops = sample_trip_stops[
                sample_trip_stops['stop_sequence'] <= branch_point_seq.iloc[0]['stop_sequence']
            ]['stop_id'].tolist()

    # Build complete station list
    all_stops = []
    seen_stops = set()

    # Add trunk stops
    for stop_id in trunk_stops:
        normalized_id = normalize_stop_id(feed, stop_id)
        if normalized_id not in seen_stops:
            stop_name = feed.stops[feed.stops['stop_id'] == normalized_id]['stop_name'].values
            if len(stop_name) > 0:
                all_stops.append((normalized_id, stop_name[0]))
                seen_stops.add(normalized_id)

    # Add each branch
    for branch in branches_info:
        # Get a trip to this terminal with the most stops
        terminals = stop_times.groupby('trip_id').last().reset_index()
        branch_trip_ids = terminals[terminals['stop_id'] == branch['terminal_id']]['trip_id'].tolist()
        branch_stop_times = stop_times[stop_times['trip_id'].isin(branch_trip_ids)]
        branch_stop_counts = branch_stop_times.groupby('trip_id').size()
        branch_max_trip = branch_stop_counts.idxmax()

        branch_stops = stop_times[stop_times['trip_id'] == branch_max_trip].sort_values('stop_sequence')

        # Add stops after the branch point
        for stop_id in branch_stops['stop_id']:
            normalized_id = normalize_stop_id(feed, stop_id)
            if normalized_id not in seen_stops:
                stop_name = feed.stops[feed.stops['stop_id'] == normalized_id]['stop_name'].values
                if len(stop_name) > 0:
                    all_stops.append((normalized_id, stop_name[0]))
                    seen_stops.add(normalized_id)

    return all_stops


def filter_station_order_express(feed, station_order, route_id, direction_id, service_id='Weekday',
                                  express_boroughs=None, all_stops_boroughs=None):
    """
    Filter station order to show only express stops in certain boroughs.

    Parameters:
    -----------
    feed : gtfs_kit.Feed
        A GTFS feed object loaded with gtfs_kit
    station_order : list
        Full station order from get_station_order()
    route_id : str
        The route ID
    direction_id : int
        Direction ID (0 or 1)
    service_id : str, default='Weekday'
        Service ID to filter by
    express_boroughs : list, optional
        List of borough names where only express stops should be shown
        (e.g., ['Manhattan', 'Brooklyn'])
    all_stops_boroughs : list, optional
        List of borough names where all stops should be shown
        (e.g., ['Queens'])

    Returns:
    --------
    list
        Filtered station order (stop_id, stop_name) tuples
    """
    if not express_boroughs:
        return station_order

    # Import express_local module to get borough mapping
    import express_local as el

    # Create borough mapping
    stop_boroughs = el.create_stop_borough_mapping(feed)
    stop_borough_map = dict(zip(stop_boroughs['stop_id'], stop_boroughs['borough']))

    # Get express/local classification for this route
    patterns = el.analyze_route_express_patterns(feed, route_id, direction_id, service_id)

    if patterns.empty:
        return station_order

    # Find which stops have express service
    express_stops = set()

    for _, row in patterns.iterrows():
        trip_id = row['trip_id']

        # Check if this trip runs express in any of the express_boroughs
        is_express_trip = False
        for borough in express_boroughs:
            if borough in row and row[borough] == 'express':
                is_express_trip = True
                break

        if is_express_trip:
            # Get stops for this express trip
            stop_times = feed.stop_times[feed.stop_times['trip_id'] == trip_id]
            for stop_id in stop_times['stop_id']:
                normalized_stop_id = normalize_stop_id(feed, stop_id)
                express_stops.add(normalized_stop_id)

    # Filter station order
    filtered_order = []
    for stop_id, stop_name in station_order:
        borough = stop_borough_map.get(stop_id)

        # Include if:
        # 1. In all_stops_boroughs (show all stops), OR
        # 2. In express_boroughs AND is an express stop, OR
        # 3. Not in any specified borough (include by default)
        if all_stops_boroughs and borough in all_stops_boroughs:
            # Always include stops in all_stops_boroughs
            filtered_order.append((stop_id, stop_name))
        elif express_boroughs and borough in express_boroughs:
            # Only include if it's an express stop
            if stop_id in express_stops:
                filtered_order.append((stop_id, stop_name))
        elif borough not in (express_boroughs or []) and borough not in (all_stops_boroughs or []):
            # Not in any specified borough - include by default
            filtered_order.append((stop_id, stop_name))

    return filtered_order


def calculate_travel_time_matrix(feed, route_id, direction_id, service_id='Weekday', canonical_station_order=None):
    """
    Calculate a travel time matrix for a route.

    For each pair of stations (origin, destination), calculates the average
    travel time across all trips that serve both stations.

    Parameters:
    -----------
    feed : gtfs_kit.Feed
        A GTFS feed object loaded with gtfs_kit
    route_id : str
        The route ID (e.g., 'A', 'L', '7')
    direction_id : int
        Direction ID (0 or 1)
    service_id : str, default='Weekday'
        Service ID to filter by
    canonical_station_order : list, optional
        Pre-determined station order to use. If None, will determine from this direction.

    Returns:
    --------
    pd.DataFrame
        Travel time matrix with station names as both row and column indices.
        Values are travel times in minutes (float).
        NaN indicates no direct service between those stations.
    """
    # Get station ordering
    if canonical_station_order is None:
        station_order = get_station_order(feed, route_id, direction_id, service_id)
    else:
        station_order = canonical_station_order

    if not station_order:
        return pd.DataFrame()

    stop_ids = [s[0] for s in station_order]
    stop_names = [s[1] for s in station_order]

    # Get all trips for this route/direction/service
    trips = feed.trips[
        (feed.trips['route_id'] == route_id) &
        (feed.trips['direction_id'] == direction_id) &
        (feed.trips['service_id'] == service_id)
    ].copy()

    # Initialize matrix to store travel times (list of times for each pair)
    travel_times = defaultdict(list)

    # For each trip, calculate travel times between all pairs of stops
    for trip_id in trips['trip_id']:
        stop_times = feed.stop_times[feed.stop_times['trip_id'] == trip_id].sort_values('stop_sequence')

        # Convert to list for easier iteration
        stops_data = []
        for _, row in stop_times.iterrows():
            # Normalize stop ID to parent station
            normalized_stop_id = normalize_stop_id(feed, row['stop_id'])

            if normalized_stop_id in stop_ids:
                # Parse time to seconds
                arrival_parts = row['arrival_time'].split(':')
                arrival_seconds = int(arrival_parts[0]) * 3600 + int(arrival_parts[1]) * 60 + int(arrival_parts[2])

                departure_parts = row['departure_time'].split(':')
                departure_seconds = int(departure_parts[0]) * 3600 + int(departure_parts[1]) * 60 + int(departure_parts[2])

                stops_data.append({
                    'stop_id': normalized_stop_id,
                    'arrival_seconds': arrival_seconds,
                    'departure_seconds': departure_seconds
                })

        # Calculate travel time between each pair of stops on this trip
        for i, origin in enumerate(stops_data):
            for j, destination in enumerate(stops_data):
                if j > i:  # Calculate for the direction this trip is traveling
                    travel_seconds = destination['arrival_seconds'] - origin['departure_seconds']
                    travel_minutes = travel_seconds / 60.0

                    # Store the travel time for this pair
                    pair_key = (origin['stop_id'], destination['stop_id'])
                    travel_times[pair_key].append(travel_minutes)

    # Calculate average travel times
    matrix_data = np.full((len(stop_ids), len(stop_ids)), np.nan)

    for i, origin_id in enumerate(stop_ids):
        for j, dest_id in enumerate(stop_ids):
            if i == j:
                matrix_data[i][j] = 0  # Same station = 0 minutes
            else:
                # Fill based on actual travel time data (could be upper or lower triangle)
                pair_key = (origin_id, dest_id)
                if pair_key in travel_times and travel_times[pair_key]:
                    matrix_data[i][j] = np.mean(travel_times[pair_key])

    # Create DataFrame with station names as indices
    # Transpose so columns = departure points, rows = destinations
    df = pd.DataFrame(matrix_data, index=stop_names, columns=stop_names)
    df = df.T

    return df


def load_official_direction_names(csv_path='direction_names.csv'):
    """
    Load official direction names from CSV file.

    The CSV should have columns: route_id, direction_id, direction_name
    Example:
        route_id,direction_id,direction_name
        L,0,To Manhattan
        L,1,To Brooklyn

    Parameters:
    -----------
    csv_path : str
        Path to the CSV file with official direction names

    Returns:
    --------
    dict
        Dictionary mapping (route_id, direction_id) -> direction_name
    """
    if not os.path.exists(csv_path):
        return {}

    try:
        df = pd.read_csv(csv_path)
        direction_map = {}
        for _, row in df.iterrows():
            key = (str(row['route_id']), int(row['direction_id']))
            direction_map[key] = row['direction_name']
        return direction_map
    except Exception as e:
        print(f"Warning: Could not load direction names from {csv_path}: {e}")
        return {}


def get_direction_name(feed, route_id, direction_id, service_id='Weekday', csv_path='direction_names.csv'):
    """
    Get a human-readable direction name.

    First tries to use official names from direction_names.csv.
    If not found, falls back to using the route's terminal station.

    Parameters:
    -----------
    feed : gtfs_kit.Feed
        A GTFS feed object loaded with gtfs_kit
    route_id : str
        The route ID
    direction_id : int
        Direction ID (0 or 1)
    service_id : str, default='Weekday'
        Service ID to filter by
    csv_path : str, default='direction_names.csv'
        Path to CSV file with official direction names

    Returns:
    --------
    str
        Direction name like "To Manhattan" or "to 8 Av" or "Northbound"
    """
    # First, try to load official direction names from CSV
    official_names = load_official_direction_names(csv_path)
    key = (route_id, direction_id)

    if key in official_names:
        return official_names[key]

    # Fall back to terminal-based naming
    # Get trips for this route/direction/service
    trips = feed.trips[
        (feed.trips['route_id'] == route_id) &
        (feed.trips['direction_id'] == direction_id) &
        (feed.trips['service_id'] == service_id)
    ].copy()

    if trips.empty:
        return "Northbound" if direction_id == 0 else "Southbound"

    # Get the trip with the most stops (the local/all-stops trip)
    stop_times = feed.stop_times[feed.stop_times['trip_id'].isin(trips['trip_id'])].copy()
    stop_counts = stop_times.groupby('trip_id').size()
    max_stops_trip_id = stop_counts.idxmax()

    # Get the last stop (terminal) for this trip
    trip_stop_times = stop_times[stop_times['trip_id'] == max_stops_trip_id].sort_values('stop_sequence')
    terminal_stop_id = trip_stop_times.iloc[-1]['stop_id']

    # Get the terminal stop name
    terminal_name = feed.stops[feed.stops['stop_id'] == terminal_stop_id]['stop_name'].values
    if len(terminal_name) > 0:
        return f"to {terminal_name[0]}"

    return "Northbound" if direction_id == 0 else "Southbound"


def combine_bidirectional_matrix(matrix_dir0, matrix_dir1):
    """
    Combine two directional travel time matrices into one.

    After transposing (columns=origins, rows=destinations):
    - Upper triangle (j > i): direction 0 times
    - Lower triangle (j < i): direction 1 times
    Both matrices must have the same stations in the same order.

    Parameters:
    -----------
    matrix_dir0 : pd.DataFrame
        Travel time matrix for direction 0 (transposed: columns=origins, rows=destinations)
    matrix_dir1 : pd.DataFrame
        Travel time matrix for direction 1 (transposed: columns=origins, rows=destinations)

    Returns:
    --------
    pd.DataFrame
        Combined matrix with both directions
    """
    # Start with a copy of direction 0
    combined = matrix_dir0.copy()

    # After transpose:
    # - Direction 0 originally had lower triangle → now has UPPER triangle
    # - Direction 1 originally had upper triangle → now has LOWER triangle
    # So we just need to fill in NaN values from direction 1
    for i in range(len(combined)):
        for j in range(len(combined.columns)):
            if pd.isna(combined.iloc[i, j]) and pd.notna(matrix_dir1.iloc[i, j]):
                combined.iloc[i, j] = matrix_dir1.iloc[i, j]

    return combined


def print_travel_time_matrix(matrix, route_id, direction_id, service_id, direction_name=None):
    """
    Print a formatted travel time matrix.

    Parameters:
    -----------
    matrix : pd.DataFrame
        Travel time matrix from calculate_travel_time_matrix()
    route_id : str
        The route ID for display
    direction_id : int
        Direction ID for display
    service_id : str
        Service ID for display
    direction_name : str, optional
        Human-readable direction name. If None, uses default "Northbound"/"Southbound"
    """
    if direction_name is None:
        direction_name = "Northbound" if direction_id == 0 else "Southbound"

    print(f"\n{'='*80}")
    print(f"{route_id} Train - {service_id} - {direction_name}")
    print(f"Travel Times (minutes)")
    print(f"{'='*80}\n")

    # Print the matrix with formatting
    pd.set_option('display.max_rows', None)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    pd.set_option('display.float_format', '{:.1f}'.format)

    print(matrix.to_string())
    print()


def print_combined_travel_time_matrix(matrix, route_id, service_id, direction_name_0, direction_name_1):
    """
    Print a combined bidirectional travel time matrix.

    Parameters:
    -----------
    matrix : pd.DataFrame
        Combined travel time matrix
    route_id : str
        The route ID for display
    service_id : str
        Service ID for display
    direction_name_0 : str
        Direction name for upper triangle
    direction_name_1 : str
        Direction name for lower triangle
    """
    print(f"\n{'='*80}")
    print(f"{route_id} Train - {service_id} - Combined Directions")
    print(f"Travel Times (minutes)")
    print(f"{'='*80}\n")
    print(f"Upper triangle (above diagonal): {direction_name_0}")
    print(f"Lower triangle (below diagonal): {direction_name_1}")
    print(f"Diagonal: Same station = 0 minutes")
    print()

    # Print the matrix with formatting
    pd.set_option('display.max_rows', None)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    pd.set_option('display.float_format', '{:.1f}'.format)

    print(matrix.to_string())
    print()


def export_travel_time_matrix_csv(matrix, route_id, direction_id, service_id, filename=None):
    """
    Export travel time matrix to CSV file.

    Parameters:
    -----------
    matrix : pd.DataFrame
        Travel time matrix from calculate_travel_time_matrix()
    route_id : str
        The route ID
    direction_id : int
        Direction ID
    service_id : str
        Service ID
    filename : str, optional
        Output filename. If None, generates from route info.
    """
    if filename is None:
        direction_name = "northbound" if direction_id == 0 else "southbound"
        filename = f"{route_id}_{service_id.lower()}_{direction_name}_travel_times.csv"

    matrix.to_csv(filename)
    print(f"Exported to {filename}")


def main():
    # Load GTFS feed
    feed = gk.read_feed("/Users/lennyphelan/Downloads/gtfs_subway.zip", dist_units="m")

    # Example: A train on weekdays (multi-branch route)
    route_id = 'A'
    service_id = 'Weekday'

    print(f"Calculating travel time matrices for {route_id} train...")

    # First, let's see what branches exist
    branch_point, branches_info = identify_branches(feed, route_id, 1, service_id)
    if branches_info:
        print(f"\nBranches for {route_id} train direction 1:")
        for i, branch in enumerate(branches_info):
            print(f"  {i+1}. {branch['terminal_name']}: {branch['trip_count']} trips, {branch['stop_count']} stops")
        if branch_point:
            branch_name = feed.stops[feed.stops['stop_id'] == branch_point]['stop_name'].values
            print(f"\nBranch point: {branch_name[0] if len(branch_name) > 0 else branch_point}")
        print()

    # Get canonical station order (use direction 0's ordering for both directions)
    canonical_order = get_station_order(feed, route_id, 0, service_id)

    # Create filtered version: express stops only in Manhattan/Brooklyn, all stops in Queens
    print("\nGenerating FILTERED matrix (express stops in Manhattan/Brooklyn, all stops in Queens)...")
    print("="*80)

    filtered_order = filter_station_order_express(
        feed, canonical_order, route_id, 0, service_id,
        express_boroughs=['Manhattan', 'Brooklyn'],
        all_stops_boroughs=['Queens']
    )

    print(f"\nFiltered from {len(canonical_order)} stations to {len(filtered_order)} stations")

    # Calculate matrices for both directions using the filtered station order
    matrix_dir0_filtered = calculate_travel_time_matrix(feed, route_id, 0, service_id, filtered_order)
    matrix_dir1_filtered = calculate_travel_time_matrix(feed, route_id, 1, service_id, filtered_order)

    if not matrix_dir0_filtered.empty and not matrix_dir1_filtered.empty:
        # Get direction names
        direction_name_0 = get_direction_name(feed, route_id, 0, service_id)
        direction_name_1 = get_direction_name(feed, route_id, 1, service_id)

        # Combine the matrices
        combined_matrix_filtered = combine_bidirectional_matrix(matrix_dir0_filtered, matrix_dir1_filtered)

        # Print combined matrix
        print_combined_travel_time_matrix(combined_matrix_filtered, route_id, service_id,
                                         direction_name_0, direction_name_1)

        # Optionally export to CSV
        # combined_matrix_filtered.to_csv(f'{route_id}_{service_id}_express_travel_times.csv')
    else:
        print(f"Could not generate travel time matrix for {route_id} train")


if __name__ == "__main__":
    main()
