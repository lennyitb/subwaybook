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
    # Strategy: Add trunk first, then add branches in order:
    # full-time branches (shortest to longest), then part-time branches

    terminals = stop_times.groupby('trip_id').last().reset_index()

    # Build complete station list
    all_stops = []
    seen_stops = set()

    # First, add the trunk stops (common to all branches)
    # Find the branch point and use any trip to get trunk stops
    if branch_point:
        # Get a sample trip to extract trunk stops
        sample_trip_id = terminals['trip_id'].iloc[0]
        sample_trip_stops = stop_times[stop_times['trip_id'] == sample_trip_id].sort_values('stop_sequence')

        # Add trunk stops up to and including the branch point
        for _, row in sample_trip_stops.iterrows():
            normalized_id = normalize_stop_id(feed, row['stop_id'])
            if normalized_id not in seen_stops:
                stop_name = feed.stops[feed.stops['stop_id'] == normalized_id]['stop_name'].values
                if len(stop_name) > 0:
                    all_stops.append((normalized_id, stop_name[0]))
                    seen_stops.add(normalized_id)

            # Stop after branch point
            if normalize_stop_id(feed, row['stop_id']) == normalize_stop_id(feed, branch_point):
                break

    # Now add stops from each branch in order:
    # branches_info is already sorted by: trip_count desc, then stop_count asc
    # This means full-time branches (by ascending length) come first, then part-time
    for branch in branches_info:
        # Get a trip to this terminal with the most stops
        branch_trip_ids = terminals[terminals['stop_id'] == branch['terminal_id']]['trip_id'].tolist()
        branch_stop_times = stop_times[stop_times['trip_id'].isin(branch_trip_ids)]
        branch_stop_counts = branch_stop_times.groupby('trip_id').size()
        branch_max_trip = branch_stop_counts.idxmax()

        branch_stops = stop_times[stop_times['trip_id'] == branch_max_trip].sort_values('stop_sequence')

        # Add all stops from this branch (only new stops after branch point)
        for stop_id in branch_stops['stop_id']:
            normalized_id = normalize_stop_id(feed, stop_id)
            if normalized_id not in seen_stops:
                stop_name = feed.stops[feed.stops['stop_id'] == normalized_id]['stop_name'].values
                if len(stop_name) > 0:
                    all_stops.append((normalized_id, stop_name[0]))
                    seen_stops.add(normalized_id)

    return all_stops


