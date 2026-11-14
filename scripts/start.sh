#!/bin/sh
set -eu
if [ "${EVIDENCE_STORAGE_BACKEND:-local}" = local ]; then
    mkdir -p "${EVIDENCE_STORAGE_DIR:-/app/storage/evidence}"
fi
exec uvicorn backend.app.main:app --host 0.0.0.0 --port "${PORT:-10000}" --workers 1 --proxy-headers --forwarded-allow-ips='*'
