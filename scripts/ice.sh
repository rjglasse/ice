#!/bin/bash

# Task analysis workflow runner
# Usage: ./run_workflow.sh task-1

if [ $# -eq 0 ]; then
    echo "Usage: $0 <task-name>"
    echo "Example: $0 task-1"
    exit 1
fi

TASK=$1
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"

echo "🚀 Starting workflow for $TASK"
echo "================================"

cd "$BASE_DIR"

echo "📊 Step 1: Extracting commits..."
python3 "$SCRIPT_DIR/commits.py" "$TASK" --repos-dir repos
if [ $? -ne 0 ]; then echo "❌ Failed at step 1"; exit 1; fi

echo -e "\n🔍 Step 2: Extracting issues..."
python3 "$SCRIPT_DIR/issues.py" "$TASK" --repos-dir repos
if [ $? -ne 0 ]; then echo "❌ Failed at step 2"; exit 1; fi

echo -e "\n📈 Step 3: Analyzing data..."
python3 "$SCRIPT_DIR/effort.py" "$TASK"
if [ $? -ne 0 ]; then echo "❌ Failed at step 3"; exit 1; fi

echo -e "\n💬 Step 4: Generating nudges..."
python3 "$SCRIPT_DIR/nudges.py" "$TASK"
if [ $? -ne 0 ]; then echo "❌ Failed at step 4"; exit 1; fi

echo -e "\n✅ Workflow complete for $TASK!"
echo "Generated files in data/$TASK/:"
ls -la "data/$TASK/" | grep -E '\.(csv)$'