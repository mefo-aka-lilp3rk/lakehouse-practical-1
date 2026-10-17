#!/usr/bin/env python3
"""Compare the Iceberg Gold table with the assigned Q3 over TPC-H sf1."""

from __future__ import annotations

import csv
import io
import subprocess
from decimal import Decimal, ROUND_HALF_UP


QUERIES = (
    """SELECT l.orderkey, sum(l.extendedprice * (1 - l.discount)) AS revenue,
              o.orderdate, o.shippriority
       FROM tpch.sf1.customer c
       JOIN tpch.sf1.orders o ON c.custkey = o.custkey
       JOIN tpch.sf1.lineitem l ON l.orderkey = o.orderkey
       WHERE c.mktsegment = 'BUILDING'
         AND o.orderdate < DATE '1995-03-15'
         AND l.shipdate > DATE '1995-03-15'
       GROUP BY l.orderkey, o.orderdate, o.shippriority
       ORDER BY revenue DESC
       LIMIT 10""",
    """SELECT orderkey, revenue, orderdate, shippriority
       FROM iceberg.gold.q3_shipping_priority
       ORDER BY revenue DESC""",
)


def query(sql: str) -> list[list[str]]:
    result = subprocess.run(
        [
            "docker", "exec", "-i", "lakehouse-trino", "trino",
            "--server", "http://localhost:8080", "--output-format", "CSV_HEADER",
            "--execute", sql,
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(result.stderr)
    return list(csv.reader(io.StringIO(result.stdout)))[1:]


def normalize(rows: list[list[str]]) -> list[tuple[str, str, str, str]]:
    return [
        (key, str(Decimal(revenue).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)), date, priority)
        for key, revenue, date, priority in rows
    ]


def main() -> None:
    expected, actual = (normalize(query(sql)) for sql in QUERIES)
    if expected != actual:
        raise SystemExit(f"Gold does not match TPC-H Q3.\nexpected={expected}\nactual={actual}")
    print(f"Q3 verification passed: {len(actual)} rows match; revenue compared to 4 decimal places.")


if __name__ == "__main__":
    main()