def get_bidirectional_station_order(feed, route_id, service_id='Weekday'):
    """
    Get the complete station order including stops that only serve one direction.
    
    This combines stations from both directions, preserving the order from
    direction 1 (typically inbound) but adding any direction 0-only stops
    in their proper position.
    
    Parameters:
    -----------
    feed : gtfs_kit.Feed
        A GTFS feed object loaded with gtfs_kit
    route_id : str
        The route ID (e.g., 'A', 'L', '7')
    service_id : str, default='Weekday'
        Service ID to filter by
    
    Returns:
    --------
    list
        Ordered list of (stop_id, stop_name) tuples including all stations
    """
    # Get station orders from both directions
    order_dir0 = get_station_order(feed, route_id, 0, service_id)
    order_dir1 = get_station_order(feed, route_id, 1, service_id)
    
    # Use direction 1 as base (typically has better ordering for display)
    # but add any stations that only appear in direction 0
    combined_order = list(order_dir1)
    seen_stops = {stop_id for stop_id, _ in order_dir1}
    
    # Add direction 0-only stops in their proper position
    for i, (stop_id, stop_name) in enumerate(order_dir0):
        if stop_id not in seen_stops:
            # Find where to insert this stop based on its position in dir0
            # Insert it after the previous common stop
            insert_pos = len(combined_order)  # Default to end
            
            # Look backward in dir0 to find the last common stop before this one
            for j in range(i - 1, -1, -1):
                prev_stop_id = order_dir0[j][0]
                if prev_stop_id in seen_stops:
                    # Find this stop in combined_order and insert after it
                    for k, (comb_id, _) in enumerate(combined_order):
                        if comb_id == prev_stop_id:
                            insert_pos = k + 1
                            break
                    break
            
            combined_order.insert(insert_pos, (stop_id, stop_name))
            seen_stops.add(stop_id)
    
    return combined_order


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

    # Count how many trips stop at each station
    # A stop is only "express" if a significant percentage of trips stop there
    # This filters out late-night/off-peak local stops on otherwise express routes
    #
    # NOTE: This frequency-based approach was added to fix an issue where Liberty Av,
    # Van Siclen Av, and Shepherd Av were incorrectly classified as express stops.
    # The root cause was actually incorrect borough polygon boundaries in express_local.py.
    # After fixing the polygons (extending Brooklyn to include these stations), this
    # threshold may no longer be necessary and could potentially cause issues by
    # excluding legitimate express stops that have <50% service coverage due to branches
    # or service patterns. Consider removing this threshold or making it configurable
    # if it causes problems in the future.
    from collections import defaultdict

    # Get all trips for this route/direction/service
    trips_for_route = feed.trips[
        (feed.trips['route_id'] == route_id) &
        (feed.trips['direction_id'] == direction_id) &
        (feed.trips['service_id'] == service_id)
    ]
    total_trips = len(trips_for_route)
    trip_ids = set(trips_for_route['trip_id'])

    # Count trips per stop
    stop_trip_counts = defaultdict(int)
    stop_times = feed.stop_times[feed.stop_times['trip_id'].isin(trip_ids)]

    for stop_id in stop_times['stop_id']:
        normalized_stop_id = normalize_stop_id(feed, stop_id)
        stop_trip_counts[normalized_stop_id] += 1

    # A stop is considered "express" if at least 50% of trips stop there
    # This threshold filters out stations like Liberty Av (14%) while keeping
    # true express stops like 59 St (90%)
    EXPRESS_THRESHOLD = 0.5
    express_stops = set()

    for stop_id, count in stop_trip_counts.items():
        if count / total_trips >= EXPRESS_THRESHOLD:
            express_stops.add(stop_id)

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


