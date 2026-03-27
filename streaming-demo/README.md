# Streaming on the Lakehouse

## The Problem

Every casino generates massive amounts of real-time data — slot machine plays, table game outcomes, player loyalty events, IoT from the gaming floor. Today, most organizations pipe this through Kafka (or a similar message bus) into separate batch and streaming systems, each with their own APIs, governance models, and operational complexity.

This demo shows two approaches to getting that streaming data into the Databricks Lakehouse — and how the newest option (Zerobus Ingest) can eliminate the message bus entirely for single-destination flows.

## Who This Is For

Data leaders and architects evaluating how Databricks handles streaming workloads. Non-technical enough to present to stakeholders, with enough working code to run live.

## What's Inside

Two side-by-side demos using the **same synthetic casino gaming data** (same schema, same 500 events) so you can directly compare the approaches.

### Part 1: Structured Streaming (`01-structured-streaming/`)

**The established approach.** Files land in cloud storage → Auto Loader picks them up as a stream → Bronze → Silver → Analytics.

This is the same pattern you'd use with Kafka: swap `cloudFiles` for `kafka` in the read and everything downstream stays identical (the notebooks show this side-by-side).

| Notebook | What It Does |
|----------|-------------|
| `00_verify_connection` | Confirm Databricks Connect (serverless) and create the target schema |
| `01_generate_casino_data` | Generate 500 synthetic slot machine events as JSON files in a UC Volume |
| `02_streaming_ingestion` | Auto Loader streams files into a Bronze Delta table (+ Kafka equivalent shown) |
| `03_streaming_transformations` | Bronze → Silver: bet tiers, net outcomes, win/loss flags |
| `04_streaming_analytics` | Revenue by floor, top machines, win/loss by game type |

### Part 2: Zerobus Ingest (`02-zerobus-ingest/`)

**The new approach (GA Feb 2026).** Push events directly from the source to the Lakehouse via the Zerobus Python SDK (gRPC) — no Kafka, no file staging, no intermediate infrastructure.

| Notebook | What It Does |
|----------|-------------|
| `00_verify_connection` | Verify Databricks Connect + Zerobus SDK installed + env vars set |
| `01_create_target_table` | Create target Delta table (same schema as Part 1) + service principal grants |
| `02_push_casino_events` | Push 500 events via `ZerobusSdk` — gRPC stream direct to Delta table |
| `03_query_and_compare` | Same analytics as Part 1 + side-by-side comparison table |

> **Note:** Zerobus also offers a **REST API** (currently in Beta) for environments where
> installing the gRPC SDK isn't practical — think edge devices, serverless functions, or
> webhook-driven flows. Contact your Databricks account team for access and enablement details.

### When to Use Which

| | **Structured Streaming** | **Zerobus Ingest** |
|---|---|---|
| **How data arrives** | Files in cloud storage or Kafka topic | Pushed directly via gRPC SDK |
| **Infrastructure needed** | Storage + Auto Loader (or Kafka broker) | Just the Zerobus endpoint |
| **Latency** | Seconds to minutes (trigger interval) | Sub-5 seconds |
| **Processing model** | Full Spark — transforms, joins, aggregations in the stream | Ingestion only — transform after landing |
| **Best for** | Complex ETL pipelines, multi-step transforms | High-volume event push (IoT, telemetry, clickstream, gaming) |
| **Kafka relationship** | Reads from Kafka as a source | Can replace Kafka for single-destination flows |

## Setup

```bash
# Uses existing demo-env conda environment
conda activate demo-env

cp .env.example .env
# Fill in your Databricks workspace details
```

For **Part 2 (Zerobus)**, you also need:
1. `pip install databricks-zerobus-ingest-sdk` (gRPC-based SDK)
2. A service principal: Settings → Identity and Access → Service principals → Add → Generate OAuth secret
3. Add `ZEROBUS_SERVER_ENDPOINT`, `ZEROBUS_CLIENT_ID`, `ZEROBUS_CLIENT_SECRET` to `.env`

## Run Order

**Part 1:** `00` → `01` → `02` → `03` → `04`
**Part 2:** `00` → `01` → `02` → `03`

Both parts write to the same `streaming_demo` schema in Unity Catalog.

## Re-running / Reset

To re-run the demo cleanly, uncomment the reset cell at the bottom of
`01-structured-streaming/00_verify_connection.ipynb`. It drops all tables,
the volume (including checkpoints), and recreates the schema. This covers
both Part 1 and Part 2 since they share the same schema.

The reset drops: `slot_events_bronze`, `slot_events_silver`, `slot_events_zerobus`,
the `casino_raw_events` volume (which contains source files and Auto Loader
checkpoints), and recreates the `streaming_demo` schema.

After reset, re-run Part 1 (`00` → `04`) then Part 2 (`00` → `03`) as normal.

## Key Takeaways

1. **Streaming on Databricks is unified** — the same Spark engine handles both batch and streaming with identical APIs
2. **Auto Loader makes file-based streaming simple** — no custom bookkeeping, automatic schema inference, exactly-once processing
3. **Kafka fits right in** — if you already have Kafka, it's a 2-line change from file-based to Kafka-based streaming
4. **Zerobus Ingest eliminates the message bus** — for flows where the Lakehouse is the sole destination, push directly and skip the intermediate infrastructure
5. **All data is governed** — both approaches land in Unity Catalog with full lineage, access controls, and audit

## Data Disclaimer

All data in this demo is **synthetic** — generated with Faker and random seeds. It does not represent any real casino, player, or organization.
