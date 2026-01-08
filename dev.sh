#!/bin/bash
# Claude History Viewer 개발 스크립트

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

case "$1" in
  server|s)
    echo "🚀 Starting development server..."
    python3 history-server.py --host 127.0.0.1 --port 8080
    ;;

  app|a)
    echo "🖥️  Starting Electron app..."
    cd app && npm start
    ;;

  build|b)
    echo "📦 Building app..."
    cd app && npm run build
    echo "✅ Build complete! Check app/dist/"
    ;;

  index|i)
    echo "🔄 Updating session index..."
    python3 update-index.py
    ;;

  open|o)
    echo "🌐 Opening in browser..."
    open http://127.0.0.1:8080/history-viewer.html
    ;;

  install)
    echo "📥 Installing dependencies..."
    pip3 install fastapi uvicorn pydantic
    cd app && npm install
    echo "✅ Dependencies installed!"
    ;;

  clean)
    echo "🧹 Cleaning build artifacts..."
    rm -rf app/dist app/node_modules
    echo "✅ Cleaned!"
    ;;

  *)
    echo "Claude History Viewer - Development Commands"
    echo ""
    echo "Usage: ./dev.sh <command>"
    echo ""
    echo "Commands:"
    echo "  server, s    Start development server (browser mode)"
    echo "  app, a       Start Electron app"
    echo "  build, b     Build distributable app"
    echo "  index, i     Update session index"
    echo "  open, o      Open in browser"
    echo "  install      Install all dependencies"
    echo "  clean        Remove build artifacts"
    echo ""
    echo "Quick start:"
    echo "  ./dev.sh server   # Then open browser"
    echo "  ./dev.sh app      # Run as desktop app"
    ;;
esac
