-- Clean/normalize: trim and uppercase the segment; keep typed TPC-H dates and keys.
-- Enrich: join customers, orders and line items; calculate discounted line revenue.
CREATE TABLE iceberg.silver.order_lines
WITH (format = 'PARQUET', compression_codec = 'ZSTD') AS
SELECT
    o.orderkey,
    CAST(o.orderdate AS DATE) AS orderdate,
    CAST(o.shippriority AS INTEGER) AS shippriority,
    CAST(l.extendedprice AS DECIMAL(18, 2)) AS extendedprice,
    CAST(l.discount AS DECIMAL(5, 2)) AS discount,
    CAST(l.extendedprice * (1 - l.discount) AS DECIMAL(22, 4)) AS line_revenue
FROM iceberg.bronze.customer c
JOIN iceberg.bronze.orders o ON c.custkey = o.custkey
JOIN iceberg.bronze.lineitem l ON l.orderkey = o.orderkey
WHERE UPPER(TRIM(c.mktsegment)) = 'BUILDING'
  AND o.orderdate < DATE '1995-03-15'
  AND l.shipdate > DATE '1995-03-15';
