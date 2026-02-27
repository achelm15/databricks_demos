# Databricks notebook source
# Imports
import pyspark.sql.functions as F

# COMMAND ----------

# Global variables
CATALOG = 'mlb_demos'
DATABASE_L = 'mlb_gumbo_landing'
DATABASE_B = 'mlb_gumbo_bronze'
DATABASE_S = 'mlb_gumbo_silver'
DATABASE_G = 'mlb_gumbo_gold'

# Data Location
CHECKPOINT_BASE = f"/Volumes/{CATALOG}/{DATABASE_L}/mlb_gumbo_checkpoints"
