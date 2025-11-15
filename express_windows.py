#!/usr/bin/env python3
"""
Module for generating and accessing express service window data for all NYC subway routes.

This module provides functionality to:
1. Generate express service windows for all routes across all service patterns (Weekday, Saturday, Sunday)
   and export to JSON
2. Load and query express service window data by service pattern, route, direction, and borough

Express service windows indicate the time periods during which trains run express
(skip stops) in each borough they pass through. The data is organized by service pattern
to allow querying express service times for different days of the week.
"""
import json
import gtfs_kit as gk
import express_local as el
import skip_stop as ss
from travel_times import get_direction_name
from pathlib import Path


def _normalize_borough_name(borough):
    """
    Normalize borough names to their proper display format.

    Parameters:
    -----------
    borough : str
        Borough name (e.g., 'Bronx', 'Manhattan')

    Returns:
    --------
    str
        Properly formatted borough name (e.g., 'The Bronx', 'Manhattan')
    """
    if borough == 'Bronx':
        return 'The Bronx'
    return borough


def generate_express_windows(feed, service_ids=None, output_file='express_window_data.json'):
    """
    Generate express service window data for all subway routes and save to JSON.

    This function analyzes all NYC subway routes (including express variants like 6X, 7X, FX)
    and determines when each route runs express service in each borough, broken down by
    direction and service pattern (Weekday, Saturday, Sunday).

    Parameters:
    -----------
    feed : gtfs_kit.Feed
        A GTFS feed object loaded with gtfs_kit
    service_ids : str, list of str, or None, default=None
        Service ID(s) to analyze. Can be:
        - A single service ID string (e.g., 'Weekday')
        - A list of service IDs (e.g., ['Weekday', 'Saturday', 'Sunday'])
        - None to analyze all service IDs found in the feed
    output_file : str, default='express_window_data.json'
        Path to output JSON file

    Returns:
    --------
    dict
        Dictionary mapping service_id -> route_id -> direction_id -> borough -> (first_time, last_time)

    Notes:
    ------
    - J/Z trains use skip_stop.get_express_service_window() for special handling
    - Express variants (6X, 7X, FX) run express in outer boroughs, local in Manhattan
    - All hardcoded special cases from express_local.py are applied

    Example output structure:
    {
        "Weekday": {
            "A": {
                "0": {
                    "direction_name": "to Manhattan",
                    "Brooklyn": ["05:12:30", "22:18:00"],
                    "Manhattan": ["05:12:30", "22:18:00"]
                },
                "1": { ... }
            },
            ...
        },
        "Saturday": {
            "A": { ... }
        },
        "Sunday": {
            "A": { ... }
        }
    }
    """
    # Determine which service_ids to process
    if service_ids is None:
        # Get all unique service_ids from the feed
        service_ids_to_process = sorted(feed.trips['service_id'].unique().tolist())
        print(f"Auto-detected service IDs: {service_ids_to_process}")
    elif isinstance(service_ids, str):
        # Single service_id provided as string
        service_ids_to_process = [service_ids]
    else:
        # List of service_ids provided
        service_ids_to_process = service_ids

    # All standard routes (excluding J/Z which need special handling)
    standard_routes = ['A', 'C', 'E', 'B', 'D', 'F', 'M', 'N', 'Q', 'R', 'W',
                      '1', '2', '3', '4', '5', '6', '7', 'L', 'G', 'S']

    # Express variants (X trains)
    express_variants = ['6X', '7X', 'FX']

    # J/Z trains need special handling
    jz_routes = ['J', 'Z']

    all_routes = standard_routes + express_variants + jz_routes

    result = {}

    # Process each service_id
    for service_id in service_ids_to_process:
        print(f"\n{'='*80}")
        print(f"Processing service_id: {service_id}")
        print(f"{'='*80}")

        service_result = {}

        for route_id in all_routes:
            route_data = {}

            # Check if this route exists in the feed for this service_id
            route_trips = feed.trips[
                (feed.trips['route_id'] == route_id) &
                (feed.trips['service_id'] == service_id)
            ]
            if route_trips.empty:
                continue

            print(f"  Processing {route_id} train...")

            # Get available directions for this route
            available_directions = route_trips['direction_id'].unique()

            for direction_id in available_directions:
                direction_data = {}

                # Get direction name
                try:
                    direction_name = get_direction_name(feed, route_id, direction_id, service_id)
                    direction_data['direction_name'] = direction_name
                except:
                    direction_data['direction_name'] = f"Direction {direction_id}"

                # Handle J/Z trains specially
                if route_id in jz_routes:
                    try:
                        first_exp_j, first_z, last_z, last_exp_j = ss.get_express_service_window(
                            feed, direction_id, service_id
                        )

                        if route_id == 'J':
                            if first_exp_j and last_exp_j:
                                direction_data['express_J'] = [first_exp_j, last_exp_j]
                        elif route_id == 'Z':
                            if first_z and last_z:
                                direction_data['Z_service'] = [first_z, last_z]
                    except Exception as e:
                        print(f"    Error processing {route_id} direction {direction_id}: {e}")

                # Handle express variants (X trains)
                elif route_id in express_variants:
                    # X trains run express in outer boroughs, local in Manhattan
                    base_route = route_id[0]  # '6X' -> '6', '7X' -> '7', 'FX' -> 'F'

                    # Get all boroughs this route passes through
                    try:
                        patterns = el.analyze_route_express_patterns(feed, route_id, direction_id, service_id)
                        if not patterns.empty:
                            borough_cols = [col for col in patterns.columns
                                           if col in ['Manhattan', 'Brooklyn', 'Queens', 'Bronx', 'Staten Island']]

                            # Get trip times for this route
                            trip_times = []
                            for trip_id in patterns['trip_id'].head(10):  # Sample trips
                                stop_times = feed.stop_times[feed.stop_times['trip_id'] == trip_id]
                                if not stop_times.empty:
                                    stop_times = stop_times.sort_values('stop_sequence')
                                    first_dep = stop_times.iloc[0]['departure_time']
                                    last_dep = stop_times.iloc[-1]['departure_time']
                                    trip_times.append((first_dep, last_dep))

                            if trip_times:
                                # X trains run during specific hours - use actual trip times
                                first_time = min(t[0] for t in trip_times)
                                last_time = max(t[1] for t in trip_times)

                                for boro in borough_cols:
                                    if boro != 'Manhattan':
                                        # Express in outer boroughs
                                        normalized_boro = _normalize_borough_name(boro)
                                        direction_data[normalized_boro] = [first_time, last_time]
                                    # Local in Manhattan - don't add to express windows
                    except Exception as e:
                        print(f"    Error processing {route_id} direction {direction_id}: {e}")

                # Handle standard routes
                else:
                    try:
                        windows = el.get_express_service_window(
                            feed, route_id, direction_id, service_id
                        )

                        if isinstance(windows, dict) and windows:
                            for borough, (first, last) in windows.items():
                                normalized_boro = _normalize_borough_name(borough)
                                direction_data[normalized_boro] = [first, last]
                    except Exception as e:
                        print(f"    Error processing {route_id} direction {direction_id}: {e}")

                if direction_data:
                    route_data[str(direction_id)] = direction_data

            if route_data:
                service_result[route_id] = route_data

        if service_result:
            result[service_id] = service_result

    # Save to JSON
    with open(output_file, 'w') as f:
        json.dump(result, f, indent=2)

    print(f"\nExpress window data saved to {output_file}")
    return result


