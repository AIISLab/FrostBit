#!/usr/bin/env bash
set -e

# Ensure correct working directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Starting SERVER on port 8000..."
(
  cd server
  source ../.venv/bin/activate 2>/dev/null || true
  uvicorn app.main:app --reload --port 8000
) &

SERVER_PID=$!

echo "Starting CLIENT on port 5173 (Vite default)..."
(
  cd web
  npm run dev
) &

CLIENT_PID=$!

echo ""
echo "Both processes started!"
echo "  Server PID:  $SERVER_PID"
echo "  Client PID:  $CLIENT_PID"
echo ""
echo "Press CTRL+C to stop both."

trap "kill $SERVER_PID $CLIENT_PID 2>/dev/null" EXIT

# Keep the script alive until terminated
wait
