#!/usr/bin/env bash
# Runs once, every time this image's container starts — for BOTH services
# built from it (the API and the Celery worker; see Dockerfile's top
# comment and docker-compose.yml). Keeping migrations here rather than as a
# separate one-shot compose service means `docker compose up` alone is a
# genuinely complete "clone and run" path for someone grading or demoing
# this project: no second command to remember, no manual `alembic upgrade
# head` step documented in a README that's easy to skip.
#
# `alembic upgrade head` is idempotent — re-running it against an
# already-current schema is a no-op — so doing this unconditionally on
# every container start (API AND worker) is safe, not just on a "first
# run". That also means the worker can be started on its own, independent
# of the API container's startup order, without needing its own
# migration logic.
set -euo pipefail

echo "[entrypoint] Waiting for the database to accept connections..."
# docker-compose's `depends_on: postgres: condition: service_healthy`
# already blocks container start until `pg_isready` succeeds — this loop is
# a second, cheap line of defense against the narrow race where Postgres
# accepts TCP connections a moment before it's actually ready to run DDL,
# rather than a real wait-for-postgres implementation.
attempt=0
until python -c "
from app.core.config import settings
from sqlalchemy import create_engine
create_engine(settings.DATABASE_URL).connect().close()
" 2>/dev/null; do
    attempt=$((attempt + 1))
    if [ "$attempt" -ge 30 ]; then
        echo "[entrypoint] Database never became reachable after 30 attempts. Giving up."
        exit 1
    fi
    sleep 1
done

echo "[entrypoint] Running database migrations (alembic upgrade head)..."
alembic upgrade head

echo "[entrypoint] Migrations complete. Starting: $*"
exec "$@"
