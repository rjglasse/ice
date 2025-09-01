#!/usr/bin/env python3
"""
Advanced GitHub Issues Analyzer

This script provides comprehensive GitHub issues analysis using the GitHub CLI
with advanced filtering, analysis, and export capabilities.
"""

import argparse
import csv
import json
import subprocess
import sys
from datetime import datetime, timezone
from typing import Dict, List, Optional
import re


class GitHubIssuesAnalyzer:
    def __init__(self, repo: Optional[str] = None):
        self.repo = repo
        self.validate_environment()
    
    def validate_environment(self):
        """Validate gh CLI is available and authenticated."""
        try:
            subprocess.run(['gh', '--version'], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("Error: GitHub CLI (gh) not found. Install with: brew install gh", file=sys.stderr)
            sys.exit(1)
        
        try:
            subprocess.run(['gh', 'auth', 'status'], capture_output=True, check=True)
        except subprocess.CalledProcessError:
            print("Error: Not authenticated with GitHub. Run: gh auth login", file=sys.stderr)
            sys.exit(1)
    
    def collect_issues(self, state: str = 'all', limit: int = 1000) -> List[Dict]:
        """Collect issues using GitHub CLI."""
        cmd = [
            'gh', 'issue', 'list',
            '--state', state,
            '--limit', str(limit),
            '--json', 'number,title,state,createdAt,updatedAt,closedAt,author,assignees,labels,milestone,comments,reactions,body'
        ]
        
        if self.repo:
            cmd.extend(['--repo', self.repo])
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            issues = json.loads(result.stdout)
            return self.enhance_issues(issues)
        except subprocess.CalledProcessError as e:
            print(f"Error collecting issues: {e}", file=sys.stderr)
            return []
    
    def enhance_issues(self, issues: List[Dict]) -> List[Dict]:
        """Add calculated fields to issues."""
        enhanced = []
        
        for issue in issues:
            # Calculate days open
            created = datetime.fromisoformat(issue['createdAt'].replace('Z', '+00:00'))
            if issue['closedAt']:
                closed = datetime.fromisoformat(issue['closedAt'].replace('Z', '+00:00'))
                days_open = (closed - created).days
            else:
                days_open = (datetime.now(timezone.utc) - created).days
            
            # Detect issue types
            issue_type = self.classify_issue(issue['title'], issue.get('body', ''), issue['labels'])
            
            # Extract priority
            priority = self.extract_priority(issue['labels'])
            
            enhanced_issue = {
                **issue,
                'days_open': days_open,
                'issue_type': issue_type,
                'priority': priority,
                'author_login': issue['author']['login'] if issue['author'] else '',
                'assignees_list': [a['login'] for a in issue['assignees']],
                'labels_list': [l['name'] for l in issue['labels']],
                'milestone_title': issue['milestone']['title'] if issue['milestone'] else '',
                'reactions_total': issue['reactions']['total_count'],
                'has_assignee': len(issue['assignees']) > 0,
                'is_stale': days_open > 90 and issue['state'] == 'open'
            }
            enhanced.append(enhanced_issue)
        
        return enhanced
    
    def classify_issue(self, title: str, body: str, labels: List[Dict]) -> str:
        """Classify issue type based on title, body, and labels."""
        title_lower = title.lower()
        body_lower = (body or '').lower()
        label_names = [l['name'].lower() for l in labels]
        
        # Check labels first
        if any('bug' in label for label in label_names):
            return 'bug'
        if any('feature' in label or 'enhancement' in label for label in label_names):
            return 'feature'
        if any('documentation' in label or 'docs' in label for label in label_names):
            return 'documentation'
        
        # Check title and body
        if any(word in title_lower for word in ['bug', 'error', 'fix', 'broken', 'issue']):
            return 'bug'
        if any(word in title_lower for word in ['feature', 'add', 'implement', 'support']):
            return 'feature'
        if any(word in title_lower for word in ['doc', 'readme', 'guide']):
            return 'documentation'
        
        return 'other'
    
    def extract_priority(self, labels: List[Dict]) -> str:
        """Extract priority from labels."""
        label_names = [l['name'].lower() for l in labels]
        
        if any('critical' in label or 'urgent' in label for label in label_names):
            return 'critical'
        if any('high' in label for label in label_names):
            return 'high'
        if any('medium' in label for label in label_names):
            return 'medium'
        if any('low' in label for label in label_names):
            return 'low'
        
        return 'none'
    
    def export_csv(self, issues: List[Dict], output_file: Optional[str] = None):
        """Export issues to CSV."""
        if not issues:
            print("No issues to export", file=sys.stderr)
            return
        
        fieldnames = [
            'number', 'title', 'state', 'createdAt', 'updatedAt', 'closedAt',
            'author_login', 'assignees_list', 'labels_list', 'milestone_title',
            'comments', 'reactions_total', 'days_open', 'issue_type', 'priority',
            'has_assignee', 'is_stale'
        ]
        
        output = open(output_file, 'w', newline='') if output_file else sys.stdout
        
        try:
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            
            for issue in issues:
                row = {field: issue.get(field, '') for field in fieldnames}
                # Convert lists to semicolon-separated strings
                if isinstance(row['assignees_list'], list):
                    row['assignees_list'] = ';'.join(row['assignees_list'])
                if isinstance(row['labels_list'], list):
                    row['labels_list'] = ';'.join(row['labels_list'])
                writer.writerow(row)
        finally:
            if output_file:
                output.close()
    
    def print_summary(self, issues: List[Dict]):
        """Print analysis summary."""
        if not issues:
            print("No issues found.")
            return
        
        total = len(issues)
        open_issues = len([i for i in issues if i['state'] == 'open'])
        closed_issues = total - open_issues
        
        # Type breakdown
        types = {}
        priorities = {}
        for issue in issues:
            issue_type = issue.get('issue_type', 'other')
            priority = issue.get('priority', 'none')
            types[issue_type] = types.get(issue_type, 0) + 1
            priorities[priority] = priorities.get(priority, 0) + 1
        
        avg_days_open = sum(i['days_open'] for i in issues) / total
        stale_issues = len([i for i in issues if i.get('is_stale', False)])
        
        print(f"\n📊 Issues Summary:")
        print(f"Total issues: {total}")
        print(f"Open: {open_issues} | Closed: {closed_issues}")
        print(f"Average days open: {avg_days_open:.1f}")
        print(f"Stale issues (>90 days): {stale_issues}")
        
        print(f"\n🏷️  Issue Types:")
        for issue_type, count in sorted(types.items()):
            print(f"  {issue_type}: {count}")
        
        print(f"\n⚡ Priorities:")
        for priority, count in sorted(priorities.items()):
            print(f"  {priority}: {count}")


def main():
    parser = argparse.ArgumentParser(description='Analyze GitHub issues')
    parser.add_argument('--repo', '-r', help='Repository (owner/repo)')
    parser.add_argument('--state', '-s', choices=['open', 'closed', 'all'], 
                       default='all', help='Issue state')
    parser.add_argument('--limit', '-l', type=int, default=1000, 
                       help='Maximum issues to fetch')
    parser.add_argument('--output', '-o', help='Output CSV file')
    parser.add_argument('--summary', action='store_true', 
                       help='Show summary statistics')
    parser.add_argument('--format', choices=['csv', 'json'], default='csv')
    
    args = parser.parse_args()
    
    analyzer = GitHubIssuesAnalyzer(args.repo)
    issues = analyzer.collect_issues(args.state, args.limit)
    
    if args.format == 'csv':
        analyzer.export_csv(issues, args.output)
    else:
        output = open(args.output, 'w') if args.output else sys.stdout
        json.dump(issues, output, indent=2, default=str)
        if args.output:
            output.close()
    
    if args.summary:
        analyzer.print_summary(issues)


if __name__ == '__main__':
    main()
