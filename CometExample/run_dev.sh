#!/bin/bash
echo "🌟 Running CometExample in development mode"
echo "==========================================="

# Navigate to the comet directory
cd "$(dirname "$0")/comet"

# Check if virtual environment exists
if [ ! -d ".venv" ] && ! pipenv --venv &>/dev/null; then
    echo "Creating virtual environment..."
    pipenv install
fi

# Run with --dev flag
echo "Starting CometExample with console window..."
pipenv run python src/main.py --dev
