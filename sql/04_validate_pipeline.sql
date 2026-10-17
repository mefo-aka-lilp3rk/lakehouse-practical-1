-- Row counts for the report.
SELECT 'bronze.customer' AS table_name, COUNT(*) AS row_count FROM iceberg.bronze.customer
UNION ALL
SELECT 'bronze.orders', COUNT(*) FROM iceberg.bronze.orders
UNION ALL
SELECT 'bronze.lineitem', COUNT(*) FROM iceberg.bronze.lineitem
UNION ALL
SELECT 'silver.order_lines', COUNT(*) FROM iceberg.silver.order_lines
UNION ALL
SELECT 'gold.q3_shipping_priority', COUNT(*) FROM iceberg.gold.q3_shipping_priority;

-- Check the Gold result.
SELECT orderkey, revenue, orderdate, shippriority
FROM iceberg.gold.q3_shipping_priority
ORDER BY revenue DESC;

-- Physical file sizes in bytes, grouped by table.
SELECT 'bronze.customer' AS table_name, COALESCE(SUM(file_size_in_bytes), 0) AS size_bytes FROM iceberg.bronze."customer$files"
UNION ALL
SELECT 'bronze.orders', COALESCE(SUM(file_size_in_bytes), 0) FROM iceberg.bronze."orders$files"
UNION ALL
SELECT 'bronze.lineitem', COALESCE(SUM(file_size_in_bytes), 0) FROM iceberg.bronze."lineitem$files"
UNION ALL
SELECT 'silver.order_lines', COALESCE(SUM(file_size_in_bytes), 0) FROM iceberg.silver."order_lines$files"
UNION ALL
SELECT 'gold.q3_shipping_priority', COALESCE(SUM(file_size_in_bytes), 0) FROM iceberg.gold."q3_shipping_priority$files";