def load_express_windows(json_file='express_window_data.json'):
    """
    Load express service window data from JSON file.

    Parameters:
    -----------
    json_file : str, default='express_window_data.json'
        Path to JSON file containing express window data

    Returns:
    --------
    dict
        Dictionary mapping service_id -> route_id -> direction_id -> borough -> (first_time, last_time)

    Raises:
    -------
    FileNotFoundError
        If the JSON file doesn't exist

    Example:
    --------
    >>> data = load_express_windows()
    >>> print(data['Weekday']['A']['0']['Manhattan'])
    ['05:12:30', '22:18:00']
    """
    if not Path(json_file).exists():
        raise FileNotFoundError(
            f"Express window data file '{json_file}' not found. "
            f"Run generate_express_windows() first to create it."
        )

    with open(json_file, 'r') as f:
        return json.load(f)


def get_express_window(route_id, direction_id, service_id='Weekday', borough=None, json_file='express_window_data.json'):
    """
    Get express service window for a specific route, direction, service pattern, and optionally borough.

    Parameters:
    -----------
    route_id : str
        Route ID (e.g., 'A', 'D', '2', '6X')
    direction_id : int
        Direction ID (0 or 1)
    service_id : str, default='Weekday'
        Service ID (e.g., 'Weekday', 'Saturday', 'Sunday')
    borough : str, optional
        Specific borough to get window for (e.g., 'Manhattan', 'Brooklyn')
        If None, returns all boroughs
    json_file : str, default='express_window_data.json'
        Path to JSON file containing express window data

    Returns:
    --------
    dict or list or None
        If borough is None:
            Returns dict mapping borough -> [first_time, last_time]
        If borough is specified:
            Returns [first_time, last_time] for that borough, or None if no express service

    Raises:
    -------
    KeyError
        If service_id, route, or direction not found in data

    Examples:
    ---------
    >>> # Get all boroughs for A train northbound on weekdays
    >>> get_express_window('A', 0, 'Weekday')
    {'Manhattan': ['05:12:30', '22:18:00'], 'Brooklyn': ['05:12:30', '22:18:00']}

    >>> # Get specific borough
    >>> get_express_window('A', 0, 'Weekday', 'Manhattan')
    ['05:12:30', '22:18:00']

    >>> # No express service
    >>> get_express_window('C', 0, 'Weekday', 'Manhattan')
    None
    """
    data = load_express_windows(json_file)

    if service_id not in data:
        raise KeyError(f"Service ID '{service_id}' not found in express window data")

    if route_id not in data[service_id]:
        raise KeyError(f"Route '{route_id}' not found for service '{service_id}'")

    direction_str = str(direction_id)
    if direction_str not in data[service_id][route_id]:
        raise KeyError(f"Direction {direction_id} not found for route '{route_id}' on service '{service_id}'")

    direction_data = data[service_id][route_id][direction_str].copy()

    # Remove metadata fields
    if 'direction_name' in direction_data:
        del direction_data['direction_name']

    if borough is None:
        return direction_data
    else:
        return direction_data.get(borough)


