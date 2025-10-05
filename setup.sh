#!/bin/bash

# Trade Sourcer Setup Script

echo "================================================"
echo "  Trade Sourcer - Setup Script"
echo "================================================"
echo ""

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | grep -oP '\d+\.\d+')
required_version="3.9"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Error: Python 3.9 or higher is required"
    echo "   Current version: $python_version"
    exit 1
fi

echo "✅ Python $python_version detected"
echo ""

# Create virtual environment
echo "Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi
echo ""

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate
echo "✅ Virtual environment activated"
echo ""

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip -q
echo "✅ pip upgraded"
echo ""

# Install dependencies
echo "Installing dependencies..."
echo "This may take a few minutes..."
pip install -r requirements.txt -q

if [ $? -eq 0 ]; then
    echo "✅ Dependencies installed successfully"
else
    echo "⚠️  Some dependencies may have failed to install"
    echo "   You may need to install TA-Lib manually"
    echo "   See: https://github.com/mrjbq7/ta-lib#installation"
fi
echo ""

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    cp .env.example .env
    echo "✅ .env file created from template"
    echo "   Please edit .env with your API keys if needed"
else
    echo "✅ .env file already exists"
fi
echo ""

# Create necessary directories
echo "Creating directories..."
mkdir -p data reports logs
echo "✅ Directories created"
echo ""

echo "================================================"
echo "  Setup Complete!"
echo "================================================"
echo ""
echo "To get started:"
echo "  1. Activate the virtual environment: source venv/bin/activate"
echo "  2. (Optional) Edit .env with your API keys"
echo "  3. (Optional) Customize config/config.yaml"
echo "  4. Run the application: python main.py"
echo ""
echo "For more information, see README.md"
echo ""
