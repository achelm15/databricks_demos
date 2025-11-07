# Databricks notebook source
# DBTITLE 1,Variables
dbutils.widgets.dropdown("reset_all_data", "0", ["1", "0"], "Reset all data")
dbutils.widgets.text(name="catalog", defaultValue="mlb_gumbo", label="Catalog")

# COMMAND ----------

# Imports
import pyspark.sql.functions as F

# COMMAND ----------

# DBTITLE 1,Global Variables
# Reset All Data
RESET_ALL_DATA = bool(int(dbutils.widgets.get("reset_all_data")))
print(f"Reset All Data: {RESET_ALL_DATA}")

# Global variables
CATALOG = dbutils.widgets.get("catalog")
DATABASE_L = 'landing'
DATABASE_B = 'bronze'
DATABASE_S = 'silver'
DATABASE_G = 'gold'

# Data Location
CHECKPOINT_BASE = f"/Volumes/{CATALOG}/{DATABASE_L}/mlb_gumbo_checkpoints"
DATA_LOCATION = f"/Volumes/{CATALOG}/{DATABASE_L}/mlb_gumbo_data"

# COMMAND ----------

bronze_tables = list(spark.sql(f"""SHOW TABLES IN {CATALOG}.bronze""").select('tableName').toPandas()['tableName'].values)
silver_tables = list(spark.sql(f"""SHOW TABLES IN {CATALOG}.silver""").select('tableName').toPandas()['tableName'].values)

# COMMAND ----------

# Set the flag to validate all data
validate_all_data = True

# Check if validation is required
if validate_all_data:
  # Print details for Bronze Tables
  print("Bronze Tables:\n")
  for table in bronze_tables:
    # Print the table name
    print(f'Table: {table}')
    # Read the table into a DataFrame
    df = spark.read.table(f'{CATALOG}.bronze.{table}')
    # Print the number of rows in the table
    print(f'Number of rows: {df.count()}')
    # Print the number of unique events in the table
    print('===========================================================')
    print()
    
  # Print details for Silver Tables
  print("\nSilver Tables:\n")
  for table in silver_tables:
    # Print the table name
    print(f'Table: {table}')
    # Read the table into a DataFrame
    df = spark.read.table(f'{CATALOG}.silver.{table}')
    # Print the number of rows in the table
    print(f'Number of rows: {df.count()}')
    print('===========================================================')
    print()

# COMMAND ----------

# Check the flag to reset all data
if RESET_ALL_DATA:
  # Silver
  tables_to_drop = ["game_data", "pitch_data", "strike_probability"]
  for table in tables_to_drop:
    spark.sql(f"DROP TABLE IF EXISTS {CATALOG}.{DATABASE_S}.{table}")
  print("Deleted SILVER database!")


  # Silver
  tables_to_drop = ["raw_data"]
  for table in tables_to_drop:
    spark.sql(f"DROP TABLE IF EXISTS {CATALOG}.{DATABASE_B}.{table}")
  print("Deleted BRONZE database!")

  # Delete Data Checkpoints
  dbutils.fs.rm(CHECKPOINT_BASE, True)
  dbutils.fs.rm(DATA_LOCATION, True)
  print("Checkpoints cleared!")

# COMMAND ----------

