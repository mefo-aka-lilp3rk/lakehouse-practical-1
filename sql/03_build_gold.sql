-- Business-facing Q3 result: revenue by qualifying order, top ten.
CREATE TABLE iceberg.gold.q3_shipping_priority
WITH (format = 'PARQUET', compression_codec = 'ZSTD') AS
SELECT
    orderkey,
    SUM(line_revenue) AS revenue,
    orderdate,
    shippriority
FROM iceberg.silver.order_lines
GROUP BY orderkey, orderdate, shippriority
ORDER BY revenue DESC
LIMIT 10;
