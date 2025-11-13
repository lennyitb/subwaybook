import gtfs_kit as gk
import pandas as pd
from collections import defaultdict
from shapely.geometry import Point, Polygon


"""
EXPRESS/LOCAL CLASSIFICATION SYSTEM

This module determines whether each trip on a subway route runs express or local
service within each NYC borough it passes through.

METHODOLOGY:
1. Map all stops to their NYC borough using coordinate-based polygons
2. For each route/direction combination, identify branch points (where routes split)
3. For each route/direction/branch, find the reference "all stops" pattern
4. Compare each trip's stop pattern against the reference to determine if it's
   express (skips stops) or local (makes all stops) in each borough

SPECIAL CASES:
- Multi-branch routes (A, 5): Branch is detected and analyzed separately
- Routes with no express service: All trips classified as local
- J/Z lines: Excluded from analysis (uses different track system)
"""


def get_stop_borough(lat, lon):
    """
    Determine which NYC borough a stop is in based on its coordinates.

    Uses approximate polygon boundaries for the five boroughs.

    Parameters:
    -----------
    lat : float
        Latitude of the stop
    lon : float
        Longitude of the stop

    Returns:
    --------
    str or None
        'Manhattan', 'Brooklyn', 'Queens', 'Bronx', 'Staten Island', or None

    Note: These are simplified polygons focused on subway service areas.
    Edge cases near borough boundaries may be slightly imprecise.
    """
    point = Point(lon, lat)

    # Manhattan (roughly bounded by rivers)
    # Extends from Battery Park (~40.70) to Inwood (~40.88)
    manhattan = Polygon([
        (-74.019, 40.700),  # Battery Park
        (-74.015, 40.710),  # West Village
        (-74.011, 40.730),  # Chelsea
        (-74.007, 40.760),  # Hell's Kitchen
        (-73.988, 40.810),  # Upper West Side
        (-73.950, 40.865),  # Washington Heights
        (-73.920, 40.878),  # Inwood
        (-73.934, 40.877),  # Marble Hill area
        (-73.936, 40.865),  # East Harlem north
        (-73.937, 40.800),  # East Harlem
        (-73.950, 40.770),  # Upper East Side
        (-73.968, 40.750),  # Midtown East
        (-73.972, 40.730),  # Gramercy
        (-73.985, 40.710),  # East Village
        (-73.995, 40.705),  # Lower East Side
        (-74.012, 40.704),  # Financial District
        (-74.019, 40.700),  # Close polygon
    ])

    # Brooklyn (west and central portions with subway service)
    brooklyn = Polygon([
        (-74.030, 40.695),  # Brooklyn Heights
        (-74.020, 40.640),  # Sunset Park
        (-74.010, 40.600),  # Bay Ridge
        (-73.990, 40.575),  # Coney Island west
        (-73.975, 40.573),  # Coney Island
        (-73.945, 40.580),  # Sheepshead Bay
        (-73.930, 40.595),  # Marine Park
        (-73.900, 40.615),  # Canarsie
        (-73.872, 40.645),  # East New York
        (-73.903, 40.675),  # Bushwick
        (-73.920, 40.695),  # Williamsburg
        (-73.940, 40.705),  # Greenpoint
        (-73.985, 40.710),  # DUMBO
        (-74.012, 40.704),  # Brooklyn Bridge
        (-74.030, 40.695),  # Close polygon
    ])

    # Queens (all portions with subway service - clockwise from northwest)
    queens = Polygon([
        (-73.945, 40.743),  # Astoria west
        (-73.920, 40.765),  # Astoria north
        (-73.892, 40.768),  # East Elmhurst
        (-73.880, 40.775),  # LaGuardia area
        (-73.870, 40.765),  # Jackson Heights north
        (-73.860, 40.755),  # Woodside north
        (-73.850, 40.752),  # Elmhurst
        (-73.840, 40.745),  # Rego Park north
        (-73.830, 40.765),  # Flushing
        (-73.825, 40.760),  # Flushing south
        (-73.820, 40.750),  # Corona
        (-73.810, 40.720),  # Forest Hills
        (-73.800, 40.710),  # Kew Gardens
        (-73.790, 40.705),  # Richmond Hill
        (-73.783, 40.715),  # Jamaica
        (-73.778, 40.710),  # Jamaica south
        (-73.775, 40.700),  # Ozone Park
        (-73.765, 40.690),  # Howard Beach north
        (-73.760, 40.680),  # Howard Beach
        (-73.755, 40.605),  # Far Rockaway (southernmost)
        (-73.840, 40.580),  # Rockaway Park
        (-73.870, 40.595),  # Rockaway east edge
        (-73.900, 40.615),  # Jamaica Bay border
        (-73.900, 40.660),  # Broad Channel north
        (-73.870, 40.670),  # East New York border
        (-73.900, 40.680),  # Woodhaven
        (-73.920, 40.695),  # Ridgewood
        (-73.940, 40.705),  # LIC waterfront south
        (-73.950, 40.720),  # LIC east
        (-73.945, 40.743),  # Close polygon
    ])

    # Bronx (all portions with subway service - clockwise from south)
    bronx = Polygon([
        (-73.938, 40.795),  # Harlem River south (expanded west)
        (-73.933, 40.805),  # Mott Haven
        (-73.930, 40.815),  # Yankee Stadium (expanded west)
        (-73.928, 40.825),  # Concourse south (expanded west)
        (-73.925, 40.835),  # Concourse (expanded west)
        (-73.920, 40.845),  # Concourse north
        (-73.910, 40.855),  # Fordham
        (-73.895, 40.865),  # Norwood south
        (-73.890, 40.875),  # Norwood
        (-73.880, 40.890),  # Woodlawn
        (-73.870, 40.900),  # Wakefield
        (-73.860, 40.905),  # Wakefield east
        (-73.850, 40.910),  # Northeast Bronx
        (-73.840, 40.905),  # Eastchester
        (-73.825, 40.895),  # Baychester
        (-73.815, 40.885),  # Pelham Bay
        (-73.820, 40.870),  # Morris Park
        (-73.830, 40.855),  # Westchester Square
        (-73.847, 40.840),  # Parkchester
        (-73.860, 40.830),  # Soundview
        (-73.875, 40.820),  # West Farms
        (-73.890, 40.815),  # Melrose east
        (-73.905, 40.810),  # Melrose
        (-73.920, 40.800),  # Mott Haven east
        (-73.938, 40.795),  # Close polygon
    ])

    # Staten Island (North Shore with ferry terminal and SIR)
    staten_island = Polygon([
        (-74.250, 40.650),  # Tottenville area
        (-74.150, 40.550),  # South Shore
        (-74.070, 40.580),  # Great Kills
        (-74.075, 40.610),  # New Dorp
        (-74.090, 40.630),  # Stapleton
        (-74.074, 40.644),  # St. George
        (-74.085, 40.650),  # West Brighton
        (-74.135, 40.630),  # Bulls Head
        (-74.180, 40.620),  # Charleston
        (-74.250, 40.650),  # Close polygon
    ])

    # Check which borough contains the point
    if manhattan.contains(point):
        return 'Manhattan'
    elif brooklyn.contains(point):
        return 'Brooklyn'
    elif queens.contains(point):
        return 'Queens'
    elif bronx.contains(point):
        return 'Bronx'
    elif staten_island.contains(point):
        return 'Staten Island'
    else:
        return None


