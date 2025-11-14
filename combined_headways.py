#!/usr/bin/env python3
"""
Module for calculating combined headways when multiple services share a corridor.

When multiple subway lines serve the same stops, passengers can take any of them,
so the effective headway is shorter than any individual line's headway. This module
calculates the combined headway - the time between ANY train arriving at a stop,
regardless of which route it is.

Use cases:
- Lexington Avenue Line (4/5/6 trains)
- 8th Avenue Line in Manhattan (A/C/E trains)
- Queens Boulevard (E/F/M/R trains)
"""
import gtfs_kit as gk
import pandas as pd
from collections import defaultdict
from datetime import datetime, timedelta


def get_headway_dist(feed, direction_id, *route_ids, service_id='Weekday',
                     stop_id=None, exclude_first_last=True):
    """
    Get headway distribution DataFrame for one or more routes.

    This is the primary function for analyzing train frequency patterns. It calculates
    how often trains arrive, broken down by hour of day. When multiple route IDs are
    provided, it treats them as a combined service (useful for corridors where passengers
    can take any train).

    The function returns a pandas DataFrame with hourly statistics, making it easy to:
    - Analyze service patterns throughout the day
    - Compare rush hour vs off-peak service
    - Export data for further analysis or visualization
    - Calculate metrics like average wait time

    Parameters:
    -----------
    feed : gtfs_kit.Feed
        A GTFS feed object loaded with gtfs_kit. Load with:
        feed = gk.read_feed("gtfs_subway.zip", dist_units="m")

    direction_id : int
        Direction ID (0 or 1). The meaning varies by route:
        - For most routes: 0 = outbound (away from Manhattan), 1 = inbound (toward Manhattan)
        - Check direction_names.csv or use travel_times.get_direction_name() for specifics

    *route_ids : str
        Variable number of route IDs as separate arguments (e.g., '4', '5', '6').
        - Single route: Analyzes that route's headways
        - Multiple routes: Calculates combined headways (time between ANY train)
        Examples:
            get_headway_dist(feed, 1, '4')           # Single route
            get_headway_dist(feed, 1, '4', '5', '6') # Combined 4/5/6 service

    service_id : str, default='Weekday'
        Service pattern to analyze. Common values:
        - 'Weekday': Monday-Friday service
        - 'Saturday': Saturday service
        - 'Sunday': Sunday/holiday service
        Check your GTFS feed's calendar.txt for available service_ids

    stop_id : str, optional
        Specific stop to measure headways at. If None (default), uses the first
        stop of each trip (typically the terminal). Useful for analyzing service
        at a specific station rather than systemwide.

    exclude_first_last : bool, default=True
        If True, excludes the first and last headway of each service period to
        avoid boundary effects (e.g., the long gap between last train of the day
        and first train of the next day appearing as a "headway").

    Returns:
    --------
    pd.DataFrame
        DataFrame with the following structure:

        Columns:
            - hour (int): Hour of day (0-23)
            - num_trains (int): Number of trains in that hour
            - avg_headway (float): Average minutes between trains
            - min_headway (float): Minimum minutes between trains
            - max_headway (float): Maximum minutes between trains

        Metadata (stored in df.attrs):
            - route_ids (list): List of route IDs analyzed
            - direction_id (int): Direction ID used
            - direction_name (str): Human-readable direction name
            - service_id (str): Service pattern analyzed

        Notes:
            - Hours with no service have num_trains=0 and None for headway values
            - All headway values are in minutes (float)
            - The DataFrame has 24 rows (one per hour)

    Examples:
    ---------
    Basic usage - single route:
        >>> import gtfs_kit as gk
        >>> import combined_headways as ch
        >>> feed = gk.read_feed("gtfs_subway.zip", dist_units="m")
        >>> df = ch.get_headway_dist(feed, 1, '4', service_id='Weekday')
        >>> ch.print_headway_dist(df)

    Multiple routes (combined service):
        >>> # Lexington Avenue Line: 4/5/6 combined
        >>> df = ch.get_headway_dist(feed, 1, '4', '5', '6', service_id='Weekday')
        >>> ch.print_headway_dist(df)

    Analyzing specific hours:
        >>> df = ch.get_headway_dist(feed, 1, '4', '5', '6')
        >>> rush_hour = df[df['hour'] == 7].iloc[0]
        >>> print(f"7 AM: {rush_hour['avg_headway']:.1f} min average")

    Exporting to CSV:
        >>> df = ch.get_headway_dist(feed, 1, 'A', 'C', 'E')
        >>> df.to_csv('ace_headways.csv', index=False)

    Comparing time periods:
        >>> morning = df[df['hour'] == 7].iloc[0]['avg_headway']
        >>> evening = df[df['hour'] == 19].iloc[0]['avg_headway']
        >>> print(f"Morning: {morning:.1f} min, Evening: {evening:.1f} min")

    See Also:
    ---------
    print_headway_dist : Display formatted table from DataFrame
    get_combined_headways_by_hour : Lower-level function returning dict
    """

    if len(route_ids) == 0:
        raise ValueError("Must provide at least one route ID")

    # Convert to list for internal use
    route_list = list(route_ids)

    # Calculate combined headways
    headways_by_hour = get_combined_headways_by_hour(
        feed,
        route_list,
        direction_id=direction_id,
        service_id=service_id,
        stop_id=stop_id,
        exclude_first_last=exclude_first_last
    )

    # Build DataFrame
    rows = []
    for hour in range(24):
        if hour in headways_by_hour:
            headways = headways_by_hour[hour]
            if headways:
                num_trains = len(headways)
                avg_hw = sum(headways) / len(headways)
                min_hw = min(headways)
                max_hw = max(headways)

                rows.append({
                    'hour': hour,
                    'num_trains': num_trains,
                    'avg_headway': avg_hw,
                    'min_headway': min_hw,
                    'max_headway': max_hw
                })
            else:
                rows.append({
                    'hour': hour,
                    'num_trains': 0,
                    'avg_headway': None,
                    'min_headway': None,
                    'max_headway': None
                })
        else:
            rows.append({
                'hour': hour,
                'num_trains': 0,
                'avg_headway': None,
                'min_headway': None,
                'max_headway': None
            })

    df = pd.DataFrame(rows)

    # Add metadata as attributes
    df.attrs['route_ids'] = route_list
    df.attrs['direction_id'] = direction_id
    df.attrs['service_id'] = service_id

    # Get direction name
    from travel_times import get_direction_name
    df.attrs['direction_name'] = get_direction_name(feed, route_list[0], direction_id, service_id)

    return df


