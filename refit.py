import os
import pandas as pd
import datetime

start_time = datetime.datetime.now()
league = "premier-league"


# Path to the data folder
data_folder = "./data/" + league

dfs = []
for filename in os.listdir(data_folder):
    # Check if the file is a CSV
    if filename.endswith(".csv"):
        # Extract the series_id from the filename
        series_id = filename.split(".")[0]
        
        # Load the CSV file
        df = pd.read_csv(os.path.join(data_folder, filename), parse_dates=["datetime"])
        
        # Rename 'score' column to 'value'
        df.rename(columns={"score": "value"}, inplace=True)
        
        # Filter out rows where 'value' is 0
        df = df[df["value"] != 0]
        
        # Assign series_id
        df["series_id"] = series_id
        
        # Calculate the number of rows for the date range
        number_of_rows = len(df)
        if number_of_rows < 20:
            continue
        
        # Create a date range ending today, one day per row, going backwards
        end_date = pd.to_datetime("2024-02-19")
        start_date = end_date - pd.Timedelta(days=number_of_rows - 1)
        date_range = pd.date_range(start_date, periods=number_of_rows, freq="D")
        
        # Assign this date range to the datetime column of the DataFrame, in reverse order
        df["datetime"] = date_range
        
        # Append the DataFrame to the list
        dfs.append(df)

# Concatenate all DataFrames in the list into a single DataFrame
final_df = pd.concat(dfs, ignore_index=True)

from autots import AutoTS

model = AutoTS(
    forecast_length=1,
    frequency="D",
    ensemble="all",
    max_generations=0,
    num_validations=0,
    no_negatives=True,
    verbose=0,
    constraint=2.0,
    introduce_na=False
)
model = model.import_template(
    "./models/" + "ligue-1-fr_model.csv",
    method="only",
    enforce_model_list=True,
)


model = model.fit(
    final_df,
    date_col="datetime",
    value_col="value",
    id_col="series_id",
)


prediction = model.predict()
forecasts_df = prediction.forecast
print(forecasts_df)
# Define the path where you want to save the CSV
forecasts_csv_path = f"./{league}_forecasts.csv"

# Make sure the directory exists before saving
os.makedirs(os.path.dirname(forecasts_csv_path), exist_ok=True)

# Save the DataFrame to CSV
forecasts_df.to_csv(forecasts_csv_path, index=False)


forecasts_df = prediction.forecast
upper_forecasts_df = prediction.upper_forecast
lower_forecasts_df = prediction.lower_forecast

# Rename index to distinguish forecast types
forecasts_df.index = ['forecast']
upper_forecasts_df.index = ['upper_forecast']
lower_forecasts_df.index = ['lower_forecast']

# Concatenate the forecasts vertically
all_forecasts_df = pd.concat([forecasts_df, upper_forecasts_df, lower_forecasts_df])

# Define the path where you want to save the CSV
forecasts_csv_path = f"./{league}_forecasts_all.csv"

# Make sure the directory exists before saving
os.makedirs(os.path.dirname(forecasts_csv_path), exist_ok=True)

# Save the DataFrame to CSV
all_forecasts_df.to_csv(forecasts_csv_path, index_label='Type')

# Confirmation message
print(f"Forecast CSV saved to {forecasts_csv_path}")