def create_stop_borough_mapping(feed):
    """
    Create a mapping of all stops to their boroughs.

    Includes both parent stations (location_type=1) AND platforms (location_type=NA),
    since stop_times references platforms, not parent stations.

    Parameters:
    -----------
    feed : gtfs_kit.Feed
        A GTFS feed object loaded with gtfs_kit

    Returns:
    --------
    pd.DataFrame
        DataFrame with columns: stop_id, stop_name, borough, stop_lat, stop_lon
    """
    # Include all stops that have coordinates (stations and platforms)
    stops = feed.stops[feed.stops['stop_lat'].notna()].copy()

    stops['borough'] = stops.apply(
        lambda row: get_stop_borough(row['stop_lat'], row['stop_lon']),
        axis=1
    )

    return stops[['stop_id', 'stop_name', 'borough', 'stop_lat', 'stop_lon']].sort_values('stop_name')


def identify_branch_point(feed, route_id, direction_id):
    """
    Identify where a multi-branch route splits into different branches.

    For routes like the A train (splits to Lefferts Blvd, Far Rockaway, or Rockaway Park)
    or the 5 train (splits to different terminals), this finds the common trunk
    and identifies where branches diverge.

    Parameters:
    -----------
    feed : gtfs_kit.Feed
        A GTFS feed object loaded with gtfs_kit
    route_id : str
        The route ID (e.g., 'A', '5')
    direction_id : int
        Direction ID (0 or 1)

    Returns:
    --------
    tuple
        (branch_point_stop_id, branches_dict)
        where branches_dict maps terminal_stop_id -> list of trip_ids going to that terminal
    """
    # Get all trips for this route/direction
    trips = feed.trips[
        (feed.trips['route_id'] == route_id) &
        (feed.trips['direction_id'] == direction_id)
    ].copy()

    if trips.empty:
        return None, {}

    # Get the last stop for each trip (the terminal)
    stop_times = feed.stop_times[feed.stop_times['trip_id'].isin(trips['trip_id'])].copy()
    stop_times = stop_times.sort_values(['trip_id', 'stop_sequence'])

    # Get terminal stops
    terminals = stop_times.groupby('trip_id').last().reset_index()
    terminal_counts = terminals['stop_id'].value_counts()

    # If there's only one terminal, no branching
    if len(terminal_counts) == 1:
        return None, {terminal_counts.index[0]: trips['trip_id'].tolist()}

    # Find the common stops (stops that ALL trips pass through)
    # Group trips by terminal
    trips_by_terminal = {}
    for terminal in terminal_counts.index:
        terminal_trip_ids = terminals[terminals['stop_id'] == terminal]['trip_id'].tolist()
        trips_by_terminal[terminal] = terminal_trip_ids

    # Find common stops across all branches
    # Get stop sequences for a sample trip from each branch
    common_stops = None
    for terminal, trip_ids in trips_by_terminal.items():
        sample_trip = trip_ids[0]
        trip_stops = stop_times[stop_times['trip_id'] == sample_trip].sort_values('stop_sequence')
        trip_stop_ids = set(trip_stops['stop_id'].tolist())

        if common_stops is None:
            common_stops = trip_stop_ids
        else:
            common_stops = common_stops.intersection(trip_stop_ids)

    # The branch point is the last common stop
    if common_stops:
        # Find the last common stop in sequence
        sample_trip = terminals['trip_id'].iloc[0]
        trip_stops = stop_times[stop_times['trip_id'] == sample_trip].sort_values('stop_sequence')
        common_in_sequence = trip_stops[trip_stops['stop_id'].isin(common_stops)]
        if not common_in_sequence.empty:
            branch_point = common_in_sequence['stop_id'].iloc[-1]
            return branch_point, trips_by_terminal

    return None, trips_by_terminal


