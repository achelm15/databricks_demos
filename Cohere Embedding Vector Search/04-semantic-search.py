# Databricks notebook source
# MAGIC %md
# MAGIC # 🧠 Semantic Search Over Scouting Reports with Cohere + Databricks Vector Search
# MAGIC
# MAGIC This notebook demonstrates how to run **semantic similarity queries** over scouting reports using **Cohere embeddings** and **Databricks Vector Search**.
# MAGIC
# MAGIC We explore two core use cases:
# MAGIC
# MAGIC ### 🔍 1. Natural Language Search
# MAGIC Use a descriptive phrase (e.g. _"elite bat speed but struggles with offspeed pitches"_) to find relevant players based on the content of their reports.
# MAGIC
# MAGIC ### 🧠 2. Report-to-Report Similarity
# MAGIC Embed a full scouting report for a given player and return the most semantically similar players in the index — useful for comp search and player discovery.
# MAGIC
# MAGIC This notebook uses:
# MAGIC - A Delta Sync–powered vector index of chunked scouting reports
# MAGIC - External model serving with **Cohere’s `embed-english-v3`**
# MAGIC - Native search via `similarity_search()` from the Python SDK
# MAGIC - Joins back to the full report for readable output
# MAGIC

# COMMAND ----------

# MAGIC %pip install databricks-vectorsearch
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

from databricks.vector_search.client import VectorSearchClient
from pyspark.sql.types import StructType, StructField, StringType, FloatType, IntegerType
from pyspark.sql import Row
import pyspark.sql.functions as F

# Initialize the Vector Search client
vsc = VectorSearchClient(disable_notice=True)

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

# MAGIC %md
# MAGIC # 🔍 Semantic Search from Natural Language Query
# MAGIC
# MAGIC In this section, we use a **natural language phrase** to find players with similar scouting reports. The phrase is embedded using Cohere’s `search_query` mode, and then searched against our vector index of report chunks.
# MAGIC
# MAGIC This enables use cases like:
# MAGIC - "Show me players with elite bat speed but struggle with offspeed pitches"
# MAGIC - "Find hitters with power but poor plate discipline"
# MAGIC - "Find pitchers with a good fastball but poor command"
# MAGIC

# COMMAND ----------

def search_similar_players_by_text(index, query_text: str, top_k: int = 5):
    """
    Run a semantic search on a vector index using a query string, and return the top similar players.

    Parameters:
    - index: VectorSearchIndex object
    - query_text: Natural language query string
    - top_k: Number of top players to return (default 5)

    Returns:
    - final_df: Spark DataFrame with top_k similar players and their scouting reports
    """
    
    # Step 1: Run semantic search
    results = index.similarity_search(
        query_text=query_text,
        columns=["primary_key", "playerName", "ID", "Season", "chunk_index", "content_chunk"],
        num_results=100
    )

    # Step 2: Parse results
    rows = results["result"]["data_array"]
    parsed_rows = [
        Row(
            primary_key=row[0],
            playerName=row[1],
            ID=int(row[2]),
            Season=int(row[3]),
            chunk_index=int(row[4]),
            content_chunk=row[5],
            score=float(row[6])
        )
        for row in rows
    ]

    schema = StructType([
        StructField("primary_key", StringType()),
        StructField("playerName", StringType()),
        StructField("ID", IntegerType()),
        StructField("Season", IntegerType()),
        StructField("chunk_index", IntegerType()),
        StructField("content_chunk", StringType()),
        StructField("score", FloatType())
    ])

    # Step 3: Create DataFrame and temp view
    results_df = spark.createDataFrame(parsed_rows, schema=schema)
    results_df.createOrReplaceTempView("semantic_chunks")

    # Step 4: Aggregate top players
    spark.sql(f"""
        CREATE OR REPLACE TEMP VIEW top_players AS
        SELECT
            ID,
            playerName,
            Season,
            MAX(score) AS top_chunk_score
        FROM semantic_chunks
        GROUP BY ID, playerName, Season
        ORDER BY top_chunk_score DESC
        LIMIT {top_k}
    """)

    # Step 5: Join back to full report
    final_df = spark.sql(f"""
        SELECT
            orig.ID,
            orig.playerName,
            orig.Season,
            orig.Combined_Scouting_Report,
            top.top_chunk_score
        FROM top_players AS top
        JOIN {CATALOG}.{SCHEMA}.{TABLE} AS orig
          ON top.ID = orig.ID AND top.Season = orig.Season
        ORDER BY top.top_chunk_score DESC
    """)

    return final_df


