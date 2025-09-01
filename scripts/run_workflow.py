#!/usr/bin/env python3

import subprocess
import sys
import argparse
from pathlib import Path

def run_script(script_name, args, description):
    """Run a script with error handling"""
    print(f"\n🔄 {description}")
    print("-" * 50)
    
    cmd = [sys.executable, script_name] + args
    try:
        result = subprocess.run(cmd, check=True, capture_output=False)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed with exit code {e.returncode}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Run the complete task analysis workflow')
    parser.add_argument('task', help='Task pattern (e.g., task-1, task-2)')
    parser.add_argument('--repos-dir', default='repos', help='Directory containing repositories')
    args = parser.parse_args()
    
    script_dir = Path(__file__).parent
    
    scripts = [
        {
            'name': script_dir / 'extract_task_commits.py',
            'args': [args.task, '--repos-dir', args.repos_dir],
            'description': 'Extracting commit data'
        },
        {
            'name': script_dir / 'extract_task_issues.py',
            'args': [args.task, '--repos-dir', args.repos_dir],
            'description': 'Extracting issues data'
        },
        {
            'name': script_dir / 'analyze_task_data.py',
            'args': [args.task],
            'description': 'Analyzing effort data'
        },
        {
            'name': script_dir / 'nudges.py',
            'args': [args.task],
            'description': 'Generating nudge messages'
        }
    ]
    
    print(f"🚀 Starting workflow for {args.task}")
    print("=" * 60)
    
    for i, script in enumerate(scripts, 1):
        if not run_script(str(script['name']), script['args'], f"Step {i}: {script['description']}"):
            print(f"\n❌ Workflow failed at step {i}")
            sys.exit(1)
    
    print(f"\n🎉 Workflow completed successfully for {args.task}!")
    
    # Show generated files
    data_dir = Path('data') / args.task
    if data_dir.exists():
        print(f"\n📁 Generated files in {data_dir}:")
        for csv_file in data_dir.glob('*.csv'):
            print(f"  - {csv_file.name}")

if __name__ == '__main__':
    main()