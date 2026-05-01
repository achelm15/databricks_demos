"""PySpark schemas for SportLogiq Hockey API JSON payloads.

These mirror the response shape of each API route. The silver notebook uses
them with `from_json(VARIANT_to_string, schema)` to flatten array-typed sub-
fields where the `data:field::type` VARIANT path syntax can't reach (e.g.
nested STRUCT-of-ARRAY-of-STRUCT in metrics groupings).
"""
from pyspark.sql.types import StructType, StructField, StringType, ArrayType, IntegerType

# 1. get_competition_list
get_competition_list_schema = StructType([
    StructField("id", StringType(), True),
    StructField("name", StringType(), True)
])

# 2. get_competition_details
get_competition_details_schema = StructType([
    StructField("id", StringType(), True),
    StructField("name", StringType(), True),
    StructField("seasons", ArrayType(
        StructType([
            StructField("name", StringType(), True),
            StructField("stages", ArrayType(
                StructType([
                    StructField("name", StringType(), True),
                    StructField("start_date", StringType(), True),
                    StructField("end_date", StringType(), True)
                ])
            ), True)
        ])
    ), True)
])

# 3. get_game_list
get_game_list_schema = StructType([
    StructField("season", StringType(), True),
    StructField("stage", StringType(), True),
    StructField("competition_id", StringType(), True),
    StructField("team_id", StringType(), True),
    StructField("games", ArrayType(
        StructType([
            StructField("id", StringType(), True),
            StructField("date", StringType(), True),
            StructField("scheduled_time", StringType(), True),
            StructField("home_team_id", StringType(), True),
            StructField("away_team_id", StringType(), True),
            StructField("venue_id", StringType(), True)
        ])
    ), True)
])

# 4. get_venue_list
get_venue_list_schema = StructType([
    StructField("competition_id", StringType(), True),
    StructField("season", StringType(), True),
    StructField("stage", StringType(), True),
    StructField("venues", ArrayType(
        StructType([
            StructField("id", StringType(), True),
            StructField("name", StringType(), True),
            StructField("city", StringType(), True),
            StructField("state", StringType(), True),
            StructField("country", StringType(), True),
            StructField("timezone", StringType(), True),
            StructField("capacity", IntegerType(), True)
        ])
    ), True)
])

# 5. get_roster_non_player
get_roster_non_player_schema = StructType([
    StructField("id", StringType(), True),
    StructField("first_name", StringType(), True),
    StructField("last_name", StringType(), True),
    StructField("position", StringType(), True),
    StructField("task", StringType(), True)
])

# 6. get_roster_player
get_roster_player_schema = StructType([
    StructField("id", StringType(), True),
    StructField("first_name", StringType(), True),
    StructField("last_name", StringType(), True),
    StructField("position", StringType(), True),
    StructField("role", StringType(), True)
])

# 7. get_game_roster
get_game_roster_schema = StructType([
    StructField("crew", ArrayType(
        StructType([
            StructField("id", StringType(), True),
            StructField("first_name", StringType(), True),
            StructField("last_name", StringType(), True),
            StructField("position", StringType(), True),
            StructField("task", StringType(), True)
        ])
    ),True)
])

# 8. get_leadersteamleader
get_leadersteamleader_schema = StructType([
    StructField("first_name", StringType(), True),
    StructField("last_name", StringType(), True),
    StructField("value", IntegerType(), True),
    StructField("value_display", StringType(), True)
])

# 9. get_leadersteam
get_leadersteam_schema = StructType([
    StructField("type", StringType(), True),
    StructField("team", StringType(), True),
    StructField("shorthand", StringType(), True),
    StructField("value", IntegerType(), True),
    StructField("value_display", StringType(), True),
    StructField("leaders", ArrayType(
        StructType([
            StructField("first_name", StringType(), True),
            StructField("last_name", StringType(), True),
            StructField("value", IntegerType(), True),
            StructField("value_display", StringType(), True)
        ])
    ), True)
])

