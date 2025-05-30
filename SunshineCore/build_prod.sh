#!/bin/bash
echo "Building Sunshine System for Production"
echo "======================================"

# Change to the sunshine_systems directory
cd sunshine_systems

# Install dependencies
echo "Installing dependencies..."
pipenv install

# Build executable with PyInstaller
echo "Building executable..."
pipenv run pyinstaller --onefile --noconsole --add-data "templates:templates" main.py

# Return to root directory
cd ..

# Move the built executable to the root sunshine folder
echo "Moving executable to root folder..."
if [ -f "sunshine_systems/dist/main" ]; then
    mv sunshine_systems/dist/main sunshine_system
elif [ -f "sunshine_systems/dist/main.exe" ]; then
    mv sunshine_systems/dist/main.exe sunshine_system.exe
fi

echo "Build complete! Executable created in root folder"
