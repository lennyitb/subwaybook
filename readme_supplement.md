# Subway Analysis Functions - Reference Guide

This document provides an overview of the key functions developed for analyzing NYC subway GTFS data.

## Core Modules

### `travel_times.py`

Functions for calculating travel time matrices between stations.

### `combined_headways.py`

Functions for analyzing headways (time between trains) with support for branches and time filtering.

### `compare_lines.py`

Functions for comparing travel times between local and express routes.

### `skip_stop.py`

Functions for analyzing J/Z skip-stop service patterns.

### `express_local.py`

Helper functions for determining borough locations and express/local service patterns.

### `express_windows.py`

Module for generating and accessing express service window data for all NYC subway routes. Provides pre-generated JSON data for fast lookups of when trains run express service in each borough.

---

## Travel Time Analysis

### `calculate_travel_time_matrix(feed, route_id, direction_id, service_id='Weekday', canonical_station_order=None)`

**Location:** `travel_times.py`

Calculates average travel times between all station pairs for a route.

**Parameters:**

- `feed`: GTFS feed object from gtfs_kit
- `route_id`: Route ID (e.g., 'A', '1', '7')
- `direction_id`: 0 or 1
- `service_id`: Service type (default: 'Weekday')
- `canonical_station_order`: Optional pre-defined station order

**Returns:** DataFrame with travel times in minutes (rows=destinations, columns=origins)

**Example:**

```python
import gtfs_kit as gk
import travel_times as tt

feed = gk.read_feed("gtfs_subway.zip", dist_units="m")
matrix = tt.calculate_travel_time_matrix(feed, 'A', 1, 'Weekday')
```

---

### `calculate_travel_time_matrix_by_hour(feed, route_id, direction_id, hour, service_id='Weekday', canonical_station_order=None)`

**Location:** `travel_times.py`

Like `calculate_travel_time_matrix()` but filtered to specific hour(s) of the day.

**Parameters:**

- Same as `calculate_travel_time_matrix()` plus:
- `hour`: Single int (0-23) or tuple (start, end) for hour range
  - Example: `7` = 7:00-7:59 AM
  - Example: `(7, 9)` = 7:00-9:59 AM

**Returns:** DataFrame with travel times during specified hours

**Example:**

```python
# Morning rush hour only
matrix = tt.calculate_travel_time_matrix_by_hour(feed, 'A', 1, (7, 9), 'Weekday')
```

---

### `combine_bidirectional_matrix(matrix_dir0, matrix_dir1)`

**Location:** `travel_times.py`

Combines travel time matrices from both directions into a single symmetric matrix.

**Parameters:**

- `matrix_dir0`: Travel time matrix for direction 0
- `matrix_dir1`: Travel time matrix for direction 1

**Returns:** Combined DataFrame with both directions

---

## Headway Analysis

### `get_headway_dist(feed, route_id, direction_id, service_id='Weekday', stop_id=None, hour_range=None, exclude_first_last=True)`

**Location:** `combined_headways.py`

Analyzes headways (time between consecutive trains) for a route.

**Parameters:**

- `feed`: GTFS feed object
- `route_id`: Route ID
- `direction_id`: 0 or 1
- `service_id`: Service type (default: 'Weekday')
- `stop_id`: Specific stop to analyze (default: first non-terminal stop)
- `hour_range`: Optional tuple (start_hour, end_hour) to filter by time
- `exclude_first_last`: Exclude terminal stations (default: True)

**Returns:** DataFrame with headway statistics by hour

**Example:**

```python
import combined_headways as ch

# Get headways for A train
df = ch.get_headway_dist(feed, 'A', 1, 'Weekday')
ch.print_headway_dist(df)
```

---

### `get_headway_dist_branch(feed, route_id, direction_id, branch_terminal, service_id='Weekday', stop_id=None, hour_range=None, exclude_first_last=True)`

**Location:** `combined_headways.py`

Analyzes headways for a specific branch of a multi-branch route.

**Parameters:**

- Same as `get_headway_dist()` plus:
- `branch_terminal`: Terminal station name or partial name (e.g., 'Nereid', 'Far Rockaway')

**Returns:** DataFrame with headway statistics for the specified branch

**Example:**

