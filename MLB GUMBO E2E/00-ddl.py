# Databricks notebook source
# DBTITLE 1,Imports
# Imports
import pyspark.sql.functions as F

# COMMAND ----------

# DBTITLE 1,Global Variables
# Global variables
CATALOG = 'mlb_tech_summit'
DATABASE_L = 'mlb_gumbo_landing'
DATABASE_B = 'mlb_gumbo_bronze'
DATABASE_S = 'mlb_gumbo_silver'
DATABASE_G = 'mlb_gumbo_gold'

# Data Location
CHECKPOINT_BASE = f"/Volumes/{CATALOG}/{DATABASE_L}/mlb_gumbo_checkpoints"

# COMMAND ----------

# DBTITLE 1,Create Catalog
# spark.sql(f"""
#           CREATE CATALOG IF NOT EXISTS {CATALOG}
#           COMMENT 'Catalog for storing and processing all MLB GUMBO data';
#           """)

# spark.sql(f"""
#           ALTER CATALOG {CATALOG}
#           SET TAGS ('removeAfter' = '20281231');
#           """)

spark.sql(f"""
          USE CATALOG {CATALOG};
          """)

# COMMAND ----------

spark.sql(f"""
          CREATE DATABASE IF NOT EXISTS {CATALOG}.{DATABASE_L}
          COMMENT 'Landing database for storing raw MLB Gumbo data in a UC volume';
          """)

spark.sql(f"""
          CREATE DATABASE IF NOT EXISTS {CATALOG}.{DATABASE_B}
          COMMENT 'Bronze database for copies of MLB Gumbo landing tables, augmented with metadata fields from folder paths. Uses VARIANT to store the JSON objects.';
          """)

spark.sql(f"""
          CREATE DATABASE IF NOT EXISTS {CATALOG}.{DATABASE_S}
          COMMENT 'Silver database for storing clean, normalized MLB GUMBO data for analysis, with quality constraints met';
          """)

spark.sql(f"""
          CREATE DATABASE IF NOT EXISTS {CATALOG}.{DATABASE_G}
          COMMENT 'Gold database for serving aggregated MLB GUMBo data, KPIs etc. to front-end applications';
          """)

spark.sql(f"""
          USE DATABASE {DATABASE_B};
          """)

# COMMAND ----------

# DBTITLE 1,Create Bronze Table
# MAGIC %sql
# MAGIC CREATE TABLE IF NOT EXISTS raw_data (
# MAGIC   data VARIANT COMMENT "The raw GUMBO JSON object as a Variant",
# MAGIC   file_path STRING COMMENT "Path to the source file",
# MAGIC   file_name STRING COMMENT "Name of the source file",
# MAGIC   file_size BIGINT COMMENT "Size of the source file",
# MAGIC   file_modification_time TIMESTAMP COMMENT "Last modification time of the source file",
# MAGIC   file_batch_time TIMESTAMP COMMENT "Timestamp of the batch",
# MAGIC   last_update_time TIMESTAMP COMMENT "Timestamp of the last update",
# MAGIC   year STRING COMMENT "Year of the last update",
# MAGIC   month STRING COMMENT "Month of the last update",
# MAGIC   day STRING COMMENT "Day of the last update",
# MAGIC   hour STRING COMMENT "Hour of the last update",
# MAGIC   minute STRING COMMENT "Minute of the last update",
# MAGIC   second STRING COMMENT "Second of the last update"
# MAGIC )
# MAGIC USING DELTA
# MAGIC CLUSTER BY (file_batch_time)
# MAGIC COMMENT 'The mlb_gumbo.bronze.raw_data table holds the raw GUMBO JSON object as a Variant as well as metadata about the files loaded.';

# COMMAND ----------

spark.sql(f"""
          USE DATABASE {DATABASE_S};
          """)

# COMMAND ----------

