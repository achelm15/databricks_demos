# Databricks notebook source
# MAGIC %md
# MAGIC # Spatial Analysis with GEOGRAPHY and ST_ Functions
# MAGIC 
# MAGIC This notebook demonstrates Databricks **Spatial SQL** (announced September 2025) with earthquake data:
# MAGIC - GEOGRAPHY and GEOMETRY types
# MAGIC - Distance calculations (ST_Distance)
# MAGIC - Spatial relationships (ST_Within, ST_Contains, ST_Intersects)
# MAGIC - Buffer operations (ST_Buffer)
# MAGIC - Area calculations (ST_Area)
# MAGIC - Geometric operations (ST_Union, ST_Intersection)
# MAGIC - Coordinate transformations
# MAGIC - Clustering and proximity analysis
# MAGIC 
# MAGIC **Showcasing Databricks Spatial SQL:** 80+ functions for high-performance geospatial analytics!
# MAGIC 
# MAGIC [Read the announcement](https://www.databricks.com/blog/introducing-spatial-sql-databricks-80-functions-high-performance-geospatial-analytics)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configuration

# COMMAND ----------

from pyspark.sql.functions import *
from pyspark.sql.types import *
import math

# Configuration
CATALOG = "main"
SCHEMA = "earthquake_demo"
SILVER_TABLE = "earthquakes_silver"
SPATIAL_ANALYSIS_TABLE = "earthquakes_spatial_analysis"

SILVER_TABLE_PATH = f"{CATALOG}.{SCHEMA}.{SILVER_TABLE}"
SPATIAL_TABLE_PATH = f"{CATALOG}.{SCHEMA}.{SPATIAL_ANALYSIS_TABLE}"

