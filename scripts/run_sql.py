#!/usr/bin/env python3
"""Run a SQL file through the Trino CLI inside the Compose container."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("sql_file")
    parser.add_argument("--scale", default=os.environ.get("SCALE_FACTOR", "sf1"))
    args = parser.parse_args()

    if not args.scale.startswith("sf") or not args.scale[2:].isdigit():
        parser.error("--scale must look like sf1, sf10, ...")

    sql = Path(args.sql_file).read_text(encoding="utf-8")
    sql = sql.replace("tpch.sf1.", f"tpch.{args.scale}.")
    command = [
        "docker", "exec", "-i", "lakehouse-trino", "trino",
        "--server", "http://localhost:8080", "--output-format", "CSV_HEADER",
    ]
    result = subprocess.run(command, input=sql, text=True, check=False)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
