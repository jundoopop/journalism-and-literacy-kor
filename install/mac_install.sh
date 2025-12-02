#!/bin/bash
# Highright Native Messaging Host Installer for macOS
# This script launches the Python installer

echo "========================================"
echo "Highright Installer for macOS"
echo "========================================"
echo ""

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 not found!"
    echo "Please install Python 3.7+ from https://python.org"
    echo "Or install via Homebrew: brew install python3"
    exit 1
fi

echo "Python found. Starting installation..."
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Run installer
python3 "$SCRIPT_DIR/install.py"

if [ $? -ne 0 ]; then
    echo ""
    echo "Installation failed. Please check the error messages above."
    exit 1
fi

echo ""
echo "Installation complete!"
echo "Press Enter to exit..."
read
