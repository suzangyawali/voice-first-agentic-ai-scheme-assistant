#!/bin/bash

# Browser Voice Agent Web Server Startup Script

echo "=========================================="
echo "🌐 Browser Voice Agent Web Server"
echo "=========================================="
echo ""
echo "📋 Checking environment..."

# Check if venv exists
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found"
    exit 1
fi

# Activate venv
source .venv/bin/activate

echo "✅ Virtual environment activated"
echo ""

# Check API key
if [ -z "$ASSEMBLYAI_API_KEY" ]; then
    # Try to load from .env
    if [ -f ".env" ]; then
        export $(grep ASSEMBLYAI_API_KEY .env | xargs)
    fi
fi

if [ -z "$ASSEMBLYAI_API_KEY" ]; then
    echo "⚠️  WARNING: ASSEMBLYAI_API_KEY not set"
    echo "   Add to .env file: ASSEMBLYAI_API_KEY=your_key"
    echo ""
fi

# Find available port
echo "🔍 Finding available port..."
PORT=5000
for p in {5000..5010}; do
    if ! lsof -Pi :$p -sTCP:LISTEN -t >/dev/null 2>&1 ; then
        PORT=$p
        break
    fi
done

echo "✅ Using port $PORT"
echo ""

echo "🚀 Starting web server..."
echo ""
echo "=========================================="
echo "📱 OPEN IN BROWSER:"
echo "   http://localhost:$PORT"
echo "=========================================="
echo ""
echo "Press Ctrl+C to stop server"
echo ""

# Start server with port
export FLASK_PORT=$PORT
python3 -c "
import sys
import os
sys.path.insert(0, '.')
sys.path.insert(0, 'src')
from web_server import app
port = int(os.environ.get('FLASK_PORT', 5000))
print(f'Server running on http://localhost:{port}')
app.run(debug=False, host='127.0.0.1', port=port, threaded=True)
"

