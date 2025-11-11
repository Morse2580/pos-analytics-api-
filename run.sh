#!/bin/bash

# Duck Retail Analytics - Quick Start Script
# This script helps you get the API up and running quickly

set -e

echo "Duck Retail Analytics - Quick Start"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed"
    exit 1
fi

echo "Python version: $(python3 --version)"
echo ""

# Check if data file exists
if [ ! -f "Test_Data.xlsx" ]; then
    echo "Error: Test_Data.xlsx not found in current directory"
    exit 1
fi

echo "Data file: Test_Data.xlsx found"
echo ""

# Check if dependencies are installed
echo "Checking dependencies..."
if ! python3 -c "import pandas, fastapi, uvicorn" 2>/dev/null; then
    echo "Installing dependencies..."
    pip install -r requirements.txt
else
    echo "Dependencies already installed"
fi
echo ""

# Run validation tests
echo "Running validation tests..."
python3 tests/test_solution.py
echo ""

# Ask user if they want to start the API
read -p "Start API server? (y/n) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "Starting API server..."
    echo ""
    echo "Access the API at:"
    echo "  - Root: http://localhost:8000"
    echo "  - Docs: http://localhost:8000/docs"
    echo "  - Health: http://localhost:8000/health"
    echo ""
    echo "Press Ctrl+C to stop the server"
    echo ""
    python3 src/api/main.py
else
    echo "Skipping API startup"
    echo ""
    echo "To start manually:"
    echo "  python3 src/api/main.py"
    echo ""
    echo "Or use Docker:"
    echo "  docker-compose up -d"
fi