def get_reference_stop_pattern(feed, route_id, direction_id, branch_terminal=None):
    """
    Find the reference "all stops" pattern for a route/direction/branch.

    This is the trip that makes the most stops, which we'll use as the baseline
    to determine if other trips are running express.

    Parameters:
    -----------
    feed : gtfs_kit.Feed
        A GTFS feed object loaded with gtfs_kit
    route_id : str
        The route ID (e.g., 'A', 'C')
    direction_id : int
        Direction ID (0 or 1)
    branch_terminal : str, optional
        For multi-branch routes, the terminal stop ID to identify which branch

    Returns:
    --------
    list
        Ordered list of stop_ids representing the complete local stop pattern
    """
    # Get trips for this route/direction
    trips = feed.trips[
        (feed.trips['route_id'] == route_id) &
        (feed.trips['direction_id'] == direction_id)
    ].copy()

    if trips.empty:
        return []

    # If branch terminal specified, filter to trips ending at that terminal
    if branch_terminal:
        stop_times = feed.stop_times[feed.stop_times['trip_id'].isin(trips['trip_id'])].copy()
        stop_times = stop_times.sort_values(['trip_id', 'stop_sequence'])
        terminals = stop_times.groupby('trip_id').last().reset_index()
        terminal_trips = terminals[terminals['stop_id'] == branch_terminal]['trip_id'].tolist()
        trips = trips[trips['trip_id'].isin(terminal_trips)]

    if trips.empty:
        return []

    # Count stops for each trip
    stop_times = feed.stop_times[feed.stop_times['trip_id'].isin(trips['trip_id'])].copy()
    stop_counts = stop_times.groupby('trip_id').size()

    # Find the trip with the most stops (the local train)
    max_stops_trip_id = stop_counts.idxmax()

    # Get the stop pattern for this trip
    reference_stops = stop_times[stop_times['trip_id'] == max_stops_trip_id].sort_values('stop_sequence')

    return reference_stops['stop_id'].tolist()


