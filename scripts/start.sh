#!/bin/sh
set -eu
mkdir -p "${EVIDENCE_STORAGE_DIR:-/app/storage/evidence}"
exec uvicorn backend.app.main:app --host 0.0.0.0 --port "${PORT:-10000}" --workers 1 --proxy-headers --forwarded-allow-ips='*'
