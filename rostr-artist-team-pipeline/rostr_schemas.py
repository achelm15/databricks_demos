"""PySpark / Spark-SQL schemas for rostr.cc API responses.

Two payload shapes drive every silver block:

1. **Artist detail** — `GET /v1/artist/{handle}`. ~60 fields including AI-generated
   bio metadata (`ai*`) and social-platform metric snapshots (`spMetric`, `igMetric`,
   etc.). Ingested as `bronze_artists` with `data VARIANT`.

2. **Per-role team list** — `GET /v1/artist/{handle}/team/{ROLE}` for ROLE in
   `MANAGEMENT | AGENCY | RECORD_LABEL | PUBLISHER`. Returns `[{company, team}]`
   where:
     - `company` is the firm — name, role, parent, websites, AI-bio metadata, and
       a `people[]` list of *all* employees at the firm (their full roster).
     - `team[].people[]` is the *artist-specific* sub-roster — i.e. the people
       at this firm actually assigned to this artist. Typically 1–3 people.

   This is the join fabric for the silver layer: one bronze row per (artist,
   role, source_file) is exploded into:
     - silver_companies          (deduped firms)
     - silver_company_people     (all employees of a firm, deduped)
     - silver_artist_company     (M:N artist × company × role)
     - silver_artist_person      (the *artist-specific* people)

The DDL strings below are inlined directly inside `from_json(...)` calls so
each silver block is self-contained — the structs here are the canonical
**reference** version. Mirror sportlogiq_schemas.py.
"""
from __future__ import annotations

from pyspark.sql.types import (
    ArrayType,
    BooleanType,
    DoubleType,
    IntegerType,
    LongType,
    StringType,
    StructField,
    StructType,
)


# -------------------------------------------------------------------- artist
# `/v1/artist/{handle}` — one row per artist in bronze_artists.
# Keep only the fields silver actually projects — drop curated noise like
# avatar blurhashes and entityDisplayOrdering (which is recursive).
ARTIST_SCHEMA = StructType([
    StructField("rostrId",       StringType()),
    StructField("uuid",           StringType()),
    StructField("airtableId",     StringType()),
    StructField("name",           StringType()),
    StructField("artistType",     StringType()),     # 'Solo Act' | 'Group' | ...
    StructField("gender",         StringType()),
    StructField("age",            IntegerType()),
    StructField("birthDate",      StringType()),     # ISO datetime; cast in silver
    StructField("deathDate",      StringType()),
    StructField("location",       StringType()),
    StructField("genres",         ArrayType(StringType())),
    StructField("claimed",        BooleanType()),
    StructField("profileUrl",     StringType()),
    StructField("avatarUrl",      StringType()),
    StructField("bannerUrl",      StringType()),

    # social platforms — URL + snapshot follower/listener metric
    StructField("spUrl",          StringType()),  StructField("spMetric",  LongType()),  # Spotify
    StructField("igUrl",          StringType()),  StructField("igMetric",  LongType()),  # Instagram
    StructField("fbUrl",          StringType()),  StructField("fbMetric",  LongType()),  # Facebook
    StructField("ttUrl",          StringType()),  StructField("ttMetric",  LongType()),  # TikTok
    StructField("ytUrl",          StringType()),  StructField("ytMetric",  LongType()),  # YouTube
    StructField("bitUrl",         StringType()),  StructField("bitMetric", LongType()),  # Bandsintown
    StructField("bitOnTour",      BooleanType()),
    StructField("bitBio",         StringType()),

    # AI-generated bio block — sources are deep links rostr surfaces in the UI
    StructField("aiAboutSection",     StringType()),
    StructField("aiFullBio",          StringType()),
    StructField("aiRealName",         StringType()),
    StructField("aiNationality",      StringType()),
    StructField("aiOriginCity",       StringType()),
    StructField("aiOriginState",      StringType()),
    StructField("aiOriginCountry",    StringType()),
    StructField("aiCurrentCity",      StringType()),
    StructField("aiCurrentState",     StringType()),
    StructField("aiCurrentCountry",   StringType()),
    StructField("aiFormationYear",    IntegerType()),
    StructField("aiFormationType",    StringType()),
    StructField("aiCareerStartDate",  StringType()),
    StructField("aiCareerEndDate",    StringType()),
    StructField("aiBreakupDate",      StringType()),
    StructField("aiGenderSinger",     StringType()),
    StructField("aiGenderGroup",      StringType()),
    StructField("aiRoles",            ArrayType(StringType())),
    StructField("aiDescriptors",      ArrayType(StringType())),
    StructField("aiOtherGroups",      ArrayType(StringType())),
    StructField("aiMembers",          ArrayType(StringType())),
    # External canonical URLs the AI bio surfaced
    StructField("aiOfficialWebsiteUrl", StringType()),
    StructField("aiOfficialStoreUrl",   StringType()),
    StructField("aiAppleMusicUrl",      StringType()),
    StructField("aiSoundcloudUrl",      StringType()),
    StructField("aiTiktokUrl",          StringType()),
    StructField("aiTwitterUrl",         StringType()),
    StructField("aiBandsintownUrl",     StringType()),
    StructField("aiWikipediaUrl",       StringType()),
])


