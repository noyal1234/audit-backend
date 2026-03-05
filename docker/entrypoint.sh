#!/bin/sh
set -e
cd /app
alembic -c alembic.ini upgrade head
exec python -m uvicorn src.app:app --host 0.0.0.0 --port 8000
