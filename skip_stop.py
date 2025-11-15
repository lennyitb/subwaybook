#!/usr/bin/env python3
"""
Module for analyzing skip-stop service patterns on the J/Z lines.

The J and Z trains use a skip-stop system during rush hours:
- When Z trains run, they skip certain stations
- During Z service hours, J trains should theoretically run skip-stop (stopping at
  stations that Z skips), though the GTFS data shows all J trips as all-stop
- When Z trains don't run, J trains run all-stop service

This is different from traditional express/local service where one train
consistently skips stations across all hours.
"""
import pandas as pd
import numpy as np


def get_z_service_hours(feed, service_id='Weekday'):
    """
    Determine which hours Z train service operates.

    Parameters:
    -----------
    feed : gtfs_kit.Feed
        A GTFS feed object loaded with gtfs_kit
    service_id : str, default='Weekday'
        Service ID to filter by

    Returns:
    --------
    set
        Set of hours (0-23) when Z trains operate
    """
    z_trips = feed.trips[
        (feed.trips['route_id'] == 'Z') &
        (feed.trips['service_id'] == service_id)
    ]

    if len(z_trips) == 0:
        return set()

    # Get all stop times for Z trains
    z_stop_times = feed.stop_times[
        feed.stop_times['trip_id'].isin(z_trips['trip_id'])
    ]

    # Extract hours from departure times
    hours = set()
    for time_str in z_stop_times['departure_time']:
        hour = int(time_str.split(':')[0])
        hours.add(hour)

    return hours


def get_skip_stop_stations(feed, direction_id=1, service_id='Weekday'):
    """
    Identify which stations are skipped by Z trains (and theoretically should
    be served by skip-stop J trains during rush hours).

    Parameters:
    -----------
    feed : gtfs_kit.Feed
        A GTFS feed object loaded with gtfs_kit
    direction_id : int, default=1
        Direction ID (0 or 1)
    service_id : str, default='Weekday'
        Service ID to filter by

    Returns:
    --------
    tuple
        (j_only_stops, z_only_stops, shared_stops) where each is a list of
        (stop_id, stop_name) tuples
        - j_only_stops: Stations J stops at but Z skips
        - z_only_stops: Stations Z stops at but J skips (if any)
        - shared_stops: Stations both J and Z stop at
    """
    # Get J and Z trips
    j_trips = feed.trips[
        (feed.trips['route_id'] == 'J') &
        (feed.trips['direction_id'] == direction_id) &
        (feed.trips['service_id'] == service_id)
    ]

    z_trips = feed.trips[
        (feed.trips['route_id'] == 'Z') &
        (feed.trips['direction_id'] == direction_id) &
        (feed.trips['service_id'] == service_id)
    ]

    # Get stops for each route
    # For J, use the trip with the most stops (all-stop pattern)
    j_stop_counts = {}
    for trip_id in j_trips['trip_id']:
        stops = feed.stop_times[feed.stop_times['trip_id'] == trip_id]['stop_id'].tolist()
        j_stop_counts[trip_id] = len(stops)

    if not j_stop_counts:
        return [], [], []

    # Get the J trip with most stops
    max_j_trip = max(j_stop_counts, key=j_stop_counts.get)
    j_stop_ids = feed.stop_times[
        feed.stop_times['trip_id'] == max_j_trip
    ].sort_values('stop_sequence')['stop_id'].tolist()

    # Get Z stops if Z trains exist
    z_stop_ids = []
    if len(z_trips) > 0:
        z_trip = z_trips.iloc[0]['trip_id']
        z_stop_ids = feed.stop_times[
            feed.stop_times['trip_id'] == z_trip
        ].sort_values('stop_sequence')['stop_id'].tolist()

    # Categorize stops
    j_only_ids = [s for s in j_stop_ids if s not in z_stop_ids]
    z_only_ids = [s for s in z_stop_ids if s not in j_stop_ids]
    shared_ids = [s for s in j_stop_ids if s in z_stop_ids]

    # Convert to (stop_id, stop_name) tuples
    def get_stop_names(stop_id_list):
        result = []
        for stop_id in stop_id_list:
            stop_name = feed.stops[feed.stops['stop_id'] == stop_id]['stop_name'].values
            if len(stop_name) > 0:
                result.append((stop_id, stop_name[0]))
        return result

    j_only_stops = get_stop_names(j_only_ids)
    z_only_stops = get_stop_names(z_only_ids)
    shared_stops = get_stop_names(shared_ids)

    return j_only_stops, z_only_stops, shared_stops


