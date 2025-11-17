# Databricks notebook source
# MAGIC %md
# MAGIC # Earthquake Visualization and Mapping
# MAGIC 
# MAGIC This notebook creates interactive visualizations and maps of earthquake data using:
# MAGIC - Databricks built-in visualization
# MAGIC - Plotly for interactive maps
# MAGIC - Folium for detailed geographic visualization
# MAGIC 
# MAGIC **Goal:** Create beautiful, interactive maps of earthquakes worldwide.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Setup and Configuration

# COMMAND ----------

# MAGIC %pip install folium plotly --quiet

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

from pyspark.sql.functions import *
from pyspark.sql.types import *
import pandas as pd
import folium
from folium import plugins
import plotly.express as px
import plotly.graph_objects as go

# Configuration
CATALOG = "main"
SCHEMA = "earthquake_demo"
SPATIAL_TABLE = "earthquakes_spatial_analysis"
SPATIAL_TABLE_PATH = f"{CATALOG}.{SCHEMA}.{SPATIAL_TABLE}"

print(f"Source: {SPATIAL_TABLE_PATH}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Load Spatial Analysis Data

# COMMAND ----------

earthquakes_df = spark.table(SPATIAL_TABLE_PATH)
print(f"Total earthquakes: {earthquakes_df.count()}")

# Convert to Pandas for visualization
earthquakes_pd = earthquakes_df.toPandas()
print(f"Loaded {len(earthquakes_pd)} earthquakes into Pandas")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Basic Statistics and Distribution

# COMMAND ----------

# Magnitude distribution
print("=== Magnitude Distribution ===")
display(
    earthquakes_df.groupBy("magnitude_category")
    .count()
    .orderBy("magnitude_category")
)

# Geographic distribution
print("\n=== Geographic Distribution ===")
display(
    earthquakes_df.groupBy("geographic_region")
    .agg(
        count("*").alias("count"),
        avg("magnitude").alias("avg_magnitude"),
        max("magnitude").alias("max_magnitude")
    )
    .orderBy(desc("count"))
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Databricks Native Visualization
# MAGIC 
# MAGIC Use Databricks built-in map visualization

# COMMAND ----------

# Prepare data for Databricks map
map_data = earthquakes_df.select(
    "latitude",
    "longitude",
    "magnitude",
    "place",
    "event_time",
    "depth_km",
    "magnitude_category"
).orderBy(desc("magnitude"))

display(map_data)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Plotly Interactive Scatter Map

# COMMAND ----------

# Create interactive scatter map with Plotly
fig = px.scatter_geo(
    earthquakes_pd,
    lat='latitude',
    lon='longitude',
    size='magnitude',
    color='magnitude',
    hover_name='place',
    hover_data={
        'magnitude': ':.2f',
        'depth_km': ':.2f',
        'event_time': True,
        'latitude': ':.4f',
        'longitude': ':.4f'
    },
    color_continuous_scale='Reds',
    size_max=30,
    title='Global Earthquake Activity (Last 24 Hours)',
    labels={'magnitude': 'Magnitude', 'depth_km': 'Depth (km)'}
)

fig.update_geos(
    showcountries=True,
    showcoastlines=True,
    showland=True,
    landcolor='lightgray',
    coastlinecolor='white',
    projection_type='natural earth'
)

fig.update_layout(
    height=600,
    margin={"r":0,"t":50,"l":0,"b":0}
)

fig.show()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Plotly Density Heatmap

# COMMAND ----------

# Create density heatmap
fig = px.density_mapbox(
    earthquakes_pd,
    lat='latitude',
    lon='longitude',
    z='magnitude',
    radius=15,
    center=dict(lat=20, lon=-100),
    zoom=2,
    mapbox_style="open-street-map",
    title='Earthquake Density Heatmap',
    color_continuous_scale='Hot',
    labels={'magnitude': 'Magnitude'}
)

fig.update_layout(
    height=600,
    margin={"r":0,"t":50,"l":0,"b":0}
)

fig.show()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Magnitude Distribution Histogram

# COMMAND ----------

# Magnitude histogram
fig = px.histogram(
    earthquakes_pd,
    x='magnitude',
    nbins=50,
    title='Earthquake Magnitude Distribution',
    labels={'magnitude': 'Magnitude', 'count': 'Frequency'},
    color_discrete_sequence=['#d62728']
)

fig.update_layout(
    xaxis_title='Magnitude',
    yaxis_title='Number of Earthquakes',
    showlegend=False,
    height=400
)

fig.show()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. Depth vs Magnitude Scatter Plot

# COMMAND ----------

# Depth vs Magnitude
fig = px.scatter(
    earthquakes_pd,
    x='magnitude',
    y='depth_km',
    color='magnitude_category',
    size='magnitude',
    hover_name='place',
    title='Earthquake Depth vs Magnitude',
    labels={'magnitude': 'Magnitude', 'depth_km': 'Depth (km)'},
    color_discrete_sequence=px.colors.qualitative.Set2
)

fig.update_yaxis(autorange="reversed")  # Deeper earthquakes at bottom
fig.update_layout(height=500)

fig.show()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 7. Folium Interactive Map - All Earthquakes

# COMMAND ----------

# Create base map centered on mean coordinates
mean_lat = earthquakes_pd['latitude'].mean()
mean_lon = earthquakes_pd['longitude'].mean()

# Create folium map
earthquake_map = folium.Map(
    location=[mean_lat, mean_lon],
    zoom_start=2,
    tiles='OpenStreetMap'
)

# Add earthquake markers
for idx, row in earthquakes_pd.iterrows():
    # Color based on magnitude
    if row['magnitude'] < 2:
        color = 'green'
        radius = 3
    elif row['magnitude'] < 4:
        color = 'blue'
        radius = 5
    elif row['magnitude'] < 5:
        color = 'orange'
        radius = 7
    elif row['magnitude'] < 6:
        color = 'red'
        radius = 9
    else:
        color = 'darkred'
        radius = 12
    
    # Create popup with earthquake details
    popup_html = f"""
    <div style="font-family: Arial; font-size: 12px; width: 250px;">
        <h4 style="margin: 0 0 10px 0; color: {color};">
            M {row['magnitude']:.2f} Earthquake
        </h4>
        <p style="margin: 5px 0;"><b>Location:</b> {row['place']}</p>
        <p style="margin: 5px 0;"><b>Time:</b> {row['event_time']}</p>
        <p style="margin: 5px 0;"><b>Depth:</b> {row['depth_km']:.2f} km</p>
        <p style="margin: 5px 0;"><b>Coordinates:</b> {row['latitude']:.4f}, {row['longitude']:.4f}</p>
        <p style="margin: 5px 0;"><b>Significance:</b> {row['significance']}</p>
        {f"<p style='margin: 5px 0;'><b>Felt Reports:</b> {int(row['felt_reports'])}</p>" if pd.notna(row['felt_reports']) else ""}
        <p style="margin: 10px 0 0 0;">
            <a href="{row['event_url']}" target="_blank">View Details</a>
        </p>
    </div>
    """
    
    folium.CircleMarker(
        location=[row['latitude'], row['longitude']],
        radius=radius,
        popup=folium.Popup(popup_html, max_width=300),
        color=color,
        fill=True,
        fillColor=color,
        fillOpacity=0.6,
        weight=2
    ).add_to(earthquake_map)

# Add layer control
folium.LayerControl().add_to(earthquake_map)

# Add legend
legend_html = '''
<div style="position: fixed; 
            bottom: 50px; right: 50px; width: 180px; height: 180px; 
            background-color: white; border:2px solid grey; z-index:9999; 
            font-size:14px; padding: 10px">
<p style="margin: 0 0 10px 0; font-weight: bold;">Magnitude Scale</p>
<p style="margin: 5px 0;"><span style="color: green;">●</span> < 2.0 (Micro)</p>
<p style="margin: 5px 0;"><span style="color: blue;">●</span> 2.0 - 4.0 (Minor)</p>
<p style="margin: 5px 0;"><span style="color: orange;">●</span> 4.0 - 5.0 (Light)</p>
<p style="margin: 5px 0;"><span style="color: red;">●</span> 5.0 - 6.0 (Moderate)</p>
<p style="margin: 5px 0;"><span style="color: darkred;">●</span> > 6.0 (Strong+)</p>
</div>
'''
earthquake_map.get_root().html.add_child(folium.Element(legend_html))

# Display map
earthquake_map

# COMMAND ----------

# MAGIC %md
# MAGIC ## 8. Folium Heatmap

# COMMAND ----------

# Create heatmap of earthquake locations
heat_map = folium.Map(
    location=[mean_lat, mean_lon],
    zoom_start=2,
    tiles='CartoDB dark_matter'
)

# Prepare heat data with magnitude as weight
heat_data = [
    [row['latitude'], row['longitude'], row['magnitude']]
    for idx, row in earthquakes_pd.iterrows()
]

# Add heatmap layer
plugins.HeatMap(
    heat_data,
    min_opacity=0.3,
    max_val=earthquakes_pd['magnitude'].max(),
    radius=15,
    blur=20,
    gradient={
        0.0: 'blue',
        0.4: 'lime',
        0.6: 'yellow',
        0.8: 'orange',
        1.0: 'red'
    }
).add_to(heat_map)

heat_map

# COMMAND ----------

# MAGIC %md
# MAGIC ## 9. Regional Focus Maps

# COMMAND ----------

# Focus on California region
california_quakes = earthquakes_pd[earthquakes_pd['geographic_region'] == 'California']

if len(california_quakes) > 0:
    ca_map = folium.Map(
        location=[37.0, -119.5],
        zoom_start=6,
        tiles='OpenStreetMap'
    )
    
    for idx, row in california_quakes.iterrows():
        color = 'red' if row['magnitude'] >= 4 else 'orange' if row['magnitude'] >= 3 else 'blue'
        
        folium.CircleMarker(
            location=[row['latitude'], row['longitude']],
            radius=row['magnitude'] * 2,
            popup=f"M{row['magnitude']:.1f} - {row['place']}",
            color=color,
            fill=True,
            fillColor=color,
            fillOpacity=0.7
        ).add_to(ca_map)
    
    print(f"California Earthquakes: {len(california_quakes)}")
    ca_map
else:
    print("No earthquakes in California region in this dataset")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 10. Timeline Visualization

# COMMAND ----------

# Convert event_time to datetime if not already
earthquakes_pd['event_time'] = pd.to_datetime(earthquakes_pd['event_time'])

# Sort by time
earthquakes_pd_sorted = earthquakes_pd.sort_values('event_time')

# Create timeline plot
fig = px.scatter(
    earthquakes_pd_sorted,
    x='event_time',
    y='magnitude',
    color='magnitude_category',
    size='magnitude',
    hover_name='place',
    title='Earthquake Timeline (Last 24 Hours)',
    labels={'event_time': 'Time', 'magnitude': 'Magnitude'},
    color_discrete_sequence=px.colors.qualitative.Set1
)

fig.update_layout(
    height=500,
    xaxis_title='Time',
    yaxis_title='Magnitude'
)

fig.show()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 11. Geographic Region Comparison

# COMMAND ----------

# Regional statistics
regional_stats = earthquakes_df.groupBy("geographic_region").agg(
    count("*").alias("count"),
    avg("magnitude").alias("avg_magnitude"),
    max("magnitude").alias("max_magnitude"),
    avg("depth_km").alias("avg_depth_km")
).orderBy(desc("count")).toPandas()

# Bar chart of earthquake counts by region
fig = px.bar(
    regional_stats,
    x='geographic_region',
    y='count',
    color='avg_magnitude',
    title='Earthquake Count by Geographic Region',
    labels={'geographic_region': 'Region', 'count': 'Number of Earthquakes', 'avg_magnitude': 'Avg Magnitude'},
    color_continuous_scale='Reds'
)

fig.update_layout(height=400)
fig.show()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 12. Distance Analysis Visualization

# COMMAND ----------

# Distance to nearest city analysis
fig = px.box(
    earthquakes_pd,
    x='nearest_major_city',
    y='distance_to_nearest_city_km',
    color='magnitude_category',
    title='Distance to Nearest Major City by Magnitude Category',
    labels={
        'nearest_major_city': 'Nearest City',
        'distance_to_nearest_city_km': 'Distance (km)',
        'magnitude_category': 'Magnitude Category'
    }
)

fig.update_layout(height=500)
fig.show()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 13. 3D Visualization - Latitude, Longitude, Depth

# COMMAND ----------

# Create 3D scatter plot
fig = go.Figure(data=[go.Scatter3d(
    x=earthquakes_pd['longitude'],
    y=earthquakes_pd['latitude'],
    z=earthquakes_pd['depth_km'],
    mode='markers',
    marker=dict(
        size=earthquakes_pd['magnitude'] * 2,
        color=earthquakes_pd['magnitude'],
        colorscale='Reds',
        showscale=True,
        colorbar=dict(title="Magnitude"),
        line=dict(width=0.5, color='white')
    ),
    text=earthquakes_pd['place'],
    hovertemplate='<b>%{text}</b><br>' +
                  'Longitude: %{x:.2f}<br>' +
                  'Latitude: %{y:.2f}<br>' +
                  'Depth: %{z:.2f} km<br>' +
                  '<extra></extra>'
)])

fig.update_layout(
    title='3D Earthquake Visualization (Lon, Lat, Depth)',
    scene=dict(
        xaxis_title='Longitude',
        yaxis_title='Latitude',
        zaxis_title='Depth (km)',
        zaxis=dict(autorange='reversed')  # Deeper is more negative
    ),
    height=700
)

fig.show()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary Statistics

# COMMAND ----------

print("=== Earthquake Visualization Summary ===\n")
print(f"Total Earthquakes Visualized: {len(earthquakes_pd)}")
print(f"\nMagnitude Range: {earthquakes_pd['magnitude'].min():.2f} - {earthquakes_pd['magnitude'].max():.2f}")
print(f"Average Magnitude: {earthquakes_pd['magnitude'].mean():.2f}")
print(f"\nDepth Range: {earthquakes_pd['depth_km'].min():.2f} - {earthquakes_pd['depth_km'].max():.2f} km")
print(f"Average Depth: {earthquakes_pd['depth_km'].mean():.2f} km")

print("\nTop 5 Largest Earthquakes:")
top_5 = earthquakes_pd.nlargest(5, 'magnitude')[['magnitude', 'place', 'event_time', 'depth_km']]
print(top_5.to_string(index=False))

print("\nGeographic Distribution:")
print(earthquakes_pd['geographic_region'].value_counts())

# COMMAND ----------

# MAGIC %md
# MAGIC ## Export Map to HTML (Optional)

# COMMAND ----------

# Save the main earthquake map to HTML file
# Uncomment to save
# earthquake_map.save('/dbfs/tmp/earthquake_map.html')
# print("Map saved to /dbfs/tmp/earthquake_map.html")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Demo Complete! 🎉
# MAGIC 
# MAGIC You've successfully created an end-to-end earthquake data pipeline with:
# MAGIC 
# MAGIC 1. ✅ Data ingestion from USGS API to Volume
# MAGIC 2. ✅ Bronze layer with raw data
# MAGIC 3. ✅ Silver layer with GEOGRAPHY type
# MAGIC 4. ✅ Spatial analysis with ST_ functions
# MAGIC 5. ✅ Interactive visualizations and maps
# MAGIC 
# MAGIC ### Key Features Demonstrated:
# MAGIC - **GEOGRAPHY type** for spatial data
# MAGIC - **ST_Distance, ST_Buffer, ST_Within** spatial functions
# MAGIC - **Interactive maps** with Folium and Plotly
# MAGIC - **Spatial clustering** and proximity analysis
# MAGIC - **3D visualizations** of earthquake data

