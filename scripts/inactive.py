#!/usr/bin/env python3
"""List students with no (valid) commits for a task, and optionally check a group.

Output: data/<year>/<task>/inactive.csv with one row per repository found. Students
in the cohort students file who have no repository at all are reported separately.
"""

import argparse
import subprocess
from datetime import datetime as dt
from pathlib import Path

import context
from common import find_task_repos, read_group_file, parse_git_datetime, write_csv

FIELDS = ['author', 'repository', 'has_commits', 'commit_count', 'late_commits']


def count_valid_commits(repo_path, task, cohort):
    course_start = dt.fromisoformat(cohort.course_start_date)
    deadline = cohort.deadline(task)
    r = subprocess.run(['git', '-C', repo_path, 'log', '--pretty=format:%an|%ai', '--no-merges'],
                       capture_output=True, text=True)
    if r.returncode != 0 or not r.stdout.strip():
        return 0, 0
    n = late = 0
    for line in r.stdout.strip().split('\n'):
        if '|' not in line:
            continue
        author, when = line.split('|', 1)
        t = parse_git_datetime(when)
        if t < course_start or cohort.is_teacher(author):
            continue
        n += 1
        if deadline and t > deadline:
            late += 1
    return n, late


def run(task, cohort, group_file=None):
    repos = find_task_repos(cohort.repos_dir, task)
    results = []
    for repo_path, student in repos:
        n, late = count_valid_commits(repo_path, task, cohort)
        results.append({'author': student, 'repository': Path(repo_path).name, 'has_commits': n > 0, 'commit_count': n, 'late_commits': late})
    results.sort(key=lambda r: r['author'])
    out = cohort.task_data_dir(task) / 'inactive.csv'
    write_csv(out, results, FIELDS)

    inactive = [r['author'] for r in results if not r['has_commits']]
    late_only = [r['author'] for r in results if r['has_commits'] and r['commit_count'] == r['late_commits']]
    print(f"[inactive] {cohort.year}/{task}: {len(results)} repos, {len(inactive)} with no commits, "
          f"{len(late_only)} with commits only after the deadline -> {out}")

    by_author = {r['author']: r for r in results}
    if cohort.students_file and cohort.students_file.exists():
        roster = read_group_file(cohort.students_file)
        missing = sorted(s for s in roster if s not in by_author)
        if missing:
            print(f"[inactive] {len(missing)} students in {cohort.students_file.name} have no {task} repo: {' '.join(missing)}")

    if group_file:
        users = read_group_file(group_file)
        print(f"\nGroup check ({len(users)} users from {group_file}):")
        for u in users:
            r = by_author.get(u)
            if r is None:
                print(f"  ? {u} - no repository")
            elif not r['has_commits']:
                print(f"  ✗ {u} - NO COMMITS")
            else:
                print(f"  ✓ {u} - {r['commit_count']} commits")
    return inactive


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('task', help='task name, e.g. task-1')
    p.add_argument('-g', '--group', help='file of usernames/emails to check (e.g. your exercise group)')
    context.add_cohort_arg(p)
    args = p.parse_args()
    run(args.task, context.load(args.cohort), args.group)


if __name__ == '__main__':
    main()
