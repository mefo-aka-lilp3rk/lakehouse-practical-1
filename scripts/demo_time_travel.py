#!/usr/bin/env python3
"""Demonstrate an Iceberg snapshot restore on an isolated demo table."""

from __future__ import annotations

import csv
import io
import subprocess


CONTAINER = "lakehouse-trino"
TABLE = "iceberg.silver.time_travel_demo"


def query(sql: str) -> list[list[str]]:
    result = subprocess.run(
        [
            "docker",
            "exec",
            CONTAINER,
            "trino",
            "--server",
            "http://localhost:8080",
            "--output-format",
            "CSV_HEADER",
            "--execute",
            sql,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return list(csv.reader(io.StringIO(result.stdout)))


def scalar(sql: str) -> str:
    rows = query(sql)
    if len(rows) != 2 or len(rows[1]) != 1:
        raise RuntimeError(f"Expected one scalar result, got: {rows!r}")
    return rows[1][0]


def main() -> None:
    query(f"DROP TABLE IF EXISTS {TABLE}")
    query(
        f"""CREATE TABLE {TABLE}
        WITH (format = 'PARQUET', compression_codec = 'ZSTD') AS
        SELECT orderkey, orderdate, line_revenue
        FROM iceberg.silver.order_lines
        LIMIT 20"""
    )

    snapshot_id = scalar(
        'SELECT snapshot_id FROM iceberg.silver."time_travel_demo$snapshots" '
        "ORDER BY committed_at DESC LIMIT 1"
    )
    query(
        f"""INSERT INTO {TABLE}
        SELECT orderkey, orderdate, line_revenue
        FROM iceberg.silver.order_lines
        WHERE orderkey NOT IN (SELECT orderkey FROM {TABLE})
        LIMIT 5"""
    )

    historical_count = int(
        scalar(f"SELECT COUNT(*) FROM {TABLE} FOR VERSION AS OF {snapshot_id}")
    )
    changed_count = int(scalar(f"SELECT COUNT(*) FROM {TABLE}"))
    query(f"ALTER TABLE {TABLE} EXECUTE rollback_to_snapshot({snapshot_id})")
    restored_count = int(scalar(f"SELECT COUNT(*) FROM {TABLE}"))

    if (historical_count, changed_count, restored_count) != (20, 25, 20):
        raise RuntimeError(
            "Unexpected snapshot counts: "
            f"historical={historical_count}, changed={changed_count}, restored={restored_count}"
        )

    print(f"Snapshot before insert: {snapshot_id}")
    print(f"Rows at snapshot: {historical_count}; rows after insert: {changed_count}")
    print(f"Rows after rollback_to_snapshot: {restored_count}")


if __name__ == "__main__":
    main()
