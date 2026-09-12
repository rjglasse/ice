#!/usr/bin/env python3
"""Extract commit data for one task from the cohort's student repositories.

Output: data/<year>/<task>/commits.csv with one row per included commit.
Filtering (unchanged from the 2025 run, to keep years comparable):
  * merges excluded
  * commits by anyone on the teacher list excluded (substring match on git author)
  * commits before course start excluded; commits after the task deadline are KEPT and
    flagged in the after_deadline column (feedback counts them, compare.py does not)
  * the repository owner (folder name) is used as the canonical student identity, so a
    student committing under another git name/email is still counted
"""

import argparse
import subprocess
from datetime import datetime as dt
from pathlib import Path

import context
from common import find_task_repos, parse_git_datetime, write_csv

FIELDS = ['repository', 'commit', 'git_author', 'author', 'datetime', 'subject', 'insertions', 'deletions', 'total', 'after_deadline']


def get_commit_data(repo_path, student, task_name, cohort, verbose=True):
    commits = []
    total = teacher_filtered = date_filtered = late = 0
    repo_name = Path(repo_path).name
    course_start = dt.fromisoformat(cohort.course_start_date)
    deadline = cohort.deadline(task_name)

    cmd = ['git', '-C', repo_path, 'log', '--pretty=format:%H|%an|%ai|%s', '--numstat', '--no-merges']
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error processing {repo_path}: {result.stderr.strip()}")
        return commits

    lines = result.stdout.strip().split('\n')
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if '|' in line and len(line.split('|')) >= 4:
            total += 1
            commit_hash, author, datetime, subject = line.split('|', 3)
            insertions = deletions = 0
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

            when = parse_git_datetime(datetime)
            if when < course_start:
                date_filtered += 1
                continue
            after_deadline = bool(deadline and when > deadline)
            if after_deadline:
                late += 1
            if cohort.is_teacher(author):
                teacher_filtered += 1
                continue
            commits.append({
                'repository': repo_name,
                'commit': commit_hash,
                'git_author': author,
                'author': student,
                'datetime': datetime,
                'subject': subject,
                'insertions': insertions,
                'deletions': deletions,
                'total': insertions + deletions,
                'after_deadline': after_deadline,
            })
        else:
            i += 1

    if verbose and total:
        print(f"    commits: {total} total, {teacher_filtered} teacher, {date_filtered} before course start, {late} after deadline, {len(commits)} kept")
    return commits


def run(task, cohort, repos_dir=None, quiet=False):
    repos_dir = Path(repos_dir) if repos_dir else cohort.repos_dir
    out_dir = cohort.task_data_dir(task)
    out_file = out_dir / 'commits.csv'

    repos = find_task_repos(repos_dir, task)
    print(f"[commits] {cohort.year}/{task}: {len(repos)} repositories under {repos_dir}")
    all_commits = []
    for repo_path, student in repos:
        if not quiet:
            print(f"  {student}")
        all_commits.extend(get_commit_data(repo_path, student, task, cohort, verbose=not quiet))

    write_csv(out_file, all_commits, FIELDS)
    print(f"[commits] wrote {len(all_commits)} commits from {len({c['author'] for c in all_commits})} students to {out_file}")
    late = sum(1 for c in all_commits if c['after_deadline'])
    print(f"[commits] from {cohort.course_start_date}; deadline {cohort.deadline(task) or 'none'}: {late} commits after it (kept, flagged); teachers filtered: {len(cohort.teachers)} names")
    if cohort.is_provisional(task):
        print(f"[commits] WARNING: deadline for {task} is PROVISIONAL in cohorts/{cohort.year}.json - verify against the task README")
    return out_file


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('task', help='task name, e.g. task-1')
    p.add_argument('--repos-dir', help='override repos directory (default repos/<year>)')
    p.add_argument('-q', '--quiet', action='store_true', help='one line per script instead of per repo')
    context.add_cohort_arg(p)
    args = p.parse_args()
    run(args.task, context.load(args.cohort), args.repos_dir, args.quiet)


if __name__ == '__main__':
    main()
