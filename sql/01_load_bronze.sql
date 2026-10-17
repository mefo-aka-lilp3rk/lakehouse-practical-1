-- Scale factor: replace sf1 with the value selected for the report.
-- Keep only columns required by the assigned Q3 query to limit local storage.

CREATE TABLE iceberg.bronze.customer
WITH (format = 'PARQUET', compression_codec = 'ZSTD') AS
SELECT custkey, mktsegment
FROM tpch.sf1.customer;

CREATE TABLE iceberg.bronze.orders
WITH (format = 'PARQUET', compression_codec = 'ZSTD') AS
SELECT orderkey, custkey, orderdate, shippriority
FROM tpch.sf1.orders;

CREATE TABLE iceberg.bronze.lineitem
WITH (format = 'PARQUET', compression_codec = 'ZSTD') AS
SELECT orderkey, extendedprice, discount, shipdate
FROM tpch.sf1.lineitem;
