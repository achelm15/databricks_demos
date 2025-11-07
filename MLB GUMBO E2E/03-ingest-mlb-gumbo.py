# Databricks notebook source
# MAGIC %run ./00-ddl

# COMMAND ----------

# MAGIC %run ./01-imports

# COMMAND ----------

import os
import requests
import json
import time
import pyspark.sql.functions as F
from datetime import datetime

# COMMAND ----------

# Variables
CHECKPOINT_LOCATION_BRONZE = f'{CHECKPOINT_BASE}/raw_data_checkpoints'

# Set Data Location
DATA_LOCATION = f"/Volumes/{CATALOG}/{DATABASE_L}/mlb_gumbo_data"

# COMMAND ----------

# Get the current date
# today = datetime.now().strftime("%Y-%m-%d") # Use current date to get games today

# Define the start and end dates for the schedule
start_date = "2024-3-01"
end_date = "2024-11-01"

# Construct the URL to fetch the schedule data from the MLB API
URL = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&teamId=116&gameType=R,D,F&startDate={start_date}&endDate={end_date}"
data = requests.get(URL).json()  # Fetch the data and parse it as JSON

# Initialize an empty list to store game PKs
game_pks = []

# Loop through the dates in the fetched data
for date in data.get("dates", []):
  # Loop through the games on each date
  for game in date.get("games", []):
    # Extract the game PK and append it to the list
    game_pk = game.get("gamePk")
    game_pks.append(game_pk)

# Output the list of game PKs
print(f"Extracted {len(game_pks)} games.")

# COMMAND ----------

# Get the current date and time
current_run = datetime.now()
folder_path = f"{DATA_LOCATION}/year={current_run.year}/month={current_run.month}/day={current_run.day}/hour={current_run.hour}/minute={current_run.minute}"

# Create the directory structure if it doesn't exist
os.makedirs(folder_path, exist_ok=True)

# Loop through the GamePKs and download the GUMBO data
for game_pk in game_pks:
  URL = f"https://statsapi.mlb.com/api/v1.1/game/{game_pk}/feed/live?hydrate=credits,alignment,flags,officials,preState"
  data = requests.get(URL).json()

  # Save the data to a JSON file in DBFS
  with open(f'{folder_path}/game_data_{game_pk}.json', 'w') as f:
    json.dump(data, f)

  # Log and sleep
  # print(game_pk)
  # time.sleep(1)

# COMMAND ----------

# Define Bronze Table
BRONZE_TABLE = f"{CATALOG}.{DATABASE_B}.raw_data"

# Ingest
query = (spark.readStream
  .format("cloudFiles")
  .option("cloudFiles.format", "json")
  .option("singleVariantColumn", "data")
  .load(f"{DATA_LOCATION}/*.json")
  .withColumn("file_path", F.col("_metadata.file_path"))
  .withColumn("file_name", F.col("_metadata.file_name"))
  .withColumn("file_size", F.col("_metadata.file_size"))
  .withColumn("file_modification_time", F.col("_metadata.file_modification_time"))
  .withColumn("file_batch_time", F.lit(current_run))
  .withColumn("last_update_time", F.current_timestamp())
  .writeStream
  .option("checkpointLocation", f"{CHECKPOINT_LOCATION_BRONZE}")
  .trigger(availableNow=True)
  .toTable(BRONZE_TABLE)
)

query.awaitTermination()

# COMMAND ----------

