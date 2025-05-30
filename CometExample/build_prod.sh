#!/bin/bash
echo "🔨 Building CometExample"
echo "======================="

# Navigate to the comet directory
cd "$(dirname "$0")/comet"

# Install dependencies including dev
echo "Installing dependencies..."
pipenv install --dev

# Build with PyInstaller
echo "Building executable..."
pipenv run pyinstaller --onefile --name CometExample src/main.py

# Move the executable to the parent dist folder
cd ..
mkdir -p dist
mv comet/dist/CometExample* dist/

echo ""
echo "✅ Build complete!"
echo "📦 Executable: dist/CometExample.exe"
echo ""
echo "To install in Sunshine:"
echo "1. Copy dist/CometExample.exe to:"
echo "   - Windows: %USERPROFILE%\Documents\Sunshine\plugins\"
echo "   - Mac/Linux: ~/Documents/Sunshine/plugins/"
echo "2. Start Sunshine normally"
echo ""
echo "Crash logs will be saved to:"
echo "   - Windows: %USERPROFILE%\Documents\Sunshine\Crash\"
echo "   - Mac/Linux: ~/Documents/Sunshine/Crash/"