def print_express_windows(route_id=None, service_id=None, json_file='express_window_data.json'):
    """
    Pretty-print express service windows for routes.

    Parameters:
    -----------
    route_id : str, optional
        Specific route to print. If None, prints all routes
    service_id : str, optional
        Specific service ID to print. If None, prints all service IDs
    json_file : str, default='express_window_data.json'
        Path to JSON file containing express window data

    Example:
    --------
    >>> print_express_windows('A', 'Weekday')
    Weekday Service - A Train
    ========================================
    to Manhattan:
      Brooklyn       : 05:12:30 → 22:18:00
      Manhattan      : 05:12:30 → 22:18:00
    ...
    """
    data = load_express_windows(json_file)

    services_to_print = [service_id] if service_id else sorted(data.keys())

    for service in services_to_print:
        if service not in data:
            print(f"Service '{service}' not found in data")
            continue

        routes_to_print = [route_id] if route_id else sorted(data[service].keys())

        for route in routes_to_print:
            if route not in data[service]:
                print(f"Route '{route}' not found for service '{service}'")
                continue

            print(f"\n{service} Service - {route} Train")
            print("=" * 80)

            for direction_id, direction_data in data[service][route].items():
                direction_name = direction_data.get('direction_name', f'Direction {direction_id}')
                print(f"\n{direction_name}:")
                print("-" * 80)

                # Filter out metadata
                express_windows = {k: v for k, v in direction_data.items()
                                 if k not in ['direction_name', 'express_J', 'Z_service']}

                # Print special J/Z fields
                if 'express_J' in direction_data:
                    first, last = direction_data['express_J']
                    print(f"  {'Express J':15s}: {first} → {last}")
                if 'Z_service' in direction_data:
                    first, last = direction_data['Z_service']
                    print(f"  {'Z service':15s}: {first} → {last}")

                if express_windows:
                    for borough, (first, last) in sorted(express_windows.items()):
                        print(f"  {borough:15s}: {first} → {last}")
                else:
                    if 'express_J' not in direction_data and 'Z_service' not in direction_data:
                        print("  No express service")


if __name__ == '__main__':
    """
    Generate express window data for all routes across all service patterns.
    Run this script directly to regenerate the express_window_data.json file.
    """
    print("Loading GTFS feed...")
    feed = gk.read_feed("gtfs_subway.zip", dist_units="m")

    print("\n" + "="*80)
    print("GENERATING EXPRESS SERVICE WINDOWS - ALL SERVICE PATTERNS")
    print("="*80 + "\n")

    # Generate for common service patterns (Weekday, Saturday, Sunday)
    # You can also pass None to auto-detect all service_ids from the feed
    data = generate_express_windows(feed, service_ids=['Weekday', 'Saturday', 'Sunday'])

    print("\n" + "="*80)
    print("GENERATION COMPLETE")
    print("="*80)

    # Count routes per service
    for service_id, routes in data.items():
        print(f"\n{service_id}: {len(routes)} routes processed")

    print(f"\nOutput file: express_window_data.json")
    print("\nUse load_express_windows() or get_express_window() to access the data.")
    print("Example: get_express_window('A', 0, 'Weekday', 'Manhattan')")
