# Databricks notebook source
# MAGIC %run ./00-ddl

# COMMAND ----------

# MAGIC %run ./01-imports

# COMMAND ----------

import os
import requests
import json
import time
import pyspark.sql.functions as F
from datetime import datetime

# COMMAND ----------

# Variables
checkpoint_location_silver = f'{CHECKPOINT_BASE}/pitch_data_checkpoints'
table_bronze_raw = f'{CATALOG}.{DATABASE_B}.raw_data'
temp_table_name = "temp_mlb_gumbo_raw_data_stream"

# COMMAND ----------

# Stream in the raw_data table
df_raw = (
  spark.readStream
  .format('delta')
  .table(table_bronze_raw)
)

# COMMAND ----------

# Save the streaming table off as a temp view
df_raw.createOrReplaceTempView(temp_table_name)

# COMMAND ----------

# Pitch Data using Spark SQL
df = spark.sql(f"""
    SELECT
    -- Game Metadata
    data:gameData.game.season::int as season,
    data:gameData.datetime.officialDate::date as official_date,
    data:gameData.datetime.dateTime::timestamp_ntz as game_datetime,
    data:gamePk::int as game_pk,
    data:gameData.game.gamedayType::string as gameday_type,
    data:gameData.game.gameNumber::int as game_number,
    data:gameData.teams.away.id::integer as away_team_id,
    data:gameData.teams.away.name::string as away_team_name,
    data:gameData.teams.home.id::integer as home_team_id,
    data:gameData.teams.home.name::string as home_team_name,

    -- Play Metadata
    allPlays.value:result.event::string AS play_event,
    allPlays.value:result.eventType::string AS play_event_type,
    allPlays.value:result.description::string AS play_description,
    allPlays.value:result.rbi::int AS play_rbi,
    allPlays.value:result.awayScore::int AS post_play_away_score,
    allPlays.value:result.homeScore::int AS post_play_home_score,
    allPlays.value:about.atBatIndex::int AS at_bat_index,
    allPlays.value:about.halfInning::string AS half_inning,
    allPlays.value:about.isTopInning::boolean AS is_top_inning,
    allPlays.value:about.inning::int AS inning,
    allPlays.value:about.captivatingIndex::int AS captivating_index,

    -- Pitch Metadata
    playEvents.value:index::int AS pitch_index,
    playEvents.value:playId::string AS pitch_guid,
    playEvents.value:pitchNumber::int AS pitch_number,
    playEvents.value:startTime::string AS start_time,
    playEvents.value:endTime::string AS end_time,
    playEvents.value:isPitch::boolean AS is_pitch,
    playEvents.value:type::string AS event_type,

    -- Pitch Results
    playEvents.value:details:call:code::string AS call_code,
    playEvents.value:details:call:description::string AS call_description,
    playEvents.value:details:description::string AS pitch_description,
    playEvents.value:details:code::string AS pitch_code,
    playEvents.value:details:ballColor::string AS ball_color,
    playEvents.value:details:trailColor::string AS trail_color,
    playEvents.value:details:isInPlay::boolean AS is_in_play,
    playEvents.value:details:isStrike::boolean AS is_strike,
    playEvents.value:details:isBall::boolean AS is_ball,
    playEvents.value:details:type:code::string AS pitch_type_code,
    playEvents.value:details:type:description::string AS pitch_type_description,
    playEvents.value:details:isOut::boolean AS is_out,
    playEvents.value:details:hasReview::boolean AS has_review,

    -- Pitch Count
    playEvents.value:count:balls::int AS balls_count,
    playEvents.value:count:strikes::int AS strikes_count,
    playEvents.value:count:outs::int AS outs_count,

    playEvents.value:preCount:balls::int AS pre_balls_count,
    playEvents.value:preCount:strikes::int AS pre_strikes_count,
    playEvents.value:preCount:outs::int AS pre_outs_count,

    -- Pitch Data
    playEvents.value:pitchData:startSpeed::double AS pitch_start_speed,
    playEvents.value:pitchData:endSpeed::double AS pitch_end_speed,
    playEvents.value:pitchData:strikeZoneTop::double AS strike_zone_top,
    playEvents.value:pitchData:strikeZoneBottom::double AS strike_zone_bottom,

    playEvents.value:pitchData:coordinates:aY::double AS acceleration_y,
    playEvents.value:pitchData:coordinates:aZ::double AS acceleration_z,
    playEvents.value:pitchData:coordinates:pfxX::double AS pfx_x,
    playEvents.value:pitchData:coordinates:pfxZ::double AS pfx_z,
    playEvents.value:pitchData:coordinates:pX::double AS position_x,
    playEvents.value:pitchData:coordinates:pZ::double AS position_z,
    playEvents.value:pitchData:coordinates:vX0::double AS initial_velocity_x,
    playEvents.value:pitchData:coordinates:vY0::double AS initial_velocity_y,
    playEvents.value:pitchData:coordinates:vZ0::double AS initial_velocity_z,
    playEvents.value:pitchData:coordinates:x::double AS x,
    playEvents.value:pitchData:coordinates:y::double AS y,
    playEvents.value:pitchData:coordinates:x0::double AS initial_x,
    playEvents.value:pitchData:coordinates:y0::double AS initial_y,
    playEvents.value:pitchData:coordinates:z0::double AS initial_z,
    playEvents.value:pitchData:coordinates:aX::double AS acceleration_x,

    playEvents.value:pitchData:breaks:breakAngle::double AS pitch_break_angle,
    playEvents.value:pitchData:breaks:breakLength::double AS pitch_break_length,
    playEvents.value:pitchData:breaks:breakY::double AS pitch_break_y,
    playEvents.value:pitchData:breaks:breakVertical::double AS pitch_break_vertical,
    playEvents.value:pitchData:breaks:breakVerticalInduced::double AS pitch_break_vertical_induced,
    playEvents.value:pitchData:breaks:breakHorizontal::double AS pitch_break_horizontal,
    playEvents.value:pitchData:breaks:spinRate::int AS pitch_spin_rate,
    playEvents.value:pitchData:breaks:spinDirection::int AS pitch_spin_direction,

    playEvents.value:pitchData:zone::int AS pitch_zone,
    playEvents.value:pitchData:typeConfidence::double AS pitch_type_confidence,
    playEvents.value:pitchData:plateTime::double AS plate_time,
    playEvents.value:pitchData:extension::double AS extension,

    -- Hit Data
    playEvents.value:hitData:launchSpeed::double AS hit_launch_speed,
    playEvents.value:hitData:launchAngle::double AS hit_launch_angle,
    playEvents.value:hitData:totalDistance::double AS hit_total_distance,
    playEvents.value:hitData:trajectory::string AS hit_trajectory,
    playEvents.value:hitData:hardness::string AS hit_hardness,
    playEvents.value:hitData:location::string AS hit_location,
    playEvents.value:hitData:coordinates:coordX::double AS hit_coord_x,
    playEvents.value:hitData:coordinates:coordY::double AS hit_coord_y,

    -- Player Data
    -- Offense
    playEvents.value:offense:batter:id::int AS batter_id,
    allPlays.value:matchup.batter.fullName::string AS batter_full_name,
    playEvents.value:offense:batter:link::string AS batter_link,
    playEvents.value:offense:batter:batSide:code::string AS batter_side_code,
    playEvents.value:offense:batter:batSide:description::string AS batter_side_description,
    playEvents.value:offense:batterPosition:code::string AS batter_position_code,
    playEvents.value:offense:batterPosition:name::string AS batter_position_name,
    playEvents.value:offense:batterPosition:type::string AS batter_position_type,
    playEvents.value:offense:batterPosition:abbreviation::string AS batter_position_abbreviation,

    -- Defense
    playEvents.value:defense:pitcher:id::int AS pitcher_id,
    allPlays.value:matchup.pitcher.fullName::string AS pitcher_full_name,
    playEvents.value:defense:pitcher:link::string AS pitcher_link,
    playEvents.value:defense:pitcher:pitchHand:code::string AS pitcher_hand_code,
    playEvents.value:defense:pitcher:pitchHand:description::string AS pitcher_hand_description,
    playEvents.value:defense:catcher:id::int AS catcher_id,
    playEvents.value:defense:catcher:link::string AS catcher_link,
    playEvents.value:defense:first:id::int AS first_base_id,
    playEvents.value:defense:second:id::int AS second_base_id,
    playEvents.value:defense:third:id::int AS third_base_id,
    playEvents.value:defense:shortstop:id::int AS shortstop_id,
    playEvents.value:defense:left:id::int AS left_fielder_id,
    playEvents.value:defense:center:id::int AS center_fielder_id,
    playEvents.value:defense:right:id::int AS right_fielder_id,

    -- File Metadata
    file_path,
    file_name,
    file_size,
    file_modification_time,
    file_batch_time,
    last_update_time
    FROM
    {temp_table_name},
    LATERAL variant_explode(data:liveData.plays.allPlays) AS allPlays,
    LATERAL variant_explode(allPlays.value:playEvents) AS playEvents"""
)

