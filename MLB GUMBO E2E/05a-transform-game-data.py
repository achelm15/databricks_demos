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
checkpoint_location_silver = f'{CHECKPOINT_BASE}/game_data_checkpoints'
table_bronze_raw = f'{CATALOG}.{DATABASE_B}.raw_data'

# COMMAND ----------

# Stream in the raw_data table using PySpark API
df_raw = (
  spark.readStream
  .format('delta')
  .table(table_bronze_raw)
  .selectExpr(
    "data:gamePk::int as game_pk",
    "data:link::string as link",
    "data:gameData.game.type::string as game_type",
    "data:gameData.game.doubleHeader::string as double_header",
    "data:gameData.game.id::string as game_id",
    "data:gameData.game.gamedayType::string as gameday_type",
    "data:gameData.game.tiebreaker::string as tiebreaker",
    "data:gameData.game.gameNumber::int as game_number",
    "data:gameData.game.calendarEventID::string as calendar_event_id",
    "data:gameData.game.season::int as season",
    "data:gameData.game.seasonDisplay::int as season_display",
    "data:gameData.datetime.dateTime::timestamp_ntz as date_time",
    "data:gameData.datetime.originalDate::date as original_date",
    "data:gameData.datetime.officialDate::date as official_date",
    "data:gameData.datetime.dayNight::string as day_night",
    "data:gameData.datetime.time::string as time",
    "data:gameData.datetime.ampm::string as ampm",
    "data:gameData.status.abstractGameState::string as abstract_game_state",
    "data:gameData.status.codedGameState::string as coded_game_state",
    "data:gameData.status.detailedState::string as detailed_state",
    "data:gameData.status.statusCode::string as status_code",
    "data:gameData.status.startTimeTBD::string as start_time_tbd",
    "data:gameData.status.abstractGameCode::string as abstract_game_code",
    "data:gameData.teams.away.abbreviation::string as away_team_abbreviation",
    "data:gameData.teams.away.active::boolean as away_team_active",
    "data:gameData.teams.away.allStarStatus::string as away_team_all_star_status",
    "data:gameData.teams.away.clubName::string as away_team_club_name",
    "data:gameData.teams.away.division.id::integer as away_team_division_id",
    "data:gameData.teams.away.division.link::string as away_team_division_link",
    "data:gameData.teams.away.division.name::string as away_team_division_name",
    "data:gameData.teams.away.fileCode::string as away_team_file_code",
    "data:gameData.teams.away.firstYearOfPlay::integer as away_team_first_year_of_play",
    "data:gameData.teams.away.franchiseName::string as away_team_franchise_name",
    "data:gameData.teams.away.id::integer as away_team_id",
    "data:gameData.teams.away.league.id::integer as away_team_league_id",
    "data:gameData.teams.away.league.link::string as away_team_league_link",
    "data:gameData.teams.away.league.name::string as away_team_league_name",
    "data:gameData.teams.away.link::string as away_team_link",
    "data:gameData.teams.away.locationName::string as away_team_location_name",
    "data:gameData.teams.away.name::string as away_team_name",
    "data:gameData.teams.away.record.conferenceGamesBack::string as away_team_record_conference_games_back",
    "data:gameData.teams.away.record.divisionGamesBack::string as away_team_record_division_games_back",
    "data:gameData.teams.away.record.divisionLeader::boolean as away_team_record_division_leader",
    "data:gameData.teams.away.record.gamesPlayed::int as away_team_record_games_played",
    "data:gameData.teams.away.record.leagueGamesBack::string as away_team_record_league_games_back",
    "data:gameData.teams.away.record.leagueRecord.losses::int as away_team_record_league_losses",
    "data:gameData.teams.away.record.leagueRecord.pct::double as away_team_record_league_pct",
    "data:gameData.teams.away.record.leagueRecord.ties::int as away_team_record_league_ties",
    "data:gameData.teams.away.record.leagueRecord.wins::int as away_team_record_league_wins",
    "data:gameData.teams.away.record.losses::int as away_team_record_losses",
    "data:gameData.teams.away.record.sportGamesBack::string as away_team_record_sport_games_back",
    "data:gameData.teams.away.record.springLeagueGamesBack::string as away_team_record_spring_league_games_back",
    "data:gameData.teams.away.record.wildCardGamesBack::string as away_team_record_wild_card_games_back",
    "data:gameData.teams.away.record.winningPercentage::double as away_team_record_winning_percentage",
    "data:gameData.teams.away.record.wins::int as away_team_record_wins",
    "data:gameData.teams.away.season::string as away_team_season",
    "data:gameData.teams.away.shortName::string as away_team_short_name",
    "data:gameData.teams.away.sport.id::int as away_team_sport_id",
    "data:gameData.teams.away.sport.link::string as away_team_sport_link",
    "data:gameData.teams.away.sport.name::string as away_team_sport_name",
    "data:gameData.teams.away.springLeague.abbreviation::string as away_team_spring_league_abbreviation",
    "data:gameData.teams.away.springLeague.id::int as away_team_spring_league_id",
    "data:gameData.teams.away.springLeague.link::string as away_team_spring_league_link",
    "data:gameData.teams.away.springLeague.name::string as away_team_spring_league_name",
    "data:gameData.teams.away.springVenue.id::string as away_team_spring_venue_id",
    "data:gameData.teams.away.springVenue.link::string as away_team_spring_venue_link",
    "data:gameData.teams.away.teamCode::string as away_team_team_code",
    "data:gameData.teams.away.teamName::string as away_team_team_name",
    "data:gameData.teams.away.venue.id::int as away_team_venue_id",
    "data:gameData.teams.away.venue.link::string as away_team_venue_link",
    "data:gameData.teams.away.venue.name::string as away_team_venue_name",
    "data:gameData.teams.home.abbreviation::string as home_team_abbreviation",
    "data:gameData.teams.home.active::boolean as home_team_active",
    "data:gameData.teams.home.allStarStatus::string as home_team_all_star_status",
    "data:gameData.teams.home.clubName::string as home_team_club_name",
    "data:gameData.teams.home.division.id::int as home_team_division_id",
    "data:gameData.teams.home.division.link::string as home_team_division_link",
    "data:gameData.teams.home.division.name::string as home_team_division_name",
    "data:gameData.teams.home.fileCode::string as home_team_file_code",
    "data:gameData.teams.home.firstYearOfPlay::string as home_team_first_year_of_play",
    "data:gameData.teams.home.franchiseName::string as home_team_franchise_name",
    "data:gameData.teams.home.id::int as home_team_id",
    "data:gameData.teams.home.league.id::int as home_team_league_id",
    "data:gameData.teams.home.league.link::string as home_team_league_link",
    "data:gameData.teams.home.league.name::string as home_team_league_name",
    "data:gameData.teams.home.link::string as home_team_link",
    "data:gameData.teams.home.locationName::string as home_team_location_name",
    "data:gameData.teams.home.name::string as home_team_name",
    "data:gameData.teams.home.record.conferenceGamesBack::string as home_team_record_conference_games_back",
    "data:gameData.teams.home.record.divisionGamesBack::string as home_team_record_division_games_back",
    "data:gameData.teams.home.record.divisionLeader::boolean as home_team_record_division_leader",
    "data:gameData.teams.home.record.gamesPlayed::int as home_team_record_games_played",
    "data:gameData.teams.home.record.leagueGamesBack::string as home_team_record_league_games_back",
    "data:gameData.teams.home.record.leagueRecord.losses::int as home_team_record_league_losses",
    "data:gameData.teams.home.record.leagueRecord.pct::double as home_team_record_league_pct",
    "data:gameData.teams.home.record.leagueRecord.ties::int as home_team_record_league_ties",
    "data:gameData.teams.home.record.leagueRecord.wins::int as home_team_record_league_wins",
    "data:gameData.teams.home.record.losses::int as home_team_record_losses",
    "data:gameData.teams.home.record.sportGamesBack::string as home_team_record_sport_games_back",
    "data:gameData.teams.home.record.springLeagueGamesBack::string as home_team_record_spring_league_games_back",
    "data:gameData.teams.home.record.wildCardGamesBack::string as home_team_record_wild_card_games_back",
    "data:gameData.teams.home.record.winningPercentage::double as home_team_record_winning_percentage",
    "data:gameData.teams.home.record.wins::int as home_team_record_wins",
    "data:gameData.teams.home.season::string as home_team_season",
    "data:gameData.teams.home.shortName::string as home_team_short_name",
    "data:gameData.teams.home.sport.id::int as home_team_sport_id",
    "data:gameData.teams.home.sport.link::string as home_team_sport_link",
    "data:gameData.teams.home.sport.name::string as home_team_sport_name",
    "data:gameData.teams.home.springLeague.abbreviation::string as home_team_spring_league_abbreviation",
    "data:gameData.teams.home.springLeague.id::int as home_team_spring_league_id",
    "data:gameData.teams.home.springLeague.link::string as home_team_spring_league_link",
    "data:gameData.teams.home.springLeague.name::string as home_team_spring_league_name",
    "data:gameData.teams.home.springVenue.id::int as home_team_spring_venue_id",
    "data:gameData.teams.home.springVenue.link::string as home_team_spring_venue_link",
    "data:gameData.teams.home.teamCode::string as home_team_team_code",
    "data:gameData.teams.home.teamName::string as home_team_team_name",
    "data:gameData.teams.home.venue.id::int as home_team_venue_id",
    "data:gameData.teams.home.venue.link::string as home_team_venue_link",
    "data:gameData.teams.home.venue.name::string as home_team_venue_name",
    "data:gameData.venue.id::int as venue_id",
    "data:gameData.venue.name::string as venue_name",
    "data:gameData.venue.link::string as venue_link",
    "data:gameData.venue.location.address1::string as venue_address1",
    "data:gameData.venue.location.azimuthAngle::string as venue_azimuth_angle",
    "data:gameData.venue.location.city::string as venue_city",
    "data:gameData.venue.location.country::string as venue_country",
    "data:gameData.venue.location.defaultCoordinates.latitude::double as venue_latitude",
    "data:gameData.venue.location.defaultCoordinates.longitude::double as venue_longitude",
    "data:gameData.venue.location.elevation::int as venue_elevation",
    "data:gameData.venue.location.phone::string as venue_phone",
    "data:gameData.venue.location.postalCode::string as venue_postal_code",
    "data:gameData.venue.location.state::string as venue_state",
    "data:gameData.venue.location.stateAbbrev::string as venue_state_abbrev",
    "data:gameData.venue.timeZone.id::string as venue_time_zone_id",
    "data:gameData.venue.timeZone.offset::int as venue_time_zone_offset",
    "data:gameData.venue.timeZone.offsetAtGameTime::int as venue_time_zone_offset_at_game_time",
    "data:gameData.venue.timeZone.tz::string as venue_time_zone_tz",
    "data:gameData.venue.fieldInfo.capacity::int as venue_field_capacity",
    "data:gameData.venue.fieldInfo.center::int as venue_field_center",
    "data:gameData.venue.fieldInfo.leftCenter::int as venue_field_left_center",
    "data:gameData.venue.fieldInfo.leftLine::int as venue_field_left_line",
    "data:gameData.venue.fieldInfo.rightCenter::int as venue_field_right_center",
    "data:gameData.venue.fieldInfo.rightLine::int as venue_field_right_line",
    "data:gameData.venue.fieldInfo.roofType::string as venue_field_roof_type",
    "data:gameData.venue.fieldInfo.turfType::string as venue_field_turf_type",
    "data:gameData.venue.active::boolean as venue_active",
    "data:gameData.venue.season::int as venue_season",
    "data:gameData.officialVenue.id::int as official_venue_id",
    "data:gameData.officialVenue.link::string as official_venue_link",
    "data:gameData.weather.condition::string as weather_condition",
    "data:gameData.weather.temp::int as weather_temp",
    "data:gameData.weather.wind::string as weather_wind",
    "data:gameData.gameInfo.attendance::int as game_info_attendance",
    "data:gameData.gameInfo.firstPitch::timestamp_ntz as game_info_first_pitch",
    "data:gameData.gameInfo.gameDurationMinutes::int as game_info_duration",
    "data:gameData.review.hasChallenges::boolean as review_has_challenges",
    "data:gameData.review.away.remaining::int as review_away_remaining",
    "data:gameData.review.away.used::int as review_away_used",
    "data:gameData.review.home.remaining::int as review_home_remaining",
    "data:gameData.review.home.used::int as review_home_used",
    "data:gameData.flags.noHitter::boolean as flags_no_hitter",
    "data:gameData.flags.perfectGame::boolean as flags_perfect_game",
    "data:gameData.flags.awayTeamNoHitter::boolean as flags_away_team_no_hitter",
    "data:gameData.flags.awayTeamPerfectGame::boolean as flags_away_team_perfect_game",
    "data:gameData.flags.homeTeamNoHitter::boolean as flags_home_team_no_hitter",
    "data:gameData.flags.homeTeamPerfectGame::boolean as flags_home_team_perfect_game",
    "data:gameData.probablePitchers.away.fullName::string as probable_pitchers_away_full_name",
    "data:gameData.probablePitchers.away.id::int as probable_pitchers_away_id",
    "data:gameData.probablePitchers.away.link::string as probable_pitchers_away_link",
    "data:gameData.probablePitchers.home.fullName::string as probable_pitchers_home_full_name",
    "data:gameData.probablePitchers.home.id::int as probable_pitchers_home_id",
    "data:gameData.probablePitchers.home.link::string as probable_pitchers_home_link",
    "data:gameData.officialScorer.id::int as official_scorer_id",
    "data:gameData.officialScorer.fullName::string as official_scorer_full_name",
    "data:gameData.officialScorer.link::string as official_scorer_link",
    "data:gameData.primaryDatacaster.id::int as primary_datacaster_id",
    "data:gameData.primaryDatacaster.fullName::string as primary_datacaster_full_name",
    "data:gameData.primaryDatacaster.link::string as primary_datacaster_link",
    "data:gameData.moundVisits.away.remaining::int as mound_visits_away_remaining",
    "data:gameData.moundVisits.away.used::int as mound_visits_away_used",
    "data:gameData.moundVisits.home.remaining::int as mound_visits_home_remaining",
    "data:gameData.moundVisits.home.used::int as mound_visits_home_used",
    "file_path",
    "file_name",
    "file_size",
    "file_modification_time",
    "file_batch_time",
    "last_update_time"
  )
)

# COMMAND ----------

# Define the upsert function
def upsert_to_silver(batch_df, batch_id):
    silver_table_name = "mlb_tech_summit.mlb_gumbo_silver.game_data"  # Unity Catalog table name
    temp_table_name = "temp_silver_mlb_gumbo_game_data"

    # Register the incoming batch as a temporary view
    batch_df.createOrReplaceTempView(temp_table_name)
    
    # Perform the MERGE operation with SQL
    spark.sql(f"""
        MERGE INTO {silver_table_name} AS silver
        USING `{temp_table_name}` AS updates
        ON silver.season = updates.season and
        silver.official_date = updates.official_date and
        silver.game_pk = updates.game_pk  
        WHEN MATCHED THEN UPDATE SET *
        WHEN NOT MATCHED THEN INSERT *
    """)

    spark.catalog.dropTempView(temp_table_name)

# COMMAND ----------

# Write Stream with foreachBatch
(
    df_raw.writeStream.foreachBatch(upsert_to_silver)  # Process each batch with the upsert function
    .outputMode("update") 
    .option("checkpointLocation", checkpoint_location_silver)
    .trigger(availableNow=True)  # Process all available data at once
    .start()
    .awaitTermination()  # Wait for streaming to finish
)

# COMMAND ----------