# 10. get_leadersleague
get_leadersleague_schema = StructType([
    StructField("first_name", StringType(), True),
    StructField("last_name", StringType(), True),
    StructField("team", StringType(), True),
    StructField("shorthand", StringType(), True),
    StructField("value", IntegerType(), True),
    StructField("value_display", StringType(), True)
])

# 11. get_leaders
get_leaders_schema = StructType([
    StructField("id", StringType(), True),
    StructField("metric_name", StringType(), True),
    StructField("scope", StringType(), True),
    StructField("teams", ArrayType(
        StructType([
            StructField("id", StringType(), True),
            StructField("record", StructType([
                StructField("wins", IntegerType(), True),
                StructField("losses", IntegerType(), True),
                StructField("overtime_losses", IntegerType(), True),
                StructField("ties", IntegerType(), True)
            ]), True)
        ])
    ), True),
    StructField("league", StructType([
        StructField("average", IntegerType(), True),
        StructField("average_display", StringType(), True),
        StructField("leaders", ArrayType(
            StructType([
                StructField("first_name", StringType(), True),
                StructField("last_name", StringType(), True),
                StructField("team", StringType(), True),
                StructField("shorthand", StringType(), True),
                StructField("value", IntegerType(), True),
                StructField("value_display", StringType(), True)
            ])
        ), True)
    ]), True)
])

# 12. get_team_details
get_team_details_schema = StructType([
    StructField("id", StringType(), True),
    StructField("name", StringType(), True),
    StructField("location", StringType(), True),
    StructField("shorthand", StringType(), True),
    StructField("division", StringType(), True),
    StructField("conference", StringType(), True),
    StructField("logo_src", StringType(), True)
])

# 13. get_game_details
get_game_details_schema = StructType([
    StructField("id", StringType(), True),
    StructField("season", StringType(), True),
    StructField("stage", StringType(), True),
    StructField("date", StringType(), True),
    StructField("winning_team_id", StringType(), True),
    StructField("away_score", ArrayType(IntegerType()), True),
    StructField("home_score", ArrayType(IntegerType()), True),
    StructField("home_team", StructType([
        StructField("id", StringType(), True),
        StructField("name", StringType(), True),
        StructField("location", StringType(), True),
        StructField("shorthand", StringType(), True),
        StructField("division", StringType(), True),
        StructField("conference", StringType(), True),
        StructField("logo_src", StringType(), True)
    ]), True),
    StructField("away_team", StructType([
        StructField("id", StringType(), True),
        StructField("name", StringType(), True),
        StructField("location", StringType(), True),
        StructField("shorthand", StringType(), True),
        StructField("division", StringType(), True),
        StructField("conference", StringType(), True),
        StructField("logo_src", StringType(), True)
    ]), True)
])

# 14. get_full_feed_event
get_full_feed_event_schema = StructType([
    StructField("game_reference_id", StringType(), True),
    StructField("event_id", StringType(), True),
    StructField("x_coord", IntegerType(), True),
    StructField("y_coord", IntegerType(), True),
    StructField("zone", StringType(), True),
    StructField("timecode", StringType(), True),
    StructField("frame", IntegerType(), True),
    StructField("period", IntegerType(), True),
    StructField("period_time", IntegerType(), True),
    StructField("game_time", IntegerType(), True),
    StructField("minutes", IntegerType(), True),
    StructField("seconds", IntegerType(), True),
    StructField("team", StringType(), True),
    StructField("player_id", StringType(), True),
    StructField("player_position", StringType(), True),
    StructField("player_first_name", StringType(), True),
    StructField("player_last_name", StringType(), True),
    StructField("player_jersey", StringType(), True),
    StructField("event_sequence_id", StringType(), True),
    StructField("shorthand", StringType(), True),
    StructField("name", StringType(), True),
    StructField("type", StringType(), True),
    StructField("outcome", StringType(), True),
    StructField("flags", ArrayType(StringType()), True),
    StructField("players_involved_in_play", StringType(), True),
    StructField("opposing_team_players_involved_in_play", StringType(), True),
    StructField("current_possession", IntegerType(), True),
    StructField("team_in_possession", StringType(), True),
    StructField("current_play_in_possession", IntegerType(), True),
    StructField("current_off_play_in_possession", IntegerType(), True),
    StructField("current_def_play_in_possession", IntegerType(), True),
    StructField("related_event_id", StringType(), True),
    StructField("related_event_player_id", StringType(), True),
    StructField("related_event_player_first_name", StringType(), True),
    StructField("related_event_player_last_name", StringType(), True),
    StructField("related_event_player_number", StringType(), True),
    StructField("attributes", StructType([]), True)
])

