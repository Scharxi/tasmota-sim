#!/bin/bash
set -e

echo "Installing Tasmota Simulator CLI locally..."
echo

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed or not in PATH"
    echo "Please install Python 3.8+ from your package manager or https://python.org"
    exit 1
fi

# Check Python version
python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "Found Python $python_version"

# Install in development mode
echo "Installing dependencies..."
pip3 install -e .

echo
echo "✓ Installation successful!"
echo
echo "You can now use the CLI with:"
echo "  tasmota-sim --help"
echo
echo "Or directly with Python:"
echo "  python3 -m tasmota_sim.cli --help"
echo
echo "To start the Docker services (RabbitMQ + Devices):"
echo "  docker-compose -f docker-compose.services.yml up -d"
echo "  docker-compose -f docker-compose.override.yml up -d"
echo 