def classify_j_trips(feed, direction_id=1, service_id='Weekday'):
    """
    Classify J train trips as either "all-stop" or "skip-stop".

    Note: In the current GTFS data, all J trips appear to be all-stop.
    The skip-stop pattern is inferred based on when Z trains are running.

    Parameters:
    -----------
    feed : gtfs_kit.Feed
        A GTFS feed object loaded with gtfs_kit
    direction_id : int, default=1
        Direction ID (0 or 1)
    service_id : str, default='Weekday'
        Service ID to filter by

    Returns:
    --------
    pd.DataFrame
        DataFrame with columns:
        - trip_id: Trip ID
        - departure_hour: Hour of first departure
        - pattern: 'all-stop' or 'skip-stop' (inferred)
        - num_stops: Number of stops on this trip
        - z_service_active: Whether Z trains are running during this hour
    """
    j_trips = feed.trips[
        (feed.trips['route_id'] == 'J') &
        (feed.trips['direction_id'] == direction_id) &
        (feed.trips['service_id'] == service_id)
    ]

    # Get Z service hours
    z_hours = get_z_service_hours(feed, service_id)

    # Analyze each J trip
    results = []
    for _, trip in j_trips.iterrows():
        trip_id = trip['trip_id']

        # Get stops for this trip
        stop_times = feed.stop_times[feed.stop_times['trip_id'] == trip_id]
        num_stops = len(stop_times)

        # Get first departure time
        first_departure = stop_times.sort_values('stop_sequence').iloc[0]['departure_time']
        hour = int(first_departure.split(':')[0])

        # Determine if Z service is active
        z_active = hour in z_hours

        # Infer pattern
        # In theory, J should run skip-stop when Z is active
        # But GTFS data shows all J trips as all-stop
        # So we mark based on Z service presence
        if z_active:
            pattern = 'all-stop (Z active)'
        else:
            pattern = 'all-stop (no Z)'

        results.append({
            'trip_id': trip_id,
            'departure_hour': hour,
            'pattern': pattern,
            'num_stops': num_stops,
            'z_service_active': z_active
        })

    return pd.DataFrame(results)


def print_skip_stop_summary(feed, direction_id=1, service_id='Weekday'):
    """
    Print a summary of the skip-stop service pattern.

    Parameters:
    -----------
    feed : gtfs_kit.Feed
        A GTFS feed object loaded with gtfs_kit
    direction_id : int, default=1
        Direction ID (0 or 1)
    service_id : str, default='Weekday'
        Service ID to filter by
    """
    print("="*80)
    print("J/Z SKIP-STOP SERVICE ANALYSIS")
    print("="*80)

    # Get Z service hours
    z_hours = get_z_service_hours(feed, service_id)
    print(f"\nZ train service hours: {sorted(z_hours)}")

    # Get skip-stop stations
    j_only, z_only, shared = get_skip_stop_stations(feed, direction_id, service_id)

    print(f"\n{len(shared)} stations served by both J and Z trains:")
    for stop_id, stop_name in shared:
        print(f"  • {stop_name}")

    print(f"\n{len(j_only)} stations served by J but skipped by Z:")
    for stop_id, stop_name in j_only:
        print(f"  • {stop_name}")

    if z_only:
        print(f"\n{len(z_only)} stations served by Z but not J:")
        for stop_id, stop_name in z_only:
            print(f"  • {stop_name}")

    # Classify J trips
    j_classification = classify_j_trips(feed, direction_id, service_id)

    print(f"\nJ train trip patterns:")
    print(f"  Total J trips: {len(j_classification)}")
    print(f"  Trips during Z service hours: {j_classification['z_service_active'].sum()}")
    print(f"  Trips outside Z service hours: {(~j_classification['z_service_active']).sum()}")

    print(f"\nNote: GTFS data shows all J trips as all-stop service.")
    print(f"In practice, when Z trains run, J trains may operate skip-stop,")
    print(f"stopping only at the {len(j_only)} stations that Z skips.")