# 15. get_compiled_event
get_compiled_event_schema = StructType([
    StructField("game_reference_id", StringType(), True),
    StructField("event_id", StringType(), True),
    StructField("x_coord", IntegerType(), True),
    StructField("y_coord", IntegerType(), True),
    StructField("zone", StringType(), True),
    StructField("timecode", StringType(), True),
    StructField("frame", IntegerType(), True),
    StructField("period", IntegerType(), True),
    StructField("period_time", IntegerType(), True),
    StructField("game_time", IntegerType(), True),
    StructField("minutes", IntegerType(), True),
    StructField("seconds", IntegerType(), True),
    StructField("team", StringType(), True),
    StructField("player_id", StringType(), True),
    StructField("player_position", StringType(), True),
    StructField("player_first_name", StringType(), True),
    StructField("player_last_name", StringType(), True),
    StructField("player_jersey", StringType(), True),
    StructField("event_sequence_id", StringType(), True),
    StructField("shorthand", StringType(), True),
    StructField("name", StringType(), True),
    StructField("type", StringType(), True),
    StructField("outcome", StringType(), True),
    StructField("flags", ArrayType(StringType()), True),
    StructField("players_involved_in_play", StringType(), True),
    StructField("opposing_team_players_involved_in_play", StringType(), True),
    StructField("current_possession", IntegerType(), True),
    StructField("team_in_possession", StringType(), True),
    StructField("current_play_in_possession", IntegerType(), True),
    StructField("current_off_play_in_possession", IntegerType(), True),
    StructField("current_def_play_in_possession", IntegerType(), True),
    StructField("related_event_id", StringType(), True),
    StructField("related_event_player_id", StringType(), True),
    StructField("related_event_player_first_name", StringType(), True),
    StructField("related_event_player_last_name", StringType(), True),
    StructField("related_event_player_number", StringType(), True),
    StructField("attributes", StructType([]), True)
])

# 16. get_metric_details
get_metric_details_schema = StructType([
    StructField("id", StringType(), True),
    StructField("season", StringType(), True),
    StructField("stage", StringType(), True),
    StructField("competition_id", StringType(), True),
    StructField("topic_id", StringType(), True),
    StructField("groupings", ArrayType(
        StructType([
            StructField("breakdown", ArrayType(
                StructType([
                    StructField("key", StringType(), True),
                    StructField("value", StringType(), True)
                ])
            ), True),
            StructField("metrics", ArrayType(
                StructType([
                    StructField("key", StringType(), True),
                    StructField("value", IntegerType(), True)
                ])
            ), True),
            StructField("unitsplayed", ArrayType(
                StructType([
                    StructField("name", StringType(), True),
                    StructField("value", IntegerType(), True)
                ])
            ), True)
        ])
    ), True)
])

