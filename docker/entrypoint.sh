#!/bin/sh
set -eu

# Wait for the database (if DATABASE_URL points to a host:port) and create
# tables idempotently *before* uvicorn binds the port. This collapses the
# startup race where TCP accepts connections while lifespan is still running
# create_all, which manifests as "connection reset" on the very first curl
# after `compose up`.
#
# Alembic stays installed for manual migration runs:
#   docker compose exec app alembic upgrade head

python <<'PY'
import os, sys, time
from urllib.parse import urlparse

url = os.environ.get("DATABASE_URL", "")
if url.startswith(("postgresql", "postgres")):
    import socket
    p = urlparse(url.replace("postgresql+psycopg2", "postgresql"))
    host, port = p.hostname or "db", p.port or 5432
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=2):
                break
        except OSError:
            time.sleep(0.5)
    else:
        print(f"[entrypoint] db {host}:{port} unreachable after 30s", file=sys.stderr)
        sys.exit(1)

from backend.db.database import create_db_and_tables
create_db_and_tables()
print("[entrypoint] schema ready")
PY

echo "[entrypoint] starting: $*"
exec "$@"
