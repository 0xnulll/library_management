#!/usr/bin/env bash
set -euo pipefail

echo "[entrypoint] waiting for database..."
python - <<'PY'
import os, time, sys
from sqlalchemy import create_engine, text
url = os.environ["DATABASE_URL"]
engine = create_engine(url, pool_pre_ping=True)
for i in range(60):
    try:
        with engine.connect() as c:
            c.execute(text("SELECT 1"))
        sys.exit(0)
    except Exception as exc:
        print(f"[entrypoint] db not ready ({exc.__class__.__name__}); retry {i+1}/60")
        time.sleep(1)
sys.exit(1)
PY

echo "[entrypoint] running migrations..."
alembic upgrade head

echo "[entrypoint] starting gRPC server..."
exec python -m app.main