# 17. get_player_shift_event
get_player_shift_event_schema = StructType([
    StructField("game_reference_id", StringType(), True),
    StructField("event_id", StringType(), True),
    StructField("x_coord", IntegerType(), True),
    StructField("y_coord", IntegerType(), True),
    StructField("zone", StringType(), True),
    StructField("timecode", StringType(), True),
    StructField("frame", IntegerType(), True),
    StructField("period", IntegerType(), True),
    StructField("period_time", IntegerType(), True),
    StructField("game_time", IntegerType(), True),
    StructField("minutes", IntegerType(), True),
    StructField("seconds", IntegerType(), True),
    StructField("team", StringType(), True),
    StructField("player_id", StringType(), True),
    StructField("player_position", StringType(), True),
    StructField("player_first_name", StringType(), True),
    StructField("player_last_name", StringType(), True),
    StructField("player_jersey", StringType(), True),
    StructField("event_sequence_id", StringType(), True),
    StructField("shorthand", StringType(), True),
    StructField("name", StringType(), True),
    StructField("type", StringType(), True),
    StructField("outcome", StringType(), True),
    StructField("flags", ArrayType(StringType()), True),
    StructField("players_involved_in_play", StringType(), True),
    StructField("opposing_team_players_involved_in_play", StringType(), True),
    StructField("current_possession", IntegerType(), True),
    StructField("team_in_possession", StringType(), True),
    StructField("current_play_in_possession", IntegerType(), True),
    StructField("current_off_play_in_possession", IntegerType(), True),
    StructField("current_def_play_in_possession", IntegerType(), True),
    StructField("related_event_id", StringType(), True),
    StructField("related_event_player_id", StringType(), True),
    StructField("related_event_player_first_name", StringType(), True),
    StructField("related_event_player_last_name", StringType(), True),
    StructField("related_event_player_number", StringType(), True),
    StructField("attributes", StructType([]), True)
])

# 18. get_game_metrics
get_game_metrics_schema = StructType([
    StructField("id", StringType(), True),
    StructField("season", StringType(), True),
    StructField("stage", StringType(), True),
    StructField("competition_id", StringType(), True),
    StructField("topic_id", StringType(), True),
    StructField("groupings", ArrayType(
        StructType([
            StructField("breakdown", ArrayType(
                StructType([
                    StructField("key", StringType(), True),
                    StructField("value", StringType(), True)
                ])
            ), True),
            StructField("metrics", ArrayType(
                StructType([
                    StructField("key", StringType(), True),
                    StructField("value", IntegerType(), True)
                ])
            ), True),
            StructField("unitsplayed", ArrayType(
                StructType([
                    StructField("name", StringType(), True),
                    StructField("value", IntegerType(), True)
                ])
            ), True)
        ])
    ), True)
])

# 19. get_player_metrics
get_player_metrics_schema = StructType([
    StructField("id", StringType(), True),
    StructField("season", StringType(), True),
    StructField("stage", StringType(), True),
    StructField("competition_id", StringType(), True),
    StructField("topic_id", StringType(), True),
    StructField("groupings", ArrayType(
        StructType([
            StructField("breakdown", ArrayType(
                StructType([
                    StructField("key", StringType(), True),
                    StructField("value", StringType(), True)
                ])
            ), True),
            StructField("metrics", ArrayType(
                StructType([
                    StructField("key", StringType(), True),
                    StructField("value", IntegerType(), True)
                ])
            ), True),
            StructField("unitsplayed", ArrayType(
                StructType([
                    StructField("name", StringType(), True),
                    StructField("value", IntegerType(), True)
                ])
            ), True)
        ])
    ), True)
])

# 20. get_team_metrics
get_team_metrics_schema = StructType([
    StructField("season", StringType(), True),
    StructField("stage", StringType(), True),
    StructField("competition_id", StringType(), True),
    StructField("topic_id", StringType(), True),
    StructField("groupings", ArrayType(
        StructType([
            StructField("breakdown", ArrayType(
                StructType([
                    StructField("key", StringType(), True),
                    StructField("value", StringType(), True)
                ])
            ), True),
            StructField("metrics", ArrayType(
                StructType([
                    StructField("key", StringType(), True),
                    StructField("value", IntegerType(), True)
                ])
            ), True),
            StructField("unitsplayed", ArrayType(
                StructType([
                    StructField("name", StringType(), True),
                    StructField("value", IntegerType(), True)
                ])
            ), True)
        ])
    ), True)
])

