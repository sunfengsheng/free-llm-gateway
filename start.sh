#!/bin/bash
echo ""
echo " Free LLM Gateway"
echo " ================"
echo " Starting server..."
echo ""

# Open browser after 3s in background
(sleep 3 && \
  if command -v xdg-open &>/dev/null; then xdg-open http://localhost:8000; \
  elif command -v open &>/dev/null; then open http://localhost:8000; \
  fi) &

# Run server in foreground (Ctrl+C to stop)
python main.py
