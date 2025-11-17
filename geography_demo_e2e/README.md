# Earthquake Data Analysis with Databricks Spatial SQL

An end-to-end Databricks demo showcasing **Spatial SQL with 80+ geospatial functions** (announced [September 17, 2025](https://www.databricks.com/blog/introducing-spatial-sql-databricks-80-functions-high-performance-geospatial-analytics)) using real-time earthquake data from USGS.

## 🎯 Overview

This demo showcases Databricks' **brand new GEOGRAPHY and GEOMETRY types** and the comprehensive suite of **ST_ spatial functions** through a complete earthquake analysis pipeline:

1. **Data Ingestion**: Fetch real-time GeoJSON from USGS API
2. **Bronze Layer**: Parse GeoJSON directly to **GEOGRAPHY type** using `ST_GeomFromGeoJSON()`
3. **Silver Layer**: Enrich with spatial transformations (buffers, areas)
4. **Spatial Analysis**: Demonstrate 15+ **ST_ functions** for spatial operations
5. **Visualization**: Create interactive maps and visualizations

## 🆕 What's New in Databricks Spatial

This demo showcases features announced on **[September 17, 2025](https://www.databricks.com/blog/introducing-spatial-sql-databricks-80-functions-high-performance-geospatial-analytics)** (Public Preview):

### New Data Types
- **GEOGRAPHY**: WGS84 spherical coordinates (lat/lon on Earth)
- **GEOMETRY**: Planar/Cartesian coordinates

### 80+ New Spatial Functions
- **Constructors**: ST_Point, ST_GeomFromGeoJSON, ST_GeomFromText, ST_Buffer
- **Accessors**: ST_X, ST_Y, ST_AsText, ST_AsGeoJSON, ST_Area, ST_Length
- **Predicates**: ST_Within, ST_Contains, ST_Intersects, ST_DWithin
- **Transformations**: ST_Buffer, ST_Union, ST_Intersection, ST_Centroid
- **Measurements**: ST_Distance, ST_Area, ST_Length

## 📊 Data Source

- **API**: [USGS Earthquake Catalog](https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson)
- **Format**: GeoJSON (perfect for GEOGRAPHY type!)
- **Update Frequency**: Real-time (last 24 hours)
- **Coverage**: Global earthquake activity

## 🏗️ Architecture

```
USGS GeoJSON API 
    ↓
Unity Catalog Volume (raw JSON)
    ↓
Bronze Table (GEOGRAPHY type created via ST_GeomFromGeoJSON)
    ↓
Silver Table (enriched with ST_Buffer, ST_Area)
    ↓
Spatial Analysis (15+ ST_ functions)
    ↓
Visualizations (interactive maps)
```

### Key Difference: GEOGRAPHY Created Early!

Unlike traditional pipelines, we create the **GEOGRAPHY column in the Bronze layer** by parsing GeoJSON geometry directly:

```python
# Bronze layer - immediate GEOGRAPHY creation
expr("ST_GeomFromGeoJSON(to_json(feature.geometry))").alias("geography")
```

## 📚 Notebook Details

### 00_data_ingestion.py
- Fetches earthquake data from USGS GeoJSON API
- Creates Unity Catalog schema and volume
- Saves raw GeoJSON to volume
- No transformation - pure ingestion

### 01_bronze_layer.py ⭐ **GEOGRAPHY STARTS HERE**
**Key Innovation:** GEOGRAPHY type created immediately from GeoJSON!

- Reads GeoJSON from volume
- **Parses geometry to GEOGRAPHY** using `ST_GeomFromGeoJSON()`
- Extracts coordinates using `ST_X()` and `ST_Y()`
- Converts to WKT using `ST_AsText()`
- Stores raw GEOGRAPHY in Bronze table

**Functions used:**
- `ST_GeomFromGeoJSON()` - Parse GeoJSON geometry
- `ST_X()` / `ST_Y()` - Extract coordinates
- `ST_AsText()` - Convert to WKT
- `ST_Distance()` - Test spatial queries

### 02_silver_layer.py
**Enriches GEOGRAPHY** with additional spatial attributes:

- Applies data quality filters
- Creates **buffer zones** with `ST_Buffer()`
- Calculates **buffer areas** with `ST_Area()`
- Adds derived attributes (magnitude categories, regions)
- Timestamp conversions

**Functions used:**
- `ST_Buffer()` - Create 50km and 100km zones
- `ST_Area()` - Calculate zone areas on spheroid

### 03_spatial_analysis.py 🌍 **15+ FUNCTIONS SHOWCASED**

Comprehensive demonstration of spatial functions:

1. **Format Conversions**
   - `ST_AsText()` - GEOGRAPHY to WKT
   - `ST_AsGeoJSON()` - GEOGRAPHY to GeoJSON

2. **Distance Calculations**
   - `ST_Distance()` - Spherical distance (meters)
   - `ST_DWithin()` - Optimized proximity check

3. **Spatial Relationships**
   - `ST_Within()` - Point in polygon
   - `ST_Contains()` - Polygon contains point
   - `ST_Intersects()` - Geometry intersection

4. **Geometric Operations**
   - `ST_Buffer()` - Circular regions
   - `ST_Area()` - Surface area on spheroid
   - `ST_GeomFromText()` - WKT to GEOGRAPHY

5. **Coordinate Extraction**
   - `ST_X()` - Extract longitude
   - `ST_Y()` - Extract latitude

6. **Analysis Patterns**
   - Distance matrix to multiple cities
   - Spatial clustering (earthquakes within 50km)
   - Bounding box analysis (California region)
   - Buffer zone intersections
   - Geographic aggregations

### 04_visualization.py
- Folium interactive maps with GEOGRAPHY data
- Plotly scatter maps and heatmaps
- 3D visualizations (lon, lat, depth)
- Timeline analysis
- Regional comparisons

## 🚀 Getting Started

### Prerequisites

- Databricks workspace with **Spatial SQL support** (Public Preview - September 2025)
- Unity Catalog enabled
- Python 3.9+
- Note: Spatial SQL is available in public preview. Check the [Databricks documentation](https://docs.databricks.com/sql/language-manual/data-types/geography-type.html) for latest runtime requirements.

### Setup Instructions

1. **Upload notebooks** to your Databricks workspace

2. **Update configuration** in each notebook:
   ```python
   CATALOG = "main"  # Your catalog name
   SCHEMA = "earthquake_demo"  # Your schema name
   ```

3. **Run notebooks in order**:
   - `00_data_ingestion.py` → Fetch GeoJSON from USGS
   - `01_bronze_layer.py` → **Create GEOGRAPHY columns**
   - `02_silver_layer.py` → Enrich with buffers and areas
   - `03_spatial_analysis.py` → **15+ spatial functions**
   - `04_visualization.py` → Interactive maps

### Required Libraries

Built-in for spatial functions. For visualization:
```python
%pip install folium plotly
```

## 🔍 Key Concepts Demonstrated

### GEOGRAPHY Type Creation from GeoJSON

The Bronze layer immediately creates GEOGRAPHY columns:

```python
# Parse GeoJSON geometry to GEOGRAPHY type
expr("ST_GeomFromGeoJSON(to_json(feature.geometry))").alias("geography")

# Extract coordinates from GEOGRAPHY
.withColumn("longitude", expr("ST_X(geography)"))
.withColumn("latitude", expr("ST_Y(geography)"))

# Convert to WKT format
.withColumn("geography_wkt", expr("ST_AsText(geography)"))
```

### Spatial Enrichment in Silver

```python
# Create buffer zones (radius in meters)
.withColumn("geography_buffer_50km", expr("ST_Buffer(geography, 50000)"))
.withColumn("geography_buffer_100km", expr("ST_Buffer(geography, 100000)"))

# Calculate buffer area (returns square meters)
.withColumn("buffer_area_sqm", expr("ST_Area(geography_buffer_100km)"))
```

### Spatial Analysis Examples

**Distance Calculation** (returns meters on WGS84 spheroid):
```python
expr("ST_Distance(geography, ST_Point(-122.4194, 37.7749)) / 1000")
```

**Optimized Proximity Check**:
```python
# More efficient than ST_Distance < threshold
expr("ST_DWithin(geography, ST_Point(-122.4194, 37.7749), 100000)")
```

**Spatial Containment**:
```python
# Check if earthquake is within buffer zone
expr("ST_Within(geography, buffer_polygon)")

# Check if buffer contains earthquake
expr("ST_Contains(buffer_polygon, geography)")
```

**Buffer Intersection**:
```python
# Do two buffer zones overlap?
expr("ST_Intersects(buffer_a, buffer_b)")
```

**Polygon from WKT**:
```python
# Create California bounding box
california = """ST_GeomFromText('POLYGON((
    -124.5 32.5, -114.0 32.5, -114.0 42.0, -124.5 42.0, -124.5 32.5
))')"""
```

## 📈 Spatial Functions Reference

### Functions Demonstrated

| Function | Purpose | Returns |
|----------|---------|---------|
| `ST_GeomFromGeoJSON()` | Parse GeoJSON to GEOGRAPHY | GEOGRAPHY |
| `ST_Point(lon, lat)` | Create point | GEOGRAPHY |
| `ST_GeomFromText(wkt)` | Parse WKT to GEOGRAPHY | GEOGRAPHY |
| `ST_AsText(geog)` | Convert to WKT | STRING |
| `ST_AsGeoJSON(geog)` | Convert to GeoJSON | STRING |
| `ST_X(point)` | Extract longitude | DOUBLE |
| `ST_Y(point)` | Extract latitude | DOUBLE |
| `ST_Distance(a, b)` | Spherical distance | DOUBLE (meters) |
| `ST_DWithin(a, b, dist)` | Proximity check | BOOLEAN |
| `ST_Buffer(geog, radius)` | Create buffer zone | GEOGRAPHY |
| `ST_Area(geog)` | Calculate area | DOUBLE (sq meters) |
| `ST_Within(point, poly)` | Point in polygon | BOOLEAN |
| `ST_Contains(poly, point)` | Polygon contains point | BOOLEAN |
| `ST_Intersects(a, b)` | Geometries intersect | BOOLEAN |

### Additional Available Functions

- **Geometric**: ST_Union, ST_Intersection, ST_Difference, ST_Boundary
- **Measurements**: ST_Length, ST_Perimeter
- **Properties**: ST_NumPoints, ST_GeometryType, ST_SRID
- **Transformations**: ST_Centroid, ST_Envelope, ST_ConvexHull
- **Validation**: ST_IsValid, ST_IsEmpty

## 🎨 Visualizations

The demo creates multiple visualization types:

1. **Interactive Global Map**: Clickable markers with earthquake details
2. **Density Heatmap**: Seismic activity hotspots
3. **Timeline Plot**: Earthquake occurrence over 24 hours
4. **3D Scatter**: Longitude, latitude, and depth
5. **Regional Analysis**: Comparison across geographic regions
6. **Buffer Visualizations**: Show 50km and 100km zones

## 💡 Best Practices for GEOGRAPHY Type

### 1. Create GEOGRAPHY Early
Parse spatial data to GEOGRAPHY as soon as possible (Bronze layer) for:
- Type safety
- Spatial indexing
- Optimized queries

### 2. Use WGS84 (EPSG:4326)
GEOGRAPHY type uses WGS84 spherical coordinates:
- Perfect for lat/lon data
- Accurate distance calculations on Earth's surface
- No projection distortion

### 3. Buffer Distances in Meters
All distance parameters and returns are in meters:
```python
ST_Buffer(geography, 50000)  # 50km buffer
ST_Distance(a, b) / 1000     # Convert meters to km
```

### 4. Optimize with ST_DWithin
For proximity checks, prefer:
```python
ST_DWithin(geography, point, 100000)  # Faster
```
Over:
```python
ST_Distance(geography, point) < 100000  # Slower
```

### 5. Use Spatial Indexing
- GEOGRAPHY columns support spatial indexing
- Z-order by geographic columns for better performance
- Partition large datasets by region

## 🔄 Scheduling

Run as a daily job to track earthquake activity:

```json
{
  "name": "Earthquake Spatial Analysis Pipeline",
  "tasks": [
    {"notebook_path": "00_data_ingestion"},
    {"notebook_path": "01_bronze_layer"},
    {"notebook_path": "02_silver_layer"},
    {"notebook_path": "03_spatial_analysis"},
    {"notebook_path": "04_visualization"}
  ],
  "schedule": {"quartz_cron_expression": "0 0 0 * * ?"}
}
```

## 🐛 Troubleshooting

### GEOGRAPHY Function Not Found
- **Solution**: Ensure Spatial SQL is enabled in your workspace
- Spatial SQL was announced September 17, 2025 and is in public preview
- Check [Databricks Spatial SQL documentation](https://www.databricks.com/blog/introducing-spatial-sql-databricks-80-functions-high-performance-geospatial-analytics) for availability

### ST_GeomFromGeoJSON Fails
- **Solution**: Ensure valid GeoJSON format
- Check that geometry is properly stringified with `to_json()`

### Distance Calculations Seem Wrong
- **Solution**: Remember distances are in METERS
- Divide by 1000 for kilometers, multiply by 0.000621371 for miles

### Performance Issues with Spatial Joins
- **Solution**: Use ST_DWithin instead of ST_Distance
- Consider spatial partitioning or Z-ordering
- Filter by bounding box before detailed spatial operations

## 🔗 Resources

- [Introducing Spatial SQL in Databricks (Blog Post)](https://www.databricks.com/blog/introducing-spatial-sql-databricks-80-functions-high-performance-geospatial-analytics) - **September 17, 2025**
- [Databricks GEOGRAPHY Type Documentation](https://docs.databricks.com/sql/language-manual/data-types/geography-type.html)
- [Databricks Spatial Functions Reference](https://docs.databricks.com/sql/language-manual/sql-ref-functions-builtin.html#spatial-functions)
- [USGS Earthquake API Documentation](https://earthquake.usgs.gov/earthquakes/feed/v1.0/geojson.php)
- [GeoJSON Specification](https://geojson.org/)
- [Well-Known Text (WKT) Format](https://en.wikipedia.org/wiki/Well-known_text_representation_of_geometry)

## 📄 License

This demo is provided as-is for educational and demonstration purposes.

## 🤝 Contributing

Extend this demo with:
- Additional spatial functions (ST_Union, ST_Centroid, etc.)
- Time-series analysis with GEOGRAPHY
- Machine learning with spatial features
- Real-time alerting for significant earthquakes
- Historical earthquake data analysis

## 📧 Support

For questions:
- Check Databricks spatial functions documentation
- Review USGS API documentation
- Open an issue in your repository

---

**Showcase the Power of Databricks GEOGRAPHY Type! 🌍🔍**

*Demo built for Databricks Spatial SQL - announced September 17, 2025*

## 📊 Real-World Performance

According to the [Databricks announcement](https://www.databricks.com/blog/introducing-spatial-sql-databricks-80-functions-high-performance-geospatial-analytics):

> "**20X faster performance and more than 50% lower costs** on the same workloads" - Rivian Automotive

> "**Shift the load to Databricks and take advantage of distributed processing, fast spatial joins**" - TotalEnergies
