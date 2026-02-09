#!/bin/bash
# Startup script for MIDI Drum Timing Analyzer Web UI

echo "🎵 MIDI Drum Timing Analyzer Web UI"
echo "===================================="
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run:"
    echo "   python3 -m venv venv"
    echo "   source venv/bin/activate"
    echo "   pip install -r requirements.txt"
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Check if FastAPI is installed
if ! python -c "import fastapi" 2>/dev/null; then
    echo "📦 Installing backend dependencies..."
    pip install -r requirements.txt
fi

# Check if node_modules exists
if [ ! -d "web-ui/node_modules" ]; then
    echo "📦 Installing frontend dependencies..."
    cd web-ui && npm install && cd ..
fi

echo ""
echo "🚀 Starting services..."
echo ""

# Start backend in background
echo "▶️  Backend API starting on http://localhost:8000"
python api_server.py > /dev/null 2>&1 &
BACKEND_PID=$!

# Wait for backend to start
sleep 2

# Start frontend
echo "▶️  Frontend UI starting on http://localhost:5173"
cd web-ui && npm run dev

# Cleanup on exit
trap "echo ''; echo '🛑 Shutting down...'; kill $BACKEND_PID 2>/dev/null" EXIT
