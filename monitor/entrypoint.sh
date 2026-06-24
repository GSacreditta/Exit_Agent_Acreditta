#!/usr/bin/env bash
# Cloud Run Job entrypoint. Runs Alembic, then the Monitor.
set -euo pipefail

echo "[entrypoint] running migrations..."
alembic upgrade head

echo "[entrypoint] running monitor..."
exec python -m monitor.main "$@"
