# Databricks notebook source
# Imports
import pyspark.sql.functions as F

# COMMAND ----------

# DBTITLE 1,Global Variables
# Reset All Data
print(f"Resetting All Data")

# Global variables
CATALOG = 'mlb_tech_summit'
DATABASE_L = 'mlb_gumbo_landing'
DATABASE_B = 'mlb_gumbo_bronze'
DATABASE_S = 'mlb_gumbo_silver'
DATABASE_G = 'mlb_gumbo_gold'

# Data Location
CHECKPOINT_BASE = f"/Volumes/{CATALOG}/{DATABASE_L}/mlb_gumbo_checkpoints"
DATA_LOCATION = f"/Volumes/{CATALOG}/{DATABASE_L}/mlb_gumbo_data"

# COMMAND ----------

# Gold
tables_to_drop = ["game_report_mv"]
for table in tables_to_drop:
  spark.sql(f"DROP TABLE IF EXISTS {CATALOG}.{DATABASE_G}.{table}")
print("Deleted GOLD database!")

# Silver
tables_to_drop = ["game_data", "pitch_data", "strike_probability"]
for table in tables_to_drop:
  spark.sql(f"DROP TABLE IF EXISTS {CATALOG}.{DATABASE_S}.{table}")
print("Deleted SILVER database!")

# Bronze
tables_to_drop = ["raw_data"]
for table in tables_to_drop:
  spark.sql(f"DROP TABLE IF EXISTS {CATALOG}.{DATABASE_B}.{table}")
print("Deleted BRONZE database!")

# Delete Data Checkpoints
# dbutils.fs.rm(CHECKPOINT_BASE, True)
# List all items inside the checkpoint folder
items = dbutils.fs.ls(CHECKPOINT_BASE)

# Remove each item individually
for item in items:
    dbutils.fs.rm(item.path, True)

# dbutils.fs.rm(DATA_LOCATION, True)
print("Checkpoints cleared!")

# COMMAND ----------


