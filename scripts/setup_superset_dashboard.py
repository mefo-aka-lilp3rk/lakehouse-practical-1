#!/usr/bin/env python3
"""Create the Superset dataset, table chart, and dashboard for the Gold Q3 mart."""

from __future__ import annotations

import http.cookiejar
import json
import os
import shlex
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE_URL = os.environ.get("SUPERSET_URL", "http://localhost:8088").rstrip("/")
USERNAME = os.environ.get("SUPERSET_ADMIN_USERNAME", "admin")


def env_file_value(name: str) -> str | None:
    env_file = ROOT / ".env"
    if not env_file.exists():
        return None

    for line in env_file.read_text(encoding="utf-8").splitlines():
        try:
            parts = shlex.split(line, comments=True)
        except ValueError:
            continue
        if parts and parts[0].startswith(f"{name}="):
            return parts[0].split("=", 1)[1]
    return None


PASSWORD = (
    os.environ.get("SUPERSET_ADMIN_PASSWORD")
    or env_file_value("SUPERSET_ADMIN_PASSWORD")
    or "local-superset-password"
)


class SupersetClient:
    def __init__(self) -> None:
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())
        )
        login = self._request(
            "POST",
            "/api/v1/security/login",
            {
                "username": USERNAME,
                "password": PASSWORD,
                "provider": "db",
                "refresh": True,
            },
            authenticated=False,
        )
        self.token = login["access_token"]
        csrf = self._request("GET", "/api/v1/security/csrf_token/")
        self.csrf_token = csrf["result"]

    def _request(
        self,
        method: str,
        endpoint: str,
        payload: dict | None = None,
        *,
        authenticated: bool = True,
    ) -> dict:
        headers = {"Accept": "application/json"}
        if payload is not None:
            headers["Content-Type"] = "application/json"
        if authenticated and hasattr(self, "token"):
            headers["Authorization"] = f"Bearer {self.token}"
        if method != "GET" and authenticated and hasattr(self, "csrf_token"):
            headers["X-CSRFToken"] = self.csrf_token
            headers["Referer"] = BASE_URL

        body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode()
        request = urllib.request.Request(
            BASE_URL + endpoint, data=body, headers=headers, method=method
        )
        try:
            with self.opener.open(request, timeout=30) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            details = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Superset API {method} {endpoint} failed: {details}") from error
        except urllib.error.URLError as error:
            raise RuntimeError(f"Cannot reach Superset at {BASE_URL}: {error.reason}") from error

    def list_items(self, endpoint: str) -> list[dict]:
        return self._request("GET", f"/api/v1/{endpoint}").get("result", [])

    def create(self, endpoint: str, payload: dict) -> dict:
        return self._request("POST", f"/api/v1/{endpoint}", payload).get("result", {})


def main() -> None:
    client = SupersetClient()

    database = next(
        (item for item in client.list_items("database/") if item.get("database_name") == "Trino Iceberg"),
        None,
    )
    if database is None:
        raise RuntimeError("Superset database 'Trino Iceberg' is missing; add the Trino connection first.")

    dataset = next(
        (
            item
            for item in client.list_items("dataset/")
            if item.get("schema") == "gold"
            and item.get("table_name") == "q3_shipping_priority"
        ),
        None,
    )
    if dataset is None:
        dataset = client.create(
            "dataset/",
            {
                "database": database["id"],
                "schema": "gold",
                "table_name": "q3_shipping_priority",
            },
        )

    chart = next(
        (
            item
            for item in client.list_items("chart/")
            if item.get("slice_name") == "Gold — Q3 Shipping Priority"
        ),
        None,
    )
    if chart is None:
        params = {
            "datasource": f"{dataset['id']}__table",
            "viz_type": "table",
            "query_mode": "raw",
            "all_columns": ["orderkey", "revenue", "orderdate", "shippriority"],
            "order_by_cols": ['["revenue", false]'],
            "row_limit": 10,
            "server_pagination": False,
            "include_search": True,
            "table_timestamp_format": "smart_date",
            "show_cell_bars": True,
        }
        chart = client.create(
            "chart/",
            {
                "slice_name": "Gold — Q3 Shipping Priority",
                "viz_type": "table",
                "datasource_id": dataset["id"],
                "datasource_type": "table",
                "params": json.dumps(params, ensure_ascii=False),
            },
        )

    dashboard = next(
        (
            item
            for item in client.list_items("dashboard/")
            if item.get("slug") == "tpch-q3-gold"
        ),
        None,
    )
    if dashboard is None:
        position = {
            "DASHBOARD_VERSION_KEY": "v2",
            "ROOT_ID": {"type": "ROOT", "id": "ROOT_ID", "children": ["GRID_ID"]},
            "GRID_ID": {
                "type": "GRID",
                "id": "GRID_ID",
                "children": ["ROW-1"],
                "parents": ["ROOT_ID"],
            },
            "ROW-1": {
                "type": "ROW",
                "id": "ROW-1",
                "children": ["CHART-1"],
                "parents": ["ROOT_ID", "GRID_ID"],
            },
            "CHART-1": {
                "type": "CHART",
                "id": "CHART-1",
                "children": [],
                "parents": ["ROOT_ID", "GRID_ID", "ROW-1"],
                "meta": {"width": 12, "height": 50, "chartId": chart["id"]},
            },
        }
        dashboard = client.create(
            "dashboard/",
            {
                "dashboard_title": "TPC-H Q3 — Gold",
                "slug": "tpch-q3-gold",
                "published": True,
                "position_json": json.dumps(position, ensure_ascii=False),
                "json_metadata": "{}",
            },
        )

    print(f"Dataset: {BASE_URL}/explore/?dataset_type=table&dataset_id={dataset['id']}")
    print(f"Dashboard: {BASE_URL}/superset/dashboard/{dashboard['id']}/")
    print("The dashboard table uses Gold fields and sorts the ten Q3 orders by revenue descending.")


if __name__ == "__main__":
    main()
