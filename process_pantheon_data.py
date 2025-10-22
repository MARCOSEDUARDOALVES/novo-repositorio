import pandas as pd

# Load the dataset
df = pd.read_csv("person_2025_update.csv")

# Display basic information about the dataset
print("Dataset shape:", df.shape)
print("\nDataset columns:", df.columns.tolist())
print("\nDataset info:")
df.info()

# Filter for relevant columns for astrology: name, birth date, birth place, profession
# Based on the previous output, correct column names are:
# 'name', 'occupation', 'birthdate', 'bplace_name', 'bplace_lat', 'bplace_lon'

required_columns = [
    'name',
    'occupation',
    'birthdate',
    'bplace_name',
    'bplace_lat',
    'bplace_lon'
]

# Check for missing required columns
missing_cols = [col for col in required_columns if col not in df.columns]
if missing_cols:
    print(f"\nError: Missing required columns in the dataset: {missing_cols}")
else:
    # Select only the required columns
    df_filtered = df[required_columns].copy()

    # Drop rows with any missing values in the required columns
    df_filtered.dropna(inplace=True)

    print(f"\nShape after filtering for required columns and dropping NaNs: {df_filtered.shape}")

    # Convert 'birthdate' to datetime objects
    # The format seems to be 'YYYY-MM-DD' or 'YYYY-MM-DD BC'
    # We need to handle BC dates and potential missing day/month
    
    # For simplicity, let's first try to convert directly and handle errors
    # A more robust solution would parse the date string carefully
    df_filtered['birth_date_parsed'] = pd.to_datetime(df_filtered['birthdate'], errors='coerce')

    # Drop rows where birth_date could not be parsed
    df_filtered.dropna(subset=['birth_date_parsed'], inplace=True)

    print(f"\nShape after parsing birth_date and dropping NaNs: {df_filtered.shape}")

    # Display some cleaned data
    print("\nFirst 5 rows of cleaned data:")
    print(df_filtered.head())

    # Save the cleaned data for further processing
    df_filtered.to_csv("pantheon_cleaned_data.csv", index=False)
    print("\nCleaned data saved to pantheon_cleaned_data.csv")
