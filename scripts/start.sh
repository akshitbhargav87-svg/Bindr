#!/bin/sh
set -eu
if [ "${EVIDENCE_STORAGE_BACKEND:-local}" = local ]; then
    mkdir -p "${EVIDENCE_STORAGE_DIR:-/app/storage/evidence}"
fi
# Verification/reset links contain one-time codes in the query string. Do not
# reproduce them in application access logs. Cloud ingress log policy is separate.
exec uvicorn backend.app.main:app --host 0.0.0.0 --port "${PORT:-10000}" --workers 1 --proxy-headers --forwarded-allow-ips='*' --no-access-log
