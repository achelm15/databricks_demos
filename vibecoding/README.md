# Apache Iceberg with Polaris and S3

This project demonstrates how to use **PyIceberg** to interact with **Apache Polaris** (an Iceberg REST catalog) and store data in **Amazon S3**.

## Quick Start

**TL;DR - Copy the template files to your Polaris directory:**

```bash
# 1. Copy Docker Compose override
cp vibecoding/docker-compose.override.yml /path/to/polaris/getting-started/jdbc/

# 2. Copy the startup script
cp vibecoding/restart-polaris-with-aws.sh /path/to/polaris/

# 3. Edit the script to add your AWS credentials
nano /path/to/polaris/restart-polaris-with-aws.sh

# 4. Run it
bash /path/to/polaris/restart-polaris-with-aws.sh

# 5. Run the Python script
cd /path/to/databricks_demos
python vibecoding/iceberg.py
```

See the detailed setup instructions below for full context.

---

## What is This Stack?

- **Apache Iceberg**: An open table format for huge analytic datasets. Think of it as a layer on top of Parquet files that adds features like ACID transactions, time travel, and schema evolution.
- **Apache Polaris**: A REST catalog service for Iceberg that manages table metadata (where files are, what the schema is, etc.)
- **PyIceberg**: Python library for reading and writing Iceberg tables
- **Amazon S3**: Object storage where the actual data (Parquet files) is stored

## Architecture

```
┌─────────────────┐
│  Python Script  │  (iceberg.py)
└────────┬────────┘
         │
         │ PyIceberg REST API
         ↓
┌─────────────────┐
│  Polaris Server │  (localhost:8181)
└────────┬────────┘
         │
         │ Manages Metadata
         ↓
┌─────────────────┐
│   PostgreSQL    │  (stores table metadata)
└─────────────────┘

         │ Writes/Reads Data
         ↓
┌─────────────────┐
│   Amazon S3     │  (polaris-iceberg-dev bucket)
└─────────────────┘
```

## Setup Process

### 1. Prerequisites

- Docker and Docker Compose
- Python 3.12+ with conda/venv
- AWS Account with S3 access
- AWS credentials configured

### 2. AWS Setup

#### Create S3 Bucket
```bash
aws s3 mb s3://polaris-iceberg-dev --region us-east-1
```

#### Create IAM Role

1. Go to AWS IAM Console → Roles → Create Role
2. Select "Custom trust policy" and use:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::332745928618:user/YOUR_IAM_USER"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

3. Attach this inline policy to the role:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::polaris-iceberg-dev",
        "arn:aws:s3:::polaris-iceberg-dev/*"
      ]
    }
  ]
}
```

4. Note the role ARN: `arn:aws:iam::332745928618:role/polaris-iceberg-role`

### 3. Install Apache Polaris

```bash
# Clone Polaris repository
git clone https://github.com/apache/polaris.git
cd polaris
```

### 4. Configure Polaris with AWS Credentials

Copy the template override file to your Polaris directory:

```bash
cp vibecoding/docker-compose.override.yml /path/to/polaris/getting-started/jdbc/
```

This file configures Docker Compose to pass AWS credentials to the Polaris container.

### 5. Start Polaris

Use the provided bash script or run manually:

```bash
cd /path/to/polaris

# Export all required environment variables
export ASSETS_PATH=$(pwd)/getting-started/assets/
export QUARKUS_DATASOURCE_JDBC_URL=jdbc:postgresql://postgres:5432/POLARIS
export QUARKUS_DATASOURCE_USERNAME=postgres
export QUARKUS_DATASOURCE_PASSWORD=postgres
export CLIENT_ID=root
export CLIENT_SECRET=s3cr3t
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_REGION=us-east-1

# Start Polaris
docker compose -p polaris \
  -f getting-started/assets/postgres/docker-compose-postgres.yml \
  -f getting-started/jdbc/docker-compose-bootstrap-db.yml \
  -f getting-started/jdbc/docker-compose.yml \
  -f getting-started/jdbc/docker-compose.override.yml \
  up -d

# Wait for startup (about 30 seconds)
sleep 30

# Verify AWS credentials are in the container
docker exec polaris-polaris-1 env | grep AWS
```

Or use the provided script (after updating the path and credentials):
```bash
# Copy the template script from this repo
cp vibecoding/restart-polaris-with-aws.sh /path/to/polaris/

# Edit it to add your AWS credentials and correct paths
nano /path/to/polaris/restart-polaris-with-aws.sh

