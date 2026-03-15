#!/bin/bash
set -e

echo "=== RegIntel — Regulatory Intelligence Platform ==="

# Install backend dependencies
echo "[1/4] Installing backend dependencies..."
cd "$(dirname "$0")/backend"
pip install -q -r requirements.txt

# Install frontend dependencies
echo "[2/4] Installing frontend dependencies..."
cd "$(dirname "$0")/client"
npm install --silent

# Start backend
echo "[3/4] Starting backend on :8000..."
cd "$(dirname "$0")/backend"
python startup.py &
BACKEND_PID=$!

# Start frontend
echo "[4/4] Starting frontend on :5173..."
cd "$(dirname "$0")/client"
npm run dev &
FRONTEND_PID=$!

echo ""
echo "Backend:  http://localhost:8000"
echo "Frontend: http://localhost:5173"
echo ""

cleanup() {
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
}
trap cleanup EXIT

wait