def get_effective_headway(feed, direction_id=1, service_id='Weekday',
                          stop_id=None, hour_range=None):
    """
    Calculate effective headway for J/Z service, accounting for skip-stop pattern.

    For stations served by both J and Z:
    - During Z service hours: Combined J+Z headway
    - Outside Z service hours: J-only headway

    For stations served by J only (skip-stop stations):
    - During Z service hours: J-only headway (would be skip-stop J in theory)
    - Outside Z service hours: J-only headway (all-stop J)

    Parameters:
    -----------
    feed : gtfs_kit.Feed
        A GTFS feed object loaded with gtfs_kit
    direction_id : int, default=1
        Direction ID (0 or 1)
    service_id : str, default='Weekday'
        Service ID to filter by
    stop_id : str, optional
        Specific stop to analyze. If None, uses the first non-terminal stop
        that both J and Z serve.
    hour_range : tuple of (int, int), optional
        Hour range to filter (start_hour, end_hour)

    Returns:
    --------
    pd.DataFrame
        DataFrame with headway statistics by hour and station type
    """
    # Get Z service hours
    z_hours = get_z_service_hours(feed, service_id)

    # Get skip-stop station classification
    j_only_stops, z_only_stops, shared_stops = get_skip_stop_stations(
        feed, direction_id, service_id
    )

    # If no stop specified, use first shared stop
    if stop_id is None and shared_stops:
        stop_id = shared_stops[0][0]

    if stop_id is None:
        return pd.DataFrame()

    # Determine station type
    is_j_only = any(sid == stop_id for sid, _ in j_only_stops)
    is_shared = any(sid == stop_id for sid, _ in shared_stops)

    # Get all relevant trips (J and maybe Z)
    all_trips = []

    # J trips
    j_trips = feed.trips[
        (feed.trips['route_id'] == 'J') &
        (feed.trips['direction_id'] == direction_id) &
        (feed.trips['service_id'] == service_id)
    ]
    all_trips.extend(j_trips['trip_id'].tolist())

    # Z trips (only for shared stations)
    if is_shared:
        z_trips = feed.trips[
            (feed.trips['route_id'] == 'Z') &
            (feed.trips['direction_id'] == direction_id) &
            (feed.trips['service_id'] == service_id)
        ]
        all_trips.extend(z_trips['trip_id'].tolist())

    # Get stop times at this station
    stop_times = feed.stop_times[
        (feed.stop_times['stop_id'] == stop_id) &
        (feed.stop_times['trip_id'].isin(all_trips))
    ].sort_values('departure_time').copy()

    if len(stop_times) == 0:
        return pd.DataFrame()

    # Extract hour
    stop_times['hour'] = stop_times['departure_time'].apply(
        lambda x: int(x.split(':')[0])
    )

    # Filter by hour range if specified
    if hour_range is not None:
        start_hour, end_hour = hour_range
        stop_times = stop_times[
            (stop_times['hour'] >= start_hour) &
            (stop_times['hour'] < end_hour)
        ]

    # Calculate headways by hour
    results = []
    for hour in sorted(stop_times['hour'].unique()):
        hour_stops = stop_times[stop_times['hour'] == hour].sort_values('departure_time')

        if len(hour_stops) < 2:
            continue

        # Calculate time differences
        times = pd.to_datetime(hour_stops['departure_time'], format='%H:%M:%S')
        headways = times.diff().dt.total_seconds() / 60  # Convert to minutes
        headways = headways[headways.notna()]

        if len(headways) == 0:
            continue

        # Check if Z is active during this hour
        z_active = hour in z_hours

        results.append({
            'hour': hour,
            'num_trains': len(hour_stops),
            'avg_headway': headways.mean(),
            'min_headway': headways.min(),
            'max_headway': headways.max(),
            'z_active': z_active,
            'station_type': 'J-only' if is_j_only else 'Shared (J+Z)'
        })

    return pd.DataFrame(results)


