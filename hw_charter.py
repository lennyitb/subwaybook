import gtfs_kit as gk
import headways as hw


feed = gk.read_feed("/Users/lennyphelan/Downloads/gtfs_subway.zip", dist_units="m")
hw.display_headway_summary(hw.get_line_headways_by_hour_improved(feed, "A", 0, "Weekday"))
hw.display_headway_summary(hw.get_line_headways_by_hour_improved(feed, "C", 0, "Weekday"))
hw.display_headway_summary(hw.get_line_headways_by_hour_improved(feed, "W", 0, "Weekday"))