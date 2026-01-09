#!/bin/bash

# This script sets up the MinIO bucket for media storage
# Source environment variables
set -a
[ -f /app/.env ] && . /app/.env
set +a

# Use credentials from environment or fall back to defaults
ACCESS_KEY=${AWS_ACCESS_KEY_ID:-minio}
SECRET_KEY=${AWS_SECRET_ACCESS_KEY:-minio123}

# Wait for MinIO to be ready
echo "Waiting for MinIO to be ready..."
until mc alias set minio http://minio:9000 "$ACCESS_KEY" "$SECRET_KEY"; do
  sleep 5
done
echo "MinIO is ready!"

# Create a bucket for englishapp application
echo "Creating englishapp bucket in MinIO..."
mc mb minio/englishapp || echo "Bucket 'englishapp' already exists."

# Set public read policy for englishapp bucket
echo "Setting public-read policy for englishapp bucket..."
mc anonymous set public minio/englishapp || true

# Set CORS configuration for browser uploads
echo "Setting CORS configuration for englishapp bucket..."
# Create temporary CORS config file
cat > /tmp/cors.json <<'EOF'
[
  {
    "allowedOrigins": ["*"],
    "allowedMethods": ["GET", "HEAD", "PUT", "POST", "DELETE"],
    "allowedHeaders": ["*"],
    "exposeHeaders": ["ETag", "x-amz-version-id"],
    "maxAgeSeconds": 3000
  }
]
EOF

# Apply CORS config
mc cors set minio/englishapp /tmp/cors.json || echo "CORS config already applied or not supported"
echo "✓ MinIO CORS setup is complete."
echo "✓ MinIO englishapp bucket setup is complete."


