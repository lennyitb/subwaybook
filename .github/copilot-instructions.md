# NYC Subway Analysis Codebase

## Project Overview
Python toolkit for analyzing NYC subway GTFS schedule data to generate travel time matrices, headway distributions, and express/local service patterns for a spiral-bound reference guide. All code has been 100% written by AI.

## Core Architecture

### Data Source & Loading
- **GTFS Feed**: Load with `feed = gk.read_feed("gtfs_subway.zip", dist_units="m")` (always use meters)
- The feed contains: `trips`, `stop_times`, `stops`, `routes`, `calendar` tables
- **Route IDs**: Use strings like `'A'`, `'1'`, `'4'` (not integers)
- **Direction IDs**: 0 or 1 (meaning varies by route - see `direction_names.csv`)
  - Generally: 0 = outbound from Manhattan, 1 = inbound to Manhattan
  - Use `get_direction_name(feed, route_id, direction_id, service_id)` for human-readable names
- **Service IDs**: `'Weekday'`, `'Saturday'`, `'Sunday'` (check `feed.trips['service_id'].unique()` for availability)

### Module Architecture

**`travel_times.py`** - Travel time matrix generation
- `get_station_order()`: Gets canonical station sequence for a route/direction/service
- `filter_station_order_express()`: Filters to express stops only in specified boroughs
- `calculate_travel_time_matrix()`: Generates origin-destination travel time matrix with hour filtering
- `display_bidirectional_matrix()`: Combines both directions into unified matrix
- Branch handling: Multi-branch routes (A, 5) detected automatically via `identify_branches()`
- Stop ID normalization: Removes N/S suffixes to group platforms (e.g., "A42N" → "A42")

**`headways.py`** - Single-route headway (train frequency) analysis
- `get_line_headways_by_hour_improved()`: Calculates time between consecutive trains for one route
- Uses chronological sorting across entire day to avoid boundary effects
- Set `exclude_first_last=True` to avoid overnight gaps appearing as headways
- Always specify `direction_id` and `service_id` to avoid mixing services

**`combined_headways.py`** - Multi-route corridor headway analysis
- `get_headway_dist()`: Primary function returning pandas DataFrame with hourly statistics
- Accepts variable args: `get_headway_dist(feed, direction_id, *route_ids, service_id='Weekday')`
- Example: `get_headway_dist(feed, 1, '4', '5', '6')` for combined Lexington Ave service
- Returns DataFrame with `hour`, `num_trains`, `avg_headway`, `min_headway`, `max_headway`
- Metadata stored in `df.attrs`: `route_ids`, `direction_id`, `direction_name`, `service_id`

**`express_local.py`** - Express vs local classification
- `get_stop_borough()`: Maps coordinates to NYC boroughs using polygon boundaries
- `analyze_route_express_patterns()`: Determines if trips run express/local per borough
- Methodology: Compares each trip's stops against "all stops" reference pattern
- Classification is per-borough (e.g., express in Manhattan, local in Queens)

**`compare_lines.py`** - Express vs local travel time comparison
- `get_shared_express_stops()`: Finds stations served by both routes
- `calculate_travel_time_difference()`: Returns matrix of time savings (local - express)

## Critical Patterns

### GTFS Time Format
Times can exceed 24 hours (e.g., "25:30:00" = 1:30 AM next day). Always parse with:
```python
def parse_gtfs_time(time_str):
    parts = time_str.split(':')
    return int(parts[0]), int(parts[1]), int(parts[2])
```

### Stop ID Normalization
Platforms have N/S suffixes (northbound/southbound). Normalize when grouping:
```python
def normalize_stop_id(feed, stop_id):
    parent_id = feed.stops[feed.stops['stop_id'] == stop_id]['parent_station'].values
    return parent_id[0] if len(parent_id) > 0 and pd.notna(parent_id[0]) else stop_id
```

### Hour Filtering for Travel Times
Rush hour vs off-peak matters. Use `hour` parameter as tuple:
```python
# Morning rush (7-9 AM)
matrix = calculate_travel_time_matrix(feed, route_id, direction_id, service_id, 
                                     station_order, hour=(7, 9))
```

### Test Scripts Pattern
Scripts named `test_*.py` are executables that generate CSV outputs, not pytest tests:
- Load feed with `gk.read_feed("gtfs_subway.zip", dist_units="m")`
- Set pandas display options to show full matrices:
  ```python
  pd.set_option('display.max_columns', None)
  pd.set_option('display.max_rows', None)
  ```
- Export results: `df.to_csv(f'{route_id}_{service_id}_output.csv')`

## Reference Data Files

- **`direction_names.csv`**: Official direction names per route (e.g., "to Queens", "to The Bronx")
- **`terminal_reference.csv`**: Generated reference of terminal stations per route/direction
- **`stop_boroughs.csv`**: Stop-to-borough mapping cache

## Development Workflow

Run any test script directly: `python test_a_train.py`
- No pytest framework used
- Scripts generate both terminal output and CSV files
- Check CSV files for import into book

## TODO Items (from TODO file)
- Travel time tables need hour-of-day consideration (partially implemented)
- Remove express filter from `test_a_train.py`
- Implement headway calculations for individual branches
- Build information for J/Z trains
- Identify part-time terminals
- Create frequency charts for arbitrary line stretches
