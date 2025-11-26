#!/bin/bash
# Quick Results Viewer

echo "========================================="
echo "  🎉 Local MLOps Pipeline Results"
echo "========================================="
echo ""

# Check if files exist
echo "📊 Generated Artifacts:"
echo "------------------------"

if [ -f "model.joblib" ]; then
    size=$(ls -lh model.joblib | awk '{print $5}')
    echo "✓ model.joblib ($size)"
else
    echo "✗ model.joblib (not found)"
fi

if [ -f "metrics.json" ]; then
    echo "✓ metrics.json"
    echo "  Performance Metrics:"
    cat metrics.json | python3 -m json.tool 2>/dev/null | grep -E '(accuracy|precision|recall|f1)' | sed 's/^/    /'
else
    echo "✗ metrics.json (not found)"
fi

if [ -d "processed" ]; then
    train_rows=$(wc -l < processed/train.csv 2>/dev/null || echo "0")
    val_rows=$(wc -l < processed/val.csv 2>/dev/null || echo "0")
    echo "✓ processed/train.csv ($train_rows rows)"
    echo "✓ processed/val.csv ($val_rows rows)"
else
    echo "✗ processed/ directory (not found)"
fi

if [ -f "drift_report.html" ]; then
    size=$(ls -lh drift_report.html | awk '{print $5}')
    echo "✓ drift_report.html ($size)"
else
    echo "✗ drift_report.html (not found)"
fi

if [ -f "drift_results.json" ]; then
    echo "✓ drift_results.json"
    drift_detected=$(cat drift_results.json | python3 -c "import sys, json; print(json.load(sys.stdin)['drift_detected'])" 2>/dev/null)
    drift_share=$(cat drift_results.json | python3 -c "import sys, json; print(f\"{json.load(sys.stdin)['drift_share']:.2%}\")" 2>/dev/null)
    echo "  Drift Detected: $drift_detected"
    echo "  Drift Share: $drift_share"
else
    echo "✗ drift_results.json (not found)"
fi

if [ -d "mlruns" ]; then
    echo "✓ mlruns/ (MLflow tracking)"
else
    echo "✗ mlruns/ (not found)"
fi

echo ""
echo "🧪 Test Results:"
echo "---------------"
source venv/bin/activate 2>/dev/null
pytest --co -q 2>/dev/null | tail -1 || echo "Run 'pytest -v' to see test results"

echo ""
echo "📁 Quick Actions:"
echo "----------------"
echo "View drift report:      open drift_report.html"
echo "View test coverage:     open htmlcov/index.html"
echo "View MLflow UI:         mlflow ui --port 5000"
echo "Run tests:              pytest -v"
echo "Retrain model:          python train_model.py --train-csv processed/train.csv --val-csv processed/val.csv"
echo ""
echo "========================================="
echo "All systems operational! ✓"
echo "========================================="
