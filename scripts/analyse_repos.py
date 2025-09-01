#!/usr/bin/env python3
"""
Advanced Git Commit Analysis Tool

This Python version provides even more robust analysis with better error handling,
data validation, and output options. It's particularly useful for large repositories
or when you need more sophisticated analysis.
"""

import argparse
import csv
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class GitCommitAnalyzer:
    def __init__(self, author_pattern: str, exclude_patterns: Optional[List[str]] = None):
        self.author_pattern = author_pattern
        self.exclude_patterns = exclude_patterns or []
        self.fix_patterns = [
            r'\b(fix|fixes|fixed|close|closes|closed|resolve|resolves|resolved)\s+#\d+',
            r'\b(fix|close|resolve)\s*:?\s*#\d+',
            r'#\d+.*\b(fix|close|resolve)\b',
            r'\b(repair|repairs|repaired)\s+#\d+'
        ]
    
    def validate_git_repo(self) -> bool:
        """Check if we're in a valid git repository."""
        try:
            subprocess.run(['git', 'rev-parse', '--git-dir'], 
                         capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def is_fix_commit(self, subject: str) -> bool:
        """Detect if a commit is a fix using multiple patterns."""
        subject_lower = subject.lower()
        return any(re.search(pattern, subject_lower, re.IGNORECASE) 
                  for pattern in self.fix_patterns)
    
    def should_exclude_file(self, filepath: str) -> bool:
        """Check if file should be excluded based on patterns."""
        return any(Path(filepath).match(pattern) for pattern in self.exclude_patterns)
    
    def get_commits(self) -> List[Dict]:
        """Extract commit data using git log."""
        try:
            # Get commit info and stats
            cmd = [
                'git', 'log', f'--author={self.author_pattern}',
                '--date=iso', '--numstat',
                '--pretty=format:%H%x09%an%x09%ad%x09%s'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return self._parse_git_output(result.stdout)
            
        except subprocess.CalledProcessError as e:
            print(f"Error running git command: {e}", file=sys.stderr)
            return []
    
    def _parse_git_output(self, output: str) -> List[Dict]:
        """Parse git log output into structured data."""
        commits = []
        current_commit = None
        
        for line in output.strip().split('\n'):
            if not line:
                continue
                
            # Check if this is a commit line (contains tabs in specific positions)
            if '\t' in line and not line.startswith(('\t', ' ')):
                parts = line.split('\t', 3)
                if len(parts) == 4:
                    # Save previous commit if exists
                    if current_commit:
                        commits.append(current_commit)
                    
                    # Start new commit
                    current_commit = {
                        'commit': parts[0],
                        'author': parts[1],
                        'datetime': parts[2],
                        'subject': parts[3],
                        'insertions': 0,
                        'deletions': 0,
                        'files_changed': 0,
                        'fix': self.is_fix_commit(parts[3])
                    }
                    continue
            
            # Parse numstat line
            if current_commit and '\t' in line:
                parts = line.split('\t')
                if len(parts) >= 3:
                    insertions, deletions, filepath = parts[0], parts[1], parts[2]
                    
                    # Skip excluded files
                    if self.should_exclude_file(filepath):
                        continue
                    
                    # Add to totals (handle binary files)
                    if insertions != '-':
                        current_commit['insertions'] += int(insertions)
                    if deletions != '-':
                        current_commit['deletions'] += int(deletions)
                    current_commit['files_changed'] += 1
        
        # Don't forget the last commit
        if current_commit:
            commits.append(current_commit)
        
        # Add calculated fields
        for commit in commits:
            commit['total'] = commit['insertions'] + commit['deletions']
        
        return commits
    
    def export_csv(self, commits: List[Dict], output_file: Optional[str] = None):
        """Export commits to CSV format."""
        fieldnames = ['commit', 'author', 'datetime', 'subject', 'insertions', 
                     'deletions', 'total', 'files_changed', 'fix']
        
        output = open(output_file, 'w', newline='') if output_file else sys.stdout
        
        try:
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            for commit in commits:
                writer.writerow({k: commit[k] for k in fieldnames})
        finally:
            if output_file:
                output.close()
    
    def export_json(self, commits: List[Dict], output_file: Optional[str] = None):
        """Export commits to JSON format."""
        output = open(output_file, 'w') if output_file else sys.stdout
        
        try:
            json.dump(commits, output, indent=2, ensure_ascii=False)
            output.write('\n')
        finally:
            if output_file:
                output.close()
    
    def print_summary(self, commits: List[Dict]):
        """Print analysis summary."""
        if not commits:
            print("No commits found.")
            return
        
        total_commits = len(commits)
        fix_commits = sum(1 for c in commits if c['fix'])
        total_insertions = sum(c['insertions'] for c in commits)
        total_deletions = sum(c['deletions'] for c in commits)
        
        print(f"\nSummary for author pattern '{self.author_pattern}':")
        print(f"Total commits: {total_commits}")
        print(f"Fix commits: {fix_commits} ({fix_commits/total_commits*100:.1f}%)")
        print(f"Total lines added: {total_insertions:,}")
        print(f"Total lines removed: {total_deletions:,}")
        print(f"Net change: {total_insertions - total_deletions:+,}")
        
        if commits:
            avg_size = (total_insertions + total_deletions) / total_commits
            print(f"Average commit size: {avg_size:.1f} lines")


def main():
    parser = argparse.ArgumentParser(description='Analyze git commits')
    parser.add_argument('--author', '-a', default='[Gg]lassey', 
                       help='Author pattern (default: [Gg]lassey)')
    parser.add_argument('--format', '-f', choices=['csv', 'json'], default='csv',
                       help='Output format (default: csv)')
    parser.add_argument('--output', '-o', help='Output file (default: stdout)')
    parser.add_argument('--exclude', nargs='*', default=[],
                       help='File patterns to exclude (e.g. *.min.js dist/*)')
    parser.add_argument('--summary', '-s', action='store_true',
                       help='Show summary statistics')
    
    args = parser.parse_args()
    
    analyzer = GitCommitAnalyzer(args.author, args.exclude)
    
    if not analyzer.validate_git_repo():
        print("Error: Not in a git repository", file=sys.stderr)
        sys.exit(1)
    
    commits = analyzer.get_commits()
    
    if args.format == 'csv':
        analyzer.export_csv(commits, args.output)
    else:
        analyzer.export_json(commits, args.output)
    
    if args.summary:
        analyzer.print_summary(commits)


if __name__ == '__main__':
    main()
