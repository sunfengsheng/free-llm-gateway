#!/bin/bash
echo ""
echo " Free LLM Gateway"
echo " ================"
echo " Starting server..."
echo ""

# Generate embedded HTML
python -c "content=open('static/index.html',encoding='utf-8').read(); open('ui_html.py','w',encoding='utf-8').write('HTML = ' + repr(content) + '\n')"

# Open browser after 3s in background
(sleep 3 && \
  if command -v xdg-open &>/dev/null; then xdg-open http://localhost:8000; \
  elif command -v open &>/dev/null; then open http://localhost:8000; \
  fi) &

# Run server in foreground (Ctrl+C to stop)
python main.py