def get_express_service_window(feed, direction_id, service_id='Weekday'):
    """
    Get the service window for express J trains and Z trains.

    Express J trains are identified as J trains that do not stop at
    Hewes St, Lorimer St, or Flushing Av.

    Parameters:
    -----------
    feed : gtfs_kit.Feed
        A GTFS feed object loaded with gtfs_kit
    direction_id : int
        Direction ID (0 or 1)
    service_id : str, default='Weekday'
        Service ID to filter by

    Returns:
    --------
    tuple
        (first_express_j, first_z, last_z, last_express_j) where each is a
        time string in HH:MM:SS format, or None if no service found
    """
    # Get J and Z trips for this direction
    j_trips = feed.trips[
        (feed.trips['route_id'] == 'J') &
        (feed.trips['direction_id'] == direction_id) &
        (feed.trips['service_id'] == service_id)
    ]

    z_trips = feed.trips[
        (feed.trips['route_id'] == 'Z') &
        (feed.trips['direction_id'] == direction_id) &
        (feed.trips['service_id'] == service_id)
    ]

    # Get the stop IDs for the express-defining stations
    # Express trains skip: Hewes St, Lorimer St, Flushing Av
    express_skip_stops = feed.stops[
        feed.stops['stop_name'].str.contains('Hewes St|Lorimer St|Flushing Av', case=False, na=False)
    ]
    express_skip_stop_ids = set(express_skip_stops['stop_id'])

    # Find express J trips (those that don't stop at Hewes, Lorimer, or Flushing)
    express_j_times = []

    for trip_id in j_trips['trip_id']:
        trip_stops = feed.stop_times[feed.stop_times['trip_id'] == trip_id]
        stop_ids = set(trip_stops['stop_id'])

        # Check if this trip skips all three express-defining stations
        skips_express_stops = len(express_skip_stop_ids & stop_ids) == 0

        if skips_express_stops:
            # This is an express J trip
            first_stop_time = trip_stops.sort_values('stop_sequence').iloc[0]
            express_j_times.append(first_stop_time['departure_time'])

    # Get Z trip times
    z_times = []
    for trip_id in z_trips['trip_id']:
        trip_stops = feed.stop_times[feed.stop_times['trip_id'] == trip_id]
        first_stop_time = trip_stops.sort_values('stop_sequence').iloc[0]
        z_times.append(first_stop_time['departure_time'])

    # Sort times
    express_j_times = sorted(express_j_times) if express_j_times else []
    z_times = sorted(z_times) if z_times else []

    # Return tuple
    first_express_j = express_j_times[0] if express_j_times else None
    first_z = z_times[0] if z_times else None
    last_z = z_times[-1] if z_times else None
    last_express_j = express_j_times[-1] if express_j_times else None

    return (first_express_j, first_z, last_z, last_express_j)