def print_headway_dist(df):
    """
    Print a formatted headway distribution table from a DataFrame.

    Takes the DataFrame returned by get_headway_dist() and displays it as a
    nicely formatted table with headers and metadata. This function handles
    all the presentation logic, separating it from data generation.

    The output includes:
    - Route(s) being analyzed
    - Direction and direction name
    - Service pattern (Weekday/Saturday/Sunday)
    - Hourly breakdown showing:
        * Hour of day (00:00 - 23:00)
        * Number of trains per hour
        * Average headway (minutes between trains)
        * Minimum headway (shortest gap)
        * Maximum headway (longest gap)

    Parameters:
    -----------
    df : pd.DataFrame
        DataFrame returned by get_headway_dist(). Must have the following:
        - Columns: hour, num_trains, avg_headway, min_headway, max_headway
        - Attributes: route_ids, direction_id, direction_name, service_id

    Returns:
    --------
    None
        Prints directly to stdout

    Examples:
    ---------
    Basic usage:
        >>> df = ch.get_headway_dist(feed, 1, '4', service_id='Weekday')
        >>> ch.print_headway_dist(df)

        Headway Distribution - Route 4
        Direction: 1 (to Manhattan)
        Service: Weekday
        ======================================================================
        Hour   # Trains     Avg (min)    Min (min)    Max (min)
        ----------------------------------------------------------------------
        00:00  3            20.00        20.00        20.00
        01:00  3            20.00        20.00        20.00
        ...

    Multiple routes:
        >>> df = ch.get_headway_dist(feed, 1, '4', '5', '6')
        >>> ch.print_headway_dist(df)

        Headway Distribution - Routes 4/5/6
        Direction: 1 (to Manhattan)
        Service: Weekday
        ...

    Notes:
    ------
    - Hours with no service show '-' for headway values
    - Headways are displayed with 2 decimal places
    - The table is 70 characters wide for terminal display
    - All metadata is read from df.attrs, so the DataFrame must be
      created by get_headway_dist() or have compatible attributes

    See Also:
    ---------
    get_headway_dist : Generate the DataFrame to print
    """
    # Get metadata from DataFrame attributes
    route_list = df.attrs.get('route_ids', [])
    direction_id = df.attrs.get('direction_id', None)
    direction_name = df.attrs.get('direction_name', '')
    service_id = df.attrs.get('service_id', '')

    # Format route string for display
    if len(route_list) == 1:
        route_str = f"Route {route_list[0]}"
    else:
        route_str = f"Routes {'/'.join(route_list)}"

    # Print header
    print(f"\nHeadway Distribution - {route_str}")
    print(f"Direction: {direction_id} ({direction_name})")
    print(f"Service: {service_id}")
    print("=" * 70)
    print(f"{'Hour':<6} {'# Trains':<12} {'Avg (min)':<12} {'Min (min)':<12} {'Max (min)':<12}")
    print("-" * 70)

    # Print data for each hour
    for _, row in df.iterrows():
        hour = int(row['hour'])
        num_trains = int(row['num_trains'])

        if num_trains > 0 and pd.notna(row['avg_headway']):
            avg_hw = row['avg_headway']
            min_hw = row['min_headway']
            max_hw = row['max_headway']
            print(f"{hour:02d}:00  {num_trains:<12} {avg_hw:<12.2f} {min_hw:<12.2f} {max_hw:<12.2f}")
        else:
            print(f"{hour:02d}:00  {num_trains:<12} {'-':<12} {'-':<12} {'-':<12}")


