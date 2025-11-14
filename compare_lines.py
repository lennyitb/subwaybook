#!/usr/bin/env python3
"""
Module for comparing travel times between local and express subway lines.

This generates matrices showing the difference in travel time between a local
train and an express train for the same origin-destination pairs.
"""
import gtfs_kit as gk
import travel_times as tt
import express_local as el
import pandas as pd
import numpy as np


def get_shared_express_stops(feed, local_route, express_route, direction_id=1, service_id='Weekday'):
    """
    Get the list of express stops that both routes serve.

    Returns stops in order of direction_id travel, with the last shared stop
    appearing last in the list.

    Parameters:
    -----------
    feed : gtfs_kit.Feed
        A GTFS feed object loaded with gtfs_kit
    local_route : str
        Route ID for the local train (e.g., 'C')
    express_route : str
        Route ID for the express train (e.g., 'A')
    direction_id : int, default=1
        Direction to use for ordering (0 or 1). The last stop in this direction
        will be the last stop in the returned list.
    service_id : str, default='Weekday'
        Service ID to filter by

    Returns:
    --------
    list
        List of (stop_id, stop_name) tuples for shared express stops,
        ordered by direction_id travel
    """
    # Get express stops for the express route (use direction 0 for trunk ordering)
    express_order = tt.get_station_order(feed, express_route, 0, service_id)

    # Apply express filtering to get only express stops
    express_stops = tt.filter_station_order_express(
        feed, express_order, express_route, 0, service_id,
        express_boroughs=['Manhattan', 'Brooklyn'],
        all_stops_boroughs=[]
    )

    # Get all stops for the local route
    local_order = tt.get_station_order(feed, local_route, direction_id, service_id)
    local_stop_ids = set([stop_id for stop_id, _ in local_order])

    # Filter to only stops served by both routes
    shared_stops = []
    for stop_id, stop_name in express_stops:
        if stop_id in local_stop_ids:
            shared_stops.append((stop_id, stop_name))

    # If direction_id is 1, reverse the order so terminal for direction 1 is last
    if direction_id == 1:
        shared_stops = list(reversed(shared_stops))

    return shared_stops


def calculate_travel_time_difference(feed, local_route, express_route,
                                     direction_id=1, service_id='Weekday',
                                     shared_stops=None):
    """
    Calculate the travel time difference between local and express routes.

    Result is local_time - express_time, so positive values mean the express
    train is faster.

    Parameters:
    -----------
    feed : gtfs_kit.Feed
        A GTFS feed object loaded with gtfs_kit
    local_route : str
        Route ID for the local train (e.g., 'C')
    express_route : str
        Route ID for the express train (e.g., 'A')
    direction_id : int, default=1
        Direction to use for ordering stops
    service_id : str, default='Weekday'
        Service ID to filter by
    shared_stops : list, optional
        Pre-computed list of shared stops. If None, will be calculated.

    Returns:
    --------
    pd.DataFrame
        Matrix showing travel time difference (local - express) in minutes
    """
    # Get shared stops if not provided
    if shared_stops is None:
        shared_stops = get_shared_express_stops(
            feed, local_route, express_route, direction_id, service_id
        )

    # Calculate local train matrices
    local_dir0 = tt.calculate_travel_time_matrix(feed, local_route, 0, service_id, shared_stops)
    local_dir1 = tt.calculate_travel_time_matrix(feed, local_route, 1, service_id, shared_stops)
    local_combined = tt.combine_bidirectional_matrix(local_dir0, local_dir1)

    # Calculate express train matrices
    express_dir0 = tt.calculate_travel_time_matrix(feed, express_route, 0, service_id, shared_stops)
    express_dir1 = tt.calculate_travel_time_matrix(feed, express_route, 1, service_id, shared_stops)
    express_combined = tt.combine_bidirectional_matrix(express_dir0, express_dir1)

    # Calculate difference: local - express
    # Positive values mean express is faster
    difference = local_combined - express_combined

    return difference