```python
# Headways for 5 train to Nereid Av only
df = ch.get_headway_dist_branch(feed, '5', 1, 'Nereid', 'Weekday')
```

---

### `get_headway_dist_combined(feed, direction_id, *route_specs, service_id='Weekday', stop_id=None, hour_range=None, exclude_first_last=True)`

**Location:** `combined_headways.py`

Analyzes combined headways for multiple routes and/or branches.

**Parameters:**

- `feed`: GTFS feed object
- `direction_id`: 0 or 1
- `*route_specs`: Variable number of route specifications:
  - String: full route (e.g., `'2'`)
  - Tuple: branch (e.g., `('5', 'Nereid')`)
- `service_id`: Service type (default: 'Weekday')
- `stop_id`: Specific stop to analyze
- `hour_range`: Optional tuple (start_hour, end_hour)
- `exclude_first_last`: Exclude terminal stations (default: True)

**Returns:** DataFrame with combined headway statistics

**Examples:**

```python
# Combined headways: 2 train + 5 trains to Nereid
df = ch.get_headway_dist_combined(feed, 1, '2', ('5', 'Nereid'), service_id='Weekday')

# Combined headways: A to Far Rockaway + A to Rockaway Park
df = ch.get_headway_dist_combined(feed, 0, ('A', 'Far Rockaway'), ('A', 'Rockaway Park'))

# Morning rush only (7-9 AM)
df = ch.get_headway_dist_combined(feed, 1, '2', ('5', 'Nereid'), hour_range=(7, 9))
```

---

## Skip-Stop Service Analysis

### `get_skip_stop_stations(feed, direction_id=1, service_id='Weekday')`

**Location:** `skip_stop.py`

Identifies stations in the J/Z skip-stop system.

**Parameters:**

- `feed`: GTFS feed object
- `direction_id`: 0 or 1 (default: 1)
- `service_id`: Service type (default: 'Weekday')

**Returns:** Tuple of (j_only_stops, z_only_stops, shared_stops) where each is a list of (stop_id, stop_name) tuples

**Example:**

```python
import skip_stop as ss

j_only, z_only, shared = ss.get_skip_stop_stations(feed, 1, 'Weekday')
print(f"J skips {len(j_only)} stations that Z serves")
print(f"Shared stations: {len(shared)}")
```

---

### `get_z_service_hours(feed, service_id='Weekday')`

**Location:** `skip_stop.py`

Determines which hours Z train service operates.

**Parameters:**

- `feed`: GTFS feed object
- `service_id`: Service type (default: 'Weekday')

**Returns:** Set of hours (0-23) when Z trains run

**Example:**

```python
z_hours = ss.get_z_service_hours(feed, 'Weekday')
print(f"Z trains run during hours: {sorted(z_hours)}")
# Output: Z trains run during hours: [7, 8, 16, 17, 18]
```

---

### `classify_j_trips(feed, direction_id=1, service_id='Weekday')`

**Location:** `skip_stop.py`

Classifies J train trips as all-stop or skip-stop based on Z service hours.

**Parameters:**

- `feed`: GTFS feed object
- `direction_id`: 0 or 1 (default: 1)
- `service_id`: Service type (default: 'Weekday')

**Returns:** DataFrame with trip classifications including pattern, departure hour, and Z service status

---

### `get_effective_headway(feed, direction_id=1, service_id='Weekday', stop_id=None, hour_range=None)`

**Location:** `skip_stop.py`

Calculates effective headway for J/Z service accounting for skip-stop pattern.

**Parameters:**

- `feed`: GTFS feed object
- `direction_id`: 0 or 1 (default: 1)
- `service_id`: Service type (default: 'Weekday')
- `stop_id`: Specific stop to analyze (default: first shared stop)
- `hour_range`: Optional tuple (start_hour, end_hour)

**Returns:** DataFrame with headway statistics by hour, including Z service status and station type

**Example:**

```python
# Headway at a shared station during rush hour
df = ss.get_effective_headway(feed, 1, 'Weekday',
                               stop_id='J29S',  # Broadway Junction
                               hour_range=(7, 9))
```

---

### `print_skip_stop_summary(feed, direction_id=1, service_id='Weekday')`

**Location:** `skip_stop.py`

