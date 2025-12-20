#!/bin/bash

# Start Browser-based Voice Agent

cd /Users/sujangyawali/Desktop/langgraph-voice-agent

echo "=========================================="
echo "🌐 Browser-based Voice Agent"
echo "=========================================="
echo ""

# Activate venv
source .venv/bin/activate

echo "✅ Starting Flask web server..."
echo ""

# Start server
python3 << 'PYTHON_EOF'
import sys
sys.path.insert(0, '.')
sys.path.insert(0, 'src')

from web_server import app
import logging

logging.basicConfig(level=logging.INFO)

print("=" * 70)
print("🌐 Browser Voice Agent Web Server")
print("=" * 70)
print("")
print("📱 OPEN IN BROWSER:")
print("   http://127.0.0.1:5000")
print("")
print("🎤 Features:")
print("   ✓ Browser microphone recording")
print("   ✓ AssemblyAI Hindi transcription")
print("   ✓ LangGraph voice agent processing")
print("")
print("Press Ctrl+C to stop")
print("=" * 70)
print("")

try:
    app.run(debug=False, host='127.0.0.1', port=5000, threaded=True)
except OSError:
    print("\n⚠️  Port 5000 in use, trying port 5001...")
    app.run(debug=False, host='127.0.0.1', port=5001, threaded=True)

PYTHON_EOF
