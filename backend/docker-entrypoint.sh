#!/bin/sh
set -e

python scripts/seed_default_users.py

exec uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers "${WEB_CONCURRENCY:-2}" \
  --timeout-keep-alive "${UVICORN_TIMEOUT_KEEP_ALIVE:-30}"
