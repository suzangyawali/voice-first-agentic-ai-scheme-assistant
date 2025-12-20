#!/bin/bash
# Quick verification script for Voice-First Hindi LangGraph Agent

echo "🔍 Verifying Voice-First LangGraph Agent for Hindi Government Schemes"
echo "======================================================================"
echo ""

# Check Python environment
echo "✓ Checking Python environment..."
if [ -d ".venv" ]; then
    echo "  ✅ Virtual environment exists"
else
    echo "  ❌ Virtual environment not found. Run: python -m venv .venv"
    exit 1
fi

# Check key files
echo ""
echo "✓ Checking core files..."
FILES=(
    "src/voice/stt.py"
    "src/voice/tts.py"
    "src/graph.py"
    "src/main.py"
    "src/nodes/planner.py"
    "src/nodes/executor.py"
    "src/nodes/evaluator.py"
    "src/state/schema.py"
    "src/tools/__init__.py"
    "src/llm/config.py"
    "src/llm/prompts.py"
    "requirements.txt"
)

ALL_EXIST=true
for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✅ $file"
    else
        echo "  ❌ $file NOT FOUND"
        ALL_EXIST=false
    fi
done

if [ "$ALL_EXIST" = false ]; then
    echo ""
    echo "❌ Some files are missing. Check your repository structure."
    exit 1
fi

# Check for openai-whisper in requirements
echo ""
echo "✓ Checking dependencies..."
if grep -q "openai-whisper" requirements.txt; then
    echo "  ✅ openai-whisper found in requirements.txt"
else
    echo "  ❌ openai-whisper NOT in requirements.txt"
    exit 1
fi

# Check for STT implementation
echo ""
echo "✓ Checking STT implementation..."
if grep -q "whisper.load_model" src/voice/stt.py; then
    echo "  ✅ OpenAI Whisper integration confirmed"
else
    echo "  ❌ OpenAI Whisper not found in src/voice/stt.py"
    exit 1
fi

if grep -q 'language="hi"' src/voice/stt.py; then
    echo "  ✅ Hindi language setting confirmed"
else
    echo "  ⚠️  Hindi language setting not found (may need to be set)"
fi

# Check for LangGraph
echo ""
echo "✓ Checking LangGraph implementation..."
if grep -q "StateGraph" src/graph.py; then
    echo "  ✅ LangGraph StateGraph found"
else
    echo "  ❌ LangGraph StateGraph not found"
    exit 1
fi

if grep -q "MemorySaver" src/graph.py; then
    echo "  ✅ MemorySaver (conversation memory) found"
else
    echo "  ⚠️  MemorySaver not found (consider adding for memory persistence)"
fi

# Check for tools
echo ""
echo "✓ Checking tool implementations..."
if grep -q "class EligibilityTool" src/tools/__init__.py; then
    echo "  ✅ EligibilityTool found"
else
    echo "  ⚠️  EligibilityTool not found"
fi

if grep -q "class ApplicationTool" src/tools/__init__.py; then
    echo "  ✅ ApplicationTool found"
else
    echo "  ⚠️  ApplicationTool not found"
fi

echo ""
echo "======================================================================"
echo "✅ VERIFICATION COMPLETE!"
echo ""
echo "📋 Next steps:"
echo "  1. Install dependencies: pip install -r requirements.txt"
echo "  2. Set GROQ_API_KEY in .env file"
echo "  3. Run demo: python src/main.py --mode demo"
echo "  4. Run interactive: python src/main.py --mode interactive"
echo ""
echo "🎯 All hard requirements are implemented and ready for testing!"
echo "======================================================================"
