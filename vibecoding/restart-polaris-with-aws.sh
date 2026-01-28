#!/bin/bash

# ==============================================================================
# Restart Apache Polaris with AWS Credentials
# ==============================================================================
# This script stops any running Polaris containers and restarts them with
# AWS credentials properly configured for S3 access.
#
# Usage:
#   1. Update the AWS credentials below
#   2. Run: bash restart-polaris-with-aws.sh
# ==============================================================================

# Navigate to Polaris directory
# UPDATE THIS PATH to where you cloned the Polaris repository
POLARIS_DIR="/path/to/polaris"
cd $POLARIS_DIR

echo "Stopping existing Polaris containers..."
docker compose -p polaris \
  -f getting-started/assets/postgres/docker-compose-postgres.yml \
  -f getting-started/jdbc/docker-compose-bootstrap-db.yml \
  -f getting-started/jdbc/docker-compose.yml \
  -f getting-started/jdbc/docker-compose.override.yml \
  down

# ==============================================================================
# Environment Variables
# ==============================================================================
# Polaris configuration
export ASSETS_PATH=$(pwd)/getting-started/assets/
export QUARKUS_DATASOURCE_JDBC_URL=jdbc:postgresql://postgres:5432/POLARIS
export QUARKUS_DATASOURCE_USERNAME=postgres
export QUARKUS_DATASOURCE_PASSWORD=postgres
export CLIENT_ID=root
export CLIENT_SECRET=s3cr3t

# AWS Credentials - REPLACE THESE WITH YOUR ACTUAL CREDENTIALS
# You can get these from AWS IAM Console → Users → Security credentials
export AWS_ACCESS_KEY_ID=YOUR_AWS_ACCESS_KEY_ID
export AWS_SECRET_ACCESS_KEY=YOUR_AWS_SECRET_ACCESS_KEY
export AWS_REGION=us-east-1  # Change to your bucket's region

echo "Starting Polaris with AWS credentials..."

docker compose -p polaris \
  -f getting-started/assets/postgres/docker-compose-postgres.yml \
  -f getting-started/jdbc/docker-compose-bootstrap-db.yml \
  -f getting-started/jdbc/docker-compose.yml \
  -f getting-started/jdbc/docker-compose.override.yml \
  up -d

echo "Waiting for Polaris to start..."
sleep 30

echo "Verifying AWS credentials in container..."
docker exec polaris-polaris-1 env | grep AWS

if [ $? -eq 0 ]; then
  echo ""
  echo "✅ AWS credentials are set in Polaris container!"
  echo ""
  echo "Now run your Python script:"
  echo "cd /path/to/databricks_demos"
  echo "python vibecoding/iceberg.py"
else
  echo ""
  echo "⚠️  AWS credentials NOT found in container. Something went wrong."
  echo "Check that the override file exists at:"
  echo "$POLARIS_DIR/getting-started/jdbc/docker-compose.override.yml"
fi
