#!/usr/bin/env python3
"""Helpers shared by the ICE scripts."""

import csv
import os
from datetime import datetime as dt
from pathlib import Path


def find_task_repos(repos_dir, task_pattern):
    """Return [(repo_path, student)] for every git repo under repos_dir whose name
    ends with the task (student-first layout: repos/<year>/<student>/<student>-task-1).

    Matching is on the exact suffix ``-<task>`` so task-1 does not match task-10.
    """
    repos_dir = Path(repos_dir)
    found = []
    if not repos_dir.exists():
        return found
    for student_dir in sorted(p for p in repos_dir.iterdir() if p.is_dir()):
        for repo in sorted(p for p in student_dir.iterdir() if p.is_dir()):
            if (repo.name == task_pattern or repo.name.endswith(f'-{task_pattern}')) and (repo / '.git').exists():
                found.append((str(repo), student_dir.name))
    return found


def read_group_file(group_file):
    """Usernames from a file, one per line; an @domain suffix is stripped."""
    users = []
    with open(group_file, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                users.append(line.split('@')[0])
    return users


def parse_git_datetime(value):
    """'2025-09-26 00:10:16 +0200' -> naive datetime (timezone dropped, as before)."""
    date_part = value.split(' +')[0].split(' -')[0]
    return dt.fromisoformat(date_part)


def read_csv(path):
    """Rows as dicts; header names and cell values are whitespace-stripped so that
    hand-aligned CSVs (as some 2025 files were) still parse."""
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        try:
            header = [h.strip() for h in next(reader)]
        except StopIteration:
            return []
        return [dict(zip(header, [c.strip() for c in row])) for row in reader if row]


def write_csv(path, rows, fieldnames):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, lineterminator='\n')
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, '') for k in fieldnames})


class chdir:
    """Context manager: temporarily change working directory."""
    def __init__(self, path):
        self.path = path
        self.prev = None

    def __enter__(self):
        self.prev = os.getcwd()
        os.chdir(self.path)
        return self

    def __exit__(self, *exc):
        os.chdir(self.prev)
        return False