def get_combined_headways_by_hour(feed, route_ids, direction_id=None,
                                   service_id=None, stop_id=None,
                                   exclude_first_last=True):
    """
    Calculate combined headways when multiple routes serve the same corridor.

    This treats all trains from the specified routes as a single service,
    calculating the time between ANY train arriving, regardless of route.

    Parameters:
    -----------
    feed : gtfs_kit.Feed
        A GTFS feed object loaded with gtfs_kit
    route_ids : list of str
        List of route IDs to combine (e.g., ['4', '5', '6'])
    direction_id : int, optional
        Direction ID (0 or 1) to filter by direction. If None, includes both directions.
    service_id : str, optional
        Service ID to filter by (e.g., 'Weekday'). If None, uses all services.
    stop_id : str, optional
        Specific stop to measure headways at. If None, uses first stop of each trip.
    exclude_first_last : bool, default=True
        If True, excludes the first and last headway of the service period to avoid
        boundary effects (e.g., overnight gaps appearing as "headways")

    Returns:
    --------
    dict
        Dictionary with hours (0-23) as keys and lists of headways (in minutes) as values.
        These headways represent the time between ANY train (from any of the routes).
    """

    # Get trips for all specified routes
    all_trips = []
    for route_id in route_ids:
        trips = feed.trips[feed.trips['route_id'] == route_id].copy()

        # Filter by direction if specified
        if direction_id is not None:
            trips = trips[trips['direction_id'] == direction_id]

        # Filter by service_id if specified
        if service_id is not None:
            trips = trips[trips['service_id'] == service_id]

        all_trips.append(trips)

    # Combine all trips
    combined_trips = pd.concat(all_trips, ignore_index=True)

    if combined_trips.empty:
        print(f"No trips found for routes {route_ids}")
        return {}

    # Get stop times for these trips
    stop_times = feed.stop_times[feed.stop_times['trip_id'].isin(combined_trips['trip_id'])].copy()

    # Filter by specific stop if requested
    if stop_id is not None:
        stop_times = stop_times[stop_times['stop_id'] == stop_id]
        if stop_times.empty:
            print(f"No stop times found for stop {stop_id}")
            return {}
    else:
        # Use the first stop of each trip
        stop_times = stop_times.sort_values(['trip_id', 'stop_sequence'])
        stop_times = stop_times.groupby('trip_id').first().reset_index()

    # Merge with trips to get all trip information
    trip_departures = stop_times.merge(
        combined_trips[['trip_id', 'route_id', 'direction_id', 'service_id']],
        on='trip_id'
    )

    def parse_gtfs_time(time_str):
        """Parse GTFS time format (which can exceed 24 hours)"""
        parts = time_str.split(':')
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = int(parts[2])
        return hours, minutes, seconds

    # Convert to total seconds for sorting and headway calculation
    trip_departures['departure_seconds'] = trip_departures['departure_time'].apply(
        lambda x: sum([parse_gtfs_time(x)[0] * 3600,
                      parse_gtfs_time(x)[1] * 60,
                      parse_gtfs_time(x)[2]])
    )

    # Sort by departure time (this naturally combines all routes in chronological order)
    trip_departures = trip_departures.sort_values('departure_seconds')

    # Calculate ALL headways in chronological order
    departure_times = trip_departures['departure_seconds'].values
    departure_time_strings = trip_departures['departure_time'].values

    headways_by_hour = defaultdict(list)

    if len(departure_times) < 2:
        print(f"Not enough trips to calculate headways (found {len(departure_times)})")
        return {}

    # Calculate headways between consecutive trains (ANY route)
    for i in range(1, len(departure_times)):
        headway_seconds = departure_times[i] - departure_times[i-1]
        headway_minutes = headway_seconds / 60.0

        # Skip first/last headways if requested (to avoid overnight gaps)
        if exclude_first_last and (i == 1 or i == len(departure_times) - 1):
            continue

        # Assign headway to the hour of the EARLIER train
        earlier_train_time = departure_time_strings[i-1]
        hour = parse_gtfs_time(earlier_train_time)[0] % 24

        headways_by_hour[hour].append(headway_minutes)

    return dict(headways_by_hour)


