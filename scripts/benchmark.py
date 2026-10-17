#!/usr/bin/env python3
"""Compare Iceberg Bronze writes and Q3 reads for Parquet/ORC and GZIP/ZSTD."""

from __future__ import annotations

import csv
import io
import statistics
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "benchmark" / "results.csv"
SCALE = "sf1"
FORMATS = ("PARQUET", "ORC")
CODECS = ("GZIP", "ZSTD")
SOURCES = {
    "customer": "SELECT custkey, mktsegment FROM tpch.{scale}.customer",
    "orders": "SELECT orderkey, custkey, orderdate, shippriority FROM tpch.{scale}.orders",
    "lineitem": "SELECT orderkey, extendedprice, discount, shipdate FROM tpch.{scale}.lineitem",
}


def trino(sql: str, *, output_format: str = "CSV_HEADER") -> str:
    result = subprocess.run(
        ["docker", "exec", "-i", "lakehouse-trino", "trino", "--server",
         "http://localhost:8080", "--output-format", output_format, "--execute", sql],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(f"Trino failed for SQL:\n{sql}\n{result.stderr}")
    return result.stdout.strip()


def scalar(sql: str) -> str:
    rows = list(csv.reader(io.StringIO(trino(sql))))
    if len(rows) < 2:
        raise RuntimeError(f"Expected a result row, got: {rows!r}")
    return rows[-1][0]


def q3(schema: str) -> str:
    return f"""SELECT l.orderkey,
       sum(l.extendedprice * (1 - l.discount)) AS revenue,
       o.orderdate,
       o.shippriority
FROM iceberg.{schema}.customer c
JOIN iceberg.{schema}.orders o ON c.custkey = o.custkey
JOIN iceberg.{schema}.lineitem l ON l.orderkey = o.orderkey
WHERE c.mktsegment = 'BUILDING'
  AND o.orderdate < DATE '1995-03-15'
  AND l.shipdate > DATE '1995-03-15'
GROUP BY l.orderkey, o.orderdate, o.shippriority
ORDER BY revenue DESC
LIMIT 10"""


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    results = []
    expected = None

    for file_format in FORMATS:
        for codec in CODECS:
            schema = f"bench_{file_format.lower()}_{codec.lower()}"
            trino(f"DROP SCHEMA IF EXISTS iceberg.{schema} CASCADE")
            trino(f"CREATE SCHEMA iceberg.{schema}")

            write_seconds = 0.0
            for table_name, select_sql in SOURCES.items():
                sql = (
                    f"CREATE TABLE iceberg.{schema}.{table_name} "
                    f"WITH (format = '{file_format}', compression_codec = '{codec}') "
                    f"AS {select_sql.format(scale=SCALE)}"
                )
                started = time.perf_counter()
                trino(sql, output_format="NULL")
                write_seconds += time.perf_counter() - started

            size_sql = " UNION ALL ".join(
                f"SELECT file_size_in_bytes FROM iceberg.{schema}.\"{table}$files\""
                for table in SOURCES
            )
            size_bytes = int(scalar(f"SELECT COALESCE(SUM(file_size_in_bytes), 0) FROM ({size_sql}) AS files"))

            query = q3(schema)
            trino(query, output_format="NULL")  # Warm the engine and file metadata cache.
            query_seconds = []
            q3_rows = None
            for _ in range(3):
                started = time.perf_counter()
                output = trino(query)
                query_seconds.append(time.perf_counter() - started)
                rows = list(csv.reader(io.StringIO(output)))
                current = rows[1:]
                if expected is None:
                    expected = current
                elif current != expected:
                    raise RuntimeError(f"Q3 result differs for {file_format}/{codec}")
                q3_rows = len(current)

            results.append({
                "format": file_format,
                "compression": codec,
                "bronze_write_seconds": f"{write_seconds:.3f}",
                "bronze_size_bytes": size_bytes,
                "q3_query_median_seconds": f"{statistics.median(query_seconds):.3f}",
                "q3_rows": q3_rows,
                "scale": SCALE,
            })
            print(results[-1])

    with OUT.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=results[0].keys(), lineterminator="\n")
        writer.writeheader()
        writer.writerows(results)
    print(f"Saved benchmark results to {OUT}")


if __name__ == "__main__":
    main()
