#!/bin/bash
# LinkedIn MCP Setup Script

set -e

echo "🚀 LinkedIn MCP Setup Script"
echo "============================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.11+ first."
    exit 1
fi

echo "✅ Python 3 is installed"
echo ""

# Create virtual environment
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv .venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi
echo ""

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source .venv/bin/activate
echo "✅ Virtual environment activated"
echo ""

# Install dependencies
echo "📥 Installing dependencies..."
uv sync --locked
echo "✅ Dependencies installed"
echo ""

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found. Copying .env.linkedin to .env..."
    cp .env.linkedin .env
    echo "✅ .env file created"
    echo ""
    echo "📝 Next steps:"
    echo "1. Edit .env and fill in the required variables:"
    echo "   - ENCRYPTION_KEY (generate with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\")"
    echo "   - OAUTH_CLIENT_ID (from LinkedIn Developer Portal)"
    echo "   - OAUTH_CLIENT_SECRET (from LinkedIn Developer Portal)"
    echo "   - OAUTH_REDIRECT_URI (your Twynity deployment URL)"
    echo "   - MONGODB_URI (your MongoDB connection string)"
    echo "   - ACCOUNT_SERVICE_URL (your Twynity account service URL)"
    echo "   - SERVICE_ID (your Twynity service ID)"
    echo ""
    echo "2. Generate encryption key:"
    echo "   uv run python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
    echo ""
    echo "3. Start the server:"
    echo "   uv run uvicorn app.main:app --host 0.0.0.0 --port 8000"
    echo ""
else
    echo "✅ .env file already exists"
    echo ""
    echo "🚀 To start the server, run:"
    echo "   uv run uvicorn app.main:app --host 0.0.0.0 --port 8000"
    echo ""
fi

echo "📚 For detailed instructions, see README.md"
