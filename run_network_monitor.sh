#!/bin/bash

# Network Traffic Monitor Launcher for Linux/macOS
# This script starts both the backend server and frontend application

set -e  # Exit on error

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$SCRIPT_DIR"
BACKEND_PATH="$PROJECT_ROOT/backend"
FRONTEND_PATH="$PROJECT_ROOT/frontend"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}Network Traffic Monitor Launcher${NC}"
echo -e "${GREEN}================================${NC}"
echo ""

# Check if running on macOS and requires sudo for packet capture
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo -e "${YELLOW}macOS detected. Packet capture may require sudo.${NC}"
    echo -e "${YELLOW}You may be prompted for your password.${NC}"
    echo ""
fi

# Check if running on Linux and requires sudo for packet capture
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo -e "${YELLOW}Linux detected. Packet capture requires root/sudo.${NC}"
    echo -e "${YELLOW}You may be prompted for your password.${NC}"
    echo ""
fi

# Load environment variables from .env if it exists
if [ -f "$PROJECT_ROOT/.env" ]; then
    echo -e "${GREEN}[INFO]${NC} Loading environment variables from .env"
    export $(grep -v '^#' "$PROJECT_ROOT/.env" | grep -v '^$' | xargs)
fi

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}[ERROR] Python 3 is not installed. Please install Python 3.8 or higher.${NC}"
    exit 1
fi

echo -e "${GREEN}[INFO]${NC} Python version: $(python3 --version)"
echo ""

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo -e "${RED}[ERROR] Node.js is not installed. Please install Node.js 14 or higher.${NC}"
    exit 1
fi

echo -e "${GREEN}[INFO]${NC} Node.js version: $(node --version)"
echo -e "${GREEN}[INFO]${NC} npm version: $(npm --version)"
echo ""

# Install Python dependencies if needed
echo -e "${GREEN}[INFO]${NC} Checking Python dependencies..."
cd "$BACKEND_PATH"

if [ ! -d "venv" ]; then
    echo -e "${YELLOW}[INFO]${NC} Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

echo -e "${YELLOW}[INFO]${NC} Installing Python dependencies..."
pip install -q -r requirements.txt

# Install Node dependencies if needed
echo -e "${YELLOW}[INFO]${NC} Installing Node dependencies..."
cd "$FRONTEND_PATH"

if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}[INFO]${NC} Installing npm packages..."
    npm install
fi

echo ""
echo -e "${GREEN}[INFO]${NC} All dependencies installed successfully!"
echo ""

# Start the backend server
echo -e "${GREEN}[INFO]${NC} Starting backend server..."
cd "$BACKEND_PATH"

# Use sudo for packet capture on Linux/macOS if not already root
if [[ "$EUID" -ne 0 ]] && [[ "$OSTYPE" != "msys" && "$OSTYPE" != "win32" ]]; then
    echo -e "${YELLOW}[INFO]${NC} Starting Python backend with sudo (required for packet capture)..."
    sudo -E "$(which python3)" app2.py > /tmp/ntm_backend.log 2>&1 &
else
    python3 app2.py > /tmp/ntm_backend.log 2>&1 &
fi

BACKEND_PID=$!
echo -e "${GREEN}[INFO]${NC} Backend started with PID: $BACKEND_PID"
echo -e "${GREEN}[INFO]${NC} Backend logs: tail -f /tmp/ntm_backend.log"

# Wait for backend to start
echo -e "${YELLOW}[INFO]${NC} Waiting for backend to initialize (5 seconds)..."
sleep 5

# Check if backend is running
if ! kill -0 $BACKEND_PID 2>/dev/null; then
    echo -e "${RED}[ERROR]${NC} Backend failed to start. Check logs: tail -f /tmp/ntm_backend.log"
    exit 1
fi

echo -e "${GREEN}[INFO]${NC} Backend is running!"
echo ""

# Start the frontend
echo -e "${GREEN}[INFO]${NC} Starting frontend application..."
cd "$FRONTEND_PATH"
npm start

# Cleanup on exit
trap "
    echo ''
    echo -e '${YELLOW}[INFO]${NC} Shutting down...'
    kill $BACKEND_PID 2>/dev/null || true
    exit 0
" SIGINT SIGTERM

wait $BACKEND_PID
