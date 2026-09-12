#!/usr/bin/env python3
"""Post the nudge for each student as an issue in their task repository (via gh).

Reads data/<year>/<task>/nudges.csv, skips rows already marked issue_created, and
records success back into the CSV so the script can be re-run safely. Default is a
dry run; pass --post to create issues. This is the only ICE step that writes to
student repositories.
"""

import argparse
import subprocess
from pathlib import Path

import context
from common import read_csv, write_csv
from nudges import FIELDS as NUDGE_FIELDS


def find_author_repo(author, repos_dir, task):
    for pattern in (f"{author}/{author}-{task}", f"{author}/{author}_{task}", f"{author}-{task}", f"{author}_{task}"):
        p = repos_dir / pattern
        if (p / '.git').exists():
            return p
    d = repos_dir / author
    if d.is_dir():
        for repo in d.iterdir():
            if repo.is_dir() and repo.name.endswith(f"-{task}") and (repo / '.git').exists():
                return repo
    return None


def create_issue(repo_path, title, body, post):
    """Returns the issue URL on success ('' for a dry run), None on failure."""
    if not post:
        print(f"  [DRY RUN] would create issue '{title}' ({len(body)} chars)")
        return ''
    try:
        r = subprocess.run(['gh', 'issue', 'create', '--title', title, '--body', body],
                           capture_output=True, text=True, check=True, cwd=repo_path)
        url = r.stdout.strip()
        print(f"  ✅ {url}")
        return url
    except subprocess.CalledProcessError as e:
        print(f"  ❌ gh issue create failed: {e.stderr.strip()[:200]}")
        return None


def edit_issue(repo_path, url, title, body, post):
    """Replace title and body of an already posted nudge issue (after a data correction)."""
    number = url.rstrip('/').rsplit('/', 1)[-1] if url else None
    if not number:
        # older rows have no URL: find the newest issue created by the current gh user
        r = subprocess.run(['gh', 'issue', 'list', '--state', 'all', '--author', '@me', '--json', 'number', '--jq', '.[0].number'],
                           capture_output=True, text=True, cwd=repo_path)
        number = r.stdout.strip()
    if not number:
        print("  ❌ no posted issue found to edit")
        return None
    if not post:
        print(f"  [DRY RUN] would edit issue #{number} -> '{title}'")
        return ''
    try:
        r = subprocess.run(['gh', 'issue', 'edit', number, '--title', title, '--body', body],
                           capture_output=True, text=True, check=True, cwd=repo_path)
        print(f"  ✏️  {r.stdout.strip() or ('#' + number)}")
        return r.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"  ❌ gh issue edit failed: {e.stderr.strip()[:200]}")
        return None


def run(task, cohort, post=False, student=None, limit=None, edit=False):
    d = cohort.task_data_dir(task)
    nudges_file = d / 'nudges.csv'
    rows = read_csv(nudges_file)
    if not rows:
        raise SystemExit(f"[feedback] no nudges in {nudges_file}; run nudges.py first")
    for r in rows:
        r['issue_created'] = str(r.get('issue_created', 'False')).lower() == 'true'

    targets = rows
    if student:
        targets = [r for r in rows if r['author'] == student]
        if not targets:
            raise SystemExit(f"[feedback] no nudge row for {student}")
    print(f"[feedback] {cohort.year}/{task}: {len(targets)} students, repos in {cohort.repos_dir} ({'POSTING' if post else 'dry run'})")

    created = skipped = failed = 0
    for r in targets:
        if r['issue_created'] and not edit:
            skipped += 1
            continue
        if edit and not r['issue_created']:
            continue
        if limit is not None and created >= limit:
            break
        repo = find_author_repo(r['author'], cohort.repos_dir, task)
        print(f"{r['author']} ({r['classification']})")
        if not repo:
            print("  ❌ repository not found")
            failed += 1
            continue
        if edit:
            result = edit_issue(repo, r.get('issue_url', ''), r['classification'], r['nudge_message'], post)
        else:
            result = create_issue(repo, r['classification'], r['nudge_message'], post)
        if result is None:
            failed += 1
        else:
            created += 1
            if post:
                r['issue_created'] = True
                if result:
                    r['issue_url'] = result

    if post and created:
        write_csv(nudges_file, rows, NUDGE_FIELDS)
    print(f"[feedback] {'edited' if edit else 'created'} {created}, already done {skipped}, failed {failed}" + ("" if post else " (dry run)"))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('task', help='task name, e.g. task-1')
    p.add_argument('--post', action='store_true', help='actually create the issues (default: dry run)')
    p.add_argument('--dry-run', action='store_true', help='(default) kept for backwards compatibility')
    p.add_argument('--student', help='only this student')
    p.add_argument('--limit', type=int, help='create at most N issues (useful for a pilot)')
    p.add_argument('--edit', action='store_true', help='edit already posted issues instead of creating (after a correction); combine with --student')
    context.add_cohort_arg(p)
    args = p.parse_args()
    run(args.task, context.load(args.cohort), post=args.post and not args.dry_run, student=args.student, limit=args.limit, edit=args.edit)


if __name__ == '__main__':
    main()
