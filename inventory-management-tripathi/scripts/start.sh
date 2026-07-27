#!/bin/bash

# Factory Inventory Management System - Startup Script
# This script starts both the backend (FastAPI) and frontend (Vue + Vite) servers

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}Starting Factory Inventory Management System...${NC}\n"

# Get the project root directory (parent of scripts directory)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# Check if backend dependencies are installed
if [ ! -d "$PROJECT_ROOT/server/.venv" ]; then
    echo -e "${YELLOW}Backend dependencies not found. Installing...${NC}"
    cd "$PROJECT_ROOT/server"
    uv venv
    uv sync
fi

# Check if frontend dependencies are installed
if [ ! -d "$PROJECT_ROOT/client/node_modules" ]; then
    echo -e "${YELLOW}Frontend dependencies not found. Installing...${NC}"
    cd "$PROJECT_ROOT/client"
    npm install
fi

# Start backend server in background
echo -e "${GREEN}Starting backend server on http://localhost:8001${NC}"
cd "$PROJECT_ROOT/server"
uv run python3 main.py > /tmp/inventory-backend.log 2>&1 &
BACKEND_PID=$!

# Wait a moment for backend to start
sleep 2

# Start frontend server in background
echo -e "${GREEN}Starting frontend server on http://localhost:3000${NC}"
cd "$PROJECT_ROOT/client"
npm run dev > /tmp/inventory-frontend.log 2>&1 &
FRONTEND_PID=$!

# Wait a moment for frontend to start
sleep 2

echo -e "\n${GREEN}✓ Application started successfully!${NC}"
echo -e "${BLUE}Frontend:${NC} http://localhost:3000"
echo -e "${BLUE}Backend API:${NC} http://localhost:8001"
echo -e "${BLUE}API Docs:${NC} http://localhost:8001/docs"
echo -e "\n${YELLOW}Logs:${NC}"
echo -e "  Backend: /tmp/inventory-backend.log"
echo -e "  Frontend: /tmp/inventory-frontend.log"
echo -e "\n${YELLOW}To stop the servers, run:${NC} ./stop.sh"
echo -e "${YELLOW}Or press Ctrl+C and then run:${NC} kill $BACKEND_PID $FRONTEND_PID"

# Save PIDs to file for stop script
echo "$BACKEND_PID" > /tmp/inventory-backend.pid
echo "$FRONTEND_PID" > /tmp/inventory-frontend.pid

# Wait for Ctrl+C
trap "echo -e '\n${YELLOW}Shutting down servers...${NC}'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; rm -f /tmp/inventory-*.pid; exit 0" INT TERM

echo -e "\n${GREEN}Press Ctrl+C to stop all servers${NC}"
wait
