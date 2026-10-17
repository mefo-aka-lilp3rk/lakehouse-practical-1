-- Isolated example so the production Silver table is not changed.
CREATE TABLE iceberg.silver.schema_evolution_demo
WITH (format = 'PARQUET', compression_codec = 'ZSTD') AS
SELECT orderkey, orderdate, shippriority
FROM iceberg.silver.order_lines
LIMIT 20;

ALTER TABLE iceberg.silver.schema_evolution_demo
ADD COLUMN revenue_band VARCHAR;

SELECT orderkey, orderdate, shippriority, revenue_band
FROM iceberg.silver.schema_evolution_demo
ORDER BY orderkey;
