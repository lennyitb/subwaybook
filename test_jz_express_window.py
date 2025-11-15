#!/usr/bin/env python3
"""
Test script demonstrating J/Z express service window analysis.
Shows when express J trains and Z trains operate.
"""
import gtfs_kit as gk
import skip_stop as ss

# Load GTFS feed
print("Loading GTFS feed...")
feed = gk.read_feed("gtfs_subway.zip", dist_units="m")

print("\n" + "="*80)
print("J/Z EXPRESS SERVICE WINDOW ANALYSIS")
print("="*80)

# Print visual timeline
ss.print_service_timeline(feed, service_id='Weekday')

# Get detailed times for both directions
print("\n" + "="*80)
print("DETAILED SERVICE TIMES")
print("="*80)

print("\nDirection 0 (away from Manhattan):")
print("-" * 80)
first_exp_j0, first_z0, last_z0, last_exp_j0 = ss.get_express_service_window(
    feed, 0, 'Weekday'
)
print(f"  First Express J Train: {first_exp_j0 if first_exp_j0 else 'N/A'}")
print(f"  First Z Train:         {first_z0 if first_z0 else 'N/A'}")
print(f"  Last Z Train:          {last_z0 if last_z0 else 'N/A'}")
print(f"  Last Express J Train:  {last_exp_j0 if last_exp_j0 else 'N/A'}")

print("\nDirection 1 (toward Manhattan):")
print("-" * 80)
first_exp_j1, first_z1, last_z1, last_exp_j1 = ss.get_express_service_window(
    feed, 1, 'Weekday'
)
print(f"  First Express J Train: {first_exp_j1 if first_exp_j1 else 'N/A'}")
print(f"  First Z Train:         {first_z1 if first_z1 else 'N/A'}")
print(f"  Last Z Train:          {last_z1 if last_z1 else 'N/A'}")
print(f"  Last Express J Train:  {last_exp_j1 if last_exp_j1 else 'N/A'}")

print("\n" + "="*80)
print("KEY INSIGHTS")
print("="*80)

print("\nExpress J Service:")
print("  - Express J trains skip certain stops during rush hours")
print("  - These are J trains that don't stop at all skip-stop stations")
print("  - Provides faster service during peak periods")

print("\nZ Train Service:")
print("  - Z trains operate only during rush hours")
print("  - Morning rush: ~7-8 AM")
print("  - Evening rush: ~4-6 PM")
print("  - Z trains skip 9 stations that J trains stop at")

print("\nTest completed successfully!")
