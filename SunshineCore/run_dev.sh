#!/bin/bash
echo "Starting Sunshine System in Development Mode"
echo "=========================================="

# Change to the sunshine_systems directory
cd src

# Activate pipenv environment and run with dev flag
pipenv run python main.py --devmode

# Return to root directory
cd ..