def print_service_timeline(feed, service_id='Weekday'):
    """
    Print a visual timeline showing express J and Z service windows for both directions.

    Parameters:
    -----------
    feed : gtfs_kit.Feed
        A GTFS feed object loaded with gtfs_kit
    service_id : str, default='Weekday'
        Service ID to filter by
    """
    print("="*80)
    print("J/Z EXPRESS SERVICE TIMELINE")
    print("="*80)

    # Get service windows for both directions
    dir0_times = get_express_service_window(feed, 0, service_id)
    dir1_times = get_express_service_window(feed, 1, service_id)

    def format_time(time_str):
        """Convert HH:MM:SS to HH:MM for display"""
        if time_str is None:
            return "N/A"
        return time_str[:5]  # HH:MM

    def time_to_minutes(time_str):
        """Convert HH:MM:SS to minutes since midnight"""
        if time_str is None:
            return None
        parts = time_str.split(':')
        return int(parts[0]) * 60 + int(parts[1])

    # Print direction 0
    print("\nDirection 0 (away from Manhattan):")
    print("-" * 80)
    first_exp_j0, first_z0, last_z0, last_exp_j0 = dir0_times

    print(f"First Express J: {format_time(first_exp_j0)}")
    print(f"First Z train:   {format_time(first_z0)}")
    print(f"Last Z train:    {format_time(last_z0)}")
    print(f"Last Express J:  {format_time(last_exp_j0)}")

    # Draw timeline for direction 0
    if first_z0 and last_z0:
        z_start = time_to_minutes(first_z0)
        z_end = time_to_minutes(last_z0)

        # Timeline from 6 AM to 8 PM (360 to 1200 minutes)
        timeline_start = 6 * 60  # 6 AM
        timeline_end = 20 * 60   # 8 PM
        timeline_width = 60

        print(f"\nTimeline (6 AM - 8 PM):")
        print("Time: ", end="")
        for h in range(6, 21, 2):
            print(f"{h:02d}:00".ljust(8), end="")
        print()
        print("      ", end="")
        print("-" * timeline_width)

        # Z service bar
        print("Z:    ", end="")
        for minute in range(timeline_start, timeline_end, (timeline_end - timeline_start) // timeline_width):
            if z_start <= minute <= z_end:
                print("█", end="")
            else:
                print(" ", end="")
        print()

    # Print direction 1
    print("\n" + "="*80)
    print("\nDirection 1 (toward Manhattan):")
    print("-" * 80)
    first_exp_j1, first_z1, last_z1, last_exp_j1 = dir1_times

    print(f"First Express J: {format_time(first_exp_j1)}")
    print(f"First Z train:   {format_time(first_z1)}")
    print(f"Last Z train:    {format_time(last_z1)}")
    print(f"Last Express J:  {format_time(last_exp_j1)}")

    # Draw timeline for direction 1
    if first_z1 and last_z1:
        z_start = time_to_minutes(first_z1)
        z_end = time_to_minutes(last_z1)

        print(f"\nTimeline (6 AM - 8 PM):")
        print("Time: ", end="")
        for h in range(6, 21, 2):
            print(f"{h:02d}:00".ljust(8), end="")
        print()
        print("      ", end="")
        print("-" * timeline_width)

        # Z service bar
        print("Z:    ", end="")
        for minute in range(timeline_start, timeline_end, (timeline_end - timeline_start) // timeline_width):
            if z_start <= minute <= z_end:
                print("█", end="")
            else:
                print(" ", end="")
        print()

    print("\n" + "="*80)


if __name__ == "__main__":
    import gtfs_kit as gk

    # Load feed
    feed = gk.read_feed("gtfs_subway.zip", dist_units="m")

    # Print summary
    print_skip_stop_summary(feed, direction_id=1, service_id='Weekday')

    print("\n" + "="*80)
    print("HEADWAY ANALYSIS")
    print("="*80)

    # Analyze headways at a shared station
    j_only, z_only, shared = get_skip_stop_stations(feed, 1, 'Weekday')

    if shared:
        print(f"\nHeadways at {shared[5][1]} (shared station):")
        df_shared = get_effective_headway(feed, 1, 'Weekday', stop_id=shared[5][0])
        print(df_shared.to_string(index=False))

    if j_only:
        print(f"\nHeadways at {j_only[3][1]} (J-only skip-stop station):")
        df_j_only = get_effective_headway(feed, 1, 'Weekday', stop_id=j_only[3][0])
        print(df_j_only.to_string(index=False))
