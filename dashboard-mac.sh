#!/bin/bash
# LinkedIn Auto System Launcher for Mac/Linux
# This script opens two terminals: one for the backend, one for the frontend.
# Usage: bash run_both.sh

# --- Backend Terminal ---
# Mac (Terminal.app)
if [[ "$OSTYPE" == "darwin"* ]]; then
  open -a Terminal "$(pwd)/run_server.py" &
  sleep 1
  open -a Terminal "$(pwd)/linkedin-frontend" -e "npm start" &
# Linux (Gnome Terminal or fallback)
elif command -v gnome-terminal &> /dev/null; then
  gnome-terminal -- bash -c "source venv/bin/activate; python3 run_server.py; exec bash" &
  sleep 1
  gnome-terminal -- bash -c "cd linkedin-frontend; npm start; exec bash" &
elif command -v x-terminal-emulator &> /dev/null; then
  x-terminal-emulator -e bash -c "source venv/bin/activate; python3 run_server.py; exec bash" &
  sleep 1
  x-terminal-emulator -e bash -c "cd linkedin-frontend; npm start; exec bash" &
else
  echo "Please open two terminals manually:"
  echo "1. source venv/bin/activate; python3 run_server.py"
  echo "2. cd linkedin-frontend; npm start"
fi

echo "Both services are starting!"
echo "Backend: http://127.0.0.1:5000"
echo "Frontend: http://localhost:3000" 