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

# Predictions
import mlflow.pyfunc
import pandas as pd
from pyspark.sql.functions import pandas_udf
from pyspark.sql.types import FloatType

# COMMAND ----------

# Variables
checkpoint_location_silver = f'{CHECKPOINT_BASE}/strike_probability_checkpoints'
table_silver = f'{CATALOG}.{DATABASE_S}.pitch_data'

# COMMAND ----------

# Stream in the raw_data table
df_pitches = (
  spark.readStream
  .format('delta')
  .option("skipChangeCommits", "true")  # Ignores updates/deletes
  .table(table_silver)
)

# COMMAND ----------

df = df_pitches.select(
    F.col("season"),
    F.col("official_date"),
    F.col("game_pk"),
    F.col("at_bat_index"),
    F.col("pitch_index"),
    F.col("pitch_start_speed"),
    F.col("pitch_break_vertical_induced"),
    F.col("pitch_break_horizontal"),
    F.col("pitch_spin_rate"),
    F.col("position_x"),
    F.col("position_z"),
    F.col("pitch_break_horizontal"),
)

# Drop rows with missing values
df = df.dropna()

# COMMAND ----------

# Load the MLflow model (replace with your model URI or registry path)
model_uri = "models:/mlb_gumbo.silver.strike_probability_model/1"
model = mlflow.sklearn.load_model(model_uri)

# Define a Pandas UDF for prediction
@pandas_udf(FloatType())
def predict_udf(*cols):
    # Combine feature columns into a Pandas DataFrame
    feature_cols = ["pitch_start_speed", "pitch_break_vertical_induced",
                    "pitch_break_horizontal", "pitch_spin_rate",
                    "position_x", "position_z"]
    input_data = pd.DataFrame({col: vals for col, vals in zip(feature_cols, cols)})
    
    # Apply the model to generate probabilities
    probabilities = model.predict_proba(input_data)  # 2D array
    return pd.Series(probabilities[:, 1]) 

# Apply the prediction UDF to the streaming DataFrame
feature_columns = [
    "pitch_start_speed", "pitch_break_vertical_induced", 
    "pitch_break_horizontal", "pitch_spin_rate", 
    "position_x", "position_z"
]
df_with_predictions = df.withColumn(
    "strike_probability", 
    predict_udf(*[F.col(col) for col in feature_columns])
).withColumn(
    "last_update_time", F.current_timestamp()
)

# COMMAND ----------

from delta.tables import DeltaTable

def upsert_to_silver(batch_df, batch_id):
    silver_table_name = "mlb_gumbo.silver.strike_probability"  # Unity Catalog table name

    # Reference the Delta table
    silver_table = DeltaTable.forName(spark, silver_table_name)
    
    # Perform the MERGE operation
    silver_table.alias("silver").merge(
        batch_df.alias("updates"),
        """
        silver.season = updates.season AND
        silver.official_date = updates.official_date AND
        silver.game_pk = updates.game_pk AND
        silver.at_bat_index = updates.at_bat_index AND
        silver.pitch_index = updates.pitch_index
        """
    ).whenMatchedUpdateAll() \
     .whenNotMatchedInsertAll() \
     .execute()


# COMMAND ----------

# Write Stream with foreachBatch
(
    df_with_predictions.writeStream.foreachBatch(upsert_to_silver)  # Process each batch with the upsert function
    .outputMode("update") 
    .option("checkpointLocation", checkpoint_location_silver)
    .trigger(availableNow=True)  # Process all available data at once
    .start()
    .awaitTermination()  # Wait for streaming to finish
)