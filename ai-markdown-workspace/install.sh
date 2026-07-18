cat > /workspace/ai-markdown-workspace/install.sh << 'EOF'
#!/bin/bash

echo "🚀 AI Markdown Workspace - Installer"
echo "====================================="

# 1. Check Python Version
echo "🐍 Checking Python version..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.11+ first."
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
REQUIRED_VERSION="3.11"
if [[ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]]; then
    echo "⚠️  Warning: Python version $PYTHON_VERSION might be too old. Recommended: 3.11+"
fi

# 2. Create Virtual Environment
echo "📦 Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ Virtual environment created."
else
    echo "ℹ️  Virtual environment already exists."
fi

# 3. Activate Virtual Environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate

# 4. Install Dependencies
echo "📥 Installing dependencies..."
pip install --upgrade pip
if [ -f requirements.txt ]; then
    pip install -r requirements.txt
    echo "✅ Dependencies installed."
else
    echo "❌ requirements.txt not found!"
    exit 1
fi

# 5. Setup Environment Variables
echo "⚙️  Setting up environment variables..."
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "✅ .env file created from .env.example. Please edit it with your API keys."
    else
        echo "⚠️  .env.example not found. Creating basic .env..."
        cat > .env << ENVEOF
AI_API_BASE=http://localhost:11434/v1
AI_API_KEY=ollama
DEFAULT_MODEL=llama3
USE_XIAOMI_MIMO=false
USE_OPENROUTER=false
USE_TOOL_CALLING=false
USE_MCP=false
ENVEOF
        echo "✅ Basic .env file created."
    fi
else
    echo "ℹ️  .env file already exists."
fi

# 6. Create Directories
echo "📁 Creating necessary directories..."
mkdir -p data
mkdir -p workspaces
echo "✅ Directories ready."

# 7. Initialize Database
echo "🗄️  Initializing database..."
python3 -c "from app.database import init_db; import asyncio; asyncio.run(init_db())"
echo "✅ Database initialized."

echo ""
echo "🎉 Installation Complete!"
echo "-------------------------"
echo "1. Edit the .env file with your API keys (if needed)."
echo "2. Run './start.sh' to launch the application."
echo "3. Open http://localhost:8000 in your browser."
EOF
