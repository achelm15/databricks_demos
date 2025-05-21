# Databricks notebook source
# MAGIC %md
# MAGIC # ✂️ Chunk Scouting Reports for Embedding
# MAGIC
# MAGIC Cohere’s `embed-english-v3` model (served through AWS Bedrock) has a maximum input length of **2048 characters**. To support this, we need to split long scouting reports into smaller, model-friendly chunks.
# MAGIC
# MAGIC This notebook:
# MAGIC - Loads the full scouting report table created in the previous step
# MAGIC - Splits the `Combined_Scouting_Report` column into ~2048-character chunks
# MAGIC - Creates a new Delta table with one row per chunk, including:
# MAGIC   - Player metadata
# MAGIC   - Chunk index
# MAGIC   - Chunk text
# MAGIC   - Primary key (ID + season + chunk index)
# MAGIC
# MAGIC These chunks will be used as the input to the Cohere embedding model during Delta Sync in the next step.
# MAGIC

# COMMAND ----------

# Environment Variables
CATALOG = "alexander_booth"
SCHEMA = "cohere_demo"
TABLE = "fangraphs_mlb_scouting_reports"
TABLE_CHUNKS = "fangraphs_mlb_scouting_reports_chunked"

# COMMAND ----------

# Imports
from pyspark.sql.functions import udf
from pyspark.sql.types import ArrayType, StringType
from pyspark.sql import functions as F

# COMMAND ----------

# Load the source table containing full scouting reports
df = spark.table(f"{CATALOG}.{SCHEMA}.{TABLE}")

# COMMAND ----------

# Count the number of rows with text longer than 2048 characters
df.filter(F.length(F.col("Combined_Scouting_Report")) > 2048).count()

# COMMAND ----------

# Define a function to split long text into chunks of up to 2048 characters
def chunk_text(text, max_chars=2048):
    if text is None:
        return []  # Return an empty list for null input
    return [text[i:i + max_chars] for i in range(0, len(text), max_chars)]

# Register the function as a PySpark UDF that returns an array of strings
chunk_text_udf = udf(chunk_text, ArrayType(StringType()))

# COMMAND ----------

# Apply chunking and flatten the result so each chunk is its own row
df_chunked = (
    df.withColumn("content_chunks", chunk_text_udf(F.col("Combined_Scouting_Report")))  # Apply chunking to text column
      .select("ID", "playerName", "Season", F.posexplode("content_chunks").alias("chunk_index", "content_chunk")) # one row per index
      .withColumn("primary_key", F.concat_ws("_", F.col("ID"), F.col("Season"), F.col("chunk_index")))
)

# Save the chunked output to a new Delta table for use in embedding/vector search
df_chunked.write.mode("overwrite").saveAsTable(f"{CATALOG}.{SCHEMA}.{TABLE_CHUNKS}")

# COMMAND ----------

# Enable Change Data Feed (CDF) on the scouting reports chunks table using env vars
spark.sql(f"""
  ALTER TABLE `{CATALOG}`.`{SCHEMA}`.`{TABLE_CHUNKS}`
  SET TBLPROPERTIES (delta.enableChangeDataFeed = true)
""")


# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC
# MAGIC ✅ **Next Step: Create the Vector Index with Delta Sync**
# MAGIC
# MAGIC Now that the scouting reports are chunked into 2048-character segments, you can use the Databricks **Vector Search UI** to create a vector index backed by Delta Sync.
# MAGIC
# MAGIC **To do this:**
# MAGIC 1. Navigate to the **Vector Search** tab in the Databricks workspace
# MAGIC 2. Click **"Create Vector Index"**
# MAGIC 3. Select the chunked table (e.g., `fangraphs_mlb_scouting_reports_chunked`)
# MAGIC 4. Choose the `content_chunk` column as the input text
# MAGIC 5. Select your external **Cohere embedding endpoint** (e.g., `cohere_embed_english_v3`)
# MAGIC 6. Set the primary key (e.g., `ID_Season_ChunkIndex`) and any metadata columns (e.g., player name, season)
# MAGIC
# MAGIC Databricks will automatically embed and sync the content to power fast, semantic search.
# MAGIC

# COMMAND ----------

