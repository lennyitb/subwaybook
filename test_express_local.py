#!/usr/bin/env python3
"""
Test script for express/local classification system
"""
import gtfs_kit as gk
import express_local as el
import pandas as pd


def main():
    # Load GTFS feed
    feed = gk.read_feed("/Users/lennyphelan/Downloads/gtfs_subway.zip", dist_units="m")

    # Test routes
    routes = ['A', 'C', 'W']

    for route_id in routes:
        print("=" * 70)
        print(f"{route_id} TRAIN EXPRESS/LOCAL ANALYSIS")
        print("=" * 70)

        # Analyze route
        patterns = el.analyze_route_express_patterns(
            feed,
            route_id,
            direction_id=0,
            service_id='Weekday'
        )

        if patterns.empty:
            print(f"No weekday trips found for {route_id} train\n")
            continue

        print(f"\nTotal trips analyzed: {len(patterns)}")

        # Check for branches
        if 'branch_terminal' in patterns.columns:
            terminals = patterns['branch_terminal'].value_counts()
            if len(terminals) > 1:
                print(f"\nMulti-branch route with {len(terminals)} terminals:")
                for terminal_id, count in terminals.items():
                    terminal_name = feed.stops[feed.stops['stop_id'] == terminal_id]['stop_name'].values
                    if len(terminal_name) > 0:
                        print(f"  - {terminal_name[0]}: {count} trips")

        # Summary by borough
        print("\nExpress vs Local by Borough:")
        print("-" * 50)

        boroughs = ['Bronx', 'Manhattan', 'Brooklyn', 'Queens', 'Staten Island']
        for borough in boroughs:
            if borough in patterns.columns:
                # Count non-null values
                total = patterns[borough].notna().sum()
                if total > 0:
                    counts = patterns[borough].value_counts()
                    express_count = counts.get('express', 0)
                    local_count = counts.get('local', 0)

                    express_pct = 100 * express_count / total if total > 0 else 0
                    local_pct = 100 * local_count / total if total > 0 else 0

                    print(f"{borough:12} Express: {express_count:3d} ({express_pct:5.1f}%)  |  "
                          f"Local: {local_count:3d} ({local_pct:5.1f}%)")

        print()


if __name__ == "__main__":
    main()
