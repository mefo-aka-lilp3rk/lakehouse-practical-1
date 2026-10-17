#!/bin/sh
set -eu

until mc alias set local http://object-store:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" >/dev/null 2>&1; do
  echo "Waiting for the S3 object store..."
  sleep 2
done

mc mb --ignore-existing local/lakehouse
mc anonymous set none local/lakehouse
echo "S3 bucket lakehouse is ready."
