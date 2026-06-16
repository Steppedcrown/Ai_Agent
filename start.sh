#!/bin/bash
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"

# Start the Elden Ring API in the background
cd "$ROOT/API"
uvicorn main:app --host localhost --port 8000 &

# Wait until port 8000 is accepting connections (max 15s)
echo "Waiting for Elden Ring API to start..."
for i in $(seq 1 15); do
  if python3 -c "import socket; s=socket.create_connection(('localhost',8000),1); s.close()" 2>/dev/null; then
    echo "API is up."
    break
  fi
  sleep 1
done

# Start the Flask app via gunicorn
cd "$ROOT"
exec gunicorn \
  --bind 0.0.0.0:5000 \
  --workers 1 \
  --worker-class gthread \
  --threads 4 \
  --timeout 120 \
  app:app
