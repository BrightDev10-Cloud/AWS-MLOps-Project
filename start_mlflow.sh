#!/bin/bash
# MLflow UI Launcher Script

echo "🚀 Starting MLflow Tracking Server..."
echo "📊 UI will be available at: http://localhost:5000"
echo ""
echo "Press Ctrl+C to stop the server"
echo "================================"
echo ""

cd "$(dirname "$0")"
source venv/bin/activate
mlflow ui --host 0.0.0.0 --port 5000