Prints a comprehensive summary of the J/Z skip-stop service pattern.

**Parameters:**

- `feed`: GTFS feed object
- `direction_id`: 0 or 1 (default: 1)
- `service_id`: Service type (default: 'Weekday')

---

### `get_express_service_window(feed, direction_id, service_id='Weekday')`

**Location:** `skip_stop.py`

Gets the service window for express J trains and Z trains.

Express J trains are identified as J trains that do not stop at Hewes St, Lorimer St, or Flushing Av. This function returns the first and last times for both express J trains and Z trains.

**Parameters:**

- `feed`: GTFS feed object
- `direction_id`: 0 or 1
- `service_id`: Service type (default: 'Weekday')

**Returns:** Tuple of (first_express_j, first_z, last_z, last_express_j) where each is a time string in HH:MM:SS format, or None if no service found

**Example:**

```python
import skip_stop as ss

# Get service windows for direction 1 (toward Manhattan)
first_exp_j, first_z, last_z, last_exp_j = ss.get_express_service_window(
    feed, 1, 'Weekday'
)
print(f"First Express J: {first_exp_j}")
print(f"Z trains run from {first_z} to {last_z}")
```

---

### `print_service_timeline(feed, service_id='Weekday')`

**Location:** `skip_stop.py`

Prints a visual timeline showing express J and Z service windows for both directions.

Creates an ASCII-based timeline chart displaying when Z trains operate (6 AM - 8 PM range) and shows the first/last times for both express J and Z service in each direction.

**Parameters:**

- `feed`: GTFS feed object
- `service_id`: Service type (default: 'Weekday')

**Example:**

```python
import skip_stop as ss

# Print visual timeline for J/Z service
ss.print_service_timeline(feed, 'Weekday')
```

**Output Format:**
```
Direction 0 (away from Manhattan):
First Express J: 06:35
First Z train:   16:54
Last Z train:    17:46
Last Express J:  19:32

Timeline (6 AM - 8 PM):
Time: 06:00   08:00   10:00   12:00   14:00   16:00   18:00   20:00
      ------------------------------------------------------------
Z:                                                   ████
```

---

## Express vs Local Comparison

### `compare_lines(feed, local_route, express_route, direction_id=1, service_id='Weekday', hour_range=None, export=True, verbose=True)`

**Location:** `compare_lines.py`

Compares travel times between a local route and express route.

**Parameters:**

- `feed`: GTFS feed object
- `local_route`: Route ID for local train (e.g., 'C')
- `express_route`: Route ID for express train (e.g., 'A')
- `direction_id`: 0 or 1 (default: 1)
- `service_id`: Service type (default: 'Weekday')
- `hour_range`: Optional hour filter (int or tuple)
- `export`: Whether to export CSV (default: True)
- `verbose`: Whether to print summary (default: True)

**Returns:** DataFrame showing time difference (positive = express is faster)

**Example:**

```python
import compare_lines as cl

# Compare C vs A train during morning rush
diff = cl.compare_lines(feed, 'C', 'A', hour_range=(7, 9))

# Compare all hours
diff = cl.compare_lines(feed, 'C', 'A')
```

---

### `get_shared_express_stops(feed, local_route, express_route, direction_id=1, service_id='Weekday')`

**Location:** `compare_lines.py`

Gets the list of express stops that both routes serve.

**Parameters:**

- `feed`: GTFS feed object
- `local_route`: Route ID for local train
- `express_route`: Route ID for express train
- `direction_id`: 0 or 1
- `service_id`: Service type

**Returns:** List of (stop_id, stop_name) tuples in route order

---

## Express Service Windows

### `generate_express_windows(feed, service_ids=None, output_file='express_window_data.json')`

**Location:** `express_windows.py`

Generates express service window data for all subway routes across multiple service patterns (Weekday, Saturday, Sunday) and saves to JSON.

This function analyzes all NYC subway routes (including express variants like 6X, 7X, FX) and determines when each route runs express service in each borough, broken down by direction and service pattern.

**Parameters:**

- `feed`: GTFS feed object from gtfs_kit
- `service_ids`: Service ID(s) to analyze. Can be:
  - A single service ID string (e.g., `'Weekday'`)
  - A list of service IDs (e.g., `['Weekday', 'Saturday', 'Sunday']`)
  - `None` to auto-detect all service IDs in the feed (default)
