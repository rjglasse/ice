#!/usr/bin/env python3

import os
import subprocess
import csv
import argparse
import re
import sys
from pathlib import Path
from datetime import datetime as dt

from context import teachers, course_start_date, tasks

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

def get_commit_data(repo_path, expected_author, task_name):
    """Extract commit data from a git repository, filtering out teacher commits and applying date filters"""
    commits = []
    total_commits = 0
    teacher_filtered = 0
    date_filtered = 0
    
    # Extract repository name from path for identification
    repo_name = Path(repo_path).name
    
    # Use the repository owner (expected_author) as canonical student identity
    # instead of git commit author to handle cases where students use different git identities
    canonical_student = expected_author

    # Get date filtering bounds
    course_start = dt.fromisoformat(course_start_date)
    task_deadline = None
    if task_name in tasks:
        task_deadline = dt.fromisoformat(tasks[task_name]["deadline"])
    
    # Change to repository directory
    os.chdir(repo_path)
    
    # Get commit data with numstat for accurate line counts
    cmd = ['git', 'log', '--pretty=format:%H|%an|%ai|%s', '--numstat', '--no-merges']
    result = subprocess.run(cmd, capture_output=True, text=True)
    # print(result.stdout)  # Comment out debug output
    
    if result.returncode != 0:
        print(f"Error processing {repo_path}: {result.stderr}")
        return commits
    
    lines = result.stdout.strip().split('\n')
    i = 0
    
    while i < len(lines):
        line = lines[i].strip()
        
        # Check if this is a commit line (contains pipe separators)
        if '|' in line and len(line.split('|')) >= 4:
            total_commits += 1
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
            

            # Parse commit date and apply date filtering
            # Convert git date format to ISO format (remove timezone for comparison)
            # Format: "2025-09-26 00:10:16 +0200"
            date_part = datetime.split(' +')[0].split(' -')[0]  # Remove timezone part
            commit_date_obj = dt.fromisoformat(date_part)

            # Check if commit is within valid date range
            is_valid_date = commit_date_obj >= course_start
            if task_deadline:
                is_valid_date = is_valid_date and commit_date_obj <= task_deadline

            if not is_valid_date:
                date_filtered += 1
                i += 1
                continue

            # Check if this is a teacher commit
            is_teacher_commit = any(teacher.lower() in author.lower() for teacher in teachers)
            if is_teacher_commit:
                teacher_filtered += 1
                i += 1
                continue
            
            # Include this commit
            total = insertions + deletions
            commits.append({
                'repository': repo_name,
                'commit': commit_hash,
                'git_author': author,  # Keep original git author for reference
                'author': canonical_student,  # Use repository owner as canonical student identity
                'datetime': datetime,
                'subject': subject,
                'insertions': insertions,
                'deletions': deletions,
                'total': total
            })
        else:
            i += 1

    # Print filtering summary
    if total_commits > 0:
        print(f"    Total commits processed: {total_commits}")
        print(f"    Filtered out (teachers): {teacher_filtered}")
        print(f"    Filtered out (dates): {date_filtered}")
        print(f"    Included: {len(commits)}")

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
        commits = get_commit_data(repo_path, expected_author, args.task)
        all_commits.extend(commits)
        os.chdir(original_dir)
    
    # Write to CSV
    with open(output_file, 'w', newline='') as csvfile:
        fieldnames = ['repository', 'commit', 'git_author', 'author', 'datetime', 'subject', 'insertions', 'deletions', 'total']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for commit in all_commits:
            writer.writerow(commit)
    
    print(f"\nCommit data extracted to {output_file}")
    print(f"Total filtered commits found: {len(all_commits)}")
    print(f"\nFiltering applied:")
    print(f"  Course start date: {course_start_date}")
    if args.task in tasks:
        print(f"  Task deadline: {tasks[args.task]['deadline']}")
    else:
        print(f"  Task deadline: Not defined for {args.task}")
    print(f"  Teachers filtered: {len(teachers)} teacher names")

if __name__ == '__main__':
    main()