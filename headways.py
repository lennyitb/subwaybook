import gtfs_kit as gk
import pandas as pd
from datetime import datetime, timedelta
from collections import defaultdict
from shapely.geometry import Point, Polygon


"""
METHODOLOGY EXPLANATION FOR HEADWAY CALCULATION:

The issue with part-time services appearing to run later than they do stems from 
how we're grouping trips by hour. Here's what can go wrong:

PROBLEM 1: Using the "hour" bucket for headway calculation
- If we group by the hour field and calculate headways within each hour bucket,
  we miss cross-hour boundaries
- Example: Train at 5:58 and train at 6:02 should have 4-minute headway,
  but they're in different hour buckets, so we don't capture this relationship

PROBLEM 2: Boundary effects with part-time services
- When service starts/stops, the first/last trains in an hour bucket create
  artificial headways
- Example: If service ends at 23:30, and we have trains at 23:15 and 23:30,
  then a train at 00:15 (next day), we might incorrectly calculate a 45-minute
  headway in the midnight hour when service doesn't actually run then

PROBLEM 3: Service ID confusion
- Different service_ids may represent different days or times
- Not filtering properly can mix weekday/weekend or different time periods

IMPROVED APPROACH:
1. Calculate ALL headways chronologically across the entire day
2. Assign each headway to an hour based on when it occurs (the departure time
   of the earlier train)
3. Handle wraparound times (24:00+) correctly
4. Be explicit about which service pattern we're analyzing
"""


def get_line_headways_by_hour_improved(feed, route_id, direction_id=None, 
                                       service_id=None, stop_id=None,
                                       exclude_first_last=True):
    """
    Calculate train headways for each hour of the day for a particular line.
    
    METHODOLOGY:
    - Gets all trips for the specified route/direction/service
    - If stop_id specified, uses that stop; otherwise uses first stop of each trip
    - Sorts all departures chronologically
    - Calculates headway between consecutive trains
    - Assigns each headway to the hour of the EARLIER departure
    - Optionally excludes first/last headways of the service period to avoid 
      boundary effects
    
    Parameters:
    -----------
    feed : gtfs_kit.Feed
        A GTFS feed object loaded with gtfs_kit
    route_id : str
        The route ID for the line (e.g., '1', 'A', 'L')
    direction_id : int, optional
        Direction ID (0 or 1) to filter by direction. If None, includes both directions.
    service_id : str, optional
        Service ID to filter by (e.g., weekday, weekend service). If None, uses all services.
    stop_id : str, optional
        Specific stop to measure headways at. If None, uses first stop of each trip.
    exclude_first_last : bool, default=True
        If True, excludes the first and last headway of the service period to avoid
        boundary effects (e.g., overnight gaps appearing as "headways")
    
    Returns:
    --------
    dict
        Dictionary with hours (0-23) as keys and lists of headways (in minutes) as values
    """
    
    # Get trips for the specified route
    trips = feed.trips[feed.trips['route_id'] == route_id].copy()
    
    # Filter by direction if specified
    if direction_id is not None:
        trips = trips[trips['direction_id'] == direction_id]
    
    # Filter by service_id if specified
    if service_id is not None:
        trips = trips[trips['service_id'] == service_id]
    
    if trips.empty:
        print(f"No trips found for route {route_id}")
        return {}
    
    # Get stop times for these trips
    stop_times = feed.stop_times[feed.stop_times['trip_id'].isin(trips['trip_id'])].copy()
    
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
        trips[['trip_id', 'route_id', 'direction_id', 'service_id']], 
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
    
    # Sort by departure time
    trip_departures = trip_departures.sort_values('departure_seconds')
    
    # Calculate ALL headways in chronological order
    departure_times = trip_departures['departure_seconds'].values
    departure_time_strings = trip_departures['departure_time'].values
    
    headways_by_hour = defaultdict(list)
    
    if len(departure_times) < 2:
        print(f"Not enough trips to calculate headways (found {len(departure_times)})")
        return {}
    
    # Calculate headways between consecutive trains
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


def analyze_service_pattern(feed, route_id, direction_id=None, service_id=None):
    """
    Analyze when service actually runs to help debug headway calculations.
    Shows first and last departure for each hour.
    """
    trips = feed.trips[feed.trips['route_id'] == route_id].copy()
    
    if direction_id is not None:
        trips = trips[trips['direction_id'] == direction_id]
    
    if service_id is not None:
        trips = trips[trips['service_id'] == service_id]
    
    if trips.empty:
        print(f"No trips found")
        return
    
    stop_times = feed.stop_times[feed.stop_times['trip_id'].isin(trips['trip_id'])].copy()
    stop_times = stop_times.sort_values(['trip_id', 'stop_sequence'])
    first_stops = stop_times.groupby('trip_id').first().reset_index()
    
    def parse_gtfs_time(time_str):
        parts = time_str.split(':')
        return int(parts[0]), int(parts[1]), int(parts[2])
    
    first_stops['hour'] = first_stops['departure_time'].apply(
        lambda x: parse_gtfs_time(x)[0] % 24
    )
    first_stops['time_display'] = first_stops['departure_time'].apply(
        lambda x: f"{parse_gtfs_time(x)[0]:02d}:{parse_gtfs_time(x)[1]:02d}"
    )
    
    print(f"\nService Pattern for Route {route_id}" + 
          (f", Direction {direction_id}" if direction_id is not None else "") +
          (f", Service {service_id}" if service_id is not None else ""))
    print("-" * 70)
    print(f"{'Hour':<6} {'# Departures':<15} {'First':<15} {'Last':<15}")
    print("-" * 70)
    
    for hour in range(24):
        hour_stops = first_stops[first_stops['hour'] == hour]
        if len(hour_stops) > 0:
            first_time = hour_stops['time_display'].iloc[0]
            last_time = hour_stops['time_display'].iloc[-1]
            count = len(hour_stops)
            print(f"{hour:02d}:00  {count:<15} {first_time:<15} {last_time:<15}")
        else:
            print(f"{hour:02d}:00  {0:<15} {'-':<15} {'-':<15}")


def display_headway_summary(headways_by_hour):
    """
    Display a summary of headways by hour with statistics.
    """
    print(f"\n{'Hour':<6} {'# Headways':<12} {'Avg (min)':<12} {'Min (min)':<12} {'Max (min)':<12}")
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


# Example usage showing the debugging workflow:
if __name__ == "__main__":
    print("""
    EXAMPLE USAGE:
    
    # Load your GTFS feed
    feed = gk.read_feed("gtfs_subway.zip", dist_units='m')
    
    # First, check what service IDs exist for your route
    print(feed.trips[feed.trips['route_id'] == 'L']['service_id'].unique())
    
    # Analyze the service pattern to see when trains actually run
    analyze_service_pattern(feed, route_id='L', direction_id=0, service_id='YOUR_SERVICE_ID')
    
    # Calculate headways
    headways = get_line_headways_by_hour_improved(
        feed, 
        route_id='L',
        direction_id=0,  # Specify direction to avoid mixing both directions
        service_id='YOUR_SERVICE_ID',  # Specify the service pattern
        exclude_first_last=True  # Exclude boundary headways
    )
    
    display_headway_summary(headways)
    """)