- `output_file`: Path to output JSON file (default: 'express_window_data.json')

**Returns:** Dictionary mapping service_id → route_id → direction_id → borough → (first_time, last_time)

**Notes:**

- J/Z trains use special skip-stop handling
- Express variants (6X, 7X, FX) run express in outer boroughs, local in Manhattan
- All hardcoded special cases are applied:
  - A trains are always local in Queens
  - B trains are always express in Manhattan and Brooklyn (weekdays only)
  - C, M, R, 1, 6, L, G trains are always local
  - F trains are never express in Brooklyn

**Example:**

```python
import gtfs_kit as gk
import express_windows as ew

feed = gk.read_feed("gtfs_subway.zip", dist_units="m")

# Generate data for specific service patterns
data = ew.generate_express_windows(feed, service_ids=['Weekday', 'Saturday', 'Sunday'])

# Generate for all service patterns in feed
data = ew.generate_express_windows(feed, service_ids=None)

# Generate for single service pattern
data = ew.generate_express_windows(feed, service_ids='Weekday')

# Or run as script to regenerate JSON (generates Weekday, Saturday, Sunday)
# python3 express_windows.py
```

---

### `load_express_windows(json_file='express_window_data.json')`

**Location:** `express_windows.py`

Loads pre-generated express service window data from JSON file.

**Parameters:**

- `json_file`: Path to JSON file (default: 'express_window_data.json')

**Returns:** Dictionary mapping service_id → route_id → direction_id → borough → [first_time, last_time]

**Raises:** FileNotFoundError if the JSON file doesn't exist

**Example:**

```python
import express_windows as ew

data = ew.load_express_windows()
print(data['Weekday']['A']['0']['Manhattan'])
# Output: ['05:12:30', '22:18:00']
```

---

### `get_express_window(route_id, direction_id, service_id='Weekday', borough=None, json_file='express_window_data.json')`

**Location:** `express_windows.py`

Gets express service window for a specific route, direction, service pattern, and optionally borough.

**Parameters:**

- `route_id`: Route ID (e.g., 'A', 'D', '2', '6X')
- `direction_id`: Direction ID (0 or 1)
- `service_id`: Service ID (e.g., 'Weekday', 'Saturday', 'Sunday') - default: 'Weekday'
- `borough`: Specific borough (e.g., 'Manhattan', 'Brooklyn', 'The Bronx'), or None for all boroughs
- `json_file`: Path to JSON file (default: 'express_window_data.json')

**Returns:**

- If `borough` is None: dict mapping borough → [first_time, last_time]
- If `borough` is specified: [first_time, last_time] for that borough, or None if no express service

**Raises:** KeyError if service_id, route, or direction not found

**Examples:**

```python
import express_windows as ew

# Get all boroughs for A train northbound on weekdays
windows = ew.get_express_window('A', 0, 'Weekday')
# Returns: {'Manhattan': ['05:12:30', '22:18:00'], 'Brooklyn': ['05:12:30', '22:18:00']}

# Get specific borough for weekend service
manhattan_window = ew.get_express_window('A', 0, 'Saturday', 'Manhattan')
# Returns: ['05:12:30', '22:18:00'] or None

# Check if train runs express on Sundays
bronx_window = ew.get_express_window('D', 0, 'Sunday', 'The Bronx')
# Returns: ['15:04:30', '17:24:30'] or None if no express service

# Local-only train
c_window = ew.get_express_window('C', 0, 'Weekday', 'Manhattan')
# Returns: None
```

---

### `print_express_windows(route_id=None, service_id=None, json_file='express_window_data.json')`

**Location:** `express_windows.py`

Pretty-prints express service windows for routes.

**Parameters:**

- `route_id`: Specific route to print, or None to print all routes
- `service_id`: Specific service ID to print (e.g., 'Weekday', 'Saturday'), or None to print all service IDs
- `json_file`: Path to JSON file (default: 'express_window_data.json')

**Example:**

```python
import express_windows as ew

# Print one route for weekday service
ew.print_express_windows('A', 'Weekday')

# Print one route for all service patterns
ew.print_express_windows('A')

# Print all routes for all service patterns
ew.print_express_windows()

# Print all routes for Saturday service only
ew.print_express_windows(service_id='Saturday')
```

