#!/usr/bin/env python3
"""Extract issue metadata for one task via the GitHub CLI (gh), one repo at a time.

Output: data/<year>/<task>/issues.csv. Issues created by teachers are excluded
(substring match on the creator login); the repository owner is the canonical student.
Requires `gh auth status` to show the cohort host as logged in.
"""

import argparse
import json
import subprocess
from pathlib import Path

import context
from common import find_task_repos, write_csv

FIELDS = ['repository', 'issue_creator', 'author', 'number', 'title', 'state', 'createdAt', 'closedAt']


def ensure_remote(repo_path, cohort):
    r = subprocess.run(['git', '-C', repo_path, 'remote', '-v'], capture_output=True, text=True)
    if 'origin' in r.stdout:
        return True
    url = f"{cohort.host}:{cohort.org}/{Path(repo_path).name}.git"
    a = subprocess.run(['git', '-C', repo_path, 'remote', 'add', 'origin', url], capture_output=True, text=True)
    if a.returncode != 0:
        print(f"  could not add remote {url}: {a.stderr.strip()}")
        return False
    print(f"  added remote {url}")
    return True


def get_issues_data(repo_path, student, cohort):
    issues = []
    if cohort.is_teacher(student):
        return issues
    if not ensure_remote(repo_path, cohort):
        return issues
    cmd = ['gh', 'issue', 'list', '--state', 'all', '--limit', '500',
           '--json', 'number,title,state,createdAt,closedAt,author']
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, check=True, cwd=repo_path)
    except subprocess.CalledProcessError as e:
        msg = e.stderr.strip()
        print(f"  gh failed in {repo_path}: {msg[:200]}")
        return issues
    if not r.stdout.strip():
        return issues
    for issue in json.loads(r.stdout):
        creator = (issue.get('author') or {}).get('login', 'unknown')
        if cohort.is_teacher(creator):
            continue
        issues.append({
            'repository': Path(repo_path).name,
            'issue_creator': creator,
            'author': student,
            'number': issue['number'],
            'title': issue['title'],
            'state': issue['state'],
            'createdAt': issue.get('createdAt', ''),
            'closedAt': issue.get('closedAt') or '',
        })
    return issues


def run(task, cohort, repos_dir=None, quiet=False):
    repos_dir = Path(repos_dir) if repos_dir else cohort.repos_dir
    out_file = cohort.task_data_dir(task) / 'issues.csv'
    repos = find_task_repos(repos_dir, task)
    print(f"[issues] {cohort.name}/{task}: {len(repos)} repositories under {repos_dir}")
    all_issues = []
    for repo_path, student in repos:
        found = get_issues_data(repo_path, student, cohort)
        if not quiet:
            print(f"  {student}: {len(found)} issues")
        all_issues.extend(found)
    write_csv(out_file, all_issues, FIELDS)
    print(f"[issues] wrote {len(all_issues)} issues from {len({i['author'] for i in all_issues})} students to {out_file}")
    return out_file


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('task', help='task name, e.g. task-1')
    p.add_argument('--repos-dir', help='override repos directory (default repos/<year>)')
    p.add_argument('-q', '--quiet', action='store_true')
    context.add_cohort_arg(p)
    args = p.parse_args()
    run(args.task, context.load(args.cohort), args.repos_dir, args.quiet)


if __name__ == '__main__':
    main()
