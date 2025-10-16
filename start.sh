#!/bin/bash

# Pico Startup Script
# Starts both backend and frontend in separate processes

set -e

echo "🚀 Starting Pico..."
echo ""

# Check if conda environment exists
if ! conda env list | grep -q "^pico "; then
    echo "❌ Conda environment 'pico' not found."
    echo "Please run ./setup.sh first"
    exit 1
fi

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ .env file not found."
    echo "Please run ./setup.sh first or create .env with your ANTHROPIC_API_KEY"
    exit 1
fi

# Create log directory
mkdir -p logs

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Shutting down Pico..."
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    exit 0
}

trap cleanup INT TERM

# Start backend in conda environment
echo "🐍 Starting backend (Python FastAPI)..."
# Run in a subshell with conda activated
(eval "$(conda shell.bash hook)" && conda activate pico && python3 backend/main.py) > logs/backend.log 2>&1 &
BACKEND_PID=$!
echo "   Backend PID: $BACKEND_PID"
echo "   Backend logs: logs/backend.log"

# Wait for backend to start
sleep 2

# Start frontend
echo "🎨 Starting frontend (React)..."
cd frontend
npm start > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..
echo "   Frontend PID: $FRONTEND_PID"
echo "   Frontend logs: logs/frontend.log"

echo ""
echo "✨ Pico is starting up..."
echo ""
echo "📍 Backend:  http://localhost:8000"
echo "📍 Frontend: http://localhost:4000 (opens automatically)"
echo ""
echo "Press Ctrl+C to stop both servers"
echo ""

# Wait for processes
wait