**Output Format:**

```
Weekday Service - A Train
================================================================================

to Manhattan:
--------------------------------------------------------------------------------
  Brooklyn       : 05:12:30 → 22:18:00
  Manhattan      : 05:12:30 → 22:18:00

to Queens:
--------------------------------------------------------------------------------
  Brooklyn       : 01:13:00 → 22:06:00
  Manhattan      : 05:09:00 → 22:06:00
```

---

## Helper Functions

### `get_station_order(feed, route_id, direction_id, service_id='Weekday')`

**Location:** `travel_times.py`

Gets the canonical ordering of stations for a route.

**Returns:** List of (stop_id, stop_name) tuples in route order

---

### `filter_station_order_express(feed, station_order, route_id, direction_id, service_id='Weekday', express_boroughs=None, all_stops_boroughs=None)`

**Location:** `travel_times.py`

Filters station order to show only express stops in certain boroughs.

**Parameters:**

- `express_boroughs`: List of boroughs where only express stops should be shown (e.g., `['Manhattan', 'Brooklyn']`)
- `all_stops_boroughs`: List of boroughs where all stops should be shown (e.g., `['Queens']`)

**Returns:** Filtered list of (stop_id, stop_name) tuples

---

### `print_headway_dist(df)`

**Location:** `combined_headways.py`

Pretty-prints a headway distribution DataFrame with formatting.

**Parameters:**

- `df`: DataFrame from `get_headway_dist()` or related functions

---

## Complete Examples

### Example 1: Morning Rush Hour Analysis

```python
import gtfs_kit as gk
import combined_headways as ch
import compare_lines as cl

feed = gk.read_feed("gtfs_subway.zip", dist_units="m")

# Analyze headways during morning rush
headways = ch.get_headway_dist(feed, 'A', 1, hour_range=(7, 9))
ch.print_headway_dist(headways)

# Compare express vs local during same period
diff = cl.compare_lines(feed, 'C', 'A', hour_range=(7, 9))
```

### Example 2: Branch-Specific Analysis

```python
# Compare 7 vs 7X
diff = cl.compare_lines(feed, '7', '7X', hour_range=(7, 9))

# Analyze 5 train branches separately
nereid = ch.get_headway_dist_branch(feed, '5', 1, 'Nereid')
eastchester = ch.get_headway_dist_branch(feed, '5', 1, 'Dyre')
```

### Example 3: Combined Service Analysis

```python
# Combined headways for 2 and 5 (to Nereid) trains
combined = ch.get_headway_dist_combined(
    feed, 1, '2', ('5', 'Nereid'),
    service_id='Weekday',
    hour_range=(7, 9)
)
ch.print_headway_dist(combined)
```

### Example 4: Skip-Stop Service (J/Z)

```python
import skip_stop as ss

# Get station classifications
j_only, z_only, shared = ss.get_skip_stop_stations(feed, 1, 'Weekday')

# Check when Z trains run
z_hours = ss.get_z_service_hours(feed, 'Weekday')
print(f"Z service hours: {sorted(z_hours)}")  # [7, 8, 16, 17, 18]

# Compare headways at shared vs J-only stations during rush hour
broadway_jct = shared[10][0]  # Shared station
halsey_st = j_only[4][0]      # J-only station

# Morning rush comparison
bj_rush = ss.get_effective_headway(feed, 1, 'Weekday',
                                    stop_id=broadway_jct, hour_range=(7, 9))
halsey_rush = ss.get_effective_headway(feed, 1, 'Weekday',
                                        stop_id=halsey_st, hour_range=(7, 9))

# Broadway Junction gets ~6 min headway (J+Z combined)
# Halsey St gets ~8 min headway (J only)
```

### Example 5: Express Service Windows