# -------------------------------------------------------------------- company
# Used for the `company` field of every team-by-role payload entry.
COMPANY_SCHEMA = StructType([
    StructField("rostrId",                  StringType()),
    StructField("uuid",                     StringType()),
    StructField("airtableId",               StringType()),
    StructField("name",                     StringType()),
    StructField("role",                     StringType()),     # AGENCY | MANAGEMENT | RECORD_LABEL | PUBLISHER
    StructField("otherRoles",               ArrayType(StringType())),
    StructField("recordLabelType",          StringType()),     # MAJOR | INDIE | null
    StructField("formattedRecordLabelType", StringType()),
    StructField("claimed",                  BooleanType()),
    StructField("genres",                   ArrayType(StringType())),
    StructField("hqLocations",              ArrayType(StringType())),
    StructField("otherLocations",           ArrayType(StringType())),
    StructField("websiteUrl",               StringType()),
    StructField("igUrl",                    StringType()),
    StructField("logoUrlLarge",             StringType()),
    StructField("profileUrl",               StringType()),
    StructField("radarDomain",              StringType()),
    StructField("radarEnabled",             BooleanType()),
    StructField("aiAboutSection",           StringType()),
    StructField("aiYearFounded",            IntegerType()),
    StructField("parentCompany",            StringType()),     # opaque label; recurse not modelled
    StructField("parentCompanyProfileUrl",  StringType()),
])


# -------------------------------------------------------------- company person
# Lightweight person record — appears inside `company.people` (full roster).
COMPANY_PERSON_SCHEMA = StructType([
    StructField("rostrId",     StringType()),
    StructField("airtableId",  StringType()),
    StructField("name",        StringType()),
    StructField("role",        StringType()),     # AGENT | MANAGER | EXECUTIVE | etc.
    StructField("profileUrl",  StringType()),
])


# --------------------------------------------------------------- artist person
# Richer record — appears inside `team[].people[]`, the artist-specific sub-roster.
# Carries email/phone (when published), exec roles, and a back-pointer to the
# company so we can join even after exploding.
ARTIST_PERSON_SCHEMA = StructType([
    StructField("rostrId",            StringType()),
    StructField("uuid",               StringType()),
    StructField("airtableId",         StringType()),
    StructField("name",               StringType()),
    StructField("role",               StringType()),
    StructField("otherRoles",         ArrayType(StringType())),
    StructField("execRoles",          ArrayType(StringType())),
    StructField("genres",             ArrayType(StringType())),
    StructField("email",              StringType()),
    StructField("phone",              StringType()),         # rarely populated, but defined
    StructField("claimed",            BooleanType()),
    StructField("profileUrl",         StringType()),
    StructField("displayOrder",       IntegerType()),
    StructField("companyRostrId",     StringType()),
    StructField("companyName",        StringType()),
    StructField("companyProfileUrl",  StringType()),
    StructField("companyLogoUrl",     StringType()),
])