# COMMAND ----------

# Define the upsert function
def upsert_to_silver(batch_df, batch_id):
    silver_table_name = "mlb_tech_summit.mlb_gumbo_silver.pitch_data"  # Unity Catalog table name
    temp_table_name = "temp_silver_mlb_gumbo_pitch_data"

    # Register the incoming batch as a temporary view
    batch_df.createOrReplaceTempView(temp_table_name)
    
    # Perform the MERGE operation with SQL
    spark.sql(f"""
        MERGE INTO {silver_table_name} AS silver
        USING `{temp_table_name}` AS updates
        ON silver.season = updates.season and
          silver.official_date = updates.official_date and
          silver.game_pk = updates.game_pk and 
          silver.at_bat_index = updates.at_bat_index and
          silver.pitch_index = updates.pitch_index
        WHEN MATCHED THEN UPDATE SET *
        WHEN NOT MATCHED THEN INSERT *
    """)

    spark.catalog.dropTempView(temp_table_name)

# COMMAND ----------

# Write Stream with foreachBatch
(
    df.writeStream.foreachBatch(upsert_to_silver)  # Process each batch with the upsert function
    .outputMode("update") 
    .option("checkpointLocation", checkpoint_location_silver)
    .trigger(availableNow=True)  # Process all available data at once
    .start()
    .awaitTermination()  # Wait for streaming to finish
)

# COMMAND ----------