# 21. get_league_metrics
get_league_metrics_schema = StructType([
    StructField("season", StringType(), True),
    StructField("stage", StringType(), True),
    StructField("competition_id", StringType(), True),
    StructField("topic_id", StringType(), True),
    StructField("groupings", ArrayType(
        StructType([
            StructField("breakdown", ArrayType(
                StructType([
                    StructField("key", StringType(), True),
                    StructField("value", StringType(), True)
                ])
            ), True),
            StructField("metrics", ArrayType(
                StructType([
                    StructField("key", StringType(), True),
                    StructField("value", IntegerType(), True)
                ])
            ), True),
            StructField("unitsplayed", ArrayType(
                StructType([
                    StructField("name", StringType(), True),
                    StructField("value", IntegerType(), True)
                ])
            ), True)
        ])
    ), True)
])

# 22. get_metric_topic_list
get_metric_topic_list_schema = StructType([
    StructField("scope", StringType(), True),
    StructField("topics", ArrayType(
        StructType([
            StructField("id", StringType(), True),
            StructField("name", StringType(), True)
        ])
    ), True)
])


# 23. get_metric_topic
get_metric_topic_schema = StructType([
    StructField("name", StringType(), True),
    StructField("groups", ArrayType(
        StructType([
            StructField("name", StringType(), True),
            StructField("groups", ArrayType(
                StructType([
                    StructField("name", StringType(), True),
                    StructField("metrics", ArrayType(
                        StructType([
                            StructField("key", StringType(), True),
                            StructField("name", StringType(), True),
                            StructField("format", StringType(), True),
                            StructField("directionality", StringType(), True)
                        ])
                    ), True)
                ])
            ), True),
            StructField("metrics", ArrayType(
                StructType([
                    StructField("key", StringType(), True),
                    StructField("name", StringType(), True),
                    StructField("format", StringType(), True),
                    StructField("directionality", StringType(), True)
                ])
            ), True),
            StructField("directionality", StringType(), True)
        ])
    ), True)
])

# 24. get_metric_topic_details
get_metric_topic_details_schema = StructType([
    StructField("scope", StringType(), True),
    StructField("topic_id", StringType(), True),
    StructField("topic", StructType([
        StructField("name", StringType(), True),
        StructField("groups", ArrayType(
            StructType([
                StructField("name", StringType(), True),
                StructField("metrics", ArrayType(
                    StructType([
                        StructField("key", StringType(), True),
                        StructField("name", StringType(), True),
                        StructField("format", StringType(), True),
                        StructField("directionality", StringType(), True)
                    ])
                ), True)
            ])
        ), True)
    ]), True)
])

# 25. get_player_list
get_player_list_schema = StructType([
    StructField("season", StringType(), True),
    StructField("stage", StringType(), True),
    StructField("competition_id", StringType(), True),
    StructField("team_id", StringType(), True),
    StructField("players", ArrayType(
        StructType([
            StructField("id", StringType(), True),
            StructField("first_name", StringType(), True),
            StructField("last_name", StringType(), True),
            StructField("current_team_id", StringType(), True),
            StructField("position", StringType(), True),
            StructField("role", StringType(), True),
            StructField("status", StringType(), True)
        ])
    ), True)
])

# 26. get_player_details
get_player_details_schema = StructType([
    StructField("id", StringType(), True),
    StructField("first_name", StringType(), True),
    StructField("last_name", StringType(), True),
    StructField("known_name", StringType(), True),
    StructField("current_team_id", StringType(), True),
    StructField("position", StringType(), True),
    StructField("position_type", StringType(), True),
    StructField("role", StringType(), True),
    StructField("status", StringType(), True),
    StructField("laterality", StringType(), True),
    StructField("birthdate", StringType(), True),
    StructField("birth_city", StringType(), True),
    StructField("birth_province", StringType(), True),
    StructField("birth_country", StringType(), True),
    StructField("weight", IntegerType(), True),
    StructField("height", IntegerType(), True),
    StructField("jersey_num", StringType(), True),
    StructField("picture_src", StringType(), True)
])