#!/usr/bin/env python3
"""
Test script demonstrating J/Z skip-stop service analysis.
"""
import gtfs_kit as gk
import skip_stop as ss

# Load GTFS feed
print("Loading GTFS feed...")
feed = gk.read_feed("gtfs_subway.zip", dist_units="m")

# Print overall summary
ss.print_skip_stop_summary(feed, direction_id=1, service_id='Weekday')

print("\n" + "="*80)
print("DETAILED HEADWAY COMPARISON")
print("="*80)

# Get station classifications
j_only_stops, z_only_stops, shared_stops = ss.get_skip_stop_stations(
    feed, direction_id=1, service_id='Weekday'
)

# Compare headways at shared vs J-only stations during rush hour
print("\n" + "="*80)
print("MORNING RUSH HOUR COMPARISON (7-9 AM)")
print("="*80)

# Shared station
shared_station_id, shared_station_name = shared_stops[10]  # Broadway Junction
print(f"\nAt {shared_station_name} (served by both J and Z):")
df_shared_rush = ss.get_effective_headway(
    feed, 1, 'Weekday',
    stop_id=shared_station_id,
    hour_range=(7, 9)
)
print(df_shared_rush[['hour', 'num_trains', 'avg_headway', 'z_active']].to_string(index=False))

# J-only station
j_only_station_id, j_only_station_name = j_only_stops[4]  # Halsey St
print(f"\nAt {j_only_station_name} (J-only, skipped by Z):")
df_j_only_rush = ss.get_effective_headway(
    feed, 1, 'Weekday',
    stop_id=j_only_station_id,
    hour_range=(7, 9)
)
print(df_j_only_rush[['hour', 'num_trains', 'avg_headway', 'z_active']].to_string(index=False))

# Midday comparison
print("\n" + "="*80)
print("MIDDAY COMPARISON (10 AM - 2 PM)")
print("="*80)

print(f"\nAt {shared_station_name} (served by both J and Z):")
df_shared_midday = ss.get_effective_headway(
    feed, 1, 'Weekday',
    stop_id=shared_station_id,
    hour_range=(10, 14)
)
print(df_shared_midday[['hour', 'num_trains', 'avg_headway', 'z_active']].to_string(index=False))

print(f"\nAt {j_only_station_name} (J-only, skipped by Z):")
df_j_only_midday = ss.get_effective_headway(
    feed, 1, 'Weekday',
    stop_id=j_only_station_id,
    hour_range=(10, 14)
)
print(df_j_only_midday[['hour', 'num_trains', 'avg_headway', 'z_active']].to_string(index=False))

# Trip classification
print("\n" + "="*80)
print("J TRAIN TRIP CLASSIFICATION")
print("="*80)

j_trips = ss.classify_j_trips(feed, direction_id=1, service_id='Weekday')

print("\nSample J train trips:")
print(j_trips[['departure_hour', 'pattern', 'num_stops', 'z_service_active']].head(20).to_string(index=False))

print("\n" + "="*80)
print("KEY INSIGHTS")
print("="*80)

z_hours = ss.get_z_service_hours(feed, 'Weekday')
print(f"\n1. Z trains operate during rush hours only: {sorted(z_hours)}")
print(f"   (Morning rush: 7-8 AM, Evening rush: 4-6 PM)")

print(f"\n2. The J/Z system has {len(shared_stops)} shared stops and {len(j_only_stops)} J-only stops")

print(f"\n3. During Z service hours:")
print(f"   - Shared stations get combined J+Z service")
print(f"   - J-only stations get J service only")

print(f"\n4. Outside Z service hours:")
print(f"   - All stations get J-only all-stop service")

print("\nTest completed successfully!")