# Convenience: the per-role payload is `ARRAY<STRUCT<company, team:ARRAY<STRUCT<people>>>>`.
# We don't use a top-level Spark schema for it — instead, silver SQL projects
# `data:` directly off the bronze VARIANT row using inline DDL strings (see
# 03_silver_transformations.ipynb). The structs above are the reference shapes.

ARTIST_DDL = (
    "STRUCT<"
    "rostrId:STRING,uuid:STRING,airtableId:STRING,name:STRING,artistType:STRING,"
    "gender:STRING,age:INT,birthDate:STRING,deathDate:STRING,location:STRING,"
    "genres:ARRAY<STRING>,claimed:BOOLEAN,profileUrl:STRING,avatarUrl:STRING,"
    "bannerUrl:STRING,"
    "spUrl:STRING,spMetric:BIGINT,igUrl:STRING,igMetric:BIGINT,"
    "fbUrl:STRING,fbMetric:BIGINT,ttUrl:STRING,ttMetric:BIGINT,"
    "ytUrl:STRING,ytMetric:BIGINT,bitUrl:STRING,bitMetric:BIGINT,"
    "bitOnTour:BOOLEAN,bitBio:STRING,"
    "aiAboutSection:STRING,aiFullBio:STRING,aiRealName:STRING,"
    "aiNationality:STRING,aiOriginCity:STRING,aiOriginState:STRING,"
    "aiOriginCountry:STRING,aiCurrentCity:STRING,aiCurrentState:STRING,"
    "aiCurrentCountry:STRING,aiFormationYear:INT,aiFormationType:STRING,"
    "aiCareerStartDate:STRING,aiCareerEndDate:STRING,aiBreakupDate:STRING,"
    "aiGenderSinger:STRING,aiGenderGroup:STRING,"
    "aiRoles:ARRAY<STRING>,aiDescriptors:ARRAY<STRING>,"
    "aiOtherGroups:ARRAY<STRING>,aiMembers:ARRAY<STRING>,"
    "aiOfficialWebsiteUrl:STRING,aiOfficialStoreUrl:STRING,"
    "aiAppleMusicUrl:STRING,aiSoundcloudUrl:STRING,aiTiktokUrl:STRING,"
    "aiTwitterUrl:STRING,aiBandsintownUrl:STRING,aiWikipediaUrl:STRING"
    ">"
)

COMPANY_DDL = (
    "STRUCT<"
    "rostrId:STRING,uuid:STRING,airtableId:STRING,name:STRING,role:STRING,"
    "otherRoles:ARRAY<STRING>,recordLabelType:STRING,formattedRecordLabelType:STRING,"
    "claimed:BOOLEAN,genres:ARRAY<STRING>,hqLocations:ARRAY<STRING>,"
    "otherLocations:ARRAY<STRING>,websiteUrl:STRING,igUrl:STRING,"
    "logoUrlLarge:STRING,profileUrl:STRING,radarDomain:STRING,radarEnabled:BOOLEAN,"
    "aiAboutSection:STRING,aiYearFounded:INT,"
    "parentCompany:STRING,parentCompanyProfileUrl:STRING,"
    "people:ARRAY<STRUCT<rostrId:STRING,airtableId:STRING,name:STRING,role:STRING,profileUrl:STRING>>"
    ">"
)

ARTIST_PERSON_DDL = (
    "STRUCT<"
    "rostrId:STRING,uuid:STRING,airtableId:STRING,name:STRING,role:STRING,"
    "otherRoles:ARRAY<STRING>,execRoles:ARRAY<STRING>,genres:ARRAY<STRING>,"
    "email:STRING,phone:STRING,claimed:BOOLEAN,profileUrl:STRING,"
    "displayOrder:INT,companyRostrId:STRING,companyName:STRING,"
    "companyProfileUrl:STRING,companyLogoUrl:STRING"
    ">"
)
