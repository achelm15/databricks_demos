# Databricks notebook source
# MAGIC %md
# MAGIC # 🧠 Create Vector Search Endpoint + Index (Python SDK)
# MAGIC
# MAGIC This notebook programmatically sets up the infrastructure to support semantic search using **Cohere embeddings** and **Databricks Vector Search**.
# MAGIC
# MAGIC ### What This Does:
# MAGIC - ✅ Creates a **Vector Search endpoint** (if it doesn’t already exist)
# MAGIC - ✅ Registers a **Delta Sync index** using the chunked scouting report table
# MAGIC - ✅ Configures **Cohere `embed-english-v3`** as the embedding model
# MAGIC - ✅ Optionally waits for the index to be fully ready before continuing
# MAGIC
# MAGIC Using the Python SDK ensures this process is reproducible and version-controlled — ideal for real production workflows or CI-driven pipelines.
# MAGIC

# COMMAND ----------

# MAGIC %pip install databricks-vectorsearch
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

# Environment Variables
CATALOG = "alexander_booth"
SCHEMA = "cohere_demo"
TABLE = "fangraphs_mlb_scouting_reports"
TABLE_CHUNKS = "fangraphs_mlb_scouting_reports_chunked"

# Vector Store Environment Variables
INDEX_NAME = "fangraphs_mlb_scouting_reports_index"
EMBEDDING_MODEL = "cohere_embed_english_v3"  # your model serving endpoint
VECTOR_SEARCH_ENDPOINT = "vs_scouting_reports_demo"
PRIMARY_KEY = "primary_key"
SOURCE_COLUMN = "content_chunk"

# COMMAND ----------

from databricks.vector_search.client import VectorSearchClient
vsc = VectorSearchClient(disable_notice=True)

# COMMAND ----------

# Create Vector Search Endpoint

# Check if endpoint exists
existing_endpoints = vsc.list_endpoints()
if VECTOR_SEARCH_ENDPOINT not in [ep["name"] for ep in existing_endpoints.get("endpoints", [])]:
  # Create endpoint
  vsc.create_endpoint(name=VECTOR_SEARCH_ENDPOINT)
  print(f"✅ Endpoint '{VECTOR_SEARCH_ENDPOINT}' created.")
else:
  print(f"✅ Endpoint '{VECTOR_SEARCH_ENDPOINT}' already exists.")

# COMMAND ----------

# Create Vector Search Index

# Build the full index name
FULL_INDEX_NAME = f"{CATALOG}.{SCHEMA}.{INDEX_NAME}"
existing_indexes = vsc.list_indexes(name=VECTOR_SEARCH_ENDPOINT)

if FULL_INDEX_NAME not in [idx["name"] for idx in existing_indexes.get("vector_indexes", [])]:
  # Create Index
  vsc.create_delta_sync_index(
      index_name=FULL_INDEX_NAME,
      source_table_name=f"{CATALOG}.{SCHEMA}.{TABLE_CHUNKS}",
      pipeline_type="TRIGGERED",  # or "CONTINUOUS"
      primary_key=PRIMARY_KEY,
      embedding_source_column=SOURCE_COLUMN,
      embedding_model_endpoint_name=EMBEDDING_MODEL,
      endpoint_name=VECTOR_SEARCH_ENDPOINT
  )
  print(f"✅ Index '{FULL_INDEX_NAME}' created.")
else:
  print(f"✅ Index '{FULL_INDEX_NAME}' already exists.")

# COMMAND ----------

# Retrieve the index object
index = vsc.get_index(endpoint_name=VECTOR_SEARCH_ENDPOINT, index_name=FULL_INDEX_NAME)

# Describe the index to get its status
status_info = index.describe()
print(f"Index status: {status_info['status']}")

# COMMAND ----------

# Wait for the index to be ready
index.wait_until_ready()
print("✅ Index is ready for queries.")

# COMMAND ----------

# Describe the index to get its status
status_info = index.describe()
print(f"Index status: {status_info['status']}")

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC
# MAGIC ✅ **Next Step: Run Semantic Search Queries**
# MAGIC
# MAGIC With the index created and synced, you're ready to perform vector searches using:
# MAGIC
# MAGIC - **Natural language phrases** via `vector_search(..., query_text => ...)`
# MAGIC - **Embeddings from existing reports** via `query_vector => ARRAY(...)`
# MAGIC
# MAGIC You can run these queries directly in **SQL** or using the **Python SDK**.  
# MAGIC For example:
# MAGIC - Find players with similar scouting reports
# MAGIC - Search for traits like "elite bat speed and poor offspeed recognition"
# MAGIC
# MAGIC 👉 Continue to the next notebook to explore both use cases.