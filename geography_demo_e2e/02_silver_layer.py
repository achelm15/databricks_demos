# Databricks notebook source
# MAGIC %md
# MAGIC # Silver Layer - Enriched Earthquake Data
# MAGIC 
# MAGIC This notebook transforms Bronze layer data (which already has GEOGRAPHY columns) into Silver layer with:
# MAGIC - Data quality improvements and validation
# MAGIC - Type conversions (timestamps, categories)
# MAGIC - Additional GEOGRAPHY transformations and derived spatial attributes
# MAGIC - Enriched attributes for analysis
# MAGIC 
# MAGIC **Silver Layer:** Cleaned, validated, and enriched data with rich GEOGRAPHY attributes.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configuration

# COMMAND ----------

from pyspark.sql.functions import *
from pyspark.sql.types import *
from datetime import datetime

# Configuration
CATALOG = "main"
SCHEMA = "earthquake_demo"
BRONZE_TABLE = "earthquakes_bronze"
SILVER_TABLE = "earthquakes_silver"

BRONZE_TABLE_PATH = f"{CATALOG}.{SCHEMA}.{BRONZE_TABLE}"
SILVER_TABLE_PATH = f"{CATALOG}.{SCHEMA}.{SILVER_TABLE}"

print(f"Source: {BRONZE_TABLE_PATH}")
print(f"Target: {SILVER_TABLE_PATH}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Read Bronze Table

# COMMAND ----------

bronze_df = spark.table(BRONZE_TABLE_PATH)
print(f"Bronze records: {bronze_df.count()}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Data Quality and Transformations

# COMMAND ----------

# Apply transformations and data quality rules
silver_df = (
    bronze_df
    # Filter out records with null coordinates or magnitude
    .filter(
        col("latitude").isNotNull() &
        col("longitude").isNotNull() &
        col("magnitude").isNotNull()
    )
    
    # Convert timestamps from milliseconds to proper timestamp type
    .withColumn("event_time", (col("event_time_ms") / 1000).cast("timestamp"))
    .withColumn("updated_time", (col("updated_time_ms") / 1000).cast("timestamp"))
    .withColumn("feed_generated_time", (col("feed_generated_timestamp") / 1000).cast("timestamp"))
    
    # Add derived columns
    .withColumn("magnitude_category", 
        when(col("magnitude") < 2.0, "Micro")
        .when(col("magnitude") < 4.0, "Minor")
        .when(col("magnitude") < 5.0, "Light")
        .when(col("magnitude") < 6.0, "Moderate")
        .when(col("magnitude") < 7.0, "Strong")
        .when(col("magnitude") < 8.0, "Major")
        .otherwise("Great")
    )
    
    .withColumn("depth_category",
        when(col("depth_km") < 0, "Above surface")
        .when(col("depth_km") < 70, "Shallow")
        .when(col("depth_km") < 300, "Intermediate")
        .otherwise("Deep")
    )
    
    # Extract region from place (text before comma)
    .withColumn("region", 
        when(col("place").contains(","), 
             regexp_extract(col("place"), "^.*,\\s*(.*)$", 1))
        .otherwise(col("place"))
    )
    
    # Add data quality flags
    .withColumn("has_felt_reports", col("felt_reports").isNotNull())
    .withColumn("has_tsunami_warning", col("tsunami") === 1)
    .withColumn("is_reviewed", col("status") === "reviewed")
    
    # Calculate time since event
    .withColumn("hours_since_event", 
        (unix_timestamp(current_timestamp()) - unix_timestamp(col("event_time"))) / 3600
    )
)

print(f"Silver records after quality filters: {silver_df.count()}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Enrich GEOGRAPHY Columns
# MAGIC 
# MAGIC The GEOGRAPHY column already exists from Bronze layer.
# MAGIC Now add spatial enrichments and derived geography attributes.

# COMMAND ----------

# Add spatial buffer zones around each earthquake
# Create buffers at different radii (in meters)
silver_df = (
    silver_df
    # 50km buffer zone
    .withColumn("geography_buffer_50km", expr("ST_Buffer(geography, 50000)"))
    
    # 100km buffer zone
    .withColumn("geography_buffer_100km", expr("ST_Buffer(geography, 100000)"))
    
    # Calculate the area of the 100km buffer (in square meters)
    .withColumn("buffer_100km_area_sqm", expr("ST_Area(geography_buffer_100km)"))
    
    # Convert area to square kilometers
    .withColumn("buffer_100km_area_sqkm", col("buffer_100km_area_sqm") / 1_000_000)
)

print("GEOGRAPHY enrichments added successfully!")
print("\nSample with GEOGRAPHY buffers:")
silver_df.select(
    "event_id", 
    "geography_wkt", 
    "buffer_100km_area_sqkm"
).show(5, truncate=False)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Preview Silver Data

# COMMAND ----------

display(
    silver_df.select(
        "event_id",
        "event_time",
        "magnitude",
        "magnitude_category",
        "depth_km",
        "depth_category",
        "place",
        "region",
        "latitude",
        "longitude",
        "geography_point",
        "event_type",
        "status",
        "is_reviewed",
        "has_felt_reports",
        "significance"
    )
    .orderBy(desc("magnitude"))
    .limit(20)
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Data Quality Summary

# COMMAND ----------

print("=== Silver Layer Data Quality Summary ===\n")

# Record counts
total_records = silver_df.count()
print(f"Total records: {total_records}")

# Magnitude distribution
print("\nMagnitude Category Distribution:")
silver_df.groupBy("magnitude_category").count().orderBy("magnitude_category").show()

# Depth distribution
print("Depth Category Distribution:")
silver_df.groupBy("depth_category").count().orderBy("depth_category").show()

# Review status
print("Review Status:")
silver_df.groupBy("is_reviewed").count().show()

# Top regions
print("Top 10 Regions:")
silver_df.groupBy("region").count().orderBy(desc("count")).limit(10).show(truncate=False)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Write to Silver Delta Table

# COMMAND ----------

# Select final columns for Silver table
silver_final_df = silver_df.select(
    # Identifiers
    "event_id",
    "event_type",
    
    # Time information
    "event_time",
    "updated_time",
    "hours_since_event",
    
    # Location information
    "place",
    "region",
    "latitude",
    "longitude",
    
    # GEOGRAPHY type columns (from Bronze)
    "geography",
    "geography_wkt",
    "geography_longitude",
    "geography_latitude",
    
    # GEOGRAPHY enrichments (from Silver)
    "geography_buffer_50km",
    "geography_buffer_100km",
    "buffer_100km_area_sqkm",
    
    # Earthquake properties
    "magnitude",
    "magnitude_type",
    "magnitude_category",
    "depth_km",
    "depth_category",
    
    # Quality metrics
    "significance",
    "status",
    "is_reviewed",
    "num_stations",
    "gap",
    "rms",
    "min_distance",
    
    # Impact information
    "felt_reports",
    "has_felt_reports",
    "cdi",
    "mmi",
    "alert_level",
    "tsunami",
    "has_tsunami_warning",
    
    # References
    "event_url",
    "detail_url",
    "network",
    "code",
    
    # Metadata
    "feed_generated_time",
    "ingestion_timestamp",
    "source_file"
)

# Write to Delta table
(
    silver_final_df
    .write
    .format("delta")
    .mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable(SILVER_TABLE_PATH)
)

print(f"✓ Silver table created: {SILVER_TABLE_PATH}")
print(f"✓ Record count: {silver_final_df.count()}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Verify Silver Table with GEOGRAPHY Type

# COMMAND ----------

# Read back and verify
silver_table = spark.table(SILVER_TABLE_PATH)

print("Silver table schema:")
silver_table.printSchema()

print(f"\nSilver table record count: {silver_table.count()}")

# Show sample with geography
display(
    silver_table
    .select(
        "event_id", 
        "magnitude", 
        "place", 
        "geography", 
        "geography_wkt",
        "buffer_100km_area_sqkm"
    )
    .orderBy(desc("magnitude"))
    .limit(10)
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Table Statistics

# COMMAND ----------

# Describe table
spark.sql(f"DESCRIBE DETAIL {SILVER_TABLE_PATH}").show(truncate=False)

# Show table properties
print("\nTable properties:")
spark.sql(f"SHOW TBLPROPERTIES {SILVER_TABLE_PATH}").show(truncate=False)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Next Steps
# MAGIC 
# MAGIC Run notebook `03_spatial_analysis` to perform spatial analysis using ST_ functions