# Run it
bash /path/to/polaris/restart-polaris-with-aws.sh
```

### 6. Install Python Dependencies

```bash
conda activate your-env  # or use venv
pip install pyiceberg requests pyarrow
```

### 7. Update Configuration in `iceberg.py`

Update these constants with your values:

```python
S3_BUCKET = "s3://polaris-iceberg-dev"  # Your S3 bucket
IAM_ROLE = "arn:aws:iam::332745928618:role/polaris-iceberg-role"  # Your IAM role
```

## Running the Script

```bash
cd /path/to/databricks_demos
python vibecoding/iceberg.py
```

### Expected Output

```
🔑 Obtained access token
📋 Found 1 existing catalog(s):
   - iceberg_s3 (INTERNAL)
✅ Using existing catalog: iceberg_s3
📚 Connected to catalog: polaris (<class 'pyiceberg.catalog.rest.RestCatalog'>)
📋 Available namespaces: [('demo',)]
✅ Granted CATALOG_MANAGE_CONTENT privileges
✅ Created namespace: demo
🗑️  Dropped existing table: demo.users
✅ Created table: demo.users
📍 Table location: s3://polaris-iceberg-dev/demo/users
✅ Inserted 3 rows into demo.users

📊 Table scan results:
[
  [1, 2, 3]
]
[
  ["alice", "bob", "charlie"]
]
[
  ["alice@example.com", "bob@example.com", "charlie@example.com"]
]
[
  [2026-01-28 02:12:46.586340, ...]
]
```

## What the Script Does

1. **Authenticates** with Polaris using OAuth2 client credentials
2. **Creates/Uses a Catalog** - a logical container for tables with S3 storage config
3. **Connects via PyIceberg** - establishes a connection to the REST catalog
4. **Grants Permissions** - ensures the catalog admin role can manage content
5. **Creates a Namespace** - like a database, organizes tables
6. **Creates an Iceberg Table** - defines schema with strongly-typed fields
7. **Inserts Data** - writes sample records using PyArrow
8. **Queries Data** - reads the data back from S3

## File Structure

```
polaris-iceberg-dev/           # S3 bucket
└── demo/                       # namespace
    └── users/                  # table
        ├── metadata/           # table metadata (schema, snapshots)
        │   ├── 00000-xxx.metadata.json
        │   └── snap-xxx.avro
        └── data/               # actual data files (Parquet)
            └── 00000-0-xxx.parquet
```

## Troubleshooting

### Polaris container shows "unhealthy"
This is often misleading. Check if the API is responding:
```bash
curl http://localhost:8181/api/catalog/v1/config
```

### AWS credentials not found
Verify credentials are in the container:
```bash
docker exec polaris-polaris-1 env | grep AWS
```

### S3 permission denied
Ensure your IAM role has the correct permissions and your IAM user can assume the role.

### Schema mismatch errors
PyArrow types must exactly match Iceberg types:
- `IntegerType()` → `pa.int32()`
- `StringType()` → `pa.string()`
- `TimestampType()` → `pa.timestamp('us')`
- Required fields → `nullable=False`

## Key Concepts

### Iceberg Table Format
- **Metadata Layer**: JSON files tracking schema, partitions, snapshots
- **Data Layer**: Parquet files containing actual data
- **Catalog**: Service (Polaris) that keeps track of current table state

### Why Use This Stack?
- **ACID transactions** on S3 data lakes
- **Time travel** - query historical data
- **Schema evolution** - add/rename columns without rewriting data
- **Partition evolution** - change partitioning without migrating data
- **Hidden partitioning** - users don't need to know partition columns

## Resources

- [Apache Iceberg Docs](https://iceberg.apache.org/)
- [Apache Polaris Docs](https://polaris.apache.org/)
- [PyIceberg Docs](https://py.iceberg.apache.org/)
- [Iceberg REST Catalog Spec](https://github.com/apache/iceberg/blob/main/open-api/rest-catalog-open-api.yaml)

## Files in This Project

### Main Files
- **`iceberg.py`** - Main Python script demonstrating Iceberg operations with detailed comments
- **`README.md`** - This comprehensive setup guide

### Template Files (copy to Polaris directory)
- **`restart-polaris-with-aws.sh`** - Helper script to restart Polaris with AWS credentials
- **`docker-compose.override.yml`** - Docker Compose override to inject AWS environment variables

> **Note**: The template files have placeholders for secrets. Update them with your actual AWS credentials before using.

## License

This is demo code. Use at your own risk.
