#!/usr/bin/env python3

import os
import subprocess
import csv
import json
import argparse
from pathlib import Path

def find_task_repos(repos_dir, task_pattern):
    """Find all task directories that are git repositories"""
    task_repos = []
    for root, dirs, files in os.walk(repos_dir):
        for d in dirs:
            if task_pattern in d and os.path.exists(os.path.join(root, d, '.git')):
                # Extract author name from folder structure (e.g., adamven/adamven-task-1 -> adamven)
                repo_path = os.path.join(root, d)
                relative_path = os.path.relpath(repo_path, repos_dir)
                author_name = relative_path.split(os.sep)[0]  # First part of path is author
                task_repos.append((repo_path, author_name))
    return task_repos

def setup_git_remote(repo_path, expected_author, task_pattern, base_url, namespace):
    """Setup git remote if not already configured"""
    try:
        # Check if remote already exists
        result = subprocess.run(['git', 'remote', '-v'], capture_output=True, text=True, check=True)
        if 'origin' in result.stdout:
            print(f"  Remote already configured")
            return True
            
        # Extract repo name from path (e.g., glassey-task-1)
        repo_name = os.path.basename(repo_path)
        
        # Construct remote URL: gits-15.sys.kth.se:inda-25/glassey-task-1.git
        remote_url = f"{base_url}:{namespace}/{repo_name}.git"
        
        # Add the remote
        add_result = subprocess.run(['git', 'remote', 'add', 'origin', remote_url], 
                                  capture_output=True, text=True, check=True)
        print(f"  Added remote: {remote_url}")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"  Error setting up remote: {e.stderr}")
        return False

def get_issues_data(repo_path, expected_author, task_pattern, base_url, namespace):
    """Extract GitHub issues data from a repository using gh CLI"""
    issues = []
    
    # Change to repository directory
    original_dir = os.getcwd()
    os.chdir(repo_path)
    
    try:
        # Setup remote if needed
        setup_git_remote(repo_path, expected_author, task_pattern, base_url, namespace)
        # Run gh issue list command
        cmd = ['gh', 'issue', 'list', '--state', 'all', '--json', 'number,title,state,createdAt']
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        if result.stdout.strip():
            issues_data = json.loads(result.stdout)
            
            for issue in issues_data:
                issues.append({
                    'repository': os.path.basename(repo_path),
                    'author': expected_author,
                    'number': issue['number'],
                    'title': issue['title'],
                    'state': issue['state'],
                    'createdAt': issue['createdAt']
                })
    
    except subprocess.CalledProcessError as e:
        if "no git remotes found" in e.stderr:
            print(f"  No GitHub remote configured (local repo only)")
        else:
            print(f"  Error running gh CLI in {repo_path}: {e.stderr}")
    except json.JSONDecodeError as e:
        print(f"  Error parsing JSON from {repo_path}: {e}")
    except Exception as e:
        print(f"  Unexpected error in {repo_path}: {e}")
    finally:
        os.chdir(original_dir)
    
    return issues

def main():
    parser = argparse.ArgumentParser(description='Extract GitHub/GitLab issues data from task repositories')
    parser.add_argument('task', help='Task pattern to search for (e.g., task-1, task-2, generictask)')
    parser.add_argument('--repos-dir', default='repos', help='Directory containing repositories')
    parser.add_argument('--data-dir', default='data', help='Directory to store output CSV files')
    parser.add_argument('--base-url', default='gits-15.sys.kth.se', help='Git server base URL')
    parser.add_argument('--namespace', default='inda-25', help='GitLab namespace/group')
    
    args = parser.parse_args()
    
    script_dir = Path(__file__).parent
    base_dir = script_dir.parent
    repos_dir = base_dir / args.repos_dir
    
    # Create output directory structure
    output_dir = base_dir / args.data_dir / args.task
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / 'issues.csv'
    
    # Find all task repositories
    task_repos = find_task_repos(str(repos_dir), args.task)
    print(f"Found {len(task_repos)} {args.task} repositories")
    
    # Collect all issues
    all_issues = []
    
    for repo_path, expected_author in task_repos:
        print(f"Processing repository: {repo_path} (expected author: {expected_author})")
        issues = get_issues_data(repo_path, expected_author, args.task, args.base_url, args.namespace)
        print(f"  Found {len(issues)} issues")
        all_issues.extend(issues)
    
    # Write to CSV
    if all_issues:
        with open(output_file, 'w', newline='') as csvfile:
            fieldnames = ['repository', 'author', 'number', 'title', 'state', 'createdAt']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for issue in all_issues:
                writer.writerow(issue)
        
        print(f"Issues data extracted to {output_file}")
        print(f"Total issues found: {len(all_issues)}")
    else:
        print("No issues found in any repository")
        # Still create empty CSV with headers
        with open(output_file, 'w', newline='') as csvfile:
            fieldnames = ['repository', 'author', 'number', 'title', 'state', 'createdAt']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

if __name__ == '__main__':
    main()