def print_comparison_summary(difference_matrix, local_route, express_route, service_id='Weekday'):
    """
    Print a summary of the travel time comparison.

    Parameters:
    -----------
    difference_matrix : pd.DataFrame
        The difference matrix from calculate_travel_time_difference()
    local_route : str
        Route ID for the local train
    express_route : str
        Route ID for the express train
    service_id : str, default='Weekday'
        Service ID
    """
    print("="*80)
    print(f"{local_route} Train vs {express_route} Train - Travel Time Difference")
    print(f"{service_id}")
    print("="*80)
    print()
    print(f"Positive values = {express_route} train is FASTER (saves time)")
    print(f"Negative values = {local_route} train is FASTER")
    print(f"Zero/NaN = Same time or no data")
    print()

    # Set pandas display options
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    pd.set_option('display.max_colwidth', None)
    pd.set_option('display.float_format', lambda x: f'{x:6.1f}')

    print(difference_matrix)

    # Print statistics
    print()
    print("="*80)
    print("Statistics")
    print("="*80)

    # Flatten the matrix and remove diagonal (0 values) and NaN
    values = difference_matrix.values.flatten()
    values = values[~np.isnan(values)]
    values = values[values != 0]  # Remove same-station (diagonal) values

    if len(values) > 0:
        print(f"\nTotal origin-destination pairs analyzed: {len(values)}")
        print(f"Average time saved by {express_route}: {np.mean(values):.2f} minutes")
        print(f"Maximum time saved by {express_route}: {np.max(values):.2f} minutes")
        print(f"Minimum difference ({local_route} faster): {np.min(values):.2f} minutes")
        print(f"Median time saved: {np.median(values):.2f} minutes")

        # Count how many times express is faster/slower
        express_faster = np.sum(values > 0)
        local_faster = np.sum(values < 0)
        same_time = np.sum(values == 0)

        print(f"\n{express_route} train is faster: {express_faster} pairs ({100*express_faster/len(values):.1f}%)")
        print(f"{local_route} train is faster: {local_faster} pairs ({100*local_faster/len(values):.1f}%)")
        if same_time > 0:
            print(f"Same time: {same_time} pairs ({100*same_time/len(values):.1f}%)")


def export_comparison(difference_matrix, local_route, express_route, service_id='Weekday',
                     output_dir='.'):
    """
    Export the comparison matrix to CSV.

    Parameters:
    -----------
    difference_matrix : pd.DataFrame
        The difference matrix from calculate_travel_time_difference()
    local_route : str
        Route ID for the local train
    express_route : str
        Route ID for the express train
    service_id : str, default='Weekday'
        Service ID
    output_dir : str, default='.'
        Directory to save the CSV file

    Returns:
    --------
    str
        Path to the exported CSV file
    """
    import os
    filename = f'{local_route}_vs_{express_route}_difference_{service_id}.csv'
    filepath = os.path.join(output_dir, filename)
    difference_matrix.to_csv(filepath)
    return filepath


def compare_lines(feed, local_route, express_route, direction_id=1,
                 service_id='Weekday', export=True, verbose=True):
    """
    Complete workflow to compare local and express train travel times.

    Parameters:
    -----------
    feed : gtfs_kit.Feed
        A GTFS feed object loaded with gtfs_kit
    local_route : str
        Route ID for the local train (e.g., 'C')
    express_route : str
        Route ID for the express train (e.g., 'A')
    direction_id : int, default=1
        Direction to use for ordering stops (last stop in this direction
        will be last in the list)
    service_id : str, default='Weekday'
        Service ID to filter by
    export : bool, default=True
        Whether to export results to CSV
    verbose : bool, default=True
        Whether to print detailed output

    Returns:
    --------
    pd.DataFrame
        The travel time difference matrix
    """
    if verbose:
        print(f"Comparing {local_route} vs {express_route} trains")
        print("="*80)

    # Get shared express stops
    shared_stops = get_shared_express_stops(
        feed, local_route, express_route, direction_id, service_id
    )

    if verbose:
        print(f"\nFound {len(shared_stops)} shared express stops")
        print("\nStations (ordered by direction {}):")
        print(f"(Last stop = terminal for direction {direction_id})")
        for i, (stop_id, stop_name) in enumerate(shared_stops):
            print(f"  {i+1}. {stop_name}")
        print()

    # Calculate difference matrix
    difference_matrix = calculate_travel_time_difference(
        feed, local_route, express_route, direction_id, service_id, shared_stops
    )

    if verbose:
        print_comparison_summary(difference_matrix, local_route, express_route, service_id)

    if export:
        filepath = export_comparison(difference_matrix, local_route, express_route, service_id)
        if verbose:
            print(f"\nExported to {filepath}")

    return difference_matrix


if __name__ == "__main__":
    # Example usage
    print(__doc__)
    print("\nExample: Compare C train (local) vs A train (express)")
    print("="*80)

    # Load GTFS feed
    feed = gk.read_feed("/Users/lennyphelan/Downloads/gtfs_subway.zip", dist_units="m")

    # Compare C vs A
    difference = compare_lines(
        feed,
        local_route='C',
        express_route='A',
        service_id='Weekday',
        export=True,
        verbose=True
    )
