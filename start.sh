#!/bin/bash

echo "===================================================================="
echo "Streaming Service - Quick Start"
echo "===================================================================="
echo ""

# Check if PostgreSQL is running
echo "[1/4] Checking if PostgreSQL is running..."
if ! docker ps | grep -q "jobtrak-postgres"; then
    echo "[ERROR] PostgreSQL container 'jobtrak-postgres' is not running!"
    echo ""
    echo "Please start your JobTrak services first:"
    echo "  cd path/to/JobTrak"
    echo "  docker-compose up -d postgres"
    echo ""
    exit 1
fi
echo "[OK] PostgreSQL is running"
echo ""

# Check Python
echo "[2/4] Checking Python installation..."
if ! command -v python &> /dev/null && ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python is not installed"
    exit 1
fi

PYTHON_CMD="python"
if ! command -v python &> /dev/null; then
    PYTHON_CMD="python3"
fi

echo "[OK] Python found"
echo ""

# Setup database (if needed)
echo "[3/4] Setting up database..."
$PYTHON_CMD setup_database_in_existing_pg.py
if [ $? -ne 0 ]; then
    echo "[ERROR] Database setup failed"
    exit 1
fi
echo ""

# Start the application
echo "[4/4] Starting Flask backend..."
echo ""
echo "===================================================================="
echo "Backend is starting on http://localhost:5000"
echo "Press Ctrl+C to stop"
echo "===================================================================="
echo ""

$PYTHON_CMD app.py
