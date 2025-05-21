# Databricks notebook source
# MAGIC %md
# MAGIC # Cohere Embeddings + Databricks Vector Search
# MAGIC ## ⚾ Scouting Report Demo
# MAGIC
# MAGIC This project demonstrates how to build a semantic search pipeline using **Cohere embeddings** and **Databricks Vector Search**, applied to real-world scouting reports from **FanGraphs**.
# MAGIC
# MAGIC We’ll walk through the entire lifecycle:
# MAGIC
# MAGIC ### 📥 1. Load Scouting Report Data
# MAGIC We start by pulling raw prospect data from FanGraphs, including tool grades, future value, and written scouting summaries.
# MAGIC
# MAGIC ### ✂️ 2. Chunk and Prepare Text
# MAGIC Long-form reports are normalized and chunked to fit within the 2048-character input limit of Cohere's `embed-english-v3` model.
# MAGIC
# MAGIC ### 🧠 3. Embed with Cohere + Delta Sync
# MAGIC Using Databricks Model Serving (backed by AWS Bedrock), we embed each chunk and maintain a live vector index via **Delta Sync** — no manual pipelines or orchestration required.
# MAGIC
# MAGIC ### 🔍 4. Search with Natural Language or Example Reports
# MAGIC With the vector index created, we showcase two core use cases:
# MAGIC - **Semantic search from a phrase** (e.g. "elite bat speed, struggles with offspeed")
# MAGIC - **Find similar players based on an existing report** (e.g. "show me comps for Sebastian Walcott")
# MAGIC
# MAGIC This notebook sets up the environment for the rest of the workflow.