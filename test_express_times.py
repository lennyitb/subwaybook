#!/usr/bin/env python3
"""
Test script for express service time analysis
"""
import gtfs_kit as gk
import express_local as el
import pandas as pd

# Load GTFS feed
feed = gk.read_feed("gtfs_subway.zip", dist_units="m")

# Get express service summary for A train (all boroughs)
print("="*70)
print("A TRAIN EXPRESS SERVICE SUMMARY (ALL BOROUGHS)")
print("="*70)

summary = el.summarize_express_service(feed, 'A', service_days=['Weekday', 'Saturday', 'Sunday'])

if not summary.empty:
    print("\n")
    print(summary.to_string(index=False))
else:
    print("No express service found")

# Get express service summary for A train in Manhattan only
print("\n" + "="*70)
print("A TRAIN EXPRESS SERVICE IN MANHATTAN ONLY")
print("="*70)

manhattan_summary = el.summarize_express_service(
    feed, 'A',
    service_days=['Weekday', 'Saturday', 'Sunday'],
    borough='Manhattan'
)

if not manhattan_summary.empty:
    print("\n")
    print(manhattan_summary.to_string(index=False))
else:
    print("No express service found in Manhattan")

# You can also get detailed info for a specific service/direction
print("\n" + "="*70)
print("DETAILED: A Train Weekday Direction 0")
print("="*70)

detailed = el.get_express_service_times(feed, 'A', direction_id=0, service_id='Weekday')

if detailed and detailed['first_express']:
    print(f"\nFirst Express:")
    print(f"  Departs: {detailed['first_express']['departure_time']}")
    print(f"  From: {detailed['first_express']['origin']}")
    print(f"  To: {detailed['first_express']['destination']}")
    print(f"  Trip ID: {detailed['first_express']['trip_id']}")

    print(f"\nLast Express:")
    print(f"  Departs: {detailed['last_express']['departure_time']}")
    print(f"  From: {detailed['last_express']['origin']}")
    print(f"  To: {detailed['last_express']['destination']}")
    print(f"  Trip ID: {detailed['last_express']['trip_id']}")

    print(f"\nTotal Express Trips: {detailed['total_express_trips']}")
else:
    print("No express service found")
