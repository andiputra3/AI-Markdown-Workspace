cat > /workspace/ai-markdown-workspace/start.sh << 'EOF'
#!/bin/bash

echo "🚀 Starting AI Markdown Workspace..."
echo "===================================="

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run './install.sh' first."
    exit 1
fi

# Activate Virtual Environment
source venv/bin/activate

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Creating default..."
    cp .env.example .env 2>/dev/null || echo "AI_API_BASE=http://localhost:11434/v1" > .env
fi

# Run Uvicorn
echo "🌐 Server starting on http://0.0.0.0:8000"
echo "Press Ctrl+C to stop."
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
EOF
