-- Create a small isolated table, capture its first snapshot, then change it.
CREATE TABLE iceberg.silver.time_travel_demo
WITH (format = 'PARQUET', compression_codec = 'ZSTD') AS
SELECT orderkey, orderdate, line_revenue
FROM iceberg.silver.order_lines
LIMIT 20;

INSERT INTO iceberg.silver.time_travel_demo
SELECT orderkey, orderdate, line_revenue
FROM iceberg.silver.order_lines
WHERE orderkey NOT IN (SELECT orderkey FROM iceberg.silver.time_travel_demo)
LIMIT 5;

SELECT snapshot_id, committed_at, operation
FROM iceberg.silver."time_travel_demo$snapshots"
ORDER BY committed_at;

-- Replace <snapshot_id_before_change> with the earlier ID from the query above.
-- Preview the previous state:
-- SELECT COUNT(*) FROM iceberg.silver.time_travel_demo
-- FOR VERSION AS OF <snapshot_id_before_change>;
-- Permanently restore the table's current state to that snapshot:
-- ALTER TABLE iceberg.silver.time_travel_demo
-- EXECUTE rollback_to_snapshot(<snapshot_id_before_change>);
