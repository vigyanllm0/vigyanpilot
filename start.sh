#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Free up ports if previous server instances are lingering
for port in 11436 8080; do
    pid=$(lsof -ti :$port 2>/dev/null)
    if [ -n "$pid" ]; then
        echo "[VigyanLLM] Port $port in use by PID $pid — terminating..."
        kill "$pid" 2>/dev/null
        sleep 1
    fi
done

# Create venv if not present
if [ ! -d ".venv" ]; then
  echo "[VigyanLLM] Creating virtual environment..."
  python3 -m venv .venv
fi

source .venv/bin/activate

# Install / upgrade dependencies
echo "[VigyanLLM] Installing dependencies..."
pip install --quiet -r requirements.txt

# ── Configuration ──

# Detect database mode
if [ -n "${DATABASE_URL:-}" ]; then
  echo "[VigyanLLM] Mode: PostgreSQL (production)"
  echo "[VigyanLLM] DB: ${DATABASE_URL%%@*}@***"
  GUNICORN_WORKERS="${GUNICORN_WORKERS:-1}"
else
  echo "[VigyanLLM] Mode: SQLite (development)"
  echo "[VigyanLLM] DB: ./primerforge.db"
  GUNICORN_WORKERS="${GUNICORN_WORKERS:-1}"
fi

# Clean up child processes on exit
cleanup() {
    echo "[VigyanLLM] Shutting down..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    wait $BACKEND_PID $FRONTEND_PID 2>/dev/null
    echo "[VigyanLLM] Stopped."
}
trap cleanup SIGINT SIGTERM

# Start backend via gunicorn
echo "[VigyanLLM] Starting backend on http://localhost:11436 (${GUNICORN_WORKERS} worker(s))"
export FLASK_ENV=production
# Not using PYTHONWARNINGS=error — biopython pairwise2 triggers deprecation warnings
export PYTHONWARNINGS=default
export PYTHONDONTWRITEBYTECODE=1
python -m gunicorn \
  --bind 127.0.0.1:11436 \
  --workers "$GUNICORN_WORKERS" \
  --timeout 120 \
  --access-logfile - \
  --error-logfile - \
  "primerforge.primer_server:create_app()" &
BACKEND_PID=$!

# Wait for backend to be ready
echo "[VigyanLLM] Waiting for backend..."
for i in $(seq 1 30); do
    if curl -s http://127.0.0.1:11436/health >/dev/null 2>&1; then
        echo "[VigyanLLM] Backend ready."
        break
    fi
    sleep 1
done

# Start secure frontend server (blocks path traversal, only exposed to internet)
echo "[VigyanLLM] Starting frontend on http://0.0.0.0:8080"
python -u "$SCRIPT_DIR/secure_frontend.py" &
FRONTEND_PID=$!

echo "[VigyanLLM] Frontend ready at http://localhost:8080"
echo "[VigyanLLM] Backend bound to 127.0.0.1:11436 (not directly accessible from outside)"
echo "[VigyanLLM] Press Ctrl+C to stop."

wait $BACKEND_PID
