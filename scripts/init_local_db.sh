#!/usr/bin/env bash
set -euo pipefail

ENV_FILE=.env
TIMEOUT=${1:-120}

if [ -f "$ENV_FILE" ]; then
  export $(grep -v '^#' $ENV_FILE | xargs)
fi

echo "Starting Postgres (docker-compose db)..."
docker compose up -d db

echo "Waiting for Postgres to be ready..."
start=$(date +%s)
while true; do
  if docker exec -i $(docker ps -q -f name=db) pg_isready -U ${POSTGRES_USER:-trading} -d ${POSTGRES_DB:-trading} | grep -q 'accepting connections'; then
    echo "Postgres is ready"
    break
  fi
  now=$(date +%s)
  if [ $((now - start)) -gt $TIMEOUT ]; then
    echo "Timed out waiting for Postgres after $TIMEOUT seconds" >&2
    exit 1
  fi
  sleep 2
done

if [ -z "${DATABASE_URL:-}" ]; then
  export DATABASE_URL="postgresql://${POSTGRES_USER:-trading}:${POSTGRES_PASSWORD:-trading}@localhost:5432/${POSTGRES_DB:-trading}"
  echo "Using DATABASE_URL=$DATABASE_URL"
fi

echo "Running alembic upgrade head..."
alembic upgrade head

echo "Done."
