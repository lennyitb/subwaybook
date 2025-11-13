#!/usr/bin/env python3
"""
Generate a reference CSV showing terminal stations for each route/direction.

This helps you verify direction IDs when filling in direction_names.csv
"""
import gtfs_kit as gk
import pandas as pd


def get_terminal_for_direction(feed, route_id, direction_id, service_id='Weekday'):
    """
    Get the terminal station for a route/direction.

    Parameters:
    -----------
    feed : gtfs_kit.Feed
        A GTFS feed object loaded with gtfs_kit
    route_id : str
        The route ID
    direction_id : int
        Direction ID (0 or 1)
    service_id : str, default='Weekday'
        Service ID to use for finding the terminal

    Returns:
    --------
    str
        Terminal station name, or None if not found
    """
    # Get trips for this route/direction/service
    trips = feed.trips[
        (feed.trips['route_id'] == route_id) &
        (feed.trips['direction_id'] == direction_id) &
        (feed.trips['service_id'] == service_id)
    ].copy()

    if trips.empty:
        return None

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
        return terminal_name[0]

    return None


def generate_terminal_reference(feed, service_id='Weekday', output_file='terminal_reference.csv'):
    """
    Generate a CSV showing terminal stations for all routes and directions.

    Parameters:
    -----------
    feed : gtfs_kit.Feed
        A GTFS feed object loaded with gtfs_kit
    service_id : str, default='Weekday'
        Service ID to use for finding terminals
    output_file : str, default='terminal_reference.csv'
        Output CSV filename
    """
    # Get all unique routes
    routes = feed.routes.sort_values('route_id')

    results = []

    for _, route_row in routes.iterrows():
        route_id = route_row['route_id']
        route_long_name = route_row.get('route_long_name', '')

        # Get terminals for both directions
        terminal_0 = get_terminal_for_direction(feed, route_id, 0, service_id)
        terminal_1 = get_terminal_for_direction(feed, route_id, 1, service_id)

        # Only include routes that have at least one direction with service
        if terminal_0 or terminal_1:
            results.append({
                'route_id': route_id,
                'route_name': route_long_name,
                'direction_0_terminal': terminal_0 if terminal_0 else '',
                'direction_1_terminal': terminal_1 if terminal_1 else ''
            })

    # Create DataFrame and save to CSV
    df = pd.DataFrame(results)
    df.to_csv(output_file, index=False)

    print(f"Terminal reference saved to {output_file}")
    print(f"\nFound {len(results)} routes with service on {service_id}:")
    print()
    print(df.to_string(index=False))

    return df


def main():
    # Load GTFS feed
    feed = gk.read_feed("/Users/lennyphelan/Downloads/gtfs_subway.zip", dist_units="m")

    # Generate reference CSV
    generate_terminal_reference(feed, service_id='Weekday', output_file='terminal_reference.csv')


if __name__ == "__main__":
    main()
