#!/bin/bash
set -e

echo "Starting Umutungo Production Services..."

# Change to project root
cd "$(dirname "$0")/.."

# Start backend
echo "Starting backend API..."
cd apps/api
source ../../.venv/bin/activate
AUTH_REQUIRED=false python -m uvicorn govasset_api.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
echo "Backend started with PID: $BACKEND_PID"

# Wait for backend to be ready
echo "Waiting for backend to be ready..."
sleep 5

# Check backend health
if curl -s http://localhost:8000/health > /dev/null; then
    echo "✓ Backend is healthy"
else
    echo "✗ Backend failed to start"
    exit 1
fi

# Start frontend
echo "Starting frontend..."
cd ../web
npm run dev > /tmp/frontend.log 2>&1 &
FRONTEND_PID=$!
echo "Frontend started with PID: $FRONTEND_PID"

# Wait for frontend to be ready
echo "Waiting for frontend to be ready..."
sleep 5

# Check frontend health
if curl -s http://localhost:3000 > /dev/null; then
    echo "✓ Frontend is healthy"
else
    echo "✗ Frontend failed to start"
    kill $BACKEND_PID
    exit 1
fi

echo ""
echo "=========================================="
echo "Umutungo services started successfully!"
echo "=========================================="
echo "Backend API: http://localhost:8000"
echo "Frontend: http://localhost:3000"
echo "Backend PID: $BACKEND_PID"
echo "Frontend PID: $FRONTEND_PID"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Trap to kill both processes on exit
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo 'Services stopped'; exit" INT TERM

# Wait for both processes
wait $BACKEND_PID $FRONTEND_PID
