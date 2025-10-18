import pandas as pd
from immanuel import charts
from immanuel.const import chart as immanuel_chart_const
from immanuel.setup import settings
from timezonefinder import TimezoneFinder
import pytz
import os
import json
import logging
import traceback

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Load the cleaned Pantheon data
df = pd.read_csv("pantheon_cleaned_data.csv")

# Limit to a very small number of records for debugging
df = df.head(10)

# Initialize TimezoneFinder
tf = TimezoneFinder()

# Initialize a list to store astrological data and professions
astro_data_list = []

# Function to extract astrological points from an Immanuel Natal chart object
def extract_immanuel_astro_points(natal_chart):
    points = {}
    # Extract objects (planets, nodes, etc.)
    for obj_name, obj_data in natal_chart.objects.items():
        # Example: Sun, Moon, Mercury, Venus, Mars, Jupiter, Saturn,
        # Uranus, Neptune, Pluto, Chiron, North Node, Lilith
        if obj_name in ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", 
                        "Uranus", "Neptune", "Pluto", "Chiron", "North Node", "Lilith"]:
            points[f"{obj_name.lower().replace(' ', '_')}_sign"] = getattr(obj_data.sign, 'name', None)
            points[f"{obj_name.lower().replace(' ', '_')}_degree"] = getattr(obj_data.sign_longitude, 'raw', None)
            points[f"{obj_name.lower().replace(' ', '_')}_house"] = getattr(obj_data.house, 'number', None) if obj_data.house else None

    # Extract houses
    # Iterate over the values of the natal_chart.houses dictionary
    for house_obj in natal_chart.houses.values():
        house_number = getattr(house_obj, 'number', None)
        if house_number:
            points[f"house_{house_number}_sign"] = getattr(house_obj.sign, 'name', None)
            points[f"house_{house_number}_degree"] = getattr(house_obj.sign_longitude, 'raw', None)
    
    # Ascendant and Midheaven
    points["ascendant_sign"] = getattr(natal_chart.ascendant.sign, 'name', None)
    points[f"ascendant_degree"] = getattr(natal_chart.ascendant.sign_longitude, 'raw', None)
    points["mc_sign"] = getattr(natal_chart.mc.sign, 'name', None)
    points[f"mc_degree"] = getattr(natal_chart.mc.sign_longitude, 'raw', None)

    return points

# Batch processing configuration
batch_size = 10 # Very small batch size for debugging
output_file_prefix = "astrological_features_immanuel_batch_"

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
        logging.warning(f"Skipping {name} due to invalid latitude/longitude: {birth_place_lat}, {birth_place_lon}")
        continue

    # Get timezone string from coordinates
    timezone_str = tf.timezone_at(lng=birth_place_lon, lat=birth_place_lat)
    if timezone_str is None:
        timezone_str = 'UTC' # Fallback to UTC if no timezone is found

    try:
        # Create datetime object with timezone info
        tz = pytz.timezone(timezone_str)
        dt_object = tz.localize(pd.Timestamp(year=birth_date.year, month=birth_date.month, 
                                            day=birth_date.day, hour=birth_hour, 
                                            minute=birth_minute).to_pydatetime())

        # Create Immanuel Subject
        native = charts.Subject(
            date_time=dt_object,
            latitude=birth_place_lat,
            longitude=birth_place_lon,
        )

        # Create Immanuel Natal chart
        natal_chart = charts.Natal(native)

        # Extract astrological points
        astro_points = extract_immanuel_astro_points(natal_chart)
        astro_points["occupation"] = occupation
        astro_data_list.append(astro_points)
        logging.info(f"Successfully generated chart for {name}")

    except Exception as e:
        logging.error(f"Error generating chart for {name}: {e}")
        logging.error(traceback.format_exc()) # Print full traceback

    if (index + 1) % batch_size == 0 or (index + 1) == len(df):
        # Save current batch to CSV
        if astro_data_list:
            batch_df = pd.DataFrame(astro_data_list)
            batch_file_name = f"{output_file_prefix}{index // batch_size}.csv"
            batch_df.to_csv(batch_file_name, index=False)
            logging.info(f"Processed and saved batch {index // batch_size} to {batch_file_name}")
            astro_data_list = [] # Clear list for next batch
        else:
            logging.warning(f"No data in batch {index // batch_size} to save.")

logging.info("Astrological features and professions generation complete using Immanuel.")