# DBTITLE 1,Create Silver Tables
# MAGIC %sql
# MAGIC CREATE TABLE IF NOT EXISTS game_data (
# MAGIC     -- Metadata
# MAGIC     game_pk INT COMMENT 'Primary key for the game',
# MAGIC     link STRING COMMENT 'URL link to the game details',
# MAGIC     game_type STRING COMMENT 'Type of the game (e.g., regular season, playoff)',
# MAGIC     double_header STRING COMMENT 'Whether the game is part of a doubleheader',
# MAGIC     game_id STRING COMMENT 'Unique identifier for the game',
# MAGIC     gameday_type STRING COMMENT 'Type of gameday (e.g., day, night)',
# MAGIC     tiebreaker STRING COMMENT 'Indicates if the game is a tiebreaker',
# MAGIC     game_number INT COMMENT 'Game number in the season',
# MAGIC     calendar_event_id STRING COMMENT 'Event ID for calendar integration',
# MAGIC     season INT COMMENT 'Season year',
# MAGIC     season_display INT COMMENT 'Displayable season year (may be different for display purposes)',
# MAGIC
# MAGIC     -- Game Datetime
# MAGIC     date_time TIMESTAMP COMMENT 'Date and time the game starts',
# MAGIC     original_date DATE COMMENT 'Original scheduled date of the game',
# MAGIC     official_date DATE COMMENT 'Official date of the game (if rescheduled)',
# MAGIC     day_night STRING COMMENT 'Day or night game',
# MAGIC     time STRING COMMENT 'Game start time',
# MAGIC     ampm STRING COMMENT 'AM or PM for the start time',
# MAGIC
# MAGIC     -- Game Status
# MAGIC     abstract_game_state STRING COMMENT 'Abstract status of the game (e.g., scheduled, in progress)',
# MAGIC     coded_game_state STRING COMMENT 'Coded state representing the game status',
# MAGIC     detailed_state STRING COMMENT 'Detailed state of the game',
# MAGIC     status_code STRING COMMENT 'Status code for the game',
# MAGIC     start_time_tbd STRING COMMENT 'Whether the start time is TBD (to be determined)',
# MAGIC     abstract_game_code STRING COMMENT 'Abstract code for game (e.g., postponed, completed)',
# MAGIC
# MAGIC     -- Away Team
# MAGIC     away_team_abbreviation STRING COMMENT 'Abbreviation of the away team\'s name',
# MAGIC     away_team_active BOOLEAN COMMENT 'Whether the away team is active',
# MAGIC     away_team_all_star_status STRING COMMENT 'All-Star status of the away team',
# MAGIC     away_team_club_name STRING COMMENT 'Full name of the away team',
# MAGIC     away_team_division_id INT COMMENT 'Division ID of the away team',
# MAGIC     away_team_division_link STRING COMMENT 'Link to the division of the away team',
# MAGIC     away_team_division_name STRING COMMENT 'Name of the division of the away team',
# MAGIC     away_team_file_code STRING COMMENT 'File code for the away team',
# MAGIC     away_team_first_year_of_play INT COMMENT 'First year of play for the away team',
# MAGIC     away_team_franchise_name STRING COMMENT 'Franchise name of the away team',
# MAGIC     away_team_id INT COMMENT 'Unique ID for the away team',
# MAGIC     away_team_league_id INT COMMENT 'League ID of the away team',
# MAGIC     away_team_league_link STRING COMMENT 'Link to the league of the away team',
# MAGIC     away_team_league_name STRING COMMENT 'Name of the league of the away team',
# MAGIC     away_team_link STRING COMMENT 'Link to the away team details',
# MAGIC     away_team_location_name STRING COMMENT 'Location name of the away team',
# MAGIC     away_team_name STRING COMMENT 'Full name of the away team',
# MAGIC     away_team_record_conference_games_back STRING COMMENT 'Games behind in the conference for the away team',
# MAGIC     away_team_record_division_games_back STRING COMMENT 'Games behind in the division for the away team',
# MAGIC     away_team_record_division_leader BOOLEAN COMMENT 'Whether the away team is the division leader',
# MAGIC     away_team_record_games_played INT COMMENT 'Number of games played by the away team',
# MAGIC     away_team_record_league_games_back STRING COMMENT 'Games behind in the league for the away team',
# MAGIC     away_team_record_league_losses INT COMMENT 'League losses for the away team',
# MAGIC     away_team_record_league_pct DOUBLE COMMENT 'League win percentage for the away team',
# MAGIC     away_team_record_league_ties INT COMMENT 'League ties for the away team',
# MAGIC     away_team_record_league_wins INT COMMENT 'League wins for the away team',
# MAGIC     away_team_record_losses INT COMMENT 'Total losses for the away team',
# MAGIC     away_team_record_sport_games_back STRING COMMENT 'Games behind in the sport for the away team',
# MAGIC     away_team_record_spring_league_games_back STRING COMMENT 'Games behind in the spring league for the away team',
# MAGIC     away_team_record_wild_card_games_back STRING COMMENT 'Games behind in the wild card race for the away team',
# MAGIC     away_team_record_winning_percentage DOUBLE COMMENT 'Winning percentage for the away team',
# MAGIC     away_team_record_wins INT COMMENT 'Total wins for the away team',
# MAGIC     away_team_season STRING COMMENT 'Season of the away team',
# MAGIC     away_team_short_name STRING COMMENT 'Short name for the away team',
# MAGIC     away_team_sport_id INT COMMENT 'Sport ID for the away team',
# MAGIC     away_team_sport_link STRING COMMENT 'Link to the sport details of the away team',
# MAGIC     away_team_sport_name STRING COMMENT 'Sport name for the away team',
# MAGIC     away_team_spring_league_abbreviation STRING COMMENT 'Spring league abbreviation for the away team',
# MAGIC     away_team_spring_league_id INT COMMENT 'Spring league ID for the away team',
# MAGIC     away_team_spring_league_link STRING COMMENT 'Link to the spring league of the away team',
# MAGIC     away_team_spring_league_name STRING COMMENT 'Spring league name for the away team',
# MAGIC     away_team_spring_venue_id STRING COMMENT 'Spring venue ID for the away team',
# MAGIC     away_team_spring_venue_link STRING COMMENT 'Link to the spring venue of the away team',
# MAGIC     away_team_team_code STRING COMMENT 'Team code for the away team',
# MAGIC     away_team_team_name STRING COMMENT 'Team name for the away team',
# MAGIC     away_team_venue_id INT COMMENT 'Venue ID for the away team',
# MAGIC     away_team_venue_link STRING COMMENT 'Link to the venue of the away team',
# MAGIC     away_team_venue_name STRING COMMENT 'Venue name for the away team',
# MAGIC
# MAGIC     -- Home Team
# MAGIC     home_team_abbreviation STRING COMMENT 'Abbreviation of the home team\'s name',
# MAGIC     home_team_active BOOLEAN COMMENT 'Whether the home team is active',
# MAGIC     home_team_all_star_status STRING COMMENT 'All-Star status of the home team',
# MAGIC     home_team_club_name STRING COMMENT 'Full name of the home team',
# MAGIC     home_team_division_id INT COMMENT 'Division ID of the home team',
# MAGIC     home_team_division_link STRING COMMENT 'Link to the division of the home team',
# MAGIC     home_team_division_name STRING COMMENT 'Name of the division of the home team',
# MAGIC     home_team_file_code STRING COMMENT 'File code for the home team',
# MAGIC     home_team_first_year_of_play STRING COMMENT 'First year of play for the home team',
# MAGIC     home_team_franchise_name STRING COMMENT 'Franchise name of the home team',
# MAGIC     home_team_id INT COMMENT 'Unique ID for the home team',
# MAGIC     home_team_league_id INT COMMENT 'League ID of the home team',
# MAGIC     home_team_league_link STRING COMMENT 'Link to the league of the home team',
# MAGIC     home_team_league_name STRING COMMENT 'Name of the league of the home team',
# MAGIC     home_team_link STRING COMMENT 'Link to the home team details',
# MAGIC     home_team_location_name STRING COMMENT 'Location name of the home team',
# MAGIC     home_team_name STRING COMMENT 'Full name of the home team',
# MAGIC     home_team_record_conference_games_back STRING COMMENT 'Games behind in the conference for the home team',
# MAGIC     home_team_record_division_games_back STRING COMMENT 'Games behind in the division for the home team',
# MAGIC     home_team_record_division_leader BOOLEAN COMMENT 'Whether the home team is the division leader',
# MAGIC     home_team_record_games_played INT COMMENT 'Number of games played by the home team',
# MAGIC     home_team_record_league_games_back STRING COMMENT 'Games behind in the league for the home team',
# MAGIC     home_team_record_league_losses INT COMMENT 'League losses for the home team',
# MAGIC     home_team_record_league_pct DOUBLE COMMENT 'League win percentage for the home team',
# MAGIC     home_team_record_league_ties INT COMMENT 'League ties for the home team',
# MAGIC     home_team_record_league_wins INT COMMENT 'League wins for the home team',
# MAGIC     home_team_record_losses INT COMMENT 'Total losses for the home team',
# MAGIC     home_team_record_sport_games_back STRING COMMENT 'Games behind in the sport for the home team',
# MAGIC     home_team_record_spring_league_games_back STRING COMMENT 'Games behind in the spring league for the home team',
# MAGIC     home_team_record_wild_card_games_back STRING COMMENT 'Games behind in the wild card race for the home team',
# MAGIC     home_team_record_winning_percentage DOUBLE COMMENT 'Winning percentage for the home team',
# MAGIC     home_team_record_wins INT COMMENT 'Total wins for the home team',
# MAGIC     home_team_season STRING COMMENT 'Season of the home team',
# MAGIC     home_team_short_name STRING COMMENT 'Short name for the home team',
# MAGIC     home_team_sport_id INT COMMENT 'Sport ID for the home team',
# MAGIC     home_team_sport_link STRING COMMENT 'Link to the sport details of the home team',
# MAGIC     home_team_sport_name STRING COMMENT 'Sport name for the home team',
# MAGIC     home_team_spring_league_abbreviation STRING COMMENT 'Spring league abbreviation for the home team',
# MAGIC     home_team_spring_league_id INT COMMENT 'Spring league ID for the home team',
# MAGIC     home_team_spring_league_link STRING COMMENT 'Link to the spring league of the home team',
# MAGIC     home_team_spring_league_name STRING COMMENT 'Spring league name for the home team',
# MAGIC     home_team_spring_venue_id INT COMMENT 'Spring venue ID for the home team',
# MAGIC     home_team_spring_venue_link STRING COMMENT 'Link to the spring venue of the home team',
# MAGIC     home_team_team_code STRING COMMENT 'Team code for the home team',
# MAGIC     home_team_team_name STRING COMMENT 'Team name for the home team',
# MAGIC     home_team_venue_id INT COMMENT 'Venue ID for the home team',
# MAGIC     home_team_venue_link STRING COMMENT 'Link to the venue of the home team',
# MAGIC     home_team_venue_name STRING COMMENT 'Venue name for the home team',
# MAGIC
# MAGIC     -- Venue
# MAGIC     venue_id INT COMMENT 'Unique ID for the venue',
# MAGIC     venue_name STRING COMMENT 'Name of the venue',
# MAGIC     venue_link STRING COMMENT 'Link to the venue details',
# MAGIC     venue_address1 STRING COMMENT 'Street address of the venue',
# MAGIC     venue_azimuth_angle STRING COMMENT 'Azimuth angle of the venue',
# MAGIC     venue_city STRING COMMENT 'City where the venue is located',
# MAGIC     venue_country STRING COMMENT 'Country where the venue is located',
# MAGIC     venue_latitude DOUBLE COMMENT 'Latitude of the venue',
# MAGIC     venue_longitude DOUBLE COMMENT 'Longitude of the venue',
# MAGIC     venue_elevation INT COMMENT 'Elevation of the venue',
# MAGIC     venue_phone STRING COMMENT 'Phone number for the venue',
# MAGIC     venue_postal_code STRING COMMENT 'Postal code for the venue location',
# MAGIC     venue_state STRING COMMENT 'State where the venue is located',
# MAGIC     venue_state_abbrev STRING COMMENT 'Abbreviation of the venue state',
# MAGIC     venue_time_zone_id STRING COMMENT 'Time zone ID for the venue',
# MAGIC     venue_time_zone_offset INT COMMENT 'Time zone offset from UTC for the venue',
# MAGIC     venue_time_zone_offset_at_game_time INT COMMENT 'Time zone offset from UTC at game time',
# MAGIC     venue_time_zone_tz STRING COMMENT 'Time zone abbreviation for the venue',
# MAGIC     venue_field_capacity INT COMMENT 'Field capacity of the venue',
# MAGIC     venue_field_center INT COMMENT 'Distance to the center of the field from home plate',
# MAGIC     venue_field_left_center INT COMMENT 'Distance to left-center field',
# MAGIC     venue_field_left_line INT COMMENT 'Distance to the left field line',
# MAGIC     venue_field_right_center INT COMMENT 'Distance to right-center field',
# MAGIC     venue_field_right_line INT COMMENT 'Distance to the right field line',
# MAGIC     venue_field_roof_type STRING COMMENT 'Roof type of the venue',
# MAGIC     venue_field_turf_type STRING COMMENT 'Turf type of the venue',
# MAGIC     venue_active BOOLEAN COMMENT 'Whether the venue is currently active',
# MAGIC     venue_season INT COMMENT 'Season for the venue',
# MAGIC     official_venue_id INT COMMENT 'Official ID for the venue',
# MAGIC     official_venue_link STRING COMMENT 'Official link to the venue details',
# MAGIC
# MAGIC     -- Weather & Flags
# MAGIC     weather_condition STRING COMMENT 'Weather condition at the time of the game',
# MAGIC     weather_temp INT COMMENT 'Temperature during the game (in Fahrenheit)',
# MAGIC     weather_wind STRING COMMENT 'Wind conditions during the game',
# MAGIC     game_info_attendance INT COMMENT 'Attendance at the game',
# MAGIC     game_info_first_pitch TIMESTAMP COMMENT 'Timestamp of the first pitch of the game',
# MAGIC     game_info_duration INT COMMENT 'Duration of the game in minutes',
# MAGIC     review_has_challenges BOOLEAN COMMENT 'Whether the game has review challenges',
# MAGIC     review_away_remaining INT COMMENT 'Remaining challenges for the away team',
# MAGIC     review_away_used INT COMMENT 'Used challenges for the away team',
# MAGIC     review_home_remaining INT COMMENT 'Remaining challenges for the home team',
# MAGIC     review_home_used INT COMMENT 'Used challenges for the home team',
# MAGIC     flags_no_hitter BOOLEAN COMMENT 'Whether the game was a no-hitter',
# MAGIC     flags_perfect_game BOOLEAN COMMENT 'Whether the game was a perfect game',
# MAGIC     flags_away_team_no_hitter BOOLEAN COMMENT 'Whether the away team threw a no-hitter',
# MAGIC     flags_away_team_perfect_game BOOLEAN COMMENT 'Whether the away team threw a perfect game',
# MAGIC     flags_home_team_no_hitter BOOLEAN COMMENT 'Whether the home team threw a no-hitter',
# MAGIC     flags_home_team_perfect_game BOOLEAN COMMENT 'Whether the home team threw a perfect game',
# MAGIC
# MAGIC     -- Probable Pitchers, Officials
# MAGIC     probable_pitchers_away_full_name STRING COMMENT 'Full name of the away team\'s probable pitcher',
# MAGIC     probable_pitchers_away_id INT COMMENT 'ID of the away team\'s probable pitcher',
# MAGIC     probable_pitchers_away_link STRING COMMENT 'Link to the away team\'s probable pitcher',
# MAGIC     probable_pitchers_home_full_name STRING COMMENT 'Full name of the home team\'s probable pitcher',
# MAGIC     probable_pitchers_home_id INT COMMENT 'ID of the home team\'s probable pitcher',
# MAGIC     probable_pitchers_home_link STRING COMMENT 'Link to the home team\'s probable pitcher',
# MAGIC     official_scorer_id INT COMMENT 'ID of the official scorer for the game',
# MAGIC     official_scorer_full_name STRING COMMENT 'Full name of the official scorer',
# MAGIC     official_scorer_link STRING COMMENT 'Link to the official scorer\'s profile',
# MAGIC     primary_datacaster_id INT COMMENT 'ID of the primary datacaster for the game',
# MAGIC     primary_datacaster_full_name STRING COMMENT 'Full name of the primary datacaster',
# MAGIC     primary_datacaster_link STRING COMMENT 'Link to the primary datacaster\'s profile',
# MAGIC
# MAGIC     -- Mound Visits
# MAGIC     mound_visits_away_remaining INT COMMENT 'Remaining mound visits for the away team',
# MAGIC     mound_visits_away_used INT COMMENT 'Used mound visits for the away team',
# MAGIC     mound_visits_home_remaining INT COMMENT 'Remaining mound visits for the home team',
# MAGIC     mound_visits_home_used INT COMMENT 'Used mound visits for the home team',
# MAGIC
# MAGIC     -- File Metadata
# MAGIC     file_path STRING COMMENT 'Path to the game data file',
# MAGIC     file_name STRING COMMENT 'Name of the game data file',
# MAGIC     file_size BIGINT COMMENT 'Size of the game data file in bytes',
# MAGIC     file_modification_time TIMESTAMP COMMENT 'Last modification time of the game data file',
# MAGIC     file_batch_time TIMESTAMP COMMENT 'Batch time for processing the game data file',
# MAGIC     last_update_time TIMESTAMP COMMENT 'Last update time of the game data'
# MAGIC )
# MAGIC USING delta
# MAGIC CLUSTER BY (season, official_date)
# MAGIC COMMENT 'This table contains comprehensive data about MLB games, sourced from the bronze_gumbo_data table and transformed for analytics in the silver layer. It provides detailed metadata, datetime, status, team (home and away), venue, weather, game officials, and statistical flags. Additionally, it includes information about probable pitchers, mound visits, and metadata about the file source of the data. This table is designed to support in-depth analysis of individual games and trends over time.'

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE TABLE IF NOT EXISTS pitch_data (
# MAGIC     -- Game Metadata
# MAGIC     season INT COMMENT "Season year for the game",
# MAGIC     game_datetime TIMESTAMP COMMENT "Datetime of the game",
# MAGIC     official_date DATE COMMENT 'Official date of the game (if rescheduled)',
# MAGIC     game_pk INT COMMENT "Primary key identifier for the game",
# MAGIC     gameday_type STRING COMMENT "Type of gameday (e.g., regular, postseason)",
# MAGIC     game_number INT COMMENT "Game number in the series",
# MAGIC     away_team_id INT COMMENT "Away team identifier",
# MAGIC     away_team_name STRING COMMENT "Name of the away team",
# MAGIC     home_team_id INT COMMENT "Home team identifier",
# MAGIC     home_team_name STRING COMMENT "Name of the home team",
# MAGIC
# MAGIC     -- Play Metadata
# MAGIC     play_event STRING COMMENT "Event description of the play",
# MAGIC     play_event_type STRING COMMENT "Event type of the play (e.g., hit, out)",
# MAGIC     play_description STRING COMMENT "Detailed description of the play",
# MAGIC     play_rbi INT COMMENT "Runs batted in during the play",
# MAGIC     post_play_away_score INT COMMENT "Away team score after the play",
# MAGIC     post_play_home_score INT COMMENT "Home team score after the play",
# MAGIC     at_bat_index INT COMMENT "Index of the at-bat during the game",
# MAGIC     half_inning STRING COMMENT "Half inning designation (top or bottom)",
# MAGIC     is_top_inning BOOLEAN COMMENT "Indicates if the play occurred in the top half of the inning",
# MAGIC     inning INT COMMENT "Inning number of the play",
# MAGIC     captivating_index INT COMMENT "Captivating index score for the play",
# MAGIC
# MAGIC     -- Pitch Metadata
# MAGIC     pitch_index INT COMMENT "Index of the pitch during the at-bat",
# MAGIC     pitch_guid STRING COMMENT "Unique identifier for the pitch",
# MAGIC     pitch_number INT COMMENT "Sequence number of the pitch within the at-bat",
# MAGIC     start_time STRING COMMENT "Start time of the pitch event",
# MAGIC     end_time STRING COMMENT "End time of the pitch event",
# MAGIC     is_pitch BOOLEAN COMMENT "Indicates if the event was a pitch",
# MAGIC     event_type STRING COMMENT "Type of event (e.g., pitch, play)",
# MAGIC
# MAGIC     -- Pitch Results
# MAGIC     call_code STRING COMMENT "Code representing the pitch call (e.g., ball, strike)",
# MAGIC     call_description STRING COMMENT "Description of the pitch call",
# MAGIC     pitch_description STRING COMMENT "Description of the pitch",
# MAGIC     pitch_code STRING COMMENT "Code representing the pitch type",
# MAGIC     ball_color STRING COMMENT "Color of the ball as tracked",
# MAGIC     trail_color STRING COMMENT "Trail color of the pitch",
# MAGIC     is_in_play BOOLEAN COMMENT "Indicates if the ball was put in play",
# MAGIC     is_strike BOOLEAN COMMENT "Indicates if the pitch was a strike",
# MAGIC     is_ball BOOLEAN COMMENT "Indicates if the pitch was a ball",
# MAGIC     pitch_type_code STRING COMMENT "Code for the type of pitch (e.g., fastball)",
# MAGIC     pitch_type_description STRING COMMENT "Description of the type of pitch",
# MAGIC     is_out BOOLEAN COMMENT "Indicates if the play resulted in an out",
# MAGIC     has_review BOOLEAN COMMENT "Indicates if the play underwent a review",
# MAGIC
# MAGIC     -- Pitch Count
# MAGIC     balls_count INT COMMENT "Count of balls at the time of the pitch",
# MAGIC     strikes_count INT COMMENT "Count of strikes at the time of the pitch",
# MAGIC     outs_count INT COMMENT "Count of outs at the time of the pitch",
# MAGIC     pre_balls_count INT COMMENT "Count of balls before the pitch",
# MAGIC     pre_strikes_count INT COMMENT "Count of strikes before the pitch",
# MAGIC     pre_outs_count INT COMMENT "Count of outs before the pitch",
# MAGIC
# MAGIC     -- Pitch Data
# MAGIC     pitch_start_speed DOUBLE COMMENT "Speed of the pitch at release (mph)",
# MAGIC     pitch_end_speed DOUBLE COMMENT "Speed of the pitch at the plate (mph)",
# MAGIC     strike_zone_top DOUBLE COMMENT "Top boundary of the strike zone",
# MAGIC     strike_zone_bottom DOUBLE COMMENT "Bottom boundary of the strike zone",
# MAGIC     acceleration_y DOUBLE COMMENT "Acceleration of the pitch along the Y-axis",
# MAGIC     acceleration_z DOUBLE COMMENT "Acceleration of the pitch along the Z-axis",
# MAGIC     pfx_x DOUBLE COMMENT "Horizontal movement of the pitch (inches)",
# MAGIC     pfx_z DOUBLE COMMENT "Vertical movement of the pitch (inches)",
# MAGIC     position_x DOUBLE COMMENT "Horizontal position of the pitch at the plate",
# MAGIC     position_z DOUBLE COMMENT "Vertical position of the pitch at the plate",
# MAGIC     initial_velocity_x DOUBLE COMMENT "Initial velocity of the pitch along the X-axis",
# MAGIC     initial_velocity_y DOUBLE COMMENT "Initial velocity of the pitch along the Y-axis",
# MAGIC     initial_velocity_z DOUBLE COMMENT "Initial velocity of the pitch along the Z-axis",
# MAGIC     x DOUBLE COMMENT "Coordinate X of the pitch",
# MAGIC     y DOUBLE COMMENT "Coordinate Y of the pitch",
# MAGIC     initial_x DOUBLE COMMENT "Initial X coordinate of the pitch",
# MAGIC     initial_y DOUBLE COMMENT "Initial Y coordinate of the pitch",
# MAGIC     initial_z DOUBLE COMMENT "Initial Z coordinate of the pitch",
# MAGIC     acceleration_x DOUBLE COMMENT "Acceleration of the pitch along the X-axis",
# MAGIC     pitch_break_angle DOUBLE COMMENT "Angle of the pitch break",
# MAGIC     pitch_break_length DOUBLE COMMENT "Length of the pitch break (inches)",
# MAGIC     pitch_break_y DOUBLE COMMENT "Distance to break (feet)",
# MAGIC     pitch_break_vertical DOUBLE COMMENT "Vertical break of the pitch (inches)",
# MAGIC     pitch_break_vertical_induced DOUBLE COMMENT "Induced vertical break (inches)",
# MAGIC     pitch_break_horizontal DOUBLE COMMENT "Horizontal break of the pitch (inches)",
# MAGIC     pitch_spin_rate INT COMMENT "Spin rate of the pitch (RPM)",
# MAGIC     pitch_spin_direction INT COMMENT "Spin direction of the pitch (degrees)",
# MAGIC     pitch_zone INT COMMENT "Zone location of the pitch",
# MAGIC     pitch_type_confidence DOUBLE COMMENT "Confidence score for the pitch type",
# MAGIC     plate_time DOUBLE COMMENT "Time for the pitch to reach the plate (seconds)",
# MAGIC     extension DOUBLE COMMENT "Extension of the pitcher at release (feet)",
# MAGIC
# MAGIC     -- Hit Data
# MAGIC     hit_launch_speed DOUBLE COMMENT "Exit velocity of the ball (mph)",
# MAGIC     hit_launch_angle DOUBLE COMMENT "Launch angle of the ball (degrees)",
# MAGIC     hit_total_distance DOUBLE COMMENT "Total distance of the hit (feet)",
# MAGIC     hit_trajectory STRING COMMENT "Trajectory type of the hit",
# MAGIC     hit_hardness STRING COMMENT "Hardness rating of the hit",
# MAGIC     hit_location STRING COMMENT "Location of the hit on the field",
# MAGIC     hit_coord_x DOUBLE COMMENT "X coordinate of the hit location",
# MAGIC     hit_coord_y DOUBLE COMMENT "Y coordinate of the hit location",
# MAGIC
# MAGIC     -- Player Data
# MAGIC     batter_id INT COMMENT "ID of the batter",
# MAGIC     batter_full_name STRING COMMENT "Full name of the batter",
# MAGIC     batter_link STRING COMMENT "API link for batter details",
# MAGIC     batter_side_code STRING COMMENT "Code for the batter's batting side",
# MAGIC     batter_side_description STRING COMMENT "Description of the batter's batting side",
# MAGIC     batter_position_code STRING COMMENT "Code for the batter's fielding position",
# MAGIC     batter_position_name STRING COMMENT "Name of the batter's fielding position",
# MAGIC     batter_position_type STRING COMMENT "Type of the batter's position",
# MAGIC     batter_position_abbreviation STRING COMMENT "Abbreviation for the batter's position",
# MAGIC     pitcher_id INT COMMENT "ID of the pitcher",
# MAGIC     pitcher_full_name STRING COMMENT "Full name of the pitcher",
# MAGIC     pitcher_link STRING COMMENT "API link for pitcher details",
# MAGIC     pitcher_hand_code STRING COMMENT "Code for the pitcher's throwing hand",
# MAGIC     pitcher_hand_description STRING COMMENT "Description of the pitcher's throwing hand",
# MAGIC     catcher_id INT COMMENT "ID of the catcher",
# MAGIC     catcher_link STRING COMMENT "API link for catcher details",
# MAGIC     first_base_id INT COMMENT "ID of the first baseman",
# MAGIC     second_base_id INT COMMENT "ID of the second baseman",
# MAGIC     third_base_id INT COMMENT "ID of the third baseman",
# MAGIC     shortstop_id INT COMMENT "ID of the shortstop",
# MAGIC     left_fielder_id INT COMMENT "ID of the left fielder",
# MAGIC     center_fielder_id INT COMMENT "ID of the center fielder",
# MAGIC     right_fielder_id INT COMMENT "ID of the right fielder",
# MAGIC
# MAGIC     -- File Metadata
# MAGIC     file_path STRING COMMENT "Path to the source file",
# MAGIC     file_name STRING COMMENT "Name of the source file",
# MAGIC     file_size BIGINT COMMENT "Size of the source file",
# MAGIC     file_modification_time TIMESTAMP COMMENT "Last modification time of the source file",
# MAGIC     file_batch_time TIMESTAMP COMMENT "Timestamp of the batch",
# MAGIC     last_update_time TIMESTAMP COMMENT "Timestamp of the last update"
# MAGIC )
# MAGIC USING delta
# MAGIC CLUSTER BY (season, official_date, game_pk)
# MAGIC COMMENT "Silver-layer table containing granular pitch-level MLB game data extracted and transformed from the bronze layer";
# MAGIC

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE TABLE IF NOT EXISTS strike_probability (
# MAGIC     season INTEGER COMMENT 'Year of the baseball season',
# MAGIC     official_date DATE COMMENT 'Official game date',
# MAGIC     game_pk INTEGER COMMENT 'Unique identifier for the game',
# MAGIC     at_bat_index INTEGER COMMENT 'Index of the at-bat within the game',
# MAGIC     pitch_index INTEGER COMMENT 'Index of the pitch within the at-bat',
# MAGIC     pitch_start_speed DOUBLE COMMENT 'Starting speed of the pitch (mph)',
# MAGIC     pitch_break_vertical_induced DOUBLE COMMENT 'Induced vertical break of the pitch (inches)',
# MAGIC     pitch_break_horizontal DOUBLE COMMENT 'Horizontal break of the pitch (inches)',
# MAGIC     pitch_spin_rate INTEGER COMMENT 'Spin rate of the pitch (rpm)',
# MAGIC     position_x DOUBLE COMMENT 'Horizontal position of the pitch at the plate (feet)',
# MAGIC     position_z DOUBLE COMMENT 'Vertical position of the pitch at the plate (feet)',
# MAGIC     called_strike_probability FLOAT COMMENT 'Predicted probability of the pitch being called a strike',
# MAGIC     last_update_time TIMESTAMP COMMENT "Timestamp of the last update"
# MAGIC )
# MAGIC USING delta
# MAGIC CLUSTER BY (season, official_date, game_pk)
# MAGIC COMMENT 'Table storing pitch data features and model-generated strike probabilities';

# COMMAND ----------

spark.sql(f"""
          USE DATABASE {DATABASE_G};
          """)

# COMMAND ----------

# %sql
# -- Gold Table Query: Join game_data, pitch_data, and strike_probability
# CREATE MATERIALIZED VIEW IF NOT EXISTS game_report_mv
# COMMENT 'Materialized View to power the Game Report Dashboard with pitch-level, game-level, and strike probability data'
# AS
# SELECT
#     -- Game-level Metadata
#     g.season,
#     g.game_pk,
#     g.official_date,
#     g.home_team_name,
#     g.away_team_name,
#     g.home_team_record_wins AS home_team_wins,
#     g.away_team_record_wins AS away_team_wins,
#     g.home_team_record_losses AS home_team_losses,
#     g.away_team_record_losses AS away_team_losses,
#     g.venue_name,
#     g.weather_condition,
#     g.weather_temp,
#     g.weather_wind,

#     -- Pitch Event Metadata
#     p.pitch_index,
#     p.pitch_number,
#     p.pitch_guid,
#     p.inning,
#     p.half_inning,
#     p.is_pitch,
#     p.call_description,                -- Ball, strike, foul, etc.
#     p.position_x,                     -- Horizontal position at the plate
#     p.position_z,                     -- Vertical position at the plate
#     p.pitch_type_description,          -- Pitch type (e.g., fastball, slider)
#     p.pitch_start_speed,               -- Pitch speed at release (mph)
#     p.pitch_end_speed,                 -- Pitch speed at the plate (mph)
#     p.pitch_spin_rate,                 -- Pitch spin rate (RPM)
#     p.pitch_break_length,              -- Length of pitch break (inches)
#     p.pitch_break_vertical,            -- Vertical break (inches)
#     p.pitch_break_horizontal,          -- Horizontal break (inches)
#     p.plate_time,                      -- Time for pitch to reach the plate (seconds)
#     p.extension,                       -- Extension of pitcher's release (feet)
    
#     -- Hit Data (if applicable)
#     p.hit_launch_speed,                -- Exit velocity (mph)
#     p.hit_launch_angle,                -- Launch angle (degrees)
#     p.hit_total_distance,              -- Distance of the hit (feet)
#     p.hit_trajectory,                  -- Hit trajectory type
#     p.hit_hardness,                    -- Hardness rating of the hit
    
#     -- Player Data
#     p.batter_full_name,
#     p.batter_side_description,         -- Batter's batting side
#     p.pitcher_full_name,
#     p.pitcher_hand_description,        -- Pitcher's throwing hand

#     -- Strike Probability
#     sp.strike_probability             -- Model-predicted probability of a strike

# FROM
#     mlb_tech_summit.mlb_gumbo_silver.game_data g
# JOIN
#     mlb_tech_summit.mlb_gumbo_silver.pitch_data p
# ON
#     g.game_pk = p.game_pk
# LEFT JOIN
#     mlb_tech_summit.mlb_gumbo_silver.strike_probability sp
# ON
#     g.game_pk = sp.game_pk
#     AND p.at_bat_index = sp.at_bat_index
#     AND p.pitch_index = sp.pitch_index
# WHERE
#     p.is_pitch = TRUE                 -- Only include events that are actual pitches
# ORDER BY
#     g.official_date ASC, p.inning ASC, p.pitch_index ASC;


# COMMAND ----------

# 