```python
import express_windows as ew

# Load pre-generated express window data (fast)
data = ew.load_express_windows()

# Check when A train runs express in Manhattan on weekdays
a_manhattan = ew.get_express_window('A', 0, 'Weekday', 'Manhattan')
print(f"A train express in Manhattan (Weekday): {a_manhattan[0]} to {a_manhattan[1]}")
# Output: A train express in Manhattan (Weekday): 05:12:30 to 22:18:00

# Compare weekday vs weekend service
a_manhattan_sat = ew.get_express_window('A', 0, 'Saturday', 'Manhattan')
if a_manhattan_sat:
    print(f"A train express in Manhattan (Saturday): {a_manhattan_sat[0]} to {a_manhattan_sat[1]}")

# Check all boroughs for D train southbound on weekdays
d_windows = ew.get_express_window('D', 1, 'Weekday')
for borough, (first, last) in d_windows.items():
    print(f"D train express in {borough}: {first} to {last}")

# Check if C train runs express (it doesn't)
c_windows = ew.get_express_window('C', 0, 'Weekday')
print(f"C train express windows: {c_windows}")  # Empty dict

# Check express variant (6X runs express in Bronx, local in Manhattan)
x_windows = ew.get_express_window('6X', 0, 'Weekday')
print(f"6X express windows: {x_windows}")  # Only shows Bronx

# Pretty-print all express windows for a route on weekdays
ew.print_express_windows('4', 'Weekday')

# Pretty-print all routes for all service patterns
ew.print_express_windows()

# Regenerate data from GTFS (slow, only needed when GTFS updates)
# import gtfs_kit as gk
# feed = gk.read_feed("gtfs_subway.zip", dist_units="m")
# # Generate for all standard service patterns
# ew.generate_express_windows(feed, service_ids=['Weekday', 'Saturday', 'Sunday'])
# # Or auto-detect all service_ids
# ew.generate_express_windows(feed, service_ids=None)
```

---

## Important Notes

### Hour Range Specification

- Single int: `hour=7` means 7:00-7:59 AM
- Tuple: `hour_range=(7, 9)` means 7:00-9:59 AM (inclusive)
- Hours use 24-hour format (17 = 5 PM)

### Direction IDs

- Direction 0: Typically away from Manhattan (outbound)
- Direction 1: Typically toward Manhattan (inbound)
- Check `direction_names.csv` for route-specific meanings

### Express Stop Classification

Express stops are identified using a 50% threshold: a stop is considered "express" if at least 50% of the route's trips stop there. This filters out late-night/off-peak local stops while keeping regular express stops.

### Borough Boundaries

Borough assignments use polygon boundaries defined in `express_local.py`. The boundaries could possibly contain undiscovered errors.

### Skip-Stop Service (J/Z)

The J/Z lines use a unique **skip-stop** system that differs from traditional express/local service:

- **Z trains** only run during rush hours (7-8 AM and 4-6 PM on weekdays)
- **Z trains skip 9 stations** that J trains stop at (111 St, 85 St-Forest Pkwy, Cypress Hills, Cleveland St, Halsey St, Kosciuszko St, Flushing Av, Lorimer St, Hewes St)
- **21 stations are served by both** J and Z trains
- During Z service hours:
  - Shared stations get combined J+Z service (~6 min headway during rush)
  - J-only stations get J service only (~8 min headway during rush)
  - GTFS data shows all J trips as "all-stop" even during Z service hours
- Outside Z service hours, J trains run all-stop service to all 30 stations

This differs from express/local (e.g., A/C) where the express train consistently skips the same stations throughout the day.

---

## File Outputs

### CSV Exports

**Travel Time Comparisons:**

- Format: `{local}_vs_{express}_difference_{service}_{hours}.csv`
- Example: `C_vs_A_difference_Weekday_hours_7-9.csv`

**Headway Tables:**
Generated programmatically via print statements (not automatically exported to CSV).

### JSON Exports

**Express Service Windows:**

- File: `express_window_data.json`
- Generated by: `python3 express_windows.py`
- Contains: Express service windows for all routes, all directions, all boroughs, across multiple service patterns
- Structure: `{service_id: {route_id: {direction_id: {borough: [first_time, last_time]}}}}`
- Used by: `express_windows.load_express_windows()` and `express_windows.get_express_window()`
- Includes: All standard routes plus 6X, 7X, FX express variants and J/Z skip-stop data
- Service patterns: Weekday, Saturday, Sunday (by default; can be customized)
- Special cases: Pre-applied hardcoded rules for A, B, C, F, M, R, 1, 6, L, G trains