def classify_trip_express_local(feed, trip_id, reference_stop_pattern, stop_borough_map):
    """
    Classify whether a trip runs express or local in each borough it passes through.

    Parameters:
    -----------
    feed : gtfs_kit.Feed
        A GTFS feed object loaded with gtfs_kit
    trip_id : str
        The trip ID to classify
    reference_stop_pattern : list
        The reference "all stops" pattern (list of stop_ids)
    stop_borough_map : dict
        Dictionary mapping stop_id -> borough name

    Returns:
    --------
    dict
        Dictionary mapping borough -> 'express' or 'local'
        Only includes boroughs where the trip actually runs
    """
    # Get stops for this trip
    stop_times = feed.stop_times[feed.stop_times['trip_id'] == trip_id].copy()
    stop_times = stop_times.sort_values('stop_sequence')
    trip_stops = set(stop_times['stop_id'].tolist())

    # Group reference stops by borough
    reference_by_borough = defaultdict(list)
    for stop_id in reference_stop_pattern:
        borough = stop_borough_map.get(stop_id)
        if borough:
            reference_by_borough[borough].append(stop_id)

    # Check each borough
    result = {}
    for borough, borough_reference_stops in reference_by_borough.items():
        # Which stops in this borough does this trip make?
        trip_stops_in_borough = [s for s in borough_reference_stops if s in trip_stops]

        # If the trip doesn't pass through this borough, skip
        if not trip_stops_in_borough:
            continue

        # If trip makes all reference stops in this borough, it's local
        # If it skips any, it's express
        if len(trip_stops_in_borough) == len(borough_reference_stops):
            result[borough] = 'local'
        else:
            # Check if it's skipping stops or just a short turn
            # If it makes at least 2 stops and skips some in between, it's express
            if len(trip_stops_in_borough) >= 2:
                result[borough] = 'express'
            else:
                # Single stop in borough - probably a short turn, call it local
                result[borough] = 'local'

    return result


def analyze_route_express_patterns(feed, route_id, direction_id=0, service_id=None):
    """
    Analyze express/local patterns for all trips on a route.

    Parameters:
    -----------
    feed : gtfs_kit.Feed
        A GTFS feed object loaded with gtfs_kit
    route_id : str
        The route ID (e.g., 'A', 'C')
    direction_id : int, default=0
        Direction ID (0 or 1)
    service_id : str, optional
        Service ID to filter by (e.g., weekday, weekend)

    Returns:
    --------
    pd.DataFrame
        DataFrame with columns: trip_id, and one column per borough showing 'express'/'local'/None
    """
    # Create borough mapping
    stop_boroughs = create_stop_borough_mapping(feed)
    stop_borough_map = dict(zip(stop_boroughs['stop_id'], stop_boroughs['borough']))

    # Get trips
    trips = feed.trips[
        (feed.trips['route_id'] == route_id) &
        (feed.trips['direction_id'] == direction_id)
    ].copy()

    if service_id:
        trips = trips[trips['service_id'] == service_id]

    if trips.empty:
        return pd.DataFrame()

    # Check for branches
    branch_point, branches = identify_branch_point(feed, route_id, direction_id)

    results = []

    if branch_point and len(branches) > 1:
        # Multi-branch route - analyze each branch separately
        for terminal, trip_ids in branches.items():
            reference_pattern = get_reference_stop_pattern(feed, route_id, direction_id, terminal)
            for trip_id in trip_ids:
                if trip_id in trips['trip_id'].values:
                    classification = classify_trip_express_local(
                        feed, trip_id, reference_pattern, stop_borough_map
                    )
                    classification['trip_id'] = trip_id
                    classification['branch_terminal'] = terminal
                    results.append(classification)
    else:
        # Single branch - analyze all trips against one reference
        reference_pattern = get_reference_stop_pattern(feed, route_id, direction_id)
        for trip_id in trips['trip_id']:
            classification = classify_trip_express_local(
                feed, trip_id, reference_pattern, stop_borough_map
            )
            classification['trip_id'] = trip_id
            results.append(classification)

    return pd.DataFrame(results)


