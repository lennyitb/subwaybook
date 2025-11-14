#!/usr/bin/env python3
"""
Generate timeline charts showing express/local service by hour
"""
import gtfs_kit as gk
import express_local as el
import pandas as pd
from collections import defaultdict


def create_hourly_express_timeline(feed, route_id, direction_id, service_id, borough='Manhattan'):
    """
    Create a timeline showing express vs local service for each hour of the day.

    Returns a dict mapping hour -> 'express', 'local', 'both', or 'none'
    """
    # Get all trips with express/local classification
    patterns = el.analyze_route_express_patterns(feed, route_id, direction_id, service_id)

    if patterns.empty or borough not in patterns.columns:
        return {}

    # Get departure times for each trip
    hourly_service = defaultdict(lambda: {'express': 0, 'local': 0})

    for _, row in patterns.iterrows():
        trip_id = row['trip_id']
        service_type = row[borough]

        if pd.isna(service_type):
            continue

        # Get departure time
        stop_times = feed.stop_times[feed.stop_times['trip_id'] == trip_id].copy()
        stop_times = stop_times.sort_values('stop_sequence')

        if not stop_times.empty:
            departure_time = stop_times.iloc[0]['departure_time']
            hour = int(departure_time.split(':')[0]) % 24  # Handle 24+ hour times

            hourly_service[hour][service_type] += 1

    # Classify each hour
    timeline = {}
    for hour in range(24):
        if hour in hourly_service:
            express_count = hourly_service[hour]['express']
            local_count = hourly_service[hour]['local']

            if express_count > 0 and local_count > 0:
                timeline[hour] = 'both'
            elif express_count > 0:
                timeline[hour] = 'express'
            elif local_count > 0:
                timeline[hour] = 'local'
            else:
                timeline[hour] = 'none'
        else:
            timeline[hour] = 'none'

    return timeline


def print_timeline_chart(route_id, direction_id, service_id, timeline, borough='Manhattan'):
    """
    Print a text-based timeline chart.
    """
    direction_name = "Northbound" if direction_id == 0 else "Southbound"

    print(f"\n{'='*70}")
    print(f"{route_id} Train - {service_id} - {direction_name} - {borough}")
    print(f"{'='*70}")
    print()
    print("Hour  Service Pattern")
    print("-" * 50)

    for hour in range(24):
        service = timeline.get(hour, 'none')

        # Create visual representation
        if service == 'express':
            symbol = '████████████████ EXPRESS'
            color = ''
        elif service == 'local':
            symbol = '▒▒▒▒▒▒▒▒ LOCAL'
            color = ''
        elif service == 'both':
            symbol = '████▒▒▒▒ EXPRESS + LOCAL'
            color = ''
        else:
            symbol = '-------- NO SERVICE'
            color = ''

        # Format hour
        hour_str = f"{hour:02d}:00"
        print(f"{hour_str}  {symbol}")

    # Legend
    print()
    print("Legend:")
    print("  ████ = Express service running")
    print("  ▒▒▒▒ = Local service running")
    print("  ---- = No service")


def main():
    # Load GTFS feed
    feed = gk.read_feed("gtfs_subway.zip", dist_units="m")

    route_id = '4'
    borough = 'Manhattan'

    # Generate timelines for each service day and direction
    for service_id in ['Weekday', 'Saturday', 'Sunday']:
        for direction_id in [0, 1]:
            timeline = create_hourly_express_timeline(
                feed, route_id, direction_id, service_id, borough
            )

            if timeline:
                print_timeline_chart(route_id, direction_id, service_id, timeline, borough)


if __name__ == "__main__":
    main()
