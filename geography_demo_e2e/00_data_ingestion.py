# Databricks notebook source
# MAGIC %md
# MAGIC # Earthquake Data Ingestion
# MAGIC 
# MAGIC This notebook fetches earthquake data from USGS API and saves it to a volume for processing.
# MAGIC 
# MAGIC **Data Source:** https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson
# MAGIC 
# MAGIC ---
# MAGIC 
# MAGIC **About this demo:** This is part of an end-to-end demo showcasing [Databricks Spatial SQL](https://www.databricks.com/blog/introducing-spatial-sql-databricks-80-functions-high-performance-geospatial-analytics) 
# MAGIC with GEOGRAPHY and GEOMETRY types (announced September 17, 2025).

# COMMAND ----------

# MAGIC %md
# MAGIC ## Setup and Configuration

# COMMAND ----------

import requests
import json
from datetime import datetime
from pyspark.sql import SparkSession

# Configuration
USGS_API_URL = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson"
CATALOG = "main"  # Update with your catalog name
SCHEMA = "earthquake_demo"  # Update with your schema name
VOLUME = "raw_data"

# Full volume path
VOLUME_PATH = f"/Volumes/{CATALOG}/{SCHEMA}/{VOLUME}"

# COMMAND ----------

# MAGIC %md
# MAGIC ## Create Catalog, Schema, and Volume

# COMMAND ----------

# Create catalog if not exists
spark.sql(f"CREATE CATALOG IF NOT EXISTS {CATALOG}")

# Create schema if not exists
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{SCHEMA}")

# Create volume if not exists
spark.sql(f"CREATE VOLUME IF NOT EXISTS {CATALOG}.{SCHEMA}.{VOLUME}")

print(f"✓ Catalog: {CATALOG}")
print(f"✓ Schema: {SCHEMA}")
print(f"✓ Volume: {VOLUME}")
print(f"✓ Volume Path: {VOLUME_PATH}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Fetch Earthquake Data from USGS API

# COMMAND ----------

def fetch_earthquake_data(url):
    """
    Fetch earthquake data from USGS API
    """
    try:
        print(f"Fetching data from: {url}")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        # Print summary
        metadata = data.get('metadata', {})
        features = data.get('features', [])
        
        print(f"\n✓ Successfully fetched earthquake data")
        print(f"  - Title: {metadata.get('title', 'N/A')}")
        print(f"  - Count: {metadata.get('count', len(features))} earthquakes")
        print(f"  - Generated: {datetime.fromtimestamp(metadata.get('generated', 0) / 1000)}")
        
        return data
    except Exception as e:
        print(f"✗ Error fetching data: {str(e)}")
        raise

# Fetch the data
earthquake_data = fetch_earthquake_data(USGS_API_URL)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Save Raw Data to Volume

# COMMAND ----------

# Generate timestamp for file naming
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
output_file = f"{VOLUME_PATH}/earthquakes_{timestamp}.json"

# Save to volume using dbutils
dbutils.fs.put(output_file, json.dumps(earthquake_data, indent=2), overwrite=True)

print(f"✓ Data saved to: {output_file}")
print(f"✓ File size: {len(json.dumps(earthquake_data))} bytes")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Verify Saved Data

# COMMAND ----------

# List files in volume
files = dbutils.fs.ls(VOLUME_PATH)
print("Files in volume:")
for file in files:
    print(f"  - {file.name} ({file.size} bytes)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Preview Sample Data

# COMMAND ----------

# Display sample earthquake features
features = earthquake_data.get('features', [])
if features:
    print(f"Sample earthquake data (first 3 of {len(features)}):\n")
    for i, feature in enumerate(features[:3], 1):
        props = feature.get('properties', {})
        geom = feature.get('geometry', {})
        coords = geom.get('coordinates', [])
        
        print(f"{i}. Magnitude: {props.get('mag')}")
        print(f"   Place: {props.get('place')}")
        print(f"   Time: {datetime.fromtimestamp(props.get('time', 0) / 1000)}")
        print(f"   Coordinates: [{coords[0]}, {coords[1]}] (depth: {coords[2]} km)")
        print(f"   Type: {props.get('type')}")
        print()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Next Steps
# MAGIC 
# MAGIC 1. Run notebook `01_bronze_layer` to create GEOGRAPHY columns from GeoJSON
# MAGIC 2. Transform to Silver layer with spatial enrichments
# MAGIC 3. Perform spatial analysis with 80+ ST_ functions
# MAGIC 4. Visualize earthquakes on interactive maps
# MAGIC 
# MAGIC **Learn more:** [Introducing Spatial SQL in Databricks](https://www.databricks.com/blog/introducing-spatial-sql-databricks-80-functions-high-performance-geospatial-analytics)
