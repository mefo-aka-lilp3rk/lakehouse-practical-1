#!/bin/sh
set -eu

request_status() {
  url="$1"
  shift
  curl --silent --show-error --retry 10 --retry-all-errors --retry-delay 2 \
    -o /tmp/lakekeeper-response.json -w '%{http_code}' "$@" "$url"
}

bootstrap_status="$(request_status http://lakekeeper:8181/management/v1/bootstrap \
  -X POST -H 'Content-Type: application/json' \
  -d '{"accept-terms-of-use":true}')"
case "$bootstrap_status" in
  2*) ;;
  409) echo "Lakekeeper is already bootstrapped." ;;
  *)
    if grep -q 'CatalogAlreadyBootstrapped' /tmp/lakekeeper-response.json; then
      echo "Lakekeeper is already bootstrapped."
    else
      cat /tmp/lakekeeper-response.json; echo "Lakekeeper bootstrap failed: HTTP $bootstrap_status" >&2; exit 1
    fi
    ;;
esac

warehouses_status="$(request_status http://lakekeeper:8181/management/v1/warehouse)"
if [ "$warehouses_status" != "200" ]; then
  cat /tmp/lakekeeper-response.json; echo "Lakekeeper warehouse lookup failed: HTTP $warehouses_status" >&2; exit 1
fi

if grep -Eq '"name"[[:space:]]*:[[:space:]]*"demo"' /tmp/lakekeeper-response.json; then
  echo "Lakekeeper warehouse demo already exists."
else
  sed -e "s/__S3_ACCESS_KEY__/${S3_ACCESS_KEY}/g" \
    -e "s/__S3_SECRET_KEY__/${S3_SECRET_KEY}/g" \
    /config/create-warehouse.json > /tmp/create-warehouse.json
  warehouse_status="$(request_status http://lakekeeper:8181/management/v1/warehouse \
    -X POST -H 'Content-Type: application/json' \
    --data-binary @/tmp/create-warehouse.json)"
  case "$warehouse_status" in
    2*) echo "Lakekeeper warehouse demo is ready." ;;
    *) cat /tmp/lakekeeper-response.json; echo "Lakekeeper warehouse creation failed: HTTP $warehouse_status" >&2; exit 1 ;;
  esac
fi
