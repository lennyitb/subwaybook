import gtfs_kit as gk
import headways as hw
import express_local as el
import pandas as pd


feed = gk.read_feed("/Users/lennyphelan/Downloads/gtfs_subway.zip", dist_units="m")
# hw.display_headway_summary(hw.get_line_headways_by_hour_improved(feed, "A", 0, "Weekday"))
# hw.display_headway_summary(hw.get_line_headways_by_hour_improved(feed, "C", 0, "Weekday"))
# hw.display_headway_summary(hw.get_line_headways_by_hour_improved(feed, "W", 0, "Weekday"))

# Set pandas display options to show all rows and columns
pd.set_option('display.max_rows', None)  # Show all rows
pd.set_option('display.max_columns', None)  # Show all columns
pd.set_option('display.width', None)  # Auto-detect width
pd.set_option('display.max_colwidth', None)  # Show full column content

# Analyze both directions
result_dir0 = el.analyze_route_express_patterns(feed, "A", direction_id=0)
result_dir1 = el.analyze_route_express_patterns(feed, "A", direction_id=1)

# Add direction labels
result_dir0['direction'] = 0
result_dir1['direction'] = 1

# Combine
result = pd.concat([result_dir0, result_dir1], ignore_index=True)

print(result)

# Optionally save to CSV
# result.to_csv('a_train_express_local.csv', index=False)