def get_express_service_times(feed, route_id, direction_id=0, service_id=None, borough=None):
    """
    Find the first and last express trips for a route.

    Parameters:
    -----------
    feed : gtfs_kit.Feed
        A GTFS feed object loaded with gtfs_kit
    route_id : str
        The route ID (e.g., 'A', 'D', 'E')
    direction_id : int, default=0
        Direction ID (0 or 1)
    service_id : str, optional
        Service ID to filter by (e.g., 'Weekday', 'Saturday', 'Sunday')
    borough : str, optional
        Specific borough to check for express service (e.g., 'Manhattan', 'Brooklyn')
        If None, checks if express in ANY borough

    Returns:
    --------
    dict
        Dictionary with 'first_express' and 'last_express' containing trip info
    """
    # Get express/local patterns
    patterns = analyze_route_express_patterns(feed, route_id, direction_id, service_id)

    if patterns.empty:
        return None

    # Identify express trips
    if borough:
        # Check if express in the specific borough
        if borough in patterns.columns:
            patterns['is_express'] = patterns[borough] == 'express'
        else:
            # Borough not in route - no express service possible
            return {
                'first_express': None,
                'last_express': None,
                'total_express_trips': 0
            }
    else:
        # Express in ANY borough
        borough_cols = [col for col in patterns.columns if col in ['Manhattan', 'Brooklyn', 'Queens', 'Bronx', 'Staten Island']]
        patterns['is_express'] = patterns[borough_cols].apply(
            lambda row: 'express' in row.values, axis=1
        )

    express_trips = patterns[patterns['is_express']].copy()

    if express_trips.empty:
        return {
            'first_express': None,
            'last_express': None,
            'total_express_trips': 0
        }

    # Get departure times for each trip
    trip_times = []
    for trip_id in express_trips['trip_id']:
        stop_times = feed.stop_times[feed.stop_times['trip_id'] == trip_id].copy()
        stop_times = stop_times.sort_values('stop_sequence')

        if not stop_times.empty:
            first_departure = stop_times.iloc[0]['departure_time']
            last_arrival = stop_times.iloc[-1]['arrival_time']

            # Parse time to get hours for sorting (handle 24+ hour times)
            parts = first_departure.split(':')
            departure_seconds = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])

            # Get origin and destination
            origin_stop_id = stop_times.iloc[0]['stop_id']
            dest_stop_id = stop_times.iloc[-1]['stop_id']
            origin_name = feed.stops[feed.stops['stop_id'] == origin_stop_id]['stop_name'].values[0]
            dest_name = feed.stops[feed.stops['stop_id'] == dest_stop_id]['stop_name'].values[0]

            trip_times.append({
                'trip_id': trip_id,
                'departure_time': first_departure,
                'arrival_time': last_arrival,
                'departure_seconds': departure_seconds,
                'origin': origin_name,
                'destination': dest_name
            })

    if not trip_times:
        return {
            'first_express': None,
            'last_express': None,
            'total_express_trips': 0
        }

    # Sort by departure time
    trip_times.sort(key=lambda x: x['departure_seconds'])

    return {
        'first_express': trip_times[0],
        'last_express': trip_times[-1],
        'total_express_trips': len(trip_times),
        'all_express_trips': trip_times
    }


def summarize_express_service(feed, route_id, service_days=None, borough=None):
    """
    Summarize express service times for a route across all service days and directions.

    Parameters:
    -----------
    feed : gtfs_kit.Feed
        A GTFS feed object loaded with gtfs_kit
    route_id : str
        The route ID (e.g., 'A', 'D', 'E')
    service_days : list, optional
        List of service IDs to analyze (e.g., ['Weekday', 'Saturday', 'Sunday'])
        If None, will use all unique service_ids for the route
    borough : str, optional
        Specific borough to check for express service (e.g., 'Manhattan', 'Brooklyn')
        If None, checks if express in ANY borough

    Returns:
    --------
    pd.DataFrame
        Summary table with columns: service_id, direction_id, first_express_time,
        last_express_time, total_express_trips
    """
    if service_days is None:
        # Get all service IDs for this route
        route_trips = feed.trips[feed.trips['route_id'] == route_id]
        service_days = route_trips['service_id'].unique().tolist()

    results = []

    for service_id in service_days:
        for direction_id in [0, 1]:
            info = get_express_service_times(feed, route_id, direction_id, service_id, borough)

            if info and info['first_express']:
                result_dict = {
                    'route_id': route_id,
                    'service_id': service_id,
                    'direction_id': direction_id,
                    'first_express_time': info['first_express']['departure_time'],
                    'first_express_origin': info['first_express']['origin'],
                    'last_express_time': info['last_express']['departure_time'],
                    'last_express_origin': info['last_express']['origin'],
                    'total_express_trips': info['total_express_trips']
                }

                if borough:
                    result_dict['borough'] = borough

                results.append(result_dict)

    return pd.DataFrame(results)


if __name__ == "__main__":
    print("""
    EXAMPLE USAGE:

    import gtfs_kit as gk
    import express_local as el

    # Load GTFS feed
    feed = gk.read_feed("path/to/gtfs.zip", dist_units='m')

    # Create borough mapping
    stop_boroughs = el.create_stop_borough_mapping(feed)
    print(stop_boroughs)

    # Analyze express/local patterns for a route
    patterns = el.analyze_route_express_patterns(feed, 'A', direction_id=0, service_id='Weekday')
    print(patterns)
    """)
