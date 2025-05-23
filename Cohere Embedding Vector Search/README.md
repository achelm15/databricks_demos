# 🧠 Cohere Embedding Vector Search with Databricks

This project demonstrates how to build a semantic search system over unstructured text using **Cohere embeddings**, **AWS Bedrock**, and **Databricks Vector Search**.

We use real scouting reports from FanGraphs to showcase how you can:
- Embed raw text using a Cohere model served via AWS Bedrock
- Store and sync embeddings in a Delta table using Delta Sync
- Perform similarity searches using either phrases or existing reports

---

## 📌 Overview

### ✅ Problem
Traditional keyword search fails when dealing with long, descriptive scouting reports. We want to search based on **meaning**, not exact phrasing.

### ✅ Solution
We use Cohere's `embed-english-v3` model to generate dense vector representations of scouting report text and store them in a live, searchable vector index in Databricks.

---

## 🔄 Pipeline Summary

1. **Load Scouting Data**  
   Pulls prospect reports from the FanGraphs public API and stores them in a Delta table.

2. **Chunk Long Text**  
   Scouting reports are split into 2048-character chunks to meet Cohere's input length limits.

3. **Embed with Cohere**  
   Chunks are embedded using `search_document` mode via an external model endpoint powered by AWS Bedrock.

4. **Vector Index with Delta Sync**  
   A Delta Sync–backed index is created to keep embeddings fresh and queryable.

5. **Semantic Search Examples**  
   Search by phrase (e.g. “elite bat speed, poor plate discipline”) or full report to find similar players.

---

## 📁 Notebooks

- `00-config`: Define catalog/schema/table names and set up the workspace
- `01-load-data`: Load and normalize FanGraphs scouting reports
- `02-chunk-reports`: Chunk long reports into 2048-character segments
- `03-create-index-sdk`: Create a Delta Sync vector index via the Databricks Python SDK
- `04-semantic-search`: Run example queries and join results with full scouting reports

---

## 🔍 Search Use Cases

- **Search by Phrase**  
  Run semantic queries like "high exit velocity, poor contact skills" and retrieve relevant players.

- **Search by Report**  
  Use an existing player's scouting report to find similar players — a comp finder powered by embeddings.

---

## 🚀 Future Work: RAG Demo

In a follow-up demo, we’ll build a Retrieval-Augmented Generation (RAG) prototype to:
- Answer open-ended scouting questions
- Summarize groups of similar players
- Enable a natural language interface over player data

---

## 📚 References

- [Cohere Embeddings](https://docs.cohere.com/docs/embed)
- [AWS Bedrock Model Access](https://docs.aws.amazon.com/bedrock/latest/userguide/model-access.html)
- [Databricks Vector Search](https://docs.databricks.com/en/generative-ai/vector-search.html)
- [FanGraphs API (unofficial)](https://www.fangraphs.com/api/prospects/board/data)

---

## Author

**Alexander Booth**  
[ABoothInTheWild on GitHub](https://github.com/ABoothInTheWild)  
