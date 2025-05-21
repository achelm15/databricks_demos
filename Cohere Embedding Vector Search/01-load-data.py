# Databricks notebook source
# MAGIC %md
# MAGIC # Load Scouting Reports from FanGraphs
# MAGIC
# MAGIC This notebook loads raw scouting reports from FanGraphs and prepares them for vector indexing.
# MAGIC We'll save this data as a Delta table, which will later be chunked and embedded using Cohere in the next step.
# MAGIC

# COMMAND ----------

# Environment Variables
CATALOG = "alexander_booth"
SCHEMA = "cohere_demo"
TABLE = "fangraphs_mlb_scouting_reports"
TABLE_CHUNKS = "fangraphs_mlb_scouting_reports_chunked"

# COMMAND ----------

# Imports
import requests
import pandas as pd

# COMMAND ----------

# Set parameters for the scouting board type and season
pos = "all"  
season = 2025  # The season/year of interest
board_type = "prospect"  # Options: "prospect" (preseason), "updated" (midseason), "mlb" (draft), "int" (international)

# Format the draft parameter based on the season and board type
draft = f"{season}{board_type}"

# Construct the FanGraphs API URL for the selected board
url = f"https://www.fangraphs.com/api/prospects/board/data?draft={draft}&season={season}"
print(url)


# COMMAND ----------

# Fetch raw data from the FanGraphs prospect board API
response = requests.get(url)
data = response.json()

# Convert to Pandas DataFrame
df = pd.DataFrame(data)
print(df.shape)
df.head()

# COMMAND ----------

# Combine TLDR, Summary, and Ovr_Summary into a unified text block for embedding
def combine_text(row):
    parts = []

    # Include the TLDR section if it exists
    if pd.notnull(row["TLDR"]):
        parts.append("TLDR:\n" + row["TLDR"])

    summary = row["Summary"]
    ovr_summary = row["Ovr_Summary"]

    # Handle cases where Summary is present
    if pd.notnull(summary):
        parts.append("Full Report:\n" + summary)

        # Only add Ovr_Summary if it's present and not identical to Summary
        if pd.notnull(ovr_summary) and summary != ovr_summary:
            parts.append(ovr_summary)

    # If only Ovr_Summary exists (no Summary), include it as the full report
    elif pd.notnull(ovr_summary):
        parts.append("Full Report:\n" + ovr_summary)

    # Join all sections with spacing
    return "\n\n".join(parts)


# COMMAND ----------

# Execute the function on each row
df["Combined_Scouting_Report"] = df.apply(combine_text, axis=1)
print(df.Combined_Scouting_Report[0])

# COMMAND ----------

# Convert Pandas DataFrame to Spark DataFrame
sdf = spark.createDataFrame(df)

# Write to Table
sdf.write.mode("overwrite").saveAsTable(f"{CATALOG}.{SCHEMA}.{TABLE}")

# COMMAND ----------

# Enable Change Data Feed (CDF) on the scouting reports table using env vars
spark.sql(f"""
  ALTER TABLE `{CATALOG}`.`{SCHEMA}`.`{TABLE}`
  SET TBLPROPERTIES (delta.enableChangeDataFeed = true)
""")


# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC
# MAGIC ✅ **Next Step:** Proceed to the next notebook to chunk these reports and prepare them for embedding with Cohere.
# MAGIC