def get_individual_and_combined_headways(feed, route_ids, direction_id=None,
                                         service_id=None, stop_id=None,
                                         exclude_first_last=True):
    """
    Calculate both individual route headways and combined headways.

    Useful for comparing how much better service is when combining multiple routes.

    Parameters:
    -----------
    Same as get_combined_headways_by_hour

    Returns:
    --------
    dict
        Dictionary with:
        - 'individual': dict mapping route_id to headways_by_hour
        - 'combined': headways_by_hour for all routes together
    """

    # Import the single-line headway function
    from headways import get_line_headways_by_hour_improved

    # Calculate individual headways for each route
    individual_headways = {}
    for route_id in route_ids:
        headways = get_line_headways_by_hour_improved(
            feed, route_id, direction_id, service_id, stop_id, exclude_first_last
        )
        individual_headways[route_id] = headways

    # Calculate combined headways
    combined_headways = get_combined_headways_by_hour(
        feed, route_ids, direction_id, service_id, stop_id, exclude_first_last
    )

    return {
        'individual': individual_headways,
        'combined': combined_headways
    }


def display_combined_headway_summary(headways_data, route_ids):
    """
    Display a comparison of individual vs combined headways.

    Parameters:
    -----------
    headways_data : dict
        Output from get_individual_and_combined_headways()
    route_ids : list of str
        List of route IDs (for display purposes)
    """
    print(f"\nCombined Headway Analysis for Routes: {', '.join(route_ids)}")
    print("=" * 100)

    # Header
    header = f"{'Hour':<6}"
    for route_id in route_ids:
        header += f"{route_id + ' Avg':<12}"
    header += f"{'Combined':<12} {'Improvement':<12}"
    print(header)
    print("-" * 100)

    # For each hour
    for hour in range(24):
        row = f"{hour:02d}:00  "

        # Individual route averages
        individual_avgs = []
        for route_id in route_ids:
            if route_id in headways_data['individual'] and hour in headways_data['individual'][route_id]:
                headways = headways_data['individual'][route_id][hour]
                if headways:
                    avg = sum(headways) / len(headways)
                    row += f"{avg:<12.2f}"
                    individual_avgs.append(avg)
                else:
                    row += f"{'-':<12}"
            else:
                row += f"{'-':<12}"

        # Combined average
        if hour in headways_data['combined']:
            combined_headways = headways_data['combined'][hour]
            if combined_headways:
                combined_avg = sum(combined_headways) / len(combined_headways)
                row += f"{combined_avg:<12.2f}"

                # Calculate improvement (best individual vs combined)
                if individual_avgs:
                    best_individual = min(individual_avgs)
                    improvement = best_individual - combined_avg
                    improvement_pct = (improvement / best_individual) * 100
                    row += f"{improvement_pct:<12.1f}%"
                else:
                    row += f"{'-':<12}"
            else:
                row += f"{'-':<12}"
                row += f"{'-':<12}"
        else:
            row += f"{'-':<12}"
            row += f"{'-':<12}"

        print(row)


def display_simple_combined_headways(headways_by_hour, route_ids, title=None):
    """
    Display just the combined headways in a simple table.

    Parameters:
    -----------
    headways_by_hour : dict
        Output from get_combined_headways_by_hour()
    route_ids : list of str
        List of route IDs (for display purposes)
    title : str, optional
        Custom title for the table
    """
    if title is None:
        title = f"Combined Headways for Routes: {', '.join(route_ids)}"

    print(f"\n{title}")
    print("=" * 70)
    print(f"{'Hour':<6} {'# Trains':<12} {'Avg (min)':<12} {'Min (min)':<12} {'Max (min)':<12}")
    print("-" * 70)

    for hour in range(24):
        if hour in headways_by_hour:
            headways = headways_by_hour[hour]
            if headways:
                avg_hw = sum(headways) / len(headways)
                min_hw = min(headways)
                max_hw = max(headways)
                num_headways = len(headways)

                print(f"{hour:02d}:00  {num_headways:<12} {avg_hw:<12.2f} {min_hw:<12.2f} {max_hw:<12.2f}")
            else:
                print(f"{hour:02d}:00  {0:<12} {'-':<12} {'-':<12} {'-':<12}")
        else:
            print(f"{hour:02d}:00  {0:<12} {'-':<12} {'-':<12} {'-':<12}")