# COMMAND ----------

# Build the full index name
FULL_INDEX_NAME = f"{CATALOG}.{SCHEMA}.{INDEX_NAME}"

# Retrieve the index object
index = vsc.get_index(
    endpoint_name=VECTOR_SEARCH_ENDPOINT,
    index_name=FULL_INDEX_NAME
)

QUERY = "Elite bat speed but has trouble with offspeed pitches"

final_df = search_similar_players_by_text(
    index=index,
    query_text=QUERY
)

display(final_df)

# COMMAND ----------

# MAGIC %md
# MAGIC # 🧠 Semantic Search from a Scouting Report
# MAGIC
# MAGIC Here, we select a real player's full scouting report, embed it using Cohere, and then search for **semantically similar player profiles**.
# MAGIC
# MAGIC This enables:
# MAGIC - Player comparison / comp search
# MAGIC - Scouting assistant workflows ("who does this guy remind you of?")
# MAGIC - Building similarity-driven dashboards and ranking tools
# MAGIC

# COMMAND ----------

def find_similar_to_player_report(index, player_name: str, season: int = None, top_k: int = 5):

    # Step 1: Lookup and truncate the report
    scouting_df = spark.table(f"{CATALOG}.{SCHEMA}.{TABLE}")
    filter_df = scouting_df.filter(F.col("playerName") == player_name)
    if season:
        filter_df = filter_df.filter(F.col("Season") == season)

    result = filter_df.select("Combined_Scouting_Report").limit(1).collect()
    if not result:
        raise ValueError(f"No scouting report found for {player_name} (season={season})")

    report_text = result[0]["Combined_Scouting_Report"][:2048]  # truncate

    # Step 2: Run semantic similarity search directly using the report text
    results = index.similarity_search(
        query_text=report_text,
        columns=["primary_key", "playerName", "ID", "Season", "chunk_index", "content_chunk"],
        num_results=100
    )

    # Step 3: Parse response into Spark DataFrame
    rows = results["result"]["data_array"]
    parsed_rows = [
        Row(
            primary_key=row[0],
            playerName=row[1],
            ID=int(row[2]),
            Season=int(row[3]),
            chunk_index=int(row[4]),
            content_chunk=row[5],
            score=float(row[6])
        )
        for row in rows
    ]

    schema = StructType([
        StructField("primary_key", StringType()),
        StructField("playerName", StringType()),
        StructField("ID", IntegerType()),
        StructField("Season", IntegerType()),
        StructField("chunk_index", IntegerType()),
        StructField("content_chunk", StringType()),
        StructField("score", FloatType())
    ])

    semantic_df = spark.createDataFrame(parsed_rows, schema=schema)
    semantic_df.createOrReplaceTempView("semantic_chunks")

    # Step 4: Aggregate scores to player level
    spark.sql(f"""
        CREATE OR REPLACE TEMP VIEW top_players AS
        SELECT
            ID,
            playerName,
            Season,
            MAX(score) AS similarity
        FROM semantic_chunks
        GROUP BY ID, playerName, Season
        ORDER BY similarity DESC
        LIMIT {top_k}
    """)

    # Step 5: Join with full reports
    final_df = spark.sql(f"""
        SELECT
            p.playerName,
            p.Season,
            r.Combined_Scouting_Report,
            p.similarity
        FROM top_players p
        JOIN {CATALOG}.{SCHEMA}.{TABLE} r
          ON p.ID = r.ID AND p.Season = r.Season
        ORDER BY p.similarity DESC
    """)

    return final_df

# COMMAND ----------

final_df = find_similar_to_player_report(
    index=index,
    player_name='Roki Sasaki',
    season=2025
)

display(final_df)

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC
# MAGIC ✅ That wraps up this technical walkthrough on powering semantic search with **Cohere embeddings** and **Databricks Vector Search**.
# MAGIC
# MAGIC We covered how to:
# MAGIC - Load and chunk real scouting reports
# MAGIC - Embed them using a Cohere model served through AWS Bedrock
# MAGIC - Create a live, queryable vector index with Delta Sync
# MAGIC - Perform similarity search using both natural language and existing reports
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC
# MAGIC In a follow-up demo, we’ll show how to combine this vector store with a large language model in a **Retrieval-Augmented Generation (RAG)** setup.
# MAGIC
# MAGIC Stay tuned — semantic search is just the first step.
# MAGIC