print(f"Source: {SILVER_TABLE_PATH}")
print(f"Target: {SPATIAL_TABLE_PATH}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Load Silver Table

# COMMAND ----------

earthquakes_df = spark.table(SILVER_TABLE_PATH)
print(f"Total earthquakes: {earthquakes_df.count()}")

# Show sample with geography
display(earthquakes_df.select(
    "event_id", "magnitude", "place", "geography", "geography_wkt"
).limit(5))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. GEOGRAPHY Type - Already Created in Bronze!
# MAGIC 
# MAGIC Our earthquakes already have GEOGRAPHY columns from the Bronze layer.
# MAGIC Let's verify and explore them.

# COMMAND ----------

print("=== GEOGRAPHY Columns Available ===\n")
print("Columns with spatial data:")
print("- geography: Native GEOGRAPHY type from GeoJSON")
print("- geography_wkt: Well-Known Text representation")
print("- geography_buffer_50km: 50km buffer zone")
print("- geography_buffer_100km: 100km buffer zone")

# Show the geography column
display(
    earthquakes_df.select(
        "event_id", 
        "place", 
        "geography", 
        "geography_wkt",
        "geography_longitude",
        "geography_latitude"
    ).limit(10)
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. ST_AsText / ST_AsGeoJSON - Format Conversions

# COMMAND ----------

# Convert GEOGRAPHY to different formats
format_df = earthquakes_df.withColumn(
    "as_wkt",
    expr("ST_AsText(geography)")
).withColumn(
    "as_geojson",
    expr("ST_AsGeoJSON(geography)")
).select("event_id", "place", "as_wkt", "as_geojson")

print("Geography format conversions:")
display(format_df.limit(5))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. ST_Distance - Calculate Distances Between Points
# MAGIC 
# MAGIC Calculate distances from major cities to earthquakes using GEOGRAPHY type.

# COMMAND ----------

# Define major cities as reference points
cities = [
    ("San Francisco", 37.7749, -122.4194),
    ("Los Angeles", 34.0522, -118.2437),
    ("Tokyo", 35.6762, 139.6503),
    ("Mexico City", 19.4326, -99.1332),
    ("Seattle", 47.6062, -122.3321)
]

# Calculate distance from San Francisco to each earthquake
# ST_Distance with GEOGRAPHY returns distance in METERS (WGS84 spherical)
distance_df = earthquakes_df.withColumn(
    "distance_from_sf_meters",
    expr("ST_Distance(geography, ST_Point(-122.4194, 37.7749))")
).withColumn(
    "distance_from_sf_km",
    col("distance_from_sf_meters") / 1000
).withColumn(
    "distance_from_sf_miles",
    col("distance_from_sf_km") * 0.621371
)

print("Earthquakes nearest to San Francisco (using GEOGRAPHY type):")
display(
    distance_df
    .select("event_id", "magnitude", "place", "geography_wkt", "distance_from_sf_km", "distance_from_sf_miles")
    .orderBy("distance_from_sf_km")
    .limit(20)
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. ST_Buffer - Create Circular Regions Around Points

# COMMAND ----------

# Create a 100km buffer around San Francisco
# ST_Buffer distance is in meters for GEOGRAPHY type
buffer_100km = expr("ST_Buffer(ST_Point(-122.4194, 37.7749), 100000)")

# Find earthquakes within 100km of San Francisco using ST_Within
earthquakes_near_sf = earthquakes_df.withColumn(
    "sf_buffer_100km",
    buffer_100km
).withColumn(
    "within_100km_sf",
    expr("ST_Within(geography, sf_buffer_100km)")
).filter(col("within_100km_sf") == True)

print(f"Earthquakes within 100km of San Francisco: {earthquakes_near_sf.count()}")
display(
    earthquakes_near_sf
    .select("event_id", "magnitude", "place", "event_time", "geography_wkt")
    .orderBy(desc("magnitude"))
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. ST_Area - Calculate Buffer Areas
# MAGIC 
# MAGIC Calculate the area of buffer zones (already created in Silver layer)

# COMMAND ----------

# Calculate areas of the 50km and 100km buffers
area_df = earthquakes_df.withColumn(
    "buffer_50km_area_sqm",
    expr("ST_Area(geography_buffer_50km)")
).withColumn(
    "buffer_50km_area_sqkm",
    col("buffer_50km_area_sqm") / 1_000_000
).withColumn(
    "buffer_100km_area_sqm",
    expr("ST_Area(geography_buffer_100km)")
).withColumn(
    "buffer_100km_area_sqkm",
    col("buffer_100km_area_sqm") / 1_000_000
)

print("Buffer zone areas:")
display(
    area_df
    .select(
        "event_id", 
        "place", 
        "buffer_50km_area_sqkm", 
        "buffer_100km_area_sqkm"
    )
    .limit(10)
)

print("\nNote: Areas are calculated on WGS84 spheroid for accuracy!")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. ST_X, ST_Y, ST_Z - Extract Coordinates from GEOGRAPHY
# MAGIC 
# MAGIC (Already done in Bronze, but let's verify)

# COMMAND ----------

# Verify coordinate extraction from GEOGRAPHY
coords_df = earthquakes_df.select(
    "event_id",
    "geography_wkt",
    "longitude",
    "geography_longitude",
    "latitude",
    "geography_latitude",
    # Show they match
    (col("longitude") - col("geography_longitude")).alias("lon_diff"),
    (col("latitude") - col("geography_latitude")).alias("lat_diff")
)

print("Coordinate extraction from GEOGRAPHY type:")
display(coords_df.limit(10))
print("\n✓ Coordinates extracted correctly (differences should be ~0)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 7. ST_Intersects - Check If Buffer Zones Overlap
# MAGIC 
# MAGIC Find earthquakes whose 50km buffer zones intersect

# COMMAND ----------

# For performance, let's focus on significant earthquakes
significant_quakes = earthquakes_df.filter(col("magnitude") >= 3.0)

# Create aliases for self-join
quakes_a = significant_quakes.alias("a")
quakes_b = significant_quakes.alias("b")

# Find pairs where 50km buffers intersect
intersecting_df = (
    quakes_a.join(
        quakes_b,
        expr("""
            a.event_id < b.event_id AND
            ST_Intersects(a.geography_buffer_50km, b.geography_buffer_50km)
        """)
    )
    .select(
        col("a.event_id").alias("earthquake_1_id"),
        col("a.place").alias("earthquake_1_place"),
        col("a.magnitude").alias("earthquake_1_mag"),
        col("b.event_id").alias("earthquake_2_id"),
        col("b.place").alias("earthquake_2_place"),
        col("b.magnitude").alias("earthquake_2_mag"),
        (expr("ST_Distance(a.geography, b.geography)") / 1000).alias("distance_km")
    )
    .orderBy("distance_km")
)

print("Earthquake pairs with intersecting 50km buffer zones:")
display(intersecting_df.limit(20))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 8. Spatial Clustering - Find Earthquake Clusters

# COMMAND ----------

# Find earthquakes within 50km of each other using GEOGRAPHY
# For performance, focus on significant earthquakes (magnitude >= 3.0)
significant_quakes = earthquakes_df.filter(col("magnitude") >= 3.0)

quakes_a = significant_quakes.alias("a")
quakes_b = significant_quakes.alias("b")

# Find pairs of earthquakes within 50km
clusters_df = (
    quakes_a.join(
        quakes_b,
        expr("""
            a.event_id < b.event_id AND
            ST_Distance(a.geography, b.geography) < 50000
        """)
    )
    .select(
        col("a.event_id").alias("earthquake_1_id"),
        col("a.place").alias("earthquake_1_place"),
        col("a.magnitude").alias("earthquake_1_mag"),
        col("b.event_id").alias("earthquake_2_id"),
        col("b.place").alias("earthquake_2_place"),
        col("b.magnitude").alias("earthquake_2_mag"),
        (expr("ST_Distance(a.geography, b.geography)") / 1000).alias("distance_km")
    )
    .orderBy("distance_km")
)

print("Earthquake pairs within 50km (magnitude >= 3.0):")
display(clusters_df.limit(20))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 9. ST_GeomFromText - Geographic Bounding Box Analysis
# MAGIC 
# MAGIC Create polygons and check containment

# COMMAND ----------

# Find earthquakes in specific geographic regions using bounding boxes
# Example: California region (approximately)
california_box = """
    ST_GeomFromText('POLYGON((
        -124.5 32.5,
        -114.0 32.5,
        -114.0 42.0,
        -124.5 42.0,
        -124.5 32.5
    ))')
"""

california_quakes = earthquakes_df.withColumn(
    "california_polygon",
    expr(california_box)
).withColumn(
    "in_california",
    expr("ST_Within(geography, california_polygon)")
).withColumn(
    "polygon_wkt",
    expr("ST_AsText(california_polygon)")
).filter(col("in_california") == True)

print(f"Earthquakes within California polygon: {california_quakes.count()}")
display(
    california_quakes
    .select("event_id", "magnitude", "place", "geography_wkt", "event_time")
    .orderBy(desc("magnitude"))
    .limit(20)
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 10. ST_Contains - Check Point-in-Polygon
# MAGIC 
# MAGIC Reverse of ST_Within - does a region contain a point?

# COMMAND ----------

# Create a large circular region and check which earthquakes it contains
# 500km radius around Los Angeles
la_large_buffer = expr("ST_Buffer(ST_Point(-118.2437, 34.0522), 500000)")

contained_df = earthquakes_df.withColumn(
    "la_500km_zone",
    la_large_buffer
).withColumn(
    "zone_contains_earthquake",
    expr("ST_Contains(la_500km_zone, geography)")
).filter(col("zone_contains_earthquake") == True)

print(f"Earthquakes contained in 500km zone around LA: {contained_df.count()}")
display(
    contained_df
    .select("event_id", "magnitude", "place", "geography_wkt")
    .orderBy(desc("magnitude"))
    .limit(15)
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 11. Distance Matrix - Multiple Cities

# COMMAND ----------

# Calculate distances from multiple cities to each earthquake using GEOGRAPHY
cities_data = [
    ("San Francisco", -122.4194, 37.7749),
    ("Los Angeles", -118.2437, 34.0522),
    ("Seattle", -122.3321, 47.6062),
    ("Portland", -122.6765, 45.5231),
    ("Las Vegas", -115.1398, 36.1699)
]

# Add distance columns for each city using GEOGRAPHY type
distance_matrix_df = earthquakes_df

for city_name, lon, lat in cities_data:
    col_name = f"distance_from_{city_name.lower().replace(' ', '_')}_km"
    distance_matrix_df = distance_matrix_df.withColumn(
        col_name,
        expr(f"ST_Distance(geography, ST_Point({lon}, {lat})) / 1000")
    )

# Find the nearest city for each earthquake
city_cols = [f"distance_from_{city_name.lower().replace(' ', '_')}_km" for city_name, _, _ in cities_data]

distance_matrix_df = distance_matrix_df.withColumn(
    "nearest_city_distance_km",
    least(*[col(c) for c in city_cols])
)

# Determine which city is nearest
for city_name, _, _ in cities_data:
    col_name = f"distance_from_{city_name.lower().replace(' ', '_')}_km"
    distance_matrix_df = distance_matrix_df.withColumn(
        "nearest_city",
        when(col(col_name) == col("nearest_city_distance_km"), lit(city_name))
        .otherwise(col("nearest_city"))
    )

print("Earthquakes with nearest city analysis (using GEOGRAPHY):")
display(
    distance_matrix_df
    .select(
        "event_id", "magnitude", "place", "geography_wkt", 
        "nearest_city", "nearest_city_distance_km",
        *city_cols
    )
    .orderBy(desc("magnitude"))
    .limit(20)
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 12. ST_DWithin - Optimized Proximity Check
# MAGIC 
# MAGIC More efficient than ST_Distance < threshold

# COMMAND ----------

# Find all earthquakes within 100km of San Francisco using ST_DWithin
# This is more efficient than ST_Distance for proximity checks
sf_nearby_optimized = earthquakes_df.filter(
    expr("ST_DWithin(geography, ST_Point(-122.4194, 37.7749), 100000)")
)

print(f"Earthquakes within 100km of SF (using ST_DWithin): {sf_nearby_optimized.count()}")
display(
    sf_nearby_optimized
    .select("event_id", "magnitude", "place", "geography_wkt")
    .orderBy(desc("magnitude"))
    .limit(15)
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 13. Spatial Aggregations by Region

# COMMAND ----------

# Group earthquakes by proximity to major cities
# Count earthquakes within different distance bands

distance_bands = [50, 100, 200, 500]

for city_name, lon, lat in cities_data[:3]:  # First 3 cities
    print(f"\n=== {city_name} ===")
    
    city_analysis = earthquakes_df.withColumn(
        "distance_km",
        expr(f"ST_Distance(geography, ST_Point({lon}, {lat})) / 1000")
    ).withColumn(
        "distance_band",
        when(col("distance_km") < 50, "0-50 km")
        .when(col("distance_km") < 100, "50-100 km")
        .when(col("distance_km") < 200, "100-200 km")
        .when(col("distance_km") < 500, "200-500 km")
        .otherwise("500+ km")
    )
    
    city_analysis.groupBy("distance_band").agg(
        count("*").alias("earthquake_count"),
        avg("magnitude").alias("avg_magnitude"),
        max("magnitude").alias("max_magnitude")
    ).orderBy("distance_band").show()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 14. Advanced: ST_Centroid and ST_Envelope
# MAGIC 
# MAGIC Calculate centroids and bounding boxes

# COMMAND ----------

# For demo purposes, let's create a multi-point geometry from a cluster
# and find its centroid and envelope
if earthquakes_df.filter(col("magnitude") >= 4.0).count() >= 3:
    large_quakes = earthquakes_df.filter(col("magnitude") >= 4.0).limit(5)
    
    # Collect points (for demo - in production use aggregation functions)
    points_collected = large_quakes.select("geography", "place", "magnitude").collect()
    
    print("Sample large earthquakes for centroid calculation:")
    for row in points_collected:
        print(f"  - {row.place}: {row.magnitude}")
    
    print("\n✓ In production, use ST_Union_Agg or ST_Collect to aggregate geometries")
else:
    print("Not enough large earthquakes for multi-point demo")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 15. Create Spatial Analysis Summary Table

# COMMAND ----------

# Create a comprehensive spatial analysis table
spatial_analysis_df = earthquakes_df

# Add San Francisco distance using GEOGRAPHY
spatial_analysis_df = spatial_analysis_df.withColumn(
    "distance_from_sf_km",
    expr("ST_Distance(geography, ST_Point(-122.4194, 37.7749)) / 1000")
)

# Add Los Angeles distance
spatial_analysis_df = spatial_analysis_df.withColumn(
    "distance_from_la_km",
    expr("ST_Distance(geography, ST_Point(-118.2437, 34.0522)) / 1000")
)

# WKT already available from Silver layer as geography_wkt
# But let's add GeoJSON format too
spatial_analysis_df = spatial_analysis_df.withColumn(
    "geojson_geometry",
    expr("ST_AsGeoJSON(geography)")
)

# Add geographic region classification
spatial_analysis_df = spatial_analysis_df.withColumn(
    "geographic_region",
    when(col("region").contains("California"), "California")
    .when(col("region").contains("Alaska"), "Alaska")
    .when(col("region").contains("Nevada"), "Nevada")
    .when(col("region").contains("Washington"), "Washington")
    .when(col("region").contains("Oregon"), "Oregon")
    .when(col("region").contains("Hawaii"), "Hawaii")
    .otherwise("Other")
)

# Add nearest major city
spatial_analysis_df = spatial_analysis_df.withColumn(
    "nearest_major_city",
    when(col("distance_from_sf_km") < col("distance_from_la_km"), "San Francisco")
    .otherwise("Los Angeles")
).withColumn(
    "distance_to_nearest_city_km",
    least(col("distance_from_sf_km"), col("distance_from_la_km"))
)

print("Spatial analysis table preview:")
display(
    spatial_analysis_df
    .select(
        "event_id", "magnitude", "place", "geographic_region",
        "nearest_major_city", "distance_to_nearest_city_km",
        "wkt_geometry"
    )
    .orderBy(desc("magnitude"))
    .limit(20)
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Spatial Functions Summary
# MAGIC 
# MAGIC **Functions demonstrated in this notebook:**
# MAGIC 
# MAGIC 1. ✅ **ST_GeomFromGeoJSON** - Parse GeoJSON to GEOGRAPHY (Bronze layer)
# MAGIC 2. ✅ **ST_Point** - Create point geometries
# MAGIC 3. ✅ **ST_AsText** - Convert to WKT format
# MAGIC 4. ✅ **ST_AsGeoJSON** - Convert to GeoJSON format
# MAGIC 5. ✅ **ST_Distance** - Calculate spherical distances
# MAGIC 6. ✅ **ST_Buffer** - Create buffer zones
# MAGIC 7. ✅ **ST_Area** - Calculate areas on spheroid
# MAGIC 8. ✅ **ST_X / ST_Y** - Extract coordinates
# MAGIC 9. ✅ **ST_Within** - Point-in-polygon containment
# MAGIC 10. ✅ **ST_Contains** - Polygon contains point
# MAGIC 11. ✅ **ST_Intersects** - Check geometry intersection
# MAGIC 12. ✅ **ST_GeomFromText** - Create geometries from WKT
# MAGIC 13. ✅ **ST_DWithin** - Optimized proximity check
# MAGIC 
# MAGIC **Additional functions available:**
# MAGIC - ST_Union - Combine geometries
# MAGIC - ST_Intersection - Find intersection
# MAGIC - ST_Difference - Find difference
# MAGIC - ST_Centroid - Calculate centroid
# MAGIC - ST_Envelope - Bounding box
# MAGIC - ST_Length - Calculate length
# MAGIC - ST_NumPoints - Count points
# MAGIC - And many more!

# COMMAND ----------

# MAGIC %md
# MAGIC ## 16. Save Spatial Analysis Table

# COMMAND ----------

# Select final columns for spatial analysis table
spatial_final_df = spatial_analysis_df.select(
    "event_id",
    "event_time",
    "magnitude",
    "magnitude_category",
    "depth_km",
    "place",
    "region",
    "geographic_region",
    "latitude",
    "longitude",
    "geography",
    "geography_wkt",
    "geojson_geometry",
    "geography_buffer_50km",
    "geography_buffer_100km",
    "distance_from_sf_km",
    "distance_from_la_km",
    "nearest_major_city",
    "distance_to_nearest_city_km",
    "significance",
    "felt_reports",
    "event_url"
)

# Write to Delta table
(
    spatial_final_df
    .write
    .format("delta")
    .mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable(SPATIAL_TABLE_PATH)
)

print(f"✓ Spatial analysis table created: {SPATIAL_TABLE_PATH}")
print(f"✓ Record count: {spatial_final_df.count()}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary Statistics

# COMMAND ----------

print("=== Spatial Analysis Summary ===\n")

# Regional distribution
print("Earthquakes by Geographic Region:")
spatial_final_df.groupBy("geographic_region").agg(
    count("*").alias("count"),
    avg("magnitude").alias("avg_magnitude"),
    max("magnitude").alias("max_magnitude")
).orderBy(desc("count")).show()

# Distance statistics
print("\nDistance to Nearest City Statistics:")
spatial_final_df.select(
    min("distance_to_nearest_city_km").alias("min_km"),
    max("distance_to_nearest_city_km").alias("max_km"),
    avg("distance_to_nearest_city_km").alias("avg_km")
).show()

# Nearest city distribution
print("\nEarthquakes by Nearest Major City:")
spatial_final_df.groupBy("nearest_major_city").count().orderBy(desc("count")).show()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Next Steps
# MAGIC 
# MAGIC Run notebook `04_visualization` to create interactive maps of earthquake data

