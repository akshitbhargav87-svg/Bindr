#!/bin/sh
# Optional Track B CI entry point for A to incorporate into shared CI.
set -eu
track_b_root=$(CDPATH='' cd -- "$(dirname -- "$0")/../.." && pwd)
cd "$track_b_root"
AI_PROVIDER=mock ENVIRONMENT=development AUTH_PROVIDER=anonymous PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest backend/app/tests/test_ai_adapter.py backend/app/tests/test_intelligence_*.py -q
npm --prefix frontend run check:track-b
npm --prefix frontend run build
