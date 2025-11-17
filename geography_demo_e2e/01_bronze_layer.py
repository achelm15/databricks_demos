# Databricks notebook source
# MAGIC %md
# MAGIC # Bronze Layer - Earthquake Data with GEOGRAPHY Type
# MAGIC 
# MAGIC This notebook reads the raw GeoJSON data from the volume and creates GEOGRAPHY columns immediately.
# MAGIC 
# MAGIC **Key Features:**
# MAGIC - Parse GeoJSON geometry to GEOGRAPHY type in Bronze layer
# MAGIC - Use `ST_GeomFromGeoJSON()` to convert GeoJSON geometry
# MAGIC - Preserve raw JSON/VARIANT structure
# MAGIC - Extract coordinates and create spatial columns early in the pipeline

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configuration

# COMMAND ----------

from pyspark.sql.functions import *
from pyspark.sql.types import *

# Configuration
CATALOG = "main"
SCHEMA = "earthquake_demo"
VOLUME = "raw_data"
BRONZE_TABLE = "earthquakes_bronze"

VOLUME_PATH = f"/Volumes/{CATALOG}/{SCHEMA}/{VOLUME}"
BRONZE_TABLE_PATH = f"{CATALOG}.{SCHEMA}.{BRONZE_TABLE}"

print(f"Source: {VOLUME_PATH}")
print(f"Target: {BRONZE_TABLE_PATH}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Read Raw GeoJSON Data from Volume

# COMMAND ----------

# Get the latest earthquake data file
files = dbutils.fs.ls(VOLUME_PATH)
json_files = [f for f in files if f.name.endswith('.json')]

if not json_files:
    raise Exception("No JSON files found in volume!")

# Sort by name (timestamp) and get the latest
latest_file = sorted(json_files, key=lambda x: x.name, reverse=True)[0]
print(f"Reading latest file: {latest_file.name}")

# Read the JSON file - using schema inference
raw_df = spark.read.json(latest_file.path)

print("\nRaw GeoJSON structure loaded!")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Explore Raw GeoJSON Structure

# COMMAND ----------

print("Schema of raw GeoJSON:")
raw_df.printSchema()

print("\nMetadata:")
raw_df.select("metadata.*").show(truncate=False)

print("\nSample feature geometry:")
raw_df.select(explode("features").alias("f")).select("f.geometry").show(3, truncate=False)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Create GEOGRAPHY Columns from GeoJSON
# MAGIC 
# MAGIC **Showcase:** Using Databricks new GEOGRAPHY type and spatial functions:
# MAGIC - `ST_GeomFromGeoJSON()` - Parse GeoJSON geometry to GEOGRAPHY
# MAGIC - `ST_Point()` - Create point geometry from coordinates
# MAGIC - `ST_AsText()` - Convert GEOGRAPHY to WKT format
# MAGIC - `ST_X()`, `ST_Y()` - Extract coordinates from GEOGRAPHY

# COMMAND ----------

# Explode features and create GEOGRAPHY columns immediately
bronze_df = (
    raw_df
    .select(
        col("metadata.generated").alias("feed_generated_timestamp"),
        col("metadata.title").alias("feed_title"),
        col("metadata.count").alias("feed_count"),
        col("metadata.url").alias("feed_url"),
        explode(col("features")).alias("feature")
    )
    .select(
        # Metadata columns
        col("feed_generated_timestamp"),
        col("feed_title"),
        col("feed_count"),
        col("feed_url"),
        
        # Feature ID and type
        col("feature.id").alias("event_id"),
        col("feature.type").alias("feature_type"),
        
        # Store the entire geometry as JSON string for ST_GeomFromGeoJSON
        to_json(col("feature.geometry")).alias("geometry_json"),
        
        # Create GEOGRAPHY column from GeoJSON geometry
        # This is the NEW Databricks GEOGRAPHY type!
        expr("ST_GeomFromGeoJSON(to_json(feature.geometry))").alias("geography"),
        
        # Also extract individual coordinates for convenience
        col("feature.geometry.type").alias("geometry_type"),
        col("feature.geometry.coordinates").alias("coordinates"),
        col("feature.geometry.coordinates")[0].alias("longitude"),
        col("feature.geometry.coordinates")[1].alias("latitude"),
        col("feature.geometry.coordinates")[2].alias("depth_km"),
        
        # Properties (earthquake details)
        col("feature.properties.mag").alias("magnitude"),
        col("feature.properties.place").alias("place"),
        col("feature.properties.time").alias("event_time_ms"),
        col("feature.properties.updated").alias("updated_time_ms"),
        col("feature.properties.tz").alias("timezone"),
        col("feature.properties.url").alias("event_url"),
        col("feature.properties.detail").alias("detail_url"),
        col("feature.properties.felt").alias("felt_reports"),
        col("feature.properties.cdi").alias("cdi"),
        col("feature.properties.mmi").alias("mmi"),
        col("feature.properties.alert").alias("alert_level"),
        col("feature.properties.status").alias("status"),
        col("feature.properties.tsunami").alias("tsunami"),
        col("feature.properties.sig").alias("significance"),
        col("feature.properties.net").alias("network"),
        col("feature.properties.code").alias("code"),
        col("feature.properties.ids").alias("ids"),
        col("feature.properties.sources").alias("sources"),
        col("feature.properties.types").alias("types"),
        col("feature.properties.nst").alias("num_stations"),
        col("feature.properties.dmin").alias("min_distance"),
        col("feature.properties.rms").alias("rms"),
        col("feature.properties.gap").alias("gap"),
        col("feature.properties.magType").alias("magnitude_type"),
        col("feature.properties.type").alias("event_type"),
        col("feature.properties.title").alias("title"),
        
        # Ingestion metadata
        current_timestamp().alias("ingestion_timestamp"),
        lit(latest_file.name).alias("source_file")
    )
)

# Add additional GEOGRAPHY-derived columns
bronze_df = (
    bronze_df
    # Extract coordinates from GEOGRAPHY using ST_X and ST_Y
    .withColumn("geography_longitude", expr("ST_X(geography)"))
    .withColumn("geography_latitude", expr("ST_Y(geography)"))
    
    # Convert GEOGRAPHY to Well-Known Text (WKT) format
    .withColumn("geography_wkt", expr("ST_AsText(geography)"))
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Verify GEOGRAPHY Column Creation

# COMMAND ----------

print("=== GEOGRAPHY Column Verification ===\n")

# Show GEOGRAPHY column alongside coordinates
print("Sample records with GEOGRAPHY type:")
display(
    bronze_df.select(
        "event_id",
        "geography",
        "geography_wkt",
        "longitude",
        "latitude",
        "geography_longitude",
        "geography_latitude"
    ).limit(10)
)

print("\n✓ GEOGRAPHY columns created successfully from GeoJSON!")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Data Quality Checks

# COMMAND ----------

print(f"Total records: {bronze_df.count()}")
print(f"\nNull magnitude count: {bronze_df.filter(col('magnitude').isNull()).count()}")
print(f"Null geography count: {bronze_df.filter(col('geography').isNull()).count()}")
print(f"Null coordinates count: {bronze_df.filter(col('coordinates').isNull()).count()}")

print("\nMagnitude statistics:")
bronze_df.select(
    min("magnitude").alias("min_mag"),
    max("magnitude").alias("max_mag"),
    avg("magnitude").alias("avg_mag"),
    count("magnitude").alias("count")
).show()

print("\nEvent type distribution:")
bronze_df.groupBy("event_type").count().orderBy(desc("count")).show()

print("\nGeometry type distribution:")
bronze_df.groupBy("geometry_type").count().show()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Preview Bronze Data with GEOGRAPHY

# COMMAND ----------

display(bronze_df.select(
    "event_id",
    "magnitude",
    "place",
    "event_time_ms",
    "geography",
    "geography_wkt",
    "latitude",
    "longitude",
    "depth_km",
    "event_type",
    "status"
).limit(20))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Write to Bronze Delta Table

# COMMAND ----------

# Write to Delta table with merge schema option
(
    bronze_df
    .write
    .format("delta")
    .mode("overwrite")  # Use "append" for incremental loads
    .option("mergeSchema", "true")
    .option("overwriteSchema", "true")
    .saveAsTable(BRONZE_TABLE_PATH)
)

print(f"✓ Bronze table created: {BRONZE_TABLE_PATH}")
print(f"✓ Record count: {bronze_df.count()}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Verify Bronze Table

# COMMAND ----------

# Read back the table
bronze_table = spark.table(BRONZE_TABLE_PATH)
print(f"Bronze table record count: {bronze_table.count()}")

# Show sample
display(bronze_table.limit(10))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Table Properties and Metadata

# COMMAND ----------

# Show table details
spark.sql(f"DESCRIBE DETAIL {BRONZE_TABLE_PATH}").show(truncate=False)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Test Spatial Functions on GEOGRAPHY Column
# MAGIC 
# MAGIC Quick demo of spatial functions working on our GEOGRAPHY column

# COMMAND ----------

# Calculate distance from San Francisco to each earthquake
test_spatial_df = bronze_df.withColumn(
    "distance_from_sf_km",
    expr("ST_Distance(geography, ST_Point(-122.4194, 37.7749)) / 1000")
)

print("Sample distance calculations using GEOGRAPHY type:")
display(
    test_spatial_df
    .select("event_id", "place", "geography_wkt", "distance_from_sf_km")
    .orderBy("distance_from_sf_km")
    .limit(10)
)

print("\n✓ Spatial functions working on GEOGRAPHY type!")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Next Steps
# MAGIC 
# MAGIC Run notebook `02_silver_layer` to enrich and transform the GEOGRAPHY data

