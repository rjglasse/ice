#!/usr/bin/env python3

import os
import csv
import argparse
import subprocess
from pathlib import Path

def read_nudges_data(nudges_file):
    """Read nudges CSV and return list of nudge data"""
    nudges_data = []
    
    try:
        with open(nudges_file, 'r', newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                nudges_data.append({
                    'author': row['author'],
                    'commits': int(row['commits']),
                    'issues': int(row['issues']),
                    'open_issues': int(row['open_issues']),
                    'closed_issues': int(row['closed_issues']),
                    'references': int(row['references']),
                    'closing_references': int(row['closing_references']),
                    'classification': row['classification'],
                    'nudge_message': row['nudge_message'],
                    'issue_created': row.get('issue_created', 'False').lower() == 'true'
                })
    except FileNotFoundError:
        print(f"Error: Nudges file not found: {nudges_file}")
        return []
    except Exception as e:
        print(f"Error reading nudges file: {e}")
        return []
    
    return nudges_data

def generate_issue_title(classification):
    """Generate issue title based on classification"""
    return f"{classification}"

def find_author_repo(author, repos_dir, task):
    """Find the repository path for a given author"""
    # Look for author/author-task pattern
    repo_patterns = [
        f"{author}/{author}-{task}",
        f"{author}/{author}_{task}",
        f"{author}-{task}",
        f"{author}_{task}"
    ]
    
    for pattern in repo_patterns:
        repo_path = repos_dir / pattern
        if repo_path.exists() and (repo_path / '.git').exists():
            return repo_path
    
    # If not found, search in subdirectories
    for author_dir in repos_dir.iterdir():
        if author_dir.is_dir() and author in author_dir.name:
            for repo_dir in author_dir.iterdir():
                if repo_dir.is_dir() and task in repo_dir.name and (repo_dir / '.git').exists():
                    return repo_dir
    
    return None

def create_issue(repo_path, title, body, dry_run=False):
    """Create GitHub/GitLab issue using gh CLI"""
    original_dir = os.getcwd()
    
    try:
        os.chdir(repo_path)
        
        if dry_run:
            print(f"  [DRY RUN] Would create issue:")
            print(f"    Title: {title}")
            print(f"    Body: {body[:100]}...")
            return True
        
        # Create the issue using gh CLI
        cmd = ['gh', 'issue', 'create', '--title', title, '--body', body]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        print(f"  ✅ Issue created successfully!")
        print(f"     URL: {result.stdout.strip()}")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"  ❌ Error creating issue: {e.stderr}")
        return False
    except Exception as e:
        print(f"  ❌ Unexpected error: {e}")
        return False
    finally:
        os.chdir(original_dir)

def format_issue_body(nudge_data):
    """Format the issue body with nudge message"""
    return nudge_data['nudge_message']

def update_nudges_csv(nudges_file, nudges_data):
    """Update the nudges CSV file with the latest issue_created status"""
    fieldnames = ['author', 'commits', 'issues', 'open_issues', 'closed_issues', 
                  'references', 'closing_references', 'classification', 'nudge_message', 'issue_created']
    
    with open(nudges_file, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for nudge in nudges_data:
            writer.writerow({
                'author': nudge['author'],
                'commits': nudge['commits'],
                'issues': nudge['issues'],
                'open_issues': nudge['open_issues'],
                'closed_issues': nudge['closed_issues'],
                'references': nudge['references'],
                'closing_references': nudge['closing_references'],
                'classification': nudge['classification'],
                'nudge_message': nudge['nudge_message'],
                'issue_created': nudge['issue_created']
            })

def main():
    parser = argparse.ArgumentParser(description='Create GitHub/GitLab issues with nudge feedback')
    parser.add_argument('task', help='Task pattern (e.g., task-1, task-2, generictask)')
    parser.add_argument('--data-dir', default='data', help='Directory containing CSV files')
    parser.add_argument('--repos-dir', default='repos', help='Directory containing repositories')
    parser.add_argument('--nudges-file', default='nudges.csv', help='Input nudges CSV filename')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without actually creating issues')
    parser.add_argument('--student', help='Target only one specific student (author name)')
    
    args = parser.parse_args()
    
    script_dir = Path(__file__).parent
    base_dir = script_dir.parent
    task_data_dir = base_dir / args.data_dir / args.task
    repos_dir = base_dir / args.repos_dir
    
    nudges_file = task_data_dir / args.nudges_file
    
    print(f"Creating nudge issues for {args.task}")
    print(f"Reading nudges from: {nudges_file}")
    print(f"Looking for repos in: {repos_dir}")
    
    if args.dry_run:
        print("🔍 DRY RUN MODE - No issues will be created")
    
    # Read nudges data
    nudges_data = read_nudges_data(nudges_file)
    if not nudges_data:
        print("No nudges data found. Please run nudges.py first.")
        return
    
    # Filter for specific student if requested
    if args.student:
        nudges_data = [nudge for nudge in nudges_data if nudge['author'] == args.student]
        if not nudges_data:
            print(f"No nudge data found for student: {args.student}")
            return
        print(f"Targeting specific student: {args.student}")
    
    print(f"Found nudges for {len(nudges_data)} authors")
    
    # Create issues for each author
    success_count = 0
    skip_count = 0
    total_count = len(nudges_data)
    
    for nudge in nudges_data:
        author = nudge['author']
        classification = nudge['classification']
        
        print(f"\nProcessing {author} ({classification})...")
        
        # Check if issue has already been created
        if nudge['issue_created']:
            print(f"  ✅ Issue already created for {author} - skipping")
            skip_count += 1
            continue
        
        # Find author's repository
        repo_path = find_author_repo(author, repos_dir, args.task)
        if not repo_path:
            print(f"  ❌ Repository not found for {author}")
            continue
        
        print(f"  📁 Found repo: {repo_path}")
        
        # Generate issue title and body
        title = generate_issue_title(classification)
        body = format_issue_body(nudge)
        
        # Create the issue
        if create_issue(repo_path, title, body, args.dry_run):
            success_count += 1
            # Mark as created (only for real runs, not dry runs)
            if not args.dry_run:
                nudge['issue_created'] = True
    
    # Update the CSV file with the new issue_created status (only for real runs)
    if not args.dry_run and success_count > 0:
        update_nudges_csv(nudges_file, nudges_data)
        print(f"  📝 Updated nudges.csv with issue creation status")
    
    print(f"\n📈 Summary:")
    print(f"  Total authors: {total_count}")
    print(f"  Issues created: {success_count}")
    print(f"  Already created (skipped): {skip_count}")
    
    if args.dry_run:
        print(f"  (This was a dry run - no actual issues were created)")
    
    failed_count = total_count - success_count - skip_count
    if failed_count > 0:
        print(f"  Failed: {failed_count}")
        print("  Check repository paths and GitHub CLI authentication.")

if __name__ == '__main__':
    main()