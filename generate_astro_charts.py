import pandas as pd
from kerykeion import AstrologicalSubject
from timezonefinder import TimezoneFinder
import pytz
import swisseph as swe
import os
import json

# Set the path to the Swiss Ephemeris files
kerykeion_sweph_path = "/usr/local/lib/python3.11/dist-packages/kerykeion/sweph/"
if os.path.exists(kerykeion_sweph_path):
    # Ensure pyswisseph uses the available ephemeris file
    # The error 'seas_12.se1' not found suggests it's looking for a specific file.
    # We'll try to explicitly set the path and hope it picks up 'seas_18.se1'.
    # If not, a deeper fix in pyswisseph configuration might be needed.
    swe.set_ephe_path(kerykeion_sweph_path)
    print(f"Swiss Ephemeris path set to: {kerykeion_sweph_path}")
else:
    print("Kerykeion sweph path not found. Please ensure pyswisseph is correctly installed.")

# Load the cleaned Pantheon data
df = pd.read_csv("pantheon_cleaned_data.csv")

# Limit to the first 1000 records for MVP
df = df.head(1000)

# Initialize TimezoneFinder
tf = TimezoneFinder()

# Initialize a list to store astrological data and professions
astro_data_list = []

# Function to extract astrological points from a Kerykeion AstrologicalSubject object
def extract_astro_points(chart):
    points = {}
    # Planets and other points
    for planet_name in ["sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn", 
                        "uranus", "neptune", "pluto", "chiron"]:
        planet = getattr(chart, planet_name, None)
        if planet:
            points[f"{planet_name}_sign"] = getattr(planet, 'sign', None)
            points[f"{planet_name}_degree"] = getattr(planet, 'degree', None)
            points[f"{planet_name}_house"] = getattr(planet, 'house', None)
        else:
            points[f"{planet_name}_sign"] = None
            points[f"{planet_name}_degree"] = None
            points[f"{planet_name}_house"] = None

    # Handle lilith and north_node separately as they might be missing or named differently
    points["lilith_sign"] = getattr(chart.lilith, 'sign', None) if hasattr(chart, 'lilith') else None
    points["lilith_degree"] = getattr(chart.lilith, 'degree', None) if hasattr(chart, 'lilith') else None
    points["lilith_house"] = getattr(chart.lilith, 'house', None) if hasattr(chart, 'lilith') else None

    points["north_node_sign"] = getattr(chart.north_node, 'sign', None) if hasattr(chart, 'north_node') else None
    points["north_node_degree"] = getattr(chart.north_node, 'degree', None) if hasattr(chart, 'north_node') else None
    points["north_node_house"] = getattr(chart.north_node, 'house', None) if hasattr(chart, 'north_node') else None

    # Houses
    for i in range(1, 13):
        house = getattr(chart, f"house_{i}", None)
        if house:
            points[f"house_{i}_sign"] = getattr(house, 'sign', None)
            points[f"house_{i}_degree"] = getattr(house, 'degree', None)
        else:
            points[f"house_{i}_sign"] = None
            points[f"house_{i}_degree"] = None
    
    # Ascendant and Midheaven
    points["ascendant_sign"] = getattr(chart.ascendant, 'sign', None)
    points[f"ascendant_degree"] = getattr(chart.ascendant, 'degree', None)
    points["mc_sign"] = getattr(chart.mc, 'sign', None)
    points[f"mc_degree"] = getattr(chart.mc, 'degree', None)

    return points

# Batch processing configuration
batch_size = 100 # Smaller batch size for MVP
output_file_prefix = "astrological_features_with_professions_batch_"

# Iterate through each row of the DataFrame
for index, row in df.iterrows():
    name = row["name"]
    occupation = row["occupation"]
    birth_date = pd.to_datetime(row["birthdate"])
    birth_place_lat = row["bplace_lat"]
    birth_place_lon = row["bplace_lon"]

    # Use 12:00 PM as default time if not available (as per user’s choice)
    birth_hour = 12
    birth_minute = 0

    # Ensure latitude and longitude are valid numbers
    if pd.isna(birth_place_lat) or pd.isna(birth_place_lon):
        print(f"Skipping {name} due to invalid latitude/longitude: {birth_place_lat}, {birth_place_lon}")
        continue

    # Get timezone string from coordinates
    timezone_str = tf.timezone_at(lng=birth_place_lon, lat=birth_place_lat)
    if timezone_str is None:
        timezone_str = 'UTC' # Fallback to UTC if no timezone is found

    try:
        # Create AstrologicalSubject object using explicit lat, lng, and tz_str
        chart = AstrologicalSubject(
            name=name,
            year=birth_date.year,
            month=birth_date.month,
            day=birth_date.day,
            hour=birth_hour,
            minute=birth_minute,
            lat=birth_place_lat,
            lng=birth_place_lon, 
            tz_str=timezone_str,
            geonames_username=None # Explicitly set to None to avoid warnings
        )

        # Extract astrological points
        astro_points = extract_astro_points(chart)
        astro_points["occupation"] = occupation
        astro_data_list.append(astro_points)

    except Exception as e:
        print(f"Error generating chart for {name}: {e}")

    if (index + 1) % batch_size == 0 or (index + 1) == len(df):
        # Save current batch to CSV
        batch_df = pd.DataFrame(astro_data_list)
        batch_file_name = f"{output_file_prefix}{index // batch_size}.csv"
        batch_df.to_csv(batch_file_name, index=False)
        print(f"Processed and saved batch {index // batch_size} to {batch_file_name}")
        astro_data_list = [] # Clear list for next batch

print("Astrological features and professions generation complete.")
