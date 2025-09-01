#!/usr/bin/env python3
"""
Flexible Git Commit Analysis with Configurable Date Formats
"""

import argparse
import csv
import json
import re
import subprocess
import sys
from typing import Dict, List, Optional


class FlexibleGitAnalyzer:
    DATE_FORMATS = {
        'iso': 'iso',
        'iso-strict': 'iso-strict', 
        'unix': 'unix',
        'relative': 'relative',
        'short': 'short',
        'full': 'fuller',
        'custom': 'format:%Y-%m-%d %H:%M:%S %z'
    }
    
    def __init__(self, author_pattern: str, date_format: str = 'iso'):
        self.author_pattern = author_pattern
        self.date_format = self.DATE_FORMATS.get(date_format, date_format)
    
    def analyze_commits(self) -> List[Dict]:
        """Get commits with specified date format."""
        try:
            cmd = [
                'git', 'log', f'--author={self.author_pattern}',
                f'--date={self.date_format}', '--numstat',
                '--pretty=format:%H%x09%an%x09%ad%x09%s'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return self._parse_output(result.stdout)
            
        except subprocess.CalledProcessError as e:
            print(f"Git command failed: {e}", file=sys.stderr)
            return []
    
    def _parse_output(self, output: str) -> List[Dict]:
        commits = []
        current_commit = None
        
        for line in output.strip().split('\n'):
            if not line:
                continue
                
            if '\t' in line and not line.startswith(('\t', ' ')):
                parts = line.split('\t', 3)
                if len(parts) == 4:
                    if current_commit:
                        commits.append(current_commit)
                    
                    current_commit = {
                        'commit': parts[0],
                        'author': parts[1],
                        'datetime': parts[2],
                        'subject': parts[3],
                        'insertions': 0,
                        'deletions': 0,
                        'total': 0
                    }
            elif current_commit and '\t' in line:
                parts = line.split('\t')
                if len(parts) >= 3:
                    ins, dels = parts[0], parts[1]
                    if ins != '-':
                        current_commit['insertions'] += int(ins)
                    if dels != '-':
                        current_commit['deletions'] += int(dels)
        
        if current_commit:
            commits.append(current_commit)
        
        for commit in commits:
            commit['total'] = commit['insertions'] + commit['deletions']
        
        return commits


def main():
    parser = argparse.ArgumentParser(description='Git analysis with flexible date formats')
    parser.add_argument('--author', '-a', default='.*', help='Author pattern')
    parser.add_argument('--date-format', '-d', 
                       choices=['iso', 'iso-strict', 'unix', 'relative', 'short', 'full', 'custom'],
                       default='iso', help='Date format')
    parser.add_argument('--format', '-f', choices=['csv', 'json'], default='csv')
    parser.add_argument('--output', '-o', help='Output file')
    
    args = parser.parse_args()
    
    analyzer = FlexibleGitAnalyzer(args.author, args.date_format)
    commits = analyzer.analyze_commits()
    
    if args.format == 'json':
        output = open(args.output, 'w') if args.output else sys.stdout
        json.dump(commits, output, indent=2)
        if args.output:
            output.close()
    else:
        output = open(args.output, 'w', newline='') if args.output else sys.stdout
        writer = csv.DictWriter(output, fieldnames=['commit', 'author', 'datetime', 'subject', 'insertions', 'deletions', 'total'])
        writer.writeheader()
        writer.writerows(commits)
        if args.output:
            output.close()


if __name__ == '__main__':
    main()
