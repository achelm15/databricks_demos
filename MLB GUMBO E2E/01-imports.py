# Databricks notebook source
# Imports
import pyspark.sql.functions as F

# COMMAND ----------

# Global variables
CATALOG = 'mlb_gumbo'
DATABASE_L = 'landing'
DATABASE_B = 'bronze'
DATABASE_S = 'silver'
DATABASE_G = 'gold'

# Data Location
CHECKPOINT_BASE = f"/Volumes/{CATALOG}/{DATABASE_L}/mlb_gumbo_checkpoints"