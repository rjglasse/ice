#!/usr/bin/env python3

import os
import csv
import argparse
from pathlib import Path
from collections import defaultdict

def read_commits_data(commits_file):
    """Read commits CSV and count commits per author"""
    commits_count = defaultdict(int)
    commits_details = defaultdict(list)
    
    try:
        with open(commits_file, 'r', newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                author = row['author']
                commits_count[author] += 1
                commits_details[author].append({
                    'commit': row['commit'],
                    'datetime': row['datetime'],
                    'subject': row['subject'],
                    'insertions': int(row['insertions']),
                    'deletions': int(row['deletions']),
                    'total': int(row['total'])
                })
    except FileNotFoundError:
        print(f"Warning: Commits file not found: {commits_file}")
    except Exception as e:
        print(f"Error reading commits file: {e}")
    
    return commits_count, commits_details

def read_issues_data(issues_file):
    """Read issues CSV and count issues per author"""
    issues_count = defaultdict(int)
    issues_details = defaultdict(list)
    
    try:
        with open(issues_file, 'r', newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                author = row['author']
                issues_count[author] += 1
                issues_details[author].append({
                    'repository': row['repository'],
                    'number': int(row['number']),
                    'title': row['title'],
                    'state': row['state'],
                    'createdAt': row['createdAt']
                })
    except FileNotFoundError:
        print(f"Warning: Issues file not found: {issues_file}")
    except Exception as e:
        print(f"Error reading issues file: {e}")
    
    return issues_count, issues_details

def calculate_analysis(commits_count, commits_details, issues_count, issues_details):
    """Calculate analysis metrics for each author"""
    all_authors = set(commits_count.keys()) | set(issues_count.keys())
    analysis_data = []
    
    for author in all_authors:
        commits = commits_count.get(author, 0)
        issues = issues_count.get(author, 0)
        
        # Calculate commits-to-issues ratio (higher is better)
        if issues > 0:
            ratio = commits / issues
        else:
            ratio = float('inf') if commits > 0 else 0
        
        # Calculate additional metrics from commits
        total_insertions = 0
        total_deletions = 0
        total_changes = 0
        
        if author in commits_details:
            for commit in commits_details[author]:
                total_insertions += commit['insertions']
                total_deletions += commit['deletions']
                total_changes += commit['total']
        
        # Calculate average changes per commit
        avg_changes_per_commit = total_changes / commits if commits > 0 else 0
        
        # Count open vs closed issues
        open_issues = 0
        closed_issues = 0
        
        if author in issues_details:
            for issue in issues_details[author]:
                if issue['state'].upper() == 'OPEN':
                    open_issues += 1
                else:
                    closed_issues += 1
        
        analysis_data.append({
            'author': author,
            'commits': commits,
            'issues': issues,
            'commits_to_issues_ratio': round(ratio, 4) if ratio != float('inf') else 'inf',
            'total_insertions': total_insertions,
            'total_deletions': total_deletions,
            'total_changes': total_changes,
            'avg_changes_per_commit': round(avg_changes_per_commit, 2),
            'open_issues': open_issues,
            'closed_issues': closed_issues
        })
    
    # Sort by author name for consistent output
    analysis_data.sort(key=lambda x: x['author'])
    
    return analysis_data

def write_analysis_csv(analysis_data, output_file):
    """Write analysis data to CSV file"""
    fieldnames = [
        'author', 'commits', 'issues', 'commits_to_issues_ratio',
        'total_insertions', 'total_deletions', 'total_changes',
        'avg_changes_per_commit', 'open_issues', 'closed_issues'
    ]
    
    with open(output_file, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in analysis_data:
            writer.writerow(row)

def main():
    parser = argparse.ArgumentParser(description='Analyze commits and issues data to calculate ratios and metrics')
    parser.add_argument('task', help='Task pattern (e.g., task-1, task-2, generictask)')
    parser.add_argument('--data-dir', default='data', help='Directory containing CSV files')
    parser.add_argument('--output', default='effort.csv', help='Output CSV filename')
    
    args = parser.parse_args()
    
    script_dir = Path(__file__).parent
    base_dir = script_dir.parent
    task_data_dir = base_dir / args.data_dir / args.task
    
    commits_file = task_data_dir / 'commits.csv'
    issues_file = task_data_dir / 'issues.csv'
    output_file = task_data_dir / args.output
    
    print(f"Analyzing data for {args.task}")
    print(f"Reading commits from: {commits_file}")
    print(f"Reading issues from: {issues_file}")
    
    # Read data from CSV files
    commits_count, commits_details = read_commits_data(commits_file)
    issues_count, issues_details = read_issues_data(issues_file)
    
    print(f"Found commits data for {len(commits_count)} authors")
    print(f"Found issues data for {len(issues_count)} authors")
    
    # Calculate analysis
    analysis_data = calculate_analysis(commits_count, commits_details, issues_count, issues_details)
    
    # Write results
    write_analysis_csv(analysis_data, output_file)
    
    print(f"\nAnalysis complete! Results written to: {output_file}")
    print(f"Analyzed {len(analysis_data)} authors")
    
    # Print summary
    print("\nSummary:")
    for row in analysis_data:
        ratio_str = str(row['commits_to_issues_ratio'])
        print(f"  {row['author']}: {row['commits']} commits, {row['issues']} issues, ratio: {ratio_str}")

if __name__ == '__main__':
    main()