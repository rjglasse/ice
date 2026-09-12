#!/usr/bin/env python3
"""Derive per-student workflow metrics for one task from commits.csv and issues.csv.

Output: data/<year>/<task>/effort.csv (one row per student with >=1 commit or issue).
The metric definitions are those used for the 2025 cohort and the ITiCSE 2026 paper;
change them only deliberately and record the change in docs/improvements.md.
"""

import argparse
import re
from collections import defaultdict

import context
from common import read_csv, write_csv

FIELDS = ['author', 'commits', 'issues', 'commits_to_issues_ratio',
          'total_insertions', 'total_deletions', 'total_changes',
          'avg_changes_per_commit', 'open_issues', 'closed_issues',
          'references', 'closing_references']

# GitHub closing keywords: close/closes/closed, fix/fixes/fixed, resolve/resolves/resolved
CLOSING_RE = re.compile(r'(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\s*#(\d+)', re.IGNORECASE)
REFERENCE_RE = re.compile(r'#(\d+)')


def count_issue_references(subject):
    """(all #N references, closing-keyword references) in a commit subject."""
    return len(REFERENCE_RE.findall(subject)), len(CLOSING_RE.findall(subject))


def calculate(commits, issues, strict=False):
    """strict=True drops commits flagged after_deadline (the study view used by compare.py)."""
    if strict:
        commits = [c for c in commits if str(c.get('after_deadline', 'False')).lower() != 'true']
    by_author = defaultdict(lambda: {
        'commits': 0, 'issues': 0, 'total_insertions': 0, 'total_deletions': 0, 'total_changes': 0,
        'open_issues': 0, 'closed_issues': 0, 'references': 0, 'closing_references': 0})
    for c in commits:
        a = by_author[c['author']]
        a['commits'] += 1
        refs, closing = count_issue_references(c['subject'])
        a['references'] += refs
        a['closing_references'] += closing
        a['total_insertions'] += int(c['insertions'])
        a['total_deletions'] += int(c['deletions'])
        a['total_changes'] += int(c['total'])
    for i in issues:
        a = by_author[i['author']]
        a['issues'] += 1
        if i['state'].upper() == 'OPEN':
            a['open_issues'] += 1
        else:
            a['closed_issues'] += 1

    rows = []
    for author in sorted(by_author):
        a = by_author[author]
        if a['issues'] > 0:
            ratio = round(a['commits'] / a['issues'], 4)
        else:
            ratio = 'inf' if a['commits'] > 0 else 0
        rows.append({'author': author, **a,
                     'commits_to_issues_ratio': ratio,
                     'avg_changes_per_commit': round(a['total_changes'] / a['commits'], 2) if a['commits'] else 0})
    return rows


def run(task, cohort, output='effort.csv', strict=False):
    d = cohort.task_data_dir(task)
    commits = read_csv(d / 'commits.csv') if (d / 'commits.csv').exists() else []
    issues = read_csv(d / 'issues.csv') if (d / 'issues.csv').exists() else []
    if not commits:
        print(f"[effort] WARNING: no commits.csv data in {d}")
    if not issues:
        print(f"[effort] WARNING: no issues.csv data in {d}")
    rows = calculate(commits, issues, strict)
    out = d / output
    write_csv(out, rows, FIELDS)
    print(f"[effort] {cohort.year}/{task}: {len(rows)} students -> {out}")
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('task', help='task name, e.g. task-1')
    p.add_argument('--output', default='effort.csv')
    p.add_argument('--strict', action='store_true', help='exclude commits after the deadline (default: include, for feedback)')
    context.add_cohort_arg(p)
    args = p.parse_args()
    run(args.task, context.load(args.cohort), args.output, args.strict)


if __name__ == '__main__':
    main()