def analyze_combined_service_pattern(feed, route_ids, direction_id=None, service_id=None):
    """
    Analyze when combined service runs - shows all trains from all routes together.

    Shows first and last departure for each hour across all routes.
    """

    # Get trips for all specified routes
    all_trips = []
    for route_id in route_ids:
        trips = feed.trips[feed.trips['route_id'] == route_id].copy()

        if direction_id is not None:
            trips = trips[trips['direction_id'] == direction_id]

        if service_id is not None:
            trips = trips[trips['service_id'] == service_id]

        all_trips.append(trips)

    combined_trips = pd.concat(all_trips, ignore_index=True)

    if combined_trips.empty:
        print(f"No trips found")
        return

    stop_times = feed.stop_times[feed.stop_times['trip_id'].isin(combined_trips['trip_id'])].copy()
    stop_times = stop_times.sort_values(['trip_id', 'stop_sequence'])
    first_stops = stop_times.groupby('trip_id').first().reset_index()

    # Merge with trips to get route info
    first_stops = first_stops.merge(
        combined_trips[['trip_id', 'route_id']],
        on='trip_id'
    )

    def parse_gtfs_time(time_str):
        parts = time_str.split(':')
        return int(parts[0]), int(parts[1]), int(parts[2])

    first_stops['hour'] = first_stops['departure_time'].apply(
        lambda x: parse_gtfs_time(x)[0] % 24
    )
    first_stops['time_display'] = first_stops['departure_time'].apply(
        lambda x: f"{parse_gtfs_time(x)[0]:02d}:{parse_gtfs_time(x)[1]:02d}"
    )
    first_stops['departure_seconds'] = first_stops['departure_time'].apply(
        lambda x: sum([parse_gtfs_time(x)[0] * 3600,
                      parse_gtfs_time(x)[1] * 60,
                      parse_gtfs_time(x)[2]])
    )

    first_stops = first_stops.sort_values('departure_seconds')

    print(f"\nCombined Service Pattern for Routes {', '.join(route_ids)}" +
          (f", Direction {direction_id}" if direction_id is not None else "") +
          (f", Service {service_id}" if service_id is not None else ""))
    print("-" * 70)
    print(f"{'Hour':<6} {'Total Deps':<12} {'First':<15} {'Last':<15} {'Routes':<20}")
    print("-" * 70)

    for hour in range(24):
        hour_stops = first_stops[first_stops['hour'] == hour]
        if len(hour_stops) > 0:
            first_time = hour_stops['time_display'].iloc[0]
            last_time = hour_stops['time_display'].iloc[-1]
            count = len(hour_stops)
            routes_in_hour = sorted(hour_stops['route_id'].unique())
            routes_str = ', '.join(routes_in_hour)
            print(f"{hour:02d}:00  {count:<12} {first_time:<15} {last_time:<15} {routes_str:<20}")
        else:
            print(f"{hour:02d}:00  {0:<12} {'-':<15} {'-':<15} {'-':<20}")


if __name__ == "__main__":
    print(__doc__)
    print("""
EXAMPLE USAGE:

# Load your GTFS feed
feed = gk.read_feed("gtfs_subway.zip", dist_units='m')

# Example 1: Lexington Avenue Line (4/5/6 trains)
# Calculate combined headways for all three routes
combined_data = get_individual_and_combined_headways(
    feed,
    route_ids=['4', '5', '6'],
    direction_id=1,  # Southbound
    service_id='Weekday'
)

display_combined_headway_summary(combined_data, ['4', '5', '6'])

# Example 2: Just get combined headways without individual breakdown
combined_only = get_combined_headways_by_hour(
    feed,
    route_ids=['A', 'C', 'E'],
    direction_id=0,
    service_id='Weekday',
    stop_id='A24'  # 59 St-Columbus Circle
)

# Example 3: Analyze service pattern
analyze_combined_service_pattern(
    feed,
    route_ids=['4', '5', '6'],
    direction_id=1,
    service_id='Weekday'
)
""")