def calculate_travel_time_matrix_by_hour(feed, route_id, direction_id, hour, service_id='Weekday', canonical_station_order=None):
    """
    Calculate a travel time matrix for a route filtered by hour(s) of day.

    For each pair of stations (origin, destination), calculates the average
    travel time across trips where the departure from the origin station
    occurs within the specified hour or hour range.

    Parameters:
    -----------
    feed : gtfs_kit.Feed
        A GTFS feed object loaded with gtfs_kit
    route_id : str
        The route ID (e.g., 'A', 'L', '7')
    direction_id : int
        Direction ID (0 or 1)
    hour : int or tuple of (int, int)
        Hour(s) of day to filter trips by (based on departure from origin).
        - Single int (0-23): filters to that specific hour (e.g., 7 = 7:00-7:59 AM)
        - Tuple (start, end): filters to hour range inclusive (e.g., (7, 9) = 7:00-9:59 AM)
    service_id : str, default='Weekday'
        Service ID to filter by
    canonical_station_order : list, optional
        Pre-determined station order to use. If None, will determine from this direction.

    Returns:
    --------
    pd.DataFrame
        Travel time matrix with station names as both row and column indices.
        Values are travel times in minutes (float).
        NaN indicates no direct service between those stations during this hour/range.

    Examples:
    ---------
    # Single hour (7 AM)
    >>> matrix = calculate_travel_time_matrix_by_hour(feed, 'A', 0, hour=7)

    # Hour range (7-9 AM inclusive)
    >>> matrix = calculate_travel_time_matrix_by_hour(feed, 'A', 0, hour=(7, 9))
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

    # Parse hour parameter to determine range
    if isinstance(hour, tuple) or isinstance(hour, list):
        hour_start, hour_end = hour
        hour_range = range(hour_start, hour_end + 1)  # Inclusive range
    else:
        hour_range = [hour]  # Single hour

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
                departure_hour = int(departure_parts[0]) % 24  # Handle times >= 24:00:00

                stops_data.append({
                    'stop_id': normalized_stop_id,
                    'arrival_seconds': arrival_seconds,
                    'departure_seconds': departure_seconds,
                    'departure_hour': departure_hour
                })

        # Calculate travel time between each pair of stops on this trip
        # Only include if departure from origin is within the specified hour range
        for i, origin in enumerate(stops_data):
            # Check if departure from origin is in the specified hour range
            if origin['departure_hour'] in hour_range:
                for j, destination in enumerate(stops_data):
                    if j > i:  # Calculate for the direction this trip is traveling
                        travel_seconds = destination['arrival_seconds'] - origin['departure_seconds']
                        travel_minutes = travel_seconds / 60.0

                        # Store the travel time for this pair
                        pair_key = (origin['stop_id'], destination['stop_id'])
                        travel_times[pair_key].append(travel_minutes)

    # Identify stations that actually have data during this hour
    # A station should be included if it appears in any travel time pair
    stations_with_data = set()
    for (origin_id, dest_id) in travel_times.keys():
        if travel_times[(origin_id, dest_id)]:  # Only if there's actual data
            stations_with_data.add(origin_id)
            stations_with_data.add(dest_id)

    # Filter station lists to only include stations with data
    filtered_stop_ids = []
    filtered_stop_names = []
    for stop_id, stop_name in zip(stop_ids, stop_names):
        if stop_id in stations_with_data:
            filtered_stop_ids.append(stop_id)
            filtered_stop_names.append(stop_name)

    # If no stations have data during this hour, return empty DataFrame
    if not filtered_stop_ids:
        return pd.DataFrame()

    # Calculate average travel times
    matrix_data = np.full((len(filtered_stop_ids), len(filtered_stop_ids)), np.nan)

    for i, origin_id in enumerate(filtered_stop_ids):
        for j, dest_id in enumerate(filtered_stop_ids):
            if i == j:
                matrix_data[i][j] = 0  # Same station = 0 minutes
            else:
                # Fill based on actual travel time data (could be upper or lower triangle)
                pair_key = (origin_id, dest_id)
                if pair_key in travel_times and travel_times[pair_key]:
                    matrix_data[i][j] = np.mean(travel_times[pair_key])

    # Create DataFrame with station names as indices
    # Transpose so columns = departure points, rows = destinations
    df = pd.DataFrame(matrix_data, index=filtered_stop_names, columns=filtered_stop_names)
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
    # If one matrix is empty, return the other
    if matrix_dir0.empty:
        return matrix_dir1.copy()
    if matrix_dir1.empty:
        return matrix_dir0.copy()
    
    # Always check if matrices have the same stations (not just shape)
    # This handles cases where stations differ even if dimensions match
    stations_dir0 = set(matrix_dir0.index)
    stations_dir1 = set(matrix_dir1.index)
    
    if stations_dir0 != stations_dir1:
        # Reindex both to have the same index and columns (union of both)
        # Preserve order from matrix_dir0, then add any new stations from matrix_dir1
        all_stations = list(matrix_dir0.index)
        for station in matrix_dir1.index:
            if station not in all_stations:
                all_stations.append(station)
        matrix_dir0 = matrix_dir0.reindex(index=all_stations, columns=all_stations)
        matrix_dir1 = matrix_dir1.reindex(index=all_stations, columns=all_stations)
    
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


def display_bidirectional_matrix(feed, route_id, service_id, canonical_station_order, hour=None):
    """
    Calculate and combine bidirectional travel time matrices.

    This is a convenience function that:
    1. Calculates travel time matrices for both directions (0 and 1)
    2. Combines them into a single bidirectional matrix

    The result is a matrix where:
    - Stations are ordered according to the provided canonical_station_order
    - Upper triangle shows direction 0 travel times
    - Lower triangle shows direction 1 travel times
    - Diagonal shows 0 (same station)

    Parameters:
    -----------
    feed : gtfs_kit.Feed
        A GTFS feed object loaded with gtfs_kit
    route_id : str
        The route ID (e.g., 'A', 'L', '7')
    service_id : str
        Service ID to filter by (e.g., 'Weekday', 'Saturday', 'Sunday')
    canonical_station_order : list
        Pre-determined station order (list of (stop_id, stop_name) tuples).
        The stations will be displayed in this exact order.
    hour : int, tuple of (int, int), or None, optional
        Hour(s) of day to filter trips by. If provided, only trips where
        the departure from the origin station occurs within the specified
        hour(s) will be included in the travel time calculations.
        - Single int (0-23): filters to that specific hour (e.g., 7 = 7:00-7:59 AM)
        - Tuple (start, end): filters to hour range inclusive (e.g., (7, 9) = 7:00-9:59 AM)
        - None (default): all trips are included regardless of time

    Returns:
    --------
    pd.DataFrame
        Combined bidirectional travel time matrix.
        Values are travel times in minutes (float).
        Station names appear as both row and column indices.

    Examples:
    ---------
    # Calculate A train bidirectional matrix with express filtering
    >>> feed = gk.read_feed("gtfs_subway.zip", dist_units="m")
    >>> route_id = 'A'
    >>> service_id = 'Weekday'
    >>>
    >>> # Get station order (use direction 1 for desired branch ordering)
    >>> canonical_order = get_station_order(feed, route_id, 1, service_id)
    >>>
    >>> # Filter to express stops
    >>> filtered_order = filter_station_order_express(
    ...     feed, canonical_order, route_id, 0, service_id,
    ...     express_boroughs=['Manhattan', 'Brooklyn'],
    ...     all_stops_boroughs=['Queens']
    ... )
    >>>
    >>> # Get combined matrix for all trips
    >>> combined = display_bidirectional_matrix(feed, route_id, service_id, filtered_order)
    >>>
    >>> # Get combined matrix for single hour (8 AM)
    >>> combined_8am = display_bidirectional_matrix(feed, route_id, service_id,
    ...                                              filtered_order, hour=8)
    >>>
    >>> # Get combined matrix for morning rush hour range (7-9 AM)
    >>> combined_morning_rush = display_bidirectional_matrix(feed, route_id, service_id,
    ...                                                       filtered_order, hour=(7, 9))
    >>>
    >>> # Export to CSV
    >>> combined.to_csv(f'{route_id}_{service_id}_travel_times.csv')
    >>> combined_8am.to_csv(f'{route_id}_{service_id}_travel_times_8am.csv')
    >>> combined_morning_rush.to_csv(f'{route_id}_{service_id}_travel_times_7-9am.csv')

    # Use with print function
    >>> direction_name_0 = get_direction_name(feed, route_id, 0, service_id)
    >>> direction_name_1 = get_direction_name(feed, route_id, 1, service_id)
    >>> print_combined_travel_time_matrix(combined, route_id, service_id,
    ...                                   direction_name_0, direction_name_1)

    Notes:
    ------
    - The canonical_station_order can come from either direction
    - For branched routes, use direction 1 to get the correct branch ordering
      (shortest full-time branch first, then longer branches, then part-time branches)
    - For filtered station orders, use filter_station_order_express() to focus on
      specific stops
    - The resulting matrix is symmetric in structure but not in values (travel times
      may differ between directions due to track conditions, stops, etc.)
    - When hour is specified, travel times reflect only trips departing during that
      hour or hour range, which is useful for analyzing rush hour vs off-peak performance
    - Hour ranges are inclusive: hour=(7, 9) includes trips from 7:00-9:59 AM

    See Also:
    ---------
    get_station_order : Get canonical station ordering for a route
    filter_station_order_express : Filter stations to express stops only
    calculate_travel_time_matrix : Calculate single-direction travel time matrix (all trips)
    calculate_travel_time_matrix_by_hour : Calculate single-direction matrix filtered by hour
    combine_bidirectional_matrix : Combine two directional matrices
    print_combined_travel_time_matrix : Print formatted bidirectional matrix
    """
    # Calculate matrices for both directions using the provided order
    # Use hour-filtered function if hour is specified, otherwise use standard function
    if hour is not None:
        matrix_dir0 = calculate_travel_time_matrix_by_hour(feed, route_id, 0, hour, service_id, canonical_station_order)
        matrix_dir1 = calculate_travel_time_matrix_by_hour(feed, route_id, 1, hour, service_id, canonical_station_order)
    else:
        matrix_dir0 = calculate_travel_time_matrix(feed, route_id, 0, service_id, canonical_station_order)
        matrix_dir1 = calculate_travel_time_matrix(feed, route_id, 1, service_id, canonical_station_order)

    # Combine the matrices
    combined = combine_bidirectional_matrix(matrix_dir0, matrix_dir1)

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
    feed = gk.read_feed("gtfs_subway.zip", dist_units="m")

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
