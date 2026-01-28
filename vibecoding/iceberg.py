import os
import requests
import pyarrow as pa
from datetime import datetime
from pyiceberg.catalog import load_catalog
from pyiceberg.schema import Schema
from pyiceberg.types import NestedField, StringType, IntegerType, TimestampType

# ============================================================================
# Configuration
# ============================================================================
# Polaris is an Apache Iceberg REST catalog that manages table metadata
POLARIS_URL = "http://localhost:8181"
CLIENT_ID = "root"
CLIENT_SECRET = "s3cr3t"

# S3 configuration for data storage
S3_BUCKET = "s3://polaris-iceberg-dev"
IAM_ROLE = "arn:aws:iam::332745928618:role/polaris-iceberg-role"

# ============================================================================
# Step 1: Authenticate with Polaris using OAuth
# ============================================================================
# Polaris uses OAuth2 client credentials flow for authentication
token_url = f"{POLARIS_URL}/api/catalog/v1/oauth/tokens"
token_data = {
    "grant_type": "client_credentials",
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
    "scope": "PRINCIPAL_ROLE:ALL"
}

token_response = requests.post(token_url, data=token_data)
if token_response.status_code == 200:
    access_token = token_response.json()["access_token"]
    print(f"🔑 Obtained access token")
else:
    print(f"⚠️  Failed to get token: {token_response.status_code} - {token_response.text}")
    exit(1)

# Set up headers for authenticated requests
headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json"
}

# ============================================================================
# Step 2: Get or Create Catalog (Warehouse)
# ============================================================================
# In Polaris, a "catalog" is a logical grouping of tables with shared storage config
# We'll use the Management API to check if a catalog exists, or create one
management_url = f"{POLARIS_URL}/api/management/v1/catalogs"
list_response = requests.get(management_url, headers=headers)

if list_response.status_code == 200:
    catalogs = list_response.json().get("catalogs", [])
    print(f"📋 Found {len(catalogs)} existing catalog(s):")
    for cat in catalogs:
        print(f"   - {cat['name']} ({cat['type']})")
    
    if catalogs:
        # Use the first existing catalog
        warehouse_name = catalogs[0]["name"]
        print(f"✅ Using existing catalog: {warehouse_name}")
    else:
        # Create a new catalog with S3 storage configuration
        warehouse_name = "iceberg_s3"
        warehouse_config = {
            "catalog": {
                "name": warehouse_name,
                "type": "INTERNAL",
                "properties": {"default-base-location": S3_BUCKET},
                "storageConfigInfo": {
                    "storageType": "S3",
                    "allowedLocations": [S3_BUCKET],  # Where data can be written
                    "roleArn": IAM_ROLE  # IAM role for Polaris to assume for S3 access
                }
            }
        }
        
        response = requests.post(management_url, json=warehouse_config, headers=headers)
        if response.status_code == 201:
            print(f"✅ Warehouse '{warehouse_name}' created successfully!")
        else:
            print(f"⚠️  Response: {response.status_code} - {response.text}")
            exit(1)
else:
    print(f"⚠️  Failed to list catalogs: {list_response.status_code} - {list_response.text}")
    warehouse_name = "iceberg_s3"

# ============================================================================
# Step 3: Connect to Catalog using PyIceberg
# ============================================================================
# PyIceberg is a Python library for working with Apache Iceberg tables
# It connects to Polaris via the Iceberg REST Catalog API
catalog = load_catalog(
    "polaris",
    uri=f"{POLARIS_URL}/api/catalog",
    credential=f"{CLIENT_ID}:{CLIENT_SECRET}",
    scope="PRINCIPAL_ROLE:ALL",
    warehouse=warehouse_name
)

print(f"📚 Connected to catalog: {catalog}")
print(f"📋 Available namespaces: {catalog.list_namespaces()}")

# ============================================================================
# Step 4: Grant Permissions (First-Time Setup)
# ============================================================================
# Grant the catalog_admin role permission to manage content in this catalog
# This only needs to run once, but is idempotent (safe to run multiple times)
grant_url = f"{POLARIS_URL}/api/management/v1/catalogs/{warehouse_name}/catalog-roles/catalog_admin/grants"
grants_payload = {"grant": {"type": "catalog", "privilege": "CATALOG_MANAGE_CONTENT"}}
grant_response = requests.put(grant_url, json=grants_payload, headers=headers)

if grant_response.status_code in [200, 201, 204]:
    print(f"✅ Granted CATALOG_MANAGE_CONTENT privileges")
else:
    # 500 error with duplicate key just means permissions already exist - that's fine
    print(f"⚠️  Grant response: {grant_response.status_code} - {grant_response.text}")

# ============================================================================
# Step 5: Create Namespace (Database)
# ============================================================================
# Namespaces are like databases - they organize tables into logical groups
namespace = "demo"
try:
    catalog.create_namespace(namespace)
    print(f"✅ Created namespace: {namespace}")
except Exception as e:
    print(f"ℹ️  Namespace {namespace} already exists or error: {e}")

# ============================================================================
# Step 6: Create Iceberg Table
# ============================================================================
# Drop existing table to start fresh on each run
table_name = f"{namespace}.users"

try:
    catalog.drop_table(table_name)
    print(f"🗑️  Dropped existing table: {table_name}")
except Exception:
    pass  # Table doesn't exist yet - that's fine

# Define the Iceberg table schema
# Iceberg uses strongly-typed schemas with explicit field IDs
schema = Schema(
    NestedField(field_id=1, name="user_id", field_type=IntegerType(), required=True),
    NestedField(field_id=2, name="username", field_type=StringType(), required=True),
    NestedField(field_id=3, name="email", field_type=StringType(), required=False),
    NestedField(field_id=4, name="created_at", field_type=TimestampType(), required=True),
)

# Create the table - Polaris will manage the S3 location automatically
table = catalog.create_table(identifier=table_name, schema=schema)
print(f"✅ Created table: {table_name}")
print(f"📍 Table location: {table.location()}")

# ============================================================================
# Step 7: Insert Data using PyArrow
# ============================================================================
# Iceberg tables store data in Parquet format
# We use PyArrow to create in-memory data that matches our schema exactly

# Define PyArrow schema that matches the Iceberg schema
# IMPORTANT: Types must match exactly (int32 vs int64, nullable flags, etc.)
arrow_schema = pa.schema([
    pa.field("user_id", pa.int32(), nullable=False),
    pa.field("username", pa.string(), nullable=False),
    pa.field("email", pa.string(), nullable=True),
    pa.field("created_at", pa.timestamp('us'), nullable=False)
])

# Create sample data with proper types
data = {
    "user_id": pa.array([1, 2, 3], type=pa.int32()),
    "username": pa.array(["alice", "bob", "charlie"], type=pa.string()),
    "email": pa.array(["alice@example.com", "bob@example.com", "charlie@example.com"], type=pa.string()),
    "created_at": pa.array([datetime.now(), datetime.now(), datetime.now()], type=pa.timestamp('us'))
}

# Convert to Arrow table and append to Iceberg table
arrow_table = pa.table(data, schema=arrow_schema)
table.append(arrow_table)
print(f"✅ Inserted {len(data['user_id'])} rows into {table_name}")

# ============================================================================
# Step 8: Query the Data
# ============================================================================
# Scan the table to read all data back from S3
# Iceberg handles reading Parquet files and returning the data
print(f"\n📊 Table scan results:")
scan = table.scan()
for row in scan.to_arrow():
    print(row)
