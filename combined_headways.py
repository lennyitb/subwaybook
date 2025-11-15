#!/usr/bin/env python3
"""
Module for calculating combined headways when multiple services share a corridor,
and analyzing headways for specific branches of multi-branch routes.

When multiple subway lines serve the same stops, passengers can take any of them,
so the effective headway is shorter than any individual line's headway. This module
calculates the combined headway - the time between ANY train arriving at a stop,
regardless of which route it is.

Additionally, for routes that split into multiple branches (like the A train to
Lefferts vs Far Rockaway, or the 5 train to different terminals), this module
provides functions to analyze service patterns on individual branches.

Use cases:
- Combined corridor service:
  * Lexington Avenue Line (4/5/6 trains)
  * 8th Avenue Line in Manhattan (A/C/E trains)
  * Queens Boulevard (E/F/M/R trains)
- Branch-specific analysis:
  * A train: Lefferts Blvd vs Far Rockaway vs Rockaway Park
  * 5 train: Different terminal branches
  * D train: Different terminal options
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
    headways_by_hour, trains_by_hour = get_combined_headways_by_hour(
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
        # Get number of trains from trains_by_hour
        num_trains = trains_by_hour.get(hour, 0)

        if hour in headways_by_hour:
            headways = headways_by_hour[hour]
            if headways:
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
                    'num_trains': num_trains,
                    'avg_headway': None,
                    'min_headway': None,
                    'max_headway': None
                })
        else:
            rows.append({
                'hour': hour,
                'num_trains': num_trains,
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
    route_specs = df.attrs.get('route_specs', [])
    route_id = df.attrs.get('route_id', None)
    direction_id = df.attrs.get('direction_id', None)
    direction_name = df.attrs.get('direction_name', '')
    service_id = df.attrs.get('service_id', '')
    branch_terminal = df.attrs.get('branch_terminal', None)
    branch_end_desc = df.attrs.get('branch_end_description', 'to')
    hour_range = df.attrs.get('hour_range', None)

    # Format route string for display
    if route_specs:
        # From get_headway_dist_combined
        if len(route_specs) == 1:
            route_str = f"Route {route_specs[0]}"
        else:
            route_str = f"Routes {', '.join(route_specs)}"
    elif route_list:
        # Multiple routes (from get_headway_dist)
        if len(route_list) == 1:
            route_str = f"Route {route_list[0]}"
        else:
            route_str = f"Routes {'/'.join(route_list)}"
    elif route_id:
        # Single route, possibly branch-specific (from get_headway_dist_branch)
        route_str = f"Route {route_id}"
        if branch_terminal:
            # Use proper description: "from X" or "to X" based on branch location
            if branch_end_desc == "originates from":
                route_str += f" from {branch_terminal}"
            else:
                route_str += f" to {branch_terminal}"
    else:
        route_str = "Unknown Route"

    # Print header
    print(f"\nHeadway Distribution - {route_str}")
    print(f"Direction: {direction_id} ({direction_name})")
    print(f"Service: {service_id}")
    if hour_range:
        print(f"Hours: {hour_range[0]}:00 - {hour_range[1]}:00")
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


def get_headway_dist_branch(feed, route_id, direction_id, branch_terminal,
                            service_id='Weekday', stop_id=None, exclude_first_last=True):
    """
    Get headway distribution DataFrame for a specific branch of a multi-branch route.

    This function is complementary to get_headway_dist() but specifically designed for
    analyzing individual branches of routes that split into multiple terminals (e.g.,
    the A train to Lefferts vs Far Rockaway, or the 5 train to different terminals).

    Unlike get_headway_dist() which combines all services on specified routes, this
    function isolates headways for trips that terminate at a specific branch terminal.
    This is useful for understanding service patterns on individual branches.

    Parameters:
    -----------
    feed : gtfs_kit.Feed
        A GTFS feed object loaded with gtfs_kit. Load with:
        feed = gk.read_feed("gtfs_subway.zip", dist_units="m")

    route_id : str
        Single route ID to analyze (e.g., 'A', '5', 'D')

    direction_id : int
        Direction ID (0 or 1). The meaning varies by route:
        - For most routes: 0 = outbound (away from Manhattan), 1 = inbound (toward Manhattan)
        - Check direction_names.csv or use travel_times.get_direction_name() for specifics

    branch_terminal : str
        Terminal station name or truncated version to identify the branch.
        Can be full name or substring match (case-insensitive).
        Examples:
            - "Ozone Park - Lefferts Blvd" or just "Ozone" or "Lefferts"
            - "Far Rockaway - Mott Av" or just "Far Rockaway"
            - "Flatbush Av - Brooklyn College" or just "Flatbush"

    service_id : str, default='Weekday'
        Service pattern to analyze. Common values:
        - 'Weekday': Monday-Friday service
        - 'Saturday': Saturday service
        - 'Sunday': Sunday/holiday service
        Check your GTFS feed's calendar.txt for available service_ids

    stop_id : str, optional
        Specific stop to measure headways at. If None (default), uses the first
        stop of each trip on the branch. Useful for analyzing service at a specific
        station along the branch.

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
            - num_trains (int): Number of trains in that hour going to this branch
            - avg_headway (float): Average minutes between trains to this branch
            - min_headway (float): Minimum minutes between trains
            - max_headway (float): Maximum minutes between trains

        Metadata (stored in df.attrs):
            - route_id (str): Route ID analyzed
            - direction_id (int): Direction ID used
            - direction_name (str): Human-readable direction name
            - service_id (str): Service pattern analyzed
            - branch_terminal (str): Full terminal station name found
            - branch_terminal_id (str): GTFS stop_id of the terminal

        Notes:
            - Hours with no service have num_trains=0 and None for headway values
            - All headway values are in minutes (float)
            - The DataFrame has 24 rows (one per hour)

    Raises:
    -------
    ValueError
        If no terminal matching branch_terminal is found for the route/direction

    Examples:
    ---------
    Analyze A train to Lefferts branch:
        >>> import gtfs_kit as gk
        >>> import combined_headways as ch
        >>> feed = gk.read_feed("gtfs_subway.zip", dist_units="m")
        >>> df = ch.get_headway_dist_branch(feed, 'A', 0, 'Lefferts', service_id='Weekday')
        >>> ch.print_headway_dist(df)

    Using truncated terminal name:
        >>> # "Ozone" will match "Ozone Park - Lefferts Blvd"
        >>> df = ch.get_headway_dist_branch(feed, 'A', 0, 'Ozone')
        >>> ch.print_headway_dist(df)

    Analyze 5 train to different terminals:
        >>> df_flatbush = ch.get_headway_dist_branch(feed, '5', 0, 'Flatbush')
        >>> df_nereid = ch.get_headway_dist_branch(feed, '5', 1, 'Nereid')

    Compare branch service to overall service:
        >>> # Overall A train service (all branches combined)
        >>> df_all = ch.get_headway_dist(feed, 0, 'A', service_id='Weekday')
        >>> # Just the Lefferts branch
        >>> df_lefferts = ch.get_headway_dist_branch(feed, 'A', 0, 'Lefferts')
        >>> # Compare during rush hour
        >>> all_rush = df_all[df_all['hour'] == 8].iloc[0]['avg_headway']
        >>> lefferts_rush = df_lefferts[df_lefferts['hour'] == 8].iloc[0]['avg_headway']
        >>> print(f"All A trains: {all_rush:.1f} min, Lefferts only: {lefferts_rush:.1f} min")

    Analyze at specific stop:
        >>> # Headways at Hoyt-Schermerhorn for Lefferts branch
        >>> df = ch.get_headway_dist_branch(feed, 'A', 0, 'Lefferts', stop_id='A42')

    See Also:
    ---------
    get_headway_dist : Main function for overall route headways (combines all branches)
    print_headway_dist : Display formatted table from DataFrame
    get_combined_headways_by_hour : Lower-level function for combined routes
    """
    # Get all trips for this route/direction/service
    trips = feed.trips[
        (feed.trips['route_id'] == route_id) &
        (feed.trips['direction_id'] == direction_id) &
        (feed.trips['service_id'] == service_id)
    ].copy()

    if trips.empty:
        raise ValueError(
            f"No trips found for route {route_id}, direction {direction_id}, service {service_id}"
        )

    # Get all stop times for these trips
    stop_times = feed.stop_times[feed.stop_times['trip_id'].isin(trips['trip_id'])].copy()
    stop_times = stop_times.sort_values(['trip_id', 'stop_sequence'])

    # Get both first and last stops for each trip
    first_stops = stop_times.groupby('trip_id').first().reset_index()
    last_stops = stop_times.groupby('trip_id').last().reset_index()

    # For identifying branches, we need to look at the "branch end" of the trip:
    # - For outbound trips: the last stop (terminal/destination)
    # - For inbound trips: the first stop (origin, which was the terminal of the outbound direction)
    #
    # Strategy: First check if the user's specified terminal exists at either end.
    # If found, use that end. Otherwise, use automatic detection based on which end
    # has more significant branches.

    first_stop_unique = first_stops['stop_id'].unique()
    last_stop_unique = last_stops['stop_id'].unique()

    # First, try to find the user's specified terminal at EITHER end
    branch_terminal_lower = branch_terminal.lower()

    # Check first stops (origins)
    matching_first_stop_id = None
    matching_first_stop_name = None
    for stop_id in first_stop_unique:
        stop_name = feed.stops[feed.stops['stop_id'] == stop_id]['stop_name'].values
        if len(stop_name) > 0:
            stop_name = stop_name[0]
            if branch_terminal_lower in stop_name.lower():
                matching_first_stop_id = stop_id
                matching_first_stop_name = stop_name
                break

    # Check last stops (destinations)
    matching_last_stop_id = None
    matching_last_stop_name = None
    for stop_id in last_stop_unique:
        stop_name = feed.stops[feed.stops['stop_id'] == stop_id]['stop_name'].values
        if len(stop_name) > 0:
            stop_name = stop_name[0]
            if branch_terminal_lower in stop_name.lower():
                matching_last_stop_id = stop_id
                matching_last_stop_name = stop_name
                break

    # Determine which end to use based on where we found the terminal
    if matching_first_stop_id is not None and matching_last_stop_id is not None:
        # Terminal found at BOTH ends - use automatic detection
        first_stop_counts = first_stops['stop_id'].value_counts()
        last_stop_counts = last_stops['stop_id'].value_counts()
        min_significant_trips = len(trips) * 0.05
        significant_first_stops = sum(first_stop_counts >= min_significant_trips)
        significant_last_stops = sum(last_stop_counts >= min_significant_trips)

        if significant_first_stops > significant_last_stops:
            branch_stops = first_stops
            branch_end_description = "originates from"
            matching_terminal_id = matching_first_stop_id
            matching_terminal_name = matching_first_stop_name
        elif significant_last_stops > significant_first_stops:
            branch_stops = last_stops
            branch_end_description = "terminates at"
            matching_terminal_id = matching_last_stop_id
            matching_terminal_name = matching_last_stop_name
        else:
            # Tie - use total count as tie-breaker
            if len(first_stop_unique) < len(last_stop_unique):
                branch_stops = first_stops
                branch_end_description = "originates from"
                matching_terminal_id = matching_first_stop_id
                matching_terminal_name = matching_first_stop_name
            else:
                branch_stops = last_stops
                branch_end_description = "terminates at"
                matching_terminal_id = matching_last_stop_id
                matching_terminal_name = matching_last_stop_name
    elif matching_first_stop_id is not None:
        # Found at first stops only (origins)
        branch_stops = first_stops
        branch_end_description = "originates from"
        matching_terminal_id = matching_first_stop_id
        matching_terminal_name = matching_first_stop_name
    elif matching_last_stop_id is not None:
        # Found at last stops only (destinations)
        branch_stops = last_stops
        branch_end_description = "terminates at"
        matching_terminal_id = matching_last_stop_id
        matching_terminal_name = matching_last_stop_name
    else:
        # Terminal not found at either end - build helpful error message
        available_stops = []
        for stop_id in list(first_stop_unique) + list(last_stop_unique):
            stop_name = feed.stops[feed.stops['stop_id'] == stop_id]['stop_name'].values
            if len(stop_name) > 0 and stop_name[0] not in [s.strip("'") for s in available_stops]:
                available_stops.append(f"'{stop_name[0]}'")

        raise ValueError(
            f"No stop matching '{branch_terminal}' found for route {route_id}, "
            f"direction {direction_id}.\nAvailable stops: {', '.join(sorted(set(available_stops)))}"
        )

    # Filter trips to only those associated with this branch
    branch_trip_ids = branch_stops[branch_stops['stop_id'] == matching_terminal_id]['trip_id'].tolist()
    branch_trips = trips[trips['trip_id'].isin(branch_trip_ids)]

    # Get stop times for branch trips
    branch_stop_times = feed.stop_times[
        feed.stop_times['trip_id'].isin(branch_trip_ids)
    ].copy()

    # Filter by specific stop if requested, otherwise use first stop
    if stop_id is not None:
        branch_stop_times = branch_stop_times[branch_stop_times['stop_id'] == stop_id]
        if branch_stop_times.empty:
            raise ValueError(f"No stop times found for stop {stop_id} on this branch")
    else:
        # Use the first stop of each trip
        branch_stop_times = branch_stop_times.sort_values(['trip_id', 'stop_sequence'])
        branch_stop_times = branch_stop_times.groupby('trip_id').first().reset_index()

    def parse_gtfs_time(time_str):
        """Parse GTFS time format (which can exceed 24 hours)"""
        parts = time_str.split(':')
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = int(parts[2])
        return hours, minutes, seconds

    # Convert to total seconds for sorting and headway calculation
    branch_stop_times['departure_seconds'] = branch_stop_times['departure_time'].apply(
        lambda x: sum([parse_gtfs_time(x)[0] * 3600,
                      parse_gtfs_time(x)[1] * 60,
                      parse_gtfs_time(x)[2]])
    )

    # Sort by departure time
    branch_stop_times = branch_stop_times.sort_values('departure_seconds')

    # Calculate headways
    departure_times = branch_stop_times['departure_seconds'].values
    departure_time_strings = branch_stop_times['departure_time'].values

    headways_by_hour = defaultdict(list)

    if len(departure_times) < 2:
        # Not enough trips to calculate headways, return empty DataFrame
        rows = []
        for hour in range(24):
            rows.append({
                'hour': hour,
                'num_trains': 0 if len(departure_times) == 0 else 1,
                'avg_headway': None,
                'min_headway': None,
                'max_headway': None
            })
        df = pd.DataFrame(rows)
    else:
        # Calculate headways between consecutive trains
        for i in range(1, len(departure_times)):
            headway_seconds = departure_times[i] - departure_times[i-1]
            headway_minutes = headway_seconds / 60.0

            # Skip first/last headways if requested
            if exclude_first_last and (i == 1 or i == len(departure_times) - 1):
                continue

            # Assign headway to the hour of the EARLIER train
            earlier_train_time = departure_time_strings[i-1]
            hour = parse_gtfs_time(earlier_train_time)[0] % 24

            headways_by_hour[hour].append(headway_minutes)

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
    df.attrs['route_id'] = route_id
    df.attrs['direction_id'] = direction_id
    df.attrs['service_id'] = service_id
    df.attrs['branch_terminal'] = matching_terminal_name
    df.attrs['branch_terminal_id'] = matching_terminal_id
    df.attrs['branch_end_description'] = branch_end_description

    # Get direction name
    from travel_times import get_direction_name
    df.attrs['direction_name'] = get_direction_name(feed, route_id, direction_id, service_id)

    return df


def get_headway_dist_combined(feed, direction_id, *route_specs, service_id='Weekday',
                                stop_id=None, hour_range=None, exclude_first_last=True):
    """
    Get headway distribution for a combination of routes and/or specific branches.

    This is an enhanced version of get_headway_dist() that allows:
    - Mixing regular routes with specific branch terminals
    - Filtering by time of day (hour range)
    - Analyzing combined service from different routes and branches

    Parameters:
    -----------
    feed : gtfs_kit.Feed
        A GTFS feed object loaded with gtfs_kit

    direction_id : int
        Direction ID (0 or 1)

    *route_specs : str or tuple
        Variable number of route specifications. Each can be:
        - A route ID string: e.g., 'A', '1', '4' (includes all trips on that route)
        - A tuple (route_id, branch_terminal): e.g., ('5', 'Nereid'), ('A', 'Far Rockaway')
          (includes only trips to/from that specific branch)

        Examples:
            'A', 'C'  # All A and C trains
            ('5', 'Nereid')  # Only 5 trains to/from Nereid
            '4', ('5', 'Dyre')  # All 4 trains + 5 trains to/from Dyre

    service_id : str, default='Weekday'
        Service pattern to analyze ('Weekday', 'Saturday', 'Sunday')

    stop_id : str, optional
        Specific stop to measure headways at

    hour_range : tuple of (int, int), optional
        Hour range to filter by, as (start_hour, end_hour) inclusive.
        For example, (7, 9) includes hours 7, 8, and 9.
        If None (default), includes all hours (0-23).

    exclude_first_last : bool, default=True
        Exclude first/last headways to avoid boundary effects

    Returns:
    --------
    pd.DataFrame
        Same structure as get_headway_dist(), with metadata indicating which
        routes/branches were included and the hour range if specified.

        Columns:
            - hour (int): Hour of day (filtered by hour_range if provided)
            - num_trains (int): Number of trains in that hour
            - avg_headway (float): Average minutes between trains
            - min_headway (float): Minimum minutes between trains
            - max_headway (float): Maximum minutes between trains

        Metadata (in df.attrs):
            - route_specs (list): Description of routes/branches included
            - direction_id (int): Direction ID
            - direction_name (str): Human-readable direction name
            - service_id (str): Service pattern
            - hour_range (tuple or None): Hour range filter if provided

    Examples:
    ---------
    All 4/5/6 trains on Lexington Ave:
        >>> df = ch.get_headway_dist_combined(feed, 1, '4', '5', '6', service_id='Weekday')

    Specific branches only:
        >>> # 5 trains to Nereid + A trains to Rockaway Park
        >>> df = ch.get_headway_dist_combined(feed, 0, ('5', 'Nereid'), ('A', 'Rockaway Park'))

    Mix of regular routes and branches:
        >>> # All 4 trains + only 5 trains going to Dyre
        >>> df = ch.get_headway_dist_combined(feed, 1, '4', ('5', 'Dyre'))

    Morning rush hour only (7-9 AM):
        >>> df = ch.get_headway_dist_combined(feed, 1, '4', '5', '6', hour_range=(7, 9))

    Evening rush with specific branch (5-7 PM):
        >>> df = ch.get_headway_dist_combined(feed, 0, ('5', 'Nereid'), hour_range=(17, 19))
    """
    # Parse route specifications and collect trip IDs
    all_trip_ids = []
    route_descriptions = []

    for spec in route_specs:
        if isinstance(spec, tuple):
            # Branch specification: (route_id, branch_terminal)
            route_id, branch_terminal = spec

            # Get trips for this branch using get_headway_dist_branch
            branch_df = get_headway_dist_branch(
                feed, route_id, direction_id, branch_terminal,
                service_id=service_id, stop_id=stop_id, exclude_first_last=exclude_first_last
            )

            # Extract trip IDs from the branch
            trips = feed.trips[
                (feed.trips['route_id'] == route_id) &
                (feed.trips['direction_id'] == direction_id) &
                (feed.trips['service_id'] == service_id)
            ]
            stop_times = feed.stop_times[feed.stop_times['trip_id'].isin(trips['trip_id'])].copy()
            stop_times = stop_times.sort_values(['trip_id', 'stop_sequence'])

            # Get the matching terminal ID from branch_df metadata
            terminal_id = branch_df.attrs['branch_terminal_id']
            branch_end_desc = branch_df.attrs['branch_end_description']

            # Find trips associated with this terminal
            if branch_end_desc == "originates from":
                first_stops = stop_times.groupby('trip_id').first().reset_index()
                branch_trip_ids = first_stops[first_stops['stop_id'] == terminal_id]['trip_id'].tolist()
            else:  # "terminates at"
                last_stops = stop_times.groupby('trip_id').last().reset_index()
                branch_trip_ids = last_stops[last_stops['stop_id'] == terminal_id]['trip_id'].tolist()

            all_trip_ids.extend(branch_trip_ids)

            # Build description
            terminal_name = branch_df.attrs['branch_terminal']
            if branch_end_desc == "originates from":
                route_descriptions.append(f"{route_id} from {terminal_name}")
            else:
                route_descriptions.append(f"{route_id} to {terminal_name}")

        else:
            # Simple route specification: just a route_id string
            route_id = spec

            # Get all trips for this route
            trips = feed.trips[
                (feed.trips['route_id'] == route_id) &
                (feed.trips['direction_id'] == direction_id) &
                (feed.trips['service_id'] == service_id)
            ]

            all_trip_ids.extend(trips['trip_id'].tolist())
            route_descriptions.append(route_id)

    if not all_trip_ids:
        raise ValueError("No trips found for the specified route specifications")

    # Now calculate headways for all collected trips
    combined_trips = feed.trips[feed.trips['trip_id'].isin(all_trip_ids)].copy()

    # Get stop times
    stop_times = feed.stop_times[feed.stop_times['trip_id'].isin(combined_trips['trip_id'])].copy()

    # Filter by specific stop if requested
    if stop_id is not None:
        stop_times = stop_times[stop_times['stop_id'] == stop_id]
        if stop_times.empty:
            raise ValueError(f"No stop times found for stop {stop_id}")
    else:
        # Use the first stop of each trip
        stop_times = stop_times.sort_values(['trip_id', 'stop_sequence'])
        stop_times = stop_times.groupby('trip_id').first().reset_index()

    def parse_gtfs_time(time_str):
        """Parse GTFS time format (which can exceed 24 hours)"""
        parts = time_str.split(':')
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = int(parts[2])
        return hours, minutes, seconds

    # Convert to total seconds for sorting and headway calculation
    stop_times['departure_seconds'] = stop_times['departure_time'].apply(
        lambda x: sum([parse_gtfs_time(x)[0] * 3600,
                      parse_gtfs_time(x)[1] * 60,
                      parse_gtfs_time(x)[2]])
    )

    # Filter by hour range if specified
    if hour_range is not None:
        start_hour, end_hour = hour_range
        stop_times['hour'] = stop_times['departure_time'].apply(
            lambda x: parse_gtfs_time(x)[0] % 24
        )
        stop_times = stop_times[
            (stop_times['hour'] >= start_hour) &
            (stop_times['hour'] <= end_hour)
        ]

    # Sort by departure time
    stop_times = stop_times.sort_values('departure_seconds')

    # Calculate headways
    departure_times = stop_times['departure_seconds'].values
    departure_time_strings = stop_times['departure_time'].values

    headways_by_hour = defaultdict(list)
    trains_by_hour = defaultdict(int)  # Count actual trains per hour

    # Count trains per hour (by departure time)
    for departure_time_str in departure_time_strings:
        hour = parse_gtfs_time(departure_time_str)[0] % 24
        trains_by_hour[hour] += 1

    if len(departure_times) < 2:
        # Not enough trips - return empty DataFrame
        hour_list = range(hour_range[0], hour_range[1] + 1) if hour_range else range(24)
        rows = []
        for hour in hour_list:
            rows.append({
                'hour': hour,
                'num_trains': trains_by_hour.get(hour, 0),
                'avg_headway': None,
                'min_headway': None,
                'max_headway': None
            })
        df = pd.DataFrame(rows)
    else:
        # Calculate headways between consecutive trains
        for i in range(1, len(departure_times)):
            headway_seconds = departure_times[i] - departure_times[i-1]
            headway_minutes = headway_seconds / 60.0

            # Skip first/last headways if requested
            if exclude_first_last and (i == 1 or i == len(departure_times) - 1):
                continue

            # Assign headway to the hour of the EARLIER train
            earlier_train_time = departure_time_strings[i-1]
            hour = parse_gtfs_time(earlier_train_time)[0] % 24

            headways_by_hour[hour].append(headway_minutes)

        # Build DataFrame
        hour_list = range(hour_range[0], hour_range[1] + 1) if hour_range else range(24)
        rows = []
        for hour in hour_list:
            # Use actual train count from trains_by_hour
            num_trains = trains_by_hour.get(hour, 0)

            if hour in headways_by_hour:
                headways = headways_by_hour[hour]
                if headways:
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
                        'num_trains': num_trains,
                        'avg_headway': None,
                        'min_headway': None,
                        'max_headway': None
                    })
            else:
                rows.append({
                    'hour': hour,
                    'num_trains': num_trains,
                    'avg_headway': None,
                    'min_headway': None,
                    'max_headway': None
                })

        df = pd.DataFrame(rows)

    # Add metadata
    df.attrs['route_specs'] = route_descriptions
    df.attrs['direction_id'] = direction_id
    df.attrs['service_id'] = service_id
    df.attrs['hour_range'] = hour_range

    # Get direction name from first route
    from travel_times import get_direction_name
    first_route = route_specs[0] if isinstance(route_specs[0], str) else route_specs[0][0]
    df.attrs['direction_name'] = get_direction_name(feed, first_route, direction_id, service_id)

    return df


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
    trains_by_hour = defaultdict(int)  # Count actual trains per hour

    if len(departure_times) < 2:
        print(f"Not enough trips to calculate headways (found {len(departure_times)})")
        return {}

    # Count trains per hour (by departure time)
    for departure_time_str in departure_time_strings:
        hour = parse_gtfs_time(departure_time_str)[0] % 24
        trains_by_hour[hour] += 1

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

    return dict(headways_by_hour), dict(trains_by_hour)


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
    combined_headways, trains_count = get_combined_headways_by_hour(
        feed, route_ids, direction_id, service_id, stop_id, exclude_first_last
    )

    return {
        'individual': individual_headways,
        'combined': combined_headways,
        'trains_count': trains_count
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

# Example 4: Analyze specific branch headways
# A train has multiple branches - analyze each separately
df_lefferts = get_headway_dist_branch(feed, 'A', 0, 'Lefferts', service_id='Weekday')
print_headway_dist(df_lefferts)

df_far_rockaway = get_headway_dist_branch(feed, 'A', 0, 'Far Rockaway', service_id='Weekday')
print_headway_dist(df_far_rockaway)

# Can use truncated terminal names too
df_ozone = get_headway_dist_branch(feed, 'A', 0, 'Ozone')  # Matches "Ozone Park - Lefferts Blvd"
print_headway_dist(df_ozone)

# Example 5: Compare overall vs branch-specific service
df_all_a = get_headway_dist(feed, 0, 'A', service_id='Weekday')
df_lefferts = get_headway_dist_branch(feed, 'A', 0, 'Lefferts', service_id='Weekday')

print("\\nComparison at 8 AM:")
all_8am = df_all_a[df_all_a['hour'] == 8].iloc[0]
lefferts_8am = df_lefferts[df_lefferts['hour'] == 8].iloc[0]
print(f"All A trains: {all_8am['avg_headway']:.1f} min avg, {all_8am['num_trains']} trains")
print(f"Lefferts only: {lefferts_8am['avg_headway']:.1f} min avg, {lefferts_8am['num_trains']} trains")
""")
