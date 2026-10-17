#!/bin/sh
set -eu

cd "$(dirname "$0")/.."

python3 scripts/run_sql.py sql/00_create_schemas.sql
python3 scripts/run_sql.py sql/01_load_bronze.sql
python3 scripts/run_sql.py sql/02_build_silver.sql
python3 scripts/run_sql.py sql/03_build_gold.sql
python3 scripts/verify_q3.py
python3 scripts/run_sql.py sql/04_validate_pipeline.sql
