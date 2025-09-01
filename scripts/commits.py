#!/usr/bin/env python3

import os
import subprocess
import csv
import argparse
import re
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

def get_commit_data(repo_path, expected_author):
    """Extract commit data from a git repository, filtering by expected author"""
    commits = []
    
    # Change to repository directory
    os.chdir(repo_path)
    
    # Get commit data with numstat for accurate line counts
    cmd = ['git', 'log', '--pretty=format:%H|%an|%ai|%s', '--numstat', '--no-merges']
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"Error processing {repo_path}: {result.stderr}")
        return commits
    
    lines = result.stdout.strip().split('\n')
    i = 0
    
    while i < len(lines):
        line = lines[i].strip()
        
        # Check if this is a commit line (contains pipe separators)
        if '|' in line and len(line.split('|')) == 4:
            commit_hash, author, datetime, subject = line.split('|', 3)
            insertions = 0
            deletions = 0
            
            # Process following numstat lines
            i += 1
            while i < len(lines) and lines[i].strip() and '|' not in lines[i]:
                parts = lines[i].strip().split('\t')
                if len(parts) >= 2 and parts[0] != '-' and parts[1] != '-':
                    try:
                        insertions += int(parts[0])
                        deletions += int(parts[1])
                    except ValueError:
                        pass
                i += 1
            
            # Only include commits from the expected author (case-insensitive partial match)
            if expected_author.lower() in author.lower():
                total = insertions + deletions
                commits.append({
                    'commit': commit_hash,
                    'author': author,
                    'datetime': datetime,
                    'subject': subject,
                    'insertions': insertions,
                    'deletions': deletions,
                    'total': total
                })
        else:
            i += 1
    
    return commits

def main():
    parser = argparse.ArgumentParser(description='Extract commit data from task repositories')
    parser.add_argument('task', help='Task pattern to search for (e.g., task-1, task-2, generictask)')
    parser.add_argument('--repos-dir', default='repos', help='Directory containing repositories')
    parser.add_argument('--data-dir', default='data', help='Directory to store output CSV files')
    
    args = parser.parse_args()
    
    script_dir = Path(__file__).parent
    base_dir = script_dir.parent
    repos_dir = base_dir / args.repos_dir
    
    # Create output directory structure
    output_dir = base_dir / args.data_dir / args.task
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / 'commits.csv'
    
    # Find all task repositories
    task_repos = find_task_repos(str(repos_dir), args.task)
    print(f"Found {len(task_repos)} {args.task} repositories")
    
    # Collect all commits
    all_commits = []
    original_dir = os.getcwd()
    
    for repo_path, expected_author in task_repos:
        print(f"Processing repository: {repo_path} (expected author: {expected_author})")
        commits = get_commit_data(repo_path, expected_author)
        print(f"  Found {len(commits)} commits from matching authors")
        all_commits.extend(commits)
        os.chdir(original_dir)
    
    # Write to CSV
    with open(output_file, 'w', newline='') as csvfile:
        fieldnames = ['commit', 'author', 'datetime', 'subject', 'insertions', 'deletions', 'total']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for commit in all_commits:
            writer.writerow(commit)
    
    print(f"Commit data extracted to {output_file}")
    print(f"Total filtered commits found: {len(all_commits)}")

if __name__ == '__main